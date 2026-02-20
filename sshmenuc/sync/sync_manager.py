"""SyncManager - orchestrates remote config sync lifecycle.

State machine:
  NO_SYNC      -> sync.json absent or remote_url empty
  SYNC_OK      -> pull/push succeeded
  SYNC_OFFLINE -> remote unreachable, using local encrypted backup
  LOCAL_ONLY   -> offline + no local backup (emergency fallback)
"""

import difflib
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional

from .crypto import decrypt_config, encrypt_config
from .git_remote import (
    PullStatus,
    ensure_repo_initialized,
    is_remote_reachable,
    pull_remote,
    push_remote,
)
from .passphrase_cache import get_or_prompt, has_passphrase, set_passphrase


class SyncState(Enum):
    NO_SYNC = auto()      # No remote configured
    SYNC_OK = auto()      # Last operation succeeded
    SYNC_OFFLINE = auto() # Remote unreachable, using local backup
    LOCAL_ONLY = auto()   # Offline + no local backup


class SyncManager:
    """Manages the full sync lifecycle for sshmenuc config."""

    def __init__(self, config_file: str, sync_config_path: Optional[str] = None,
                 sync_cfg_override: Optional[dict] = None):
        self._config_file = config_file
        self._enc_path = config_file + ".enc"

        if sync_config_path is None:
            sync_dir = os.path.dirname(config_file)
            sync_config_path = os.path.join(sync_dir, "sync.json")
        self._sync_config_path = sync_config_path

        # If a config dict is injected (multi-context mode), bypass disk reads.
        self._sync_cfg_override = sync_cfg_override

        self._state = SyncState.NO_SYNC
        self._sync_cfg: dict = {}

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def startup_pull(self) -> SyncState:
        """Pull from remote at startup and update local config if needed.

        Returns:
            The resulting SyncState after the operation.
        """
        self._sync_cfg = self._sync_cfg_override if self._sync_cfg_override is not None else self._load_sync_config()
        if not self._sync_cfg.get("remote_url"):
            self._state = SyncState.NO_SYNC
            return self._state

        if not self._sync_cfg.get("auto_pull", True):
            self._state = SyncState.SYNC_OK
            return self._state

        if not is_remote_reachable(self._sync_cfg["remote_url"]):
            return self._handle_offline()

        if not ensure_repo_initialized(self._sync_cfg):
            return self._handle_offline()

        passphrase = get_or_prompt("Enter sync passphrase: ")
        pull_result = pull_remote(self._sync_cfg)

        if pull_result.status == PullStatus.OFFLINE:
            return self._handle_offline()

        if pull_result.status == PullStatus.NO_CHANGE:
            self._state = SyncState.SYNC_OK
            return self._state

        # Status OK: we have remote encrypted bytes
        remote_enc = pull_result.remote_enc_bytes
        if not remote_enc:
            self._state = SyncState.SYNC_OK
            return self._state

        try:
            remote_data = decrypt_config(remote_enc, passphrase)
        except Exception as e:
            logging.error(f"[SYNC] Cannot decrypt remote config: {e}")
            self._state = SyncState.SYNC_OFFLINE
            return self._state

        local_hash = self._hash_config_file()
        last_hash = self._sync_cfg.get("last_config_hash", "")

        if local_hash == last_hash:
            # Local unchanged since last sync -> safe to overwrite with remote
            self._write_config(remote_data)
            self._update_local_enc_backup()
            self._save_sync_meta(local_hash=self._hash_config_file(), status="ok")
            self._state = SyncState.SYNC_OK
            return self._state

        # Both local and remote changed: conflict
        local_data = self._read_config()
        resolution = self._resolve_conflict(local_data, remote_data)

        if resolution == "remote":
            self._write_config(remote_data)
            self._update_local_enc_backup()
            self._push_to_remote(passphrase)
            self._save_sync_meta(local_hash=self._hash_config_file(), status="conflict_resolved_remote")
        elif resolution == "local":
            self._update_local_enc_backup()
            self._push_to_remote(passphrase)
            self._save_sync_meta(local_hash=local_hash, status="conflict_resolved_local")
        else:
            # Abort: stay with local, no push
            self._save_sync_meta(local_hash=local_hash, status="conflict_aborted")

        self._state = SyncState.SYNC_OK
        return self._state

    def post_save_push(self) -> None:
        """Encrypt and push config after a local save.

        Always updates the local encrypted backup.
        Push is best-effort: failures are logged but do not raise.
        """
        if self._state == SyncState.NO_SYNC:
            return

        if not self._sync_cfg.get("remote_url"):
            return

        if not self._update_local_enc_backup():
            return

        if not self._sync_cfg.get("auto_push", True):
            return

        if not has_passphrase():
            return  # No passphrase in cache, skip silent push

        passphrase = get_or_prompt()
        try:
            with open(self._enc_path, "rb") as f:
                enc_bytes = f.read()
        except OSError as e:
            logging.warning(f"[SYNC] Cannot read local backup: {e}")
            return

        if push_remote(self._sync_cfg, enc_bytes):
            self._save_sync_meta(local_hash=self._hash_config_file(), status="ok")
            self._state = SyncState.SYNC_OK
            self._print("[SYNC] Config sincronizzata con il repo remoto", color="green")
        else:
            self._state = SyncState.SYNC_OFFLINE
            self._print("[SYNC] Push fallito - backup locale aggiornato", color="yellow")

    def export_config(self, output_path: str) -> None:
        """Decrypt the local encrypted backup and export config in plaintext.

        Args:
            output_path: File path to write plaintext JSON, or '-' for stdout.
        """
        if not os.path.isfile(self._enc_path):
            print(f"[SYNC] Nessun backup locale criptato trovato: {self._enc_path}", file=sys.stderr)
            return

        passphrase = get_or_prompt("Enter sync passphrase to export: ")
        try:
            with open(self._enc_path, "rb") as f:
                enc_bytes = f.read()
            data = decrypt_config(enc_bytes, passphrase)
        except Exception as e:
            print(f"[SYNC] Errore decrittografia: {e}", file=sys.stderr)
            return

        plaintext = json.dumps(data, indent=4)

        if output_path == "-":
            print(plaintext)
        else:
            with open(output_path, "w") as f:
                f.write(plaintext)
            print(f"[SYNC] Config esportata in chiaro: {output_path}")

    def get_state(self) -> SyncState:
        """Return the current sync state."""
        return self._state

    def get_status_label(self) -> str:
        """Return a short human-readable sync status for display in the menu header."""
        labels = {
            SyncState.NO_SYNC: "",
            SyncState.SYNC_OK: "SYNC:OK",
            SyncState.SYNC_OFFLINE: "SYNC:OFFLINE",
            SyncState.LOCAL_ONLY: "SYNC:NO-BACKUP",
        }
        return labels.get(self._state, "")

    def setup_wizard(self) -> bool:
        """Interactive guided setup to create sync.json from scratch.

        Guides the user through entering remote URL and optional settings,
        then writes ~/.config/sshmenuc/sync.json and offers an immediate
        first sync (push of the current local config).

        Returns:
            True if setup completed and sync.json was written, False if aborted.
        """
        print("\n=== Configurazione Sync Remoto ===")
        print("Configura la sincronizzazione del config su un repo Git privato.")
        print("Il file config verrà cifrato con AES-256-GCM prima di ogni push.")
        print("Premi Invio senza digitare per annullare.\n")

        remote_url = input("URL repo remoto (es. git@github.com:utente/repo.git): ").strip()
        if not remote_url:
            print("Setup annullato.")
            return False

        branch = input("Branch [main]: ").strip() or "main"

        default_repo_path = os.path.expanduser("~/.config/sshmenuc/sync_repo")
        repo_path_input = input(f"Percorso repo locale [{default_repo_path}]: ").strip()
        sync_repo_path = repo_path_input or default_repo_path

        sync_cfg = {
            "version": 1,
            "remote_url": remote_url,
            "branch": branch,
            "sync_repo_path": sync_repo_path,
            "auto_pull": True,
            "auto_push": True,
        }

        # Ensure directory exists
        sync_dir = os.path.dirname(self._sync_config_path)
        os.makedirs(sync_dir, exist_ok=True)

        try:
            with open(self._sync_config_path, "w") as f:
                json.dump(sync_cfg, f, indent=4)
        except OSError as e:
            print(f"Errore scrittura sync.json: {e}")
            return False

        self._sync_cfg = sync_cfg
        print(f"\nSync configurato. File salvato in: {self._sync_config_path}")

        # Offer immediate first sync (push current local config)
        answer = input("\nEseguire subito la prima sincronizzazione (push)? [s/N]: ").strip().lower()
        if answer == "s":
            import getpass as _getpass
            passphrase = _getpass.getpass("Scegli una passphrase per cifrare il config: ")
            passphrase2 = _getpass.getpass("Conferma passphrase: ")
            if passphrase != passphrase2:
                print("Le passphrase non coincidono. Sync annullato.")
                print("Puoi riprovare premendo [s] dal menu principale.")
                return True  # sync.json was still written

            set_passphrase(passphrase)

            if not ensure_repo_initialized(sync_cfg):
                print("[SYNC] Impossibile raggiungere il repo remoto. Verifica l'URL e la chiave SSH.")
                print("Sync.json è stato salvato - riprova premendo [s] dal menu.")
                return True

            print("Cifratura e push in corso...")
            enc_bytes = encrypt_config(self._read_config() or {}, passphrase)
            with open(self._enc_path, "wb") as f:
                f.write(enc_bytes)

            if push_remote(sync_cfg, enc_bytes):
                self._save_sync_meta(local_hash=self._hash_config_file(), status="ok")
                self._state = SyncState.SYNC_OK
                print("[SYNC] Prima sincronizzazione completata.")
            else:
                print("[SYNC] Push fallito. Backup locale cifrato creato.")
                self._state = SyncState.SYNC_OFFLINE
        else:
            self._state = SyncState.NO_SYNC  # sync.json written but no pull/push yet

        return True

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _load_sync_config(self) -> dict:
        """Load sync.json from disk. Returns empty dict if absent."""
        try:
            with open(self._sync_config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_sync_meta(self, local_hash: str, status: str) -> None:
        """Persist last_config_hash and last_sync_status.

        In override mode (multi-context) the caller is responsible for persisting
        metadata via ContextManager; we only update the in-memory dict here.
        """
        self._sync_cfg["last_config_hash"] = local_hash
        self._sync_cfg["last_sync"] = datetime.now(timezone.utc).isoformat()
        self._sync_cfg["last_sync_status"] = status
        if self._sync_cfg_override is not None:
            return  # Metadata persistence handled by ContextManager
        try:
            with open(self._sync_config_path, "w") as f:
                json.dump(self._sync_cfg, f, indent=4)
        except OSError as e:
            logging.warning(f"[SYNC] Cannot save sync metadata: {e}")

    def _update_local_enc_backup(self) -> bool:
        """Encrypt current config.json and write to local .enc backup.

        Returns:
            True if backup was successfully written, False otherwise.
        """
        if not has_passphrase() and not self._sync_cfg.get("remote_url"):
            return False  # No passphrase and no remote: nothing to encrypt

        passphrase = get_or_prompt()
        data = self._read_config()
        if data is None:
            return False

        try:
            enc_bytes = encrypt_config(data, passphrase)
            with open(self._enc_path, "wb") as f:
                f.write(enc_bytes)
            return True
        except Exception as e:
            logging.warning(f"[SYNC] Cannot write local encrypted backup: {e}")
            return False

    def _read_config(self) -> Optional[dict]:
        """Read the plaintext config.json."""
        try:
            with open(self._config_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"[SYNC] Cannot read config file: {e}")
            return None

    def _write_config(self, data: dict) -> None:
        """Overwrite config.json with new data (after remote pull)."""
        try:
            with open(self._config_file, "w") as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            logging.error(f"[SYNC] Cannot write config file: {e}")

    def _hash_config_file(self) -> str:
        """Return SHA-256 hex digest of the current config.json content."""
        try:
            with open(self._config_file, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return ""

    def _push_to_remote(self, passphrase: str) -> bool:
        """Encrypt and push local config to remote."""
        data = self._read_config()
        if data is None:
            return False
        try:
            enc_bytes = encrypt_config(data, passphrase)
            return push_remote(self._sync_cfg, enc_bytes)
        except Exception as e:
            logging.warning(f"[SYNC] Push failed: {e}")
            return False

    def _handle_offline(self) -> SyncState:
        """Handle the case where the remote is unreachable."""
        if os.path.isfile(self._enc_path):
            self._state = SyncState.SYNC_OFFLINE
            self._print("[SYNC] Remote non raggiungibile - uso backup locale criptato", color="yellow")
        else:
            self._state = SyncState.LOCAL_ONLY
            self._print("[SYNC] Remote non raggiungibile e nessun backup locale trovato", color="red")
        return self._state

    def _resolve_conflict(self, local_data: dict, remote_data: dict) -> str:
        """Show diff and ask user how to resolve a conflict.

        Args:
            local_data: Local config dict.
            remote_data: Remote config dict.

        Returns:
            One of: 'local', 'remote', 'abort'
        """
        local_text = json.dumps(local_data, indent=4).splitlines(keepends=True)
        remote_text = json.dumps(remote_data, indent=4).splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            local_text, remote_text,
            fromfile="locale", tofile="remoto", lineterm=""
        ))

        print("\n[SYNC] CONFLITTO - entrambe le versioni sono state modificate\n")
        if diff:
            for line in diff[:50]:  # Show at most 50 diff lines
                print(line)
            if len(diff) > 50:
                print(f"... e altre {len(diff) - 50} righe")
        else:
            print("(nessuna differenza rilevata nel contenuto)")

        while True:
            choice = input("\n[L] Usa locale  [R] Usa remoto  [A] Abort > ").strip().lower()
            if choice == "l":
                return "local"
            if choice == "r":
                return "remote"
            if choice == "a":
                return "abort"
            print("Scelta non valida. Inserisci L, R o A.")

    @staticmethod
    def _print(message: str, color: str = "white") -> None:
        """Print a message using clint colors if available, otherwise plain print."""
        try:
            from clint.textui import puts
            from clint.textui.colored import green, red, yellow

            color_fn = {"green": green, "yellow": yellow, "red": red}.get(color, str)
            puts(color_fn(message))
        except ImportError:
            print(message)
