"""
Menu navigation management.
"""
import os
import logging
from typing import List, Any, Dict, Optional, Union
import readchar
from clint.textui import puts, colored

from .base import BaseSSHMenuC
from .launcher import SSHLauncher
from .config import ConnectionManager
from .config_editor import ConfigEditor
from ..ui.display import MenuDisplay
from ..utils.helpers import get_current_user
from ..sync import SyncManager, SyncState


# Constants
MAX_MARKED_SELECTIONS = 6  # Maximum number of hosts that can be marked for multi-connection


class ConnectionNavigator(BaseSSHMenuC):
    """Manages navigation through the connection menu.

    Provides interactive keyboard navigation with support for multiple selection
    and tmux integration for group connections.
    """

    def __init__(self, config_file: str, sync_cfg_override: Optional[dict] = None,
                 context_manager=None, active_context: Optional[str] = None):
        super().__init__(config_file)
        self.load_config()
        self.marked_indices = set()
        self.display = MenuDisplay()
        self.config_manager = ConnectionManager(config_file)
        self.editor = ConfigEditor(self.config_manager)
        # Multi-context support
        self._context_manager = context_manager
        self._active_context = active_context
        # Sync setup: install post-save hook and run startup pull
        self.sync_manager = SyncManager(config_file, sync_cfg_override=sync_cfg_override)
        self.config_manager._post_save_hook = lambda: self.sync_manager.post_save_push()
        # In multi-context mode, wire the metadata callback so SyncManager can
        # persist last_sync/last_config_hash to contexts.json via ContextManager.
        if context_manager is not None and active_context:
            self.sync_manager._sync_meta_callback = lambda ts, h: context_manager.update_context_meta(
                active_context, ts, h
            )
        self._run_startup_pull()
        self._wire_encrypted_io()

    def _run_startup_pull(self) -> None:
        """Pull config from remote at startup and show sync status."""
        state = self.sync_manager.startup_pull()
        data = self.sync_manager.get_config_data()
        if data is not None:
            # Zero-plaintext mode: config is in memory, set directly without file I/O.
            # Normalize old-format (no "targets" key) data that may come from legacy .enc files.
            data = self._normalize_config(data)
            self.set_config(data)
            self.config_manager.set_config(data)
        elif state == SyncState.SYNC_OK:
            # Backward compat: no in-memory data (e.g. first run, no .enc yet)
            self.load_config()
            self.config_manager.load_config()
        if state == SyncState.SYNC_OFFLINE:
            puts(colored.yellow("[SYNC] Remote non raggiungibile - uso backup locale criptato"))
        elif state == SyncState.LOCAL_ONLY:
            puts(colored.red("[SYNC] Remote non raggiungibile e nessun backup locale trovato"))
    
    def _wire_encrypted_io(self) -> None:
        """Install encrypted I/O hooks when sync is configured (zero-plaintext mode).

        After this, load_config() and save_config() on both the navigator and the
        config_manager bypass the plaintext file and work entirely through
        SyncManager's in-memory config backed by the .enc file.

        Also removes any stale plaintext config file once in-memory data is verified.
        """
        if not self.sync_manager._sync_cfg.get("remote_url"):
            return  # No sync configured: keep using plaintext file (backward compat)

        sync_mgr = self.sync_manager

        def _enc_load():
            return sync_mgr.get_config_data()

        def _enc_save(data: dict) -> None:
            # Store in SyncManager memory; post_save_push() will encrypt to .enc
            sync_mgr._config_data = data

        self._encrypted_load = _enc_load
        self._encrypted_save = _enc_save
        self.config_manager._encrypted_load = _enc_load
        self.config_manager._encrypted_save = _enc_save

        # Remove stale plaintext file now that we have verified in-memory data.
        # Only deletes if we actually loaded from .enc (get_config_data() is not None).
        if (sync_mgr.get_config_data() is not None
                and self.config_file
                and os.path.isfile(self.config_file)):
            try:
                os.unlink(self.config_file)
                logging.debug("[SYNC] Plaintext config removed: %s", self.config_file)
            except OSError as e:
                logging.warning("[SYNC] Cannot remove plaintext config: %s", e)

    def validate_config(self) -> bool:
        """Validate the configuration for navigation.

        Returns:
            True if config is valid dict with 'targets' key, False otherwise
        """
        return isinstance(self.config_data, dict) and "targets" in self.config_data
    
    def navigate(self):
        """Main navigation loop.

        Handles keyboard input for menu navigation:
        - Arrow keys: Move selection up/down/left/right
        - Space: Toggle selection for multi-host connection
        - Enter: Launch connection(s)
        - q: Quit application
        """
        current_path = []
        selected_target = 0
        
        while True:
            num_targets = self.count_elements(current_path)
            self.print_menu(selected_target, current_path)
            key = readchar.readkey()
            
            if key == "q":
                break
            elif key == readchar.key.DOWN:
                if selected_target < num_targets - 1 or num_targets == 0:
                    selected_target += 1
            elif key == readchar.key.UP:
                if selected_target > 0:
                    selected_target -= 1
            elif key == readchar.key.LEFT:
                self.marked_indices.clear()
                self.move_left(current_path)
                selected_target = 0
            elif key == " ":
                self._handle_selection(current_path, selected_target)
            elif key == readchar.key.ENTER:
                self._handle_enter(current_path, selected_target)
            elif key == "a":
                self._handle_add(current_path, selected_target)
            elif key == "e":
                self._handle_edit(current_path, selected_target)
            elif key == "d":
                self._handle_delete(current_path, selected_target)
            elif key == "r":
                self._handle_rename(current_path, selected_target)
            elif key == "s":
                self._handle_sync_status()
            elif key == "x":
                self._handle_context_switch()
            elif key == "c" and self._context_manager is not None:
                self._handle_context_manage()
    
    def _handle_selection(self, current_path: List[Any], selected_target: int):
        """Handle selection toggle with space key.

        Args:
            current_path: Current navigation path
            selected_target: Currently selected target index
        """
        node = self.get_node(current_path)
        if isinstance(node, list):
            if selected_target in self.marked_indices:
                self.marked_indices.remove(selected_target)
            else:
                if len(self.marked_indices) < MAX_MARKED_SELECTIONS:
                    self.marked_indices.add(selected_target)
                else:
                    puts(colored.red(f"Maximum {MAX_MARKED_SELECTIONS} selections allowed"))
    
    def _handle_enter(self, current_path: List[Any], selected_target: int):
        """Handle enter key press.

        Args:
            current_path: Current navigation path
            selected_target: Currently selected target index
        """
        node = self.get_node(current_path)
        
        if isinstance(node, list) and self.marked_indices:
            self._launch_multiple_hosts(node)
        else:
            self._handle_single_selection(node, selected_target, current_path)
    
    def _launch_multiple_hosts(self, node: List[Any]):
        """Launch multiple host connections in tmux split panes.

        Args:
            node: List of host entries to connect to
        """
        selected_hosts = []
        for i in sorted(self.marked_indices):
            if 0 <= i < len(node):
                item = node[i]
                if isinstance(item, dict) and ("host" in item or "friendly" in item):
                    host = item.get("host", item.get("friendly"))
                    user = item.get("user", get_current_user())
                    ident = item.get("certkey", item.get("identity_file", None))
                    extra_args = item.get("extra_args")
                    selected_hosts.append({"host": host, "user": user, "identity": ident, "extra_args": extra_args})
        
        if selected_hosts:
            SSHLauncher.launch_group(selected_hosts)
            self.marked_indices.clear()
        else:
            puts(colored.red("No valid hosts selected"))
    
    def _handle_single_selection(self, node: Any, selected_target: int, current_path: List[Any]):
        """Handle single selection (no marked hosts).

        Args:
            node: Current node (dict or list)
            selected_target: Index of selected item
            current_path: Current navigation path
        """
        if isinstance(node, list):
            if "friendly" in node[selected_target]:
                host = node[selected_target]["host"]
                user = node[selected_target].get("user", get_current_user())
                identity = node[selected_target].get("certkey")
                port = node[selected_target].get("port", 22)
                extra_args = node[selected_target].get("extra_args")
                launcher = SSHLauncher(host, user, port, identity, extra_args)
                launcher.launch()
            else:
                current_path.extend([selected_target, 0])
        else:
            current_path.append(selected_target)
    
    def get_node(self, path: List[Any]):
        """Return the current node at the given path.

        Args:
            path: Navigation path as list of indices

        Returns:
            The node at the specified path (dict, list, or host entry)
        """
        targets = self.config_data.get("targets", [])
        aggregated: Dict[str, Any] = {}
        for t in targets:
            if isinstance(t, dict):
                for k, v in t.items():
                    aggregated[k] = v
        
        if not path:
            return aggregated
        
        cur: Union[dict, list, Any] = aggregated
        for item in path:
            if isinstance(cur, dict):
                keys = list(cur.keys())
                if 0 <= item < len(keys):
                    key = keys[item]
                    cur = cur[key]
                else:
                    return cur
            elif isinstance(cur, list):
                if 0 <= item < len(cur):
                    cur = cur[item]
                else:
                    return cur
            else:
                return cur
        return cur
    
    def get_previous_node(self, path: List[Any]):
        """Return the previous node in the path.

        Args:
            path: Navigation path as list of indices

        Returns:
            The node at path[:-1]

        Raises:
            KeyError: If a key in the path is not found
            TypeError: If node type is not dict or list
        """
        # Aggregate targets like get_node() does
        targets = self.config_data.get("targets", [])
        aggregated: Dict[str, Any] = {}
        for t in targets:
            if isinstance(t, dict):
                for k, v in t.items():
                    aggregated[k] = v

        node: Union[dict, list] = aggregated  # Start from aggregated
        for item in path[:-1]:
            if isinstance(node, dict):
                keys = list(node.keys())
                if 0 <= item < len(keys):
                    key = keys[item]
                    if key in node:
                        node = node[key]
                    else:
                        raise KeyError(f"Key '{key}' not found in dictionary.")
            elif isinstance(node, list):
                if item < len(node):
                    node = node[item]
            else:
                raise TypeError(f"Unsupported type: {type(node)}")
        return node
    
    def count_elements(self, current_path: List[Any]) -> int:
        """Count elements in the current node.

        Args:
            current_path: Current navigation path

        Returns:
            Number of items in the current node
        """
        node = self.get_node(current_path)
        if isinstance(node, dict):
            return len(node)
        elif isinstance(node, list):
            return sum(1 for item in node if isinstance(item, dict))
        else:
            return 0
    
    def move_left(self, current_path: List[Any]):
        """Handle left navigation (go back).

        Args:
            current_path: Current navigation path (modified in place)
        """
        if current_path:
            if isinstance(self.get_node(current_path), dict):
                current_path.pop()
            elif isinstance(self.get_node(current_path), list) and len(current_path) > 1:
                if isinstance(self.get_previous_node(current_path), dict):
                    current_path.pop()
                    current_path.pop()
            elif len(current_path) == 1:
                current_path.clear()
            elif current_path[-1] == 0:
                current_path.pop()
            else:
                current_path[-1] -= 1
    
    def print_menu(self, selected_target: int, current_path: List[Any]):
        """Print the current menu.

        Args:
            selected_target: Index of the currently selected item
            current_path: Current navigation path
        """
        self.display.clear_screen()
        self.display.print_instructions(
            sync_label=self.sync_manager.get_status_label(),
            context_label=self._active_context or "",
        )

        logging.debug("selected_target: %d", selected_target)
        logging.debug("current_path: %s", current_path)
        
        current_node = self.get_node(current_path)
        logging.debug("current_node_type: %s", type(current_node))
        logging.debug("current_node: %s", current_node)

        level = len(current_path) if isinstance(current_node, dict) else len(current_path) + 1
        self.display.print_table(current_node, selected_target, self.marked_indices, level)

    def _handle_add(self, current_path: List[Any], selected_target: int):
        """Handle 'a' key - Add target or connection based on context."""
        node = self.get_node(current_path)
        if isinstance(node, dict) and not current_path:
            if self.editor.add_target():
                self.load_config()
                input("\nPress Enter to continue...")
        elif isinstance(node, list) and current_path:
            targets = self.config_data.get("targets", [])
            aggregated = {}
            for t in targets:
                if isinstance(t, dict):
                    for k, v in t.items():
                        aggregated[k] = v
            target_keys = list(aggregated.keys())
            if len(current_path) >= 1 and 0 <= current_path[0] < len(target_keys):
                target_name = target_keys[current_path[0]]
                if self.editor.add_connection(target_name):
                    self.load_config()
                    input("\nPress Enter to continue...")

    def _handle_edit(self, current_path: List[Any], selected_target: int):
        """Handle 'e' key - Edit connection."""
        node = self.get_node(current_path)
        if isinstance(node, list) and 0 <= selected_target < len(node):
            connection = node[selected_target]
            if isinstance(connection, dict) and "friendly" in connection:
                targets = self.config_data.get("targets", [])
                aggregated = {}
                for t in targets:
                    if isinstance(t, dict):
                        for k, v in t.items():
                            aggregated[k] = v
                target_keys = list(aggregated.keys())
                if len(current_path) >= 1 and 0 <= current_path[0] < len(target_keys):
                    target_name = target_keys[current_path[0]]
                    if self.editor.edit_connection(target_name, selected_target, connection):
                        self.load_config()
                        input("\nPress Enter to continue...")

    def _handle_delete(self, current_path: List[Any], selected_target: int):
        """Handle 'd' key - Delete target or connection based on context."""
        node = self.get_node(current_path)
        if isinstance(node, dict) and not current_path:
            target_keys = list(node.keys())
            if 0 <= selected_target < len(target_keys):
                target_name = target_keys[selected_target]
                if self.editor.delete_target(target_name):
                    self.load_config()
                    input("\nPress Enter to continue...")
        elif isinstance(node, list) and 0 <= selected_target < len(node):
            connection = node[selected_target]
            if isinstance(connection, dict) and "friendly" in connection:
                targets = self.config_data.get("targets", [])
                aggregated = {}
                for t in targets:
                    if isinstance(t, dict):
                        for k, v in t.items():
                            aggregated[k] = v
                target_keys = list(aggregated.keys())
                if len(current_path) >= 1 and 0 <= current_path[0] < len(target_keys):
                    target_name = target_keys[current_path[0]]
                    if self.editor.delete_connection(target_name, selected_target, connection):
                        self.load_config()
                        input("\nPress Enter to continue...")

    def _handle_rename(self, current_path: List[Any], selected_target: int):
        """Handle 'r' key - Rename target."""
        node = self.get_node(current_path)
        if isinstance(node, dict) and not current_path:
            target_keys = list(node.keys())
            if 0 <= selected_target < len(target_keys):
                target_name = target_keys[selected_target]
                if self.editor.rename_target(target_name):
                    self.load_config()
                    input("\nPress Enter to continue...")

    def _handle_sync_status(self) -> None:
        """Handle 's' key - Show sync status panel, allow manual sync or guided setup."""
        state = self.sync_manager.get_state()
        label = self.sync_manager.get_status_label()
        cfg = self.sync_manager._sync_cfg

        puts(colored.cyan("\n=== Sync Status ==="))
        puts(colored.white(f"Stato: {label or 'NO SYNC'}"))

        remote_url = cfg.get("remote_url", "")
        if remote_url:
            # Mask credentials in URL for display
            display_url = remote_url.split("@")[-1] if "@" in remote_url else remote_url
            puts(colored.white(f"Remote: {display_url}"))
        else:
            puts(colored.yellow("Remote: non configurato"))

        last_sync = cfg.get("last_sync", "mai")
        puts(colored.white(f"Ultimo sync: {last_sync}"))

        if state == SyncState.NO_SYNC:
            puts(colored.white("\n[s] Configura sync remoto  [Invio] Chiudi"))
            choice = input("> ").strip().lower()
            if choice == "s":
                configured = self.sync_manager.setup_wizard()
                if configured:
                    # Reload state after wizard (may have changed to SYNC_OK/SYNC_OFFLINE)
                    self.load_config()
                    self.config_manager.load_config()
            return

        puts(colored.white("\n[m] Sync manuale  [Invio] Chiudi"))
        choice = input("> ").strip().lower()
        if choice == "m":
            puts(colored.yellow("Sync in corso..."))
            self.sync_manager.startup_pull()
            self.load_config()
            self.config_manager.load_config()
            puts(colored.green("Sync completato."))
        input("\nPress Enter to continue...")

    def _switch_to_context(self, new_name: str) -> bool:
        """Load and activate a context by name.

        Builds a temporary SyncManager, runs startup_pull, and on success
        replaces the navigator's active context, sync manager, config manager,
        and config editor with those of the new context.

        Args:
            new_name: Name of the context to switch to.

        Returns:
            True if the switch succeeded, False if startup_pull failed.
        """
        puts(colored.yellow(f"[CTX] Caricamento contesto '{new_name}'..."))

        sync_cfg = self._context_manager.get_sync_cfg(new_name)
        self._context_manager.ensure_context_dir(new_name)
        new_config_file = self._context_manager.get_config_file(new_name)
        temp_sm = SyncManager(new_config_file, sync_cfg_override=sync_cfg)

        state = temp_sm.startup_pull()

        if state not in (SyncState.SYNC_OK, SyncState.SYNC_OFFLINE, SyncState.NO_SYNC):
            puts(colored.red(f"[CTX] Impossibile caricare '{new_name}' - fallback su '{self._active_context}'"))
            return False

        # Accept SYNC_OK, SYNC_OFFLINE, NO_SYNC (context may not have sync yet)
        prev_context = self._active_context
        self._active_context = new_name
        self._context_manager.set_active(new_name)
        self.config_file = new_config_file
        self.sync_manager = temp_sm
        self.config_manager = ConnectionManager(new_config_file)
        self.editor = ConfigEditor(self.config_manager)
        self.config_manager._post_save_hook = lambda: self.sync_manager.post_save_push()
        self._wire_encrypted_io()
        data = self.sync_manager.get_config_data()
        if data is not None:
            data = self._normalize_config(data)
            self.set_config(data)
            self.config_manager.set_config(data)
        else:
            self.load_config()
            self.config_manager.load_config()
        puts(colored.green(f"[CTX] Contesto cambiato: {prev_context} → {new_name}"))
        return True

    def _handle_context_switch(self) -> None:
        """Handle 'x' key - Switch to a different context (profile).

        Shows all available contexts, lets the user select one, pulls and
        decrypts it from the remote, and reloads the UI. If the pull fails,
        falls back to the previous context silently.
        """
        if self._context_manager is None:
            puts(colored.yellow("[CTX] Nessun contesto configurato (contexts.json assente)"))
            input("\nPress Enter to continue...")
            return

        names = self._context_manager.list_contexts()
        if not names:
            puts(colored.yellow("[CTX] Nessun contesto disponibile in contexts.json"))
            input("\nPress Enter to continue...")
            return

        puts(colored.cyan("\n=== Switch Contesto ==="))
        for i, name in enumerate(names, 1):
            marker = " *" if name == self._active_context else ""
            puts(colored.white(f"  [{i}] {name}{marker}"))
        puts(colored.white("\n[Invio] Annulla"))

        raw = input("> ").strip()
        if not raw:
            return

        try:
            idx = int(raw) - 1
        except ValueError:
            return

        if not (0 <= idx < len(names)):
            return

        new_name = names[idx]
        if new_name == self._active_context:
            puts(colored.yellow(f"[CTX] Contesto '{new_name}' già attivo"))
            input("\nPress Enter to continue...")
            return

        self._switch_to_context(new_name)
        input("\nPress Enter to continue...")

    def _handle_context_manage(self) -> None:
        """Handle 'c' key - Add a new context or manage an existing one."""
        names = self._context_manager.list_contexts()

        puts(colored.cyan("\n=== Gestione Contesti ==="))
        puts(colored.white("  [1] Nuovo contesto"))
        for i, name in enumerate(names, 2):
            marker = " *" if name == self._active_context else ""
            puts(colored.white(f"  [{i}] {name}{marker}"))
        puts(colored.white("\n[Invio] Annulla"))

        raw = input("> ").strip()
        if not raw:
            return

        if raw == "1":
            self._handle_new_context()
            return

        try:
            idx = int(raw) - 2
        except ValueError:
            return

        if 0 <= idx < len(names):
            self._handle_context_actions(names[idx])

    def _handle_context_actions(self, name: str) -> None:
        """Sub-menu for a selected context: edit sync params or reimport from plaintext."""
        marker = " *" if name == self._active_context else ""
        puts(colored.cyan(f"\n--- {name}{marker} ---"))
        puts(colored.white("  [m] Modifica parametri sync"))
        puts(colored.white("  [i] Reimport da file in chiaro"))
        puts(colored.white("\n[Invio] Annulla"))

        choice = input("> ").strip().lower()
        if choice == "m":
            self._handle_edit_context_sync(name)
        elif choice == "i":
            self._handle_reimport_context(name)

    def _handle_reimport_context(self, name: str) -> None:
        """Reimport config from a plaintext JSON file into the context's encrypted store.

        Reads a JSON file, encrypts it with the cached passphrase, writes the
        local .enc backup, updates contexts.json metadata, and optionally pushes
        to the remote repo.  Offers to delete the source plaintext file (default: yes).
        """
        import hashlib as _hashlib
        import json as _json
        from datetime import datetime, timezone
        from ..sync.crypto import encrypt_config
        from ..sync.passphrase_cache import get_or_prompt
        from ..sync.git_remote import ensure_repo_initialized, push_remote

        puts(colored.cyan(f"\n--- Reimport config: {name} ---"))

        src_path = input("Percorso file in chiaro (JSON): ").strip()
        if not src_path:
            return

        src_path = os.path.expanduser(src_path)
        if not os.path.isfile(src_path):
            puts(colored.red(f"[ERR] File non trovato: {src_path}"))
            input("\nPress Enter to continue...")
            return

        try:
            with open(src_path, "r") as f:
                config_data = _json.load(f)
        except (ValueError, OSError) as e:
            puts(colored.red(f"[ERR] Impossibile leggere il file: {e}"))
            input("\nPress Enter to continue...")
            return

        try:
            passphrase = get_or_prompt("Passphrase sync: ")
            enc_bytes = encrypt_config(config_data, passphrase)
        except Exception as e:
            puts(colored.red(f"[ERR] Cifratura fallita: {e}"))
            input("\nPress Enter to continue...")
            return

        # Save .enc locally
        enc_path = self._context_manager.get_enc_file(name)
        self._context_manager.ensure_context_dir(name)
        with open(enc_path, "wb") as f:
            f.write(enc_bytes)

        # Compute hash consistent with _hash_config_file() (uses json.dumps indent=4)
        content_hash = _hashlib.sha256(
            _json.dumps(config_data, indent=4).encode()
        ).hexdigest()
        self._context_manager.update_context_meta(
            name,
            datetime.now(timezone.utc).isoformat(),
            content_hash,
        )

        # If this is the active context, update in-memory state immediately
        if name == self._active_context:
            self.sync_manager._config_data = config_data
            self.sync_manager._sync_cfg["last_config_hash"] = content_hash
            self.set_config(self._normalize_config(config_data))
            self.config_manager.set_config(self._normalize_config(config_data))
            puts(colored.green(f"[CTX] Config '{name}' ricaricata in memoria."))
        else:
            puts(colored.green(f"[CTX] Backup cifrato aggiornato per '{name}'."))

        # Offer to delete source file (default: yes)
        del_src = input(f"\nEliminare il file sorgente? [S/n]: ").strip().lower()
        if del_src != "n":
            try:
                os.unlink(src_path)
                puts(colored.yellow("[CTX] File sorgente eliminato."))
            except OSError as e:
                puts(colored.yellow(f"[CTX] Non riesco a eliminare il file: {e}"))

        # Offer push to remote
        sync_cfg = self._context_manager.get_sync_cfg(name)
        if sync_cfg.get("remote_url"):
            push_now = input("\nEseguire subito un push verso il repo remoto? [S/n]: ").strip().lower()
            if push_now != "n":
                if ensure_repo_initialized(sync_cfg) and push_remote(sync_cfg, enc_bytes):
                    puts(colored.green("[SYNC] Push completato."))
                else:
                    puts(colored.yellow("[SYNC] Push fallito. Backup locale cifrato comunque aggiornato."))

        input("\nPress Enter to continue...")

    def _handle_new_context(self) -> None:
        """Wizard to create a new context from within the running app."""
        name = input("Nome nuovo contesto: ").strip()
        if not name:
            return
        if name in self._context_manager.list_contexts():
            puts(colored.red(f"[CTX] Contesto '{name}' già esistente"))
            input("\nPress Enter to continue...")
            return

        from ..contexts.wizard import add_context_wizard
        created = add_context_wizard(name)
        if not created:
            return

        puts(colored.green(f"[CTX] Contesto '{name}' creato."))
        switch = input(f"Passare subito a '{name}'? [s/N]: ").strip().lower()
        if switch == "s":
            self._switch_to_context(name)
        input("\nPress Enter to continue...")

    def _handle_edit_context_sync(self, name: str) -> None:
        """Edit the sync configuration (remote_url, branch, remote_file) of a context.

        If the edited context is currently active, the SyncManager is
        reinitialized in-session so subsequent saves use the new config.

        Changing remote_file only affects future pushes; the old file in the
        remote repo must be removed manually if no longer needed.

        Args:
            name: Name of the context whose sync config should be updated.
        """
        current_cfg = self._context_manager.get_sync_cfg(name)

        puts(colored.cyan(f"\n--- Modifica sync: {name} ---"))
        puts(colored.white(f"  remote_url:  {current_cfg.get('remote_url', '(non configurato)')}"))
        puts(colored.white(f"  branch:      {current_cfg.get('branch', 'main')}"))
        puts(colored.white(f"  remote_file: {current_cfg.get('remote_file', '(non configurato)')}"))
        puts(colored.white("\nPremi Invio per mantenere il valore corrente.\n"))

        new_url = input("Nuovo remote URL: ").strip()
        new_branch = input("Nuovo branch: ").strip()
        new_remote_file = input("Nuovo nome file remoto (es. isp.enc): ").strip()

        if not new_url and not new_branch and not new_remote_file:
            puts(colored.white("Nessuna modifica effettuata."))
            input("\nPress Enter to continue...")
            return

        partial: dict = {}
        if new_url:
            partial["remote_url"] = new_url
        if new_branch:
            partial["branch"] = new_branch
        if new_remote_file:
            partial["remote_file"] = new_remote_file
            puts(colored.yellow(f"[SYNC] remote_file aggiornato → '{new_remote_file}'. Il prossimo push creerà questo file nel repo remoto."))

        self._context_manager.update_sync_config(name, partial)
        puts(colored.green(f"[CTX] Config sync di '{name}' aggiornata."))

        # If it's the active context, reinitialize SyncManager in-session
        if name == self._active_context:
            new_cfg = self._context_manager.get_sync_cfg(name)
            self.sync_manager = SyncManager(self.config_file, sync_cfg_override=new_cfg)
            self.config_manager._post_save_hook = lambda: self.sync_manager.post_save_push()
            self._wire_encrypted_io()
            puts(colored.yellow("[SYNC] SyncManager aggiornato con la nuova configurazione."))

        input("\nPress Enter to continue...")
