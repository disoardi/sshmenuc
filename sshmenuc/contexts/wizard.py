"""Interactive wizard for creating and configuring sshmenuc contexts."""
import os
import shutil


def add_context_wizard(name: str, default_config_path: str = "") -> bool:
    """Interactive wizard to create a new context and configure its sync.

    Collects remote sync parameters, registers the context in contexts.json,
    optionally imports an existing legacy config.json, and offers an immediate
    first encrypted push to the remote repo.

    Args:
        name: The context name to create (e.g. 'personal', 'isp').
        default_config_path: Optional path to a plaintext config.json to import
            into the new context cache if no local cache exists yet.

    Returns:
        True if the context entry was created (wizard completed), False if the
        wizard was cancelled before writing anything.
    """
    import getpass as _getpass
    import hashlib as _hashlib
    import json as _json
    from datetime import datetime, timezone

    from .context_manager import ContextManager
    from ..sync.crypto import encrypt_config
    from ..sync.git_remote import ensure_repo_initialized, push_remote
    from ..sync.passphrase_cache import set_passphrase

    print(f"\n=== Nuovo contesto: '{name}' ===")
    print("Configura la sincronizzazione remota per questo contesto.")
    print("Il config verrà cifrato con AES-256-GCM prima di ogni push.")
    print("Premi Invio senza digitare per annullare.\n")

    remote_url = input("URL repo remoto (es. git@github.com:utente/repo.git): ").strip()
    if not remote_url:
        print("Wizard annullato.")
        return False

    branch = input("Branch [main]: ").strip() or "main"

    default_remote_file = f"{name}.enc"
    remote_file = input(f"Nome file nel repo [{default_remote_file}]: ").strip() or default_remote_file

    default_repo_path = os.path.expanduser("~/.config/sshmenuc/sync_repos/sshmenuc_config")
    repo_path_input = input(f"Percorso repo locale [{default_repo_path}]: ").strip()
    sync_repo_path = repo_path_input or default_repo_path

    cfg = {
        "remote_url": remote_url,
        "branch": branch,
        "remote_file": remote_file,
        "sync_repo_path": sync_repo_path,
        "auto_pull": True,
        "auto_push": True,
    }

    ctx_mgr = ContextManager()
    ctx_mgr.add_context(name, cfg)
    ctx_mgr.ensure_context_dir(name)
    print(f"\n✓ Contesto '{name}' aggiunto a contexts.json")

    # Import legacy config if cache is missing but a default config exists
    config_file = ctx_mgr.get_config_file(name)
    if not os.path.isfile(config_file) and default_config_path and os.path.isfile(default_config_path):
        shutil.copy2(default_config_path, config_file)
        print(f"  Config importato da {default_config_path}")

    # Offer immediate first push
    answer = input("\nEseguire subito la prima sincronizzazione (push)? [s/N]: ").strip().lower()
    if answer != "s":
        print(f"\nContesto '{name}' creato. Avvialo con: sshmenuc --context {name}")
        return True

    if not os.path.isfile(config_file):
        print("[SYNC] Nessun config locale da cifrare.")
        print(f"Avvia sshmenuc --context {name}, aggiungi host, poi la sync avverrà automaticamente.")
        return True

    passphrase = _getpass.getpass("Scegli una passphrase per cifrare il config: ")
    passphrase2 = _getpass.getpass("Conferma passphrase: ")
    if passphrase != passphrase2:
        print("Le passphrase non coincidono. Push annullato.")
        print(f"Contesto '{name}' salvato - riprova avviando sshmenuc --context {name}.")
        return True

    set_passphrase(passphrase)

    if not ensure_repo_initialized(cfg):
        print("[SYNC] Impossibile raggiungere il repo remoto. Verifica URL e chiave SSH.")
        print(f"Contesto '{name}' salvato - riprova avviando sshmenuc --context {name}.")
        return True

    with open(config_file, "r") as f:
        config_data = _json.load(f)

    print("Cifratura e push in corso...")
    enc_bytes = encrypt_config(config_data, passphrase)

    enc_path = config_file + ".enc"
    with open(enc_path, "wb") as f:
        f.write(enc_bytes)

    if push_remote(cfg, enc_bytes):
        # Persist sync metadata so startup_pull won't see a false conflict
        with open(config_file, "rb") as f:
            file_hash = _hashlib.sha256(f.read()).hexdigest()
        ctx_mgr.update_context_meta(name, datetime.now(timezone.utc).isoformat(), file_hash)
        print(f"[SYNC] Push completato. Contesto '{name}' pronto.")
        print(f"Avvialo con: sshmenuc --context {name}")
    else:
        print("[SYNC] Push fallito. Backup locale cifrato creato.")
        print(f"Riprova avviando sshmenuc --context {name}.")

    return True
