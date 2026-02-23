"""
Main entry point for sshmenuc application.
"""
import os
import shutil

from .core import ConnectionNavigator
from .utils import setup_argument_parser, setup_logging


def _add_context_wizard(name: str, args) -> None:
    """Interactive wizard to create a new context and configure its sync.

    Collects remote sync parameters, registers the context in contexts.json,
    optionally imports an existing legacy config.json, and offers an immediate
    first encrypted push to the remote repo.

    Args:
        name: The context name to create (e.g. 'personal', 'isp').
        args: Parsed CLI arguments (provides args.config for legacy import).
    """
    import getpass as _getpass
    import hashlib as _hashlib
    import json as _json
    from datetime import datetime, timezone

    from .contexts import ContextManager
    from .sync.crypto import encrypt_config
    from .sync.git_remote import ensure_repo_initialized, push_remote
    from .sync.passphrase_cache import set_passphrase

    print(f"\n=== Nuovo contesto: '{name}' ===")
    print("Configura la sincronizzazione remota per questo contesto.")
    print("Il config verrà cifrato con AES-256-GCM prima di ogni push.")
    print("Premi Invio senza digitare per annullare.\n")

    remote_url = input("URL repo remoto (es. git@github.com:utente/repo.git): ").strip()
    if not remote_url:
        print("Wizard annullato.")
        return

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

    # Import legacy config if cache is missing but default config exists
    config_file = ctx_mgr.get_config_file(name)
    if not os.path.isfile(config_file) and os.path.isfile(args.config):
        shutil.copy2(args.config, config_file)
        print(f"  Config importato da {args.config}")

    # Offer immediate first push
    answer = input("\nEseguire subito la prima sincronizzazione (push)? [s/N]: ").strip().lower()
    if answer != "s":
        print(f"\nContesto '{name}' creato. Avvialo con: sshmenuc --context {name}")
        return

    if not os.path.isfile(config_file):
        print("[SYNC] Nessun config locale da cifrare.")
        print(f"Avvia sshmenuc --context {name}, aggiungi host, poi la sync avverrà automaticamente.")
        return

    passphrase = _getpass.getpass("Scegli una passphrase per cifrare il config: ")
    passphrase2 = _getpass.getpass("Conferma passphrase: ")
    if passphrase != passphrase2:
        print("Le passphrase non coincidono. Push annullato.")
        print(f"Contesto '{name}' salvato - riprova avviando sshmenuc --context {name}.")
        return

    set_passphrase(passphrase)

    if not ensure_repo_initialized(cfg):
        print("[SYNC] Impossibile raggiungere il repo remoto. Verifica URL e chiave SSH.")
        print(f"Contesto '{name}' salvato - riprova avviando sshmenuc --context {name}.")
        return

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


def _select_context(ctx_mgr) -> str:
    """Interactive context selection menu.

    Prints a numbered list of available contexts and prompts the user to
    choose one. Retries on invalid input.

    Args:
        ctx_mgr: ContextManager instance.

    Returns:
        Name of the selected context.
    """
    names = ctx_mgr.list_contexts()
    active = ctx_mgr.get_active()

    print("\n=== Seleziona contesto ===")
    for i, name in enumerate(names, 1):
        marker = " *" if name == active else ""
        print(f"  [{i}] {name}{marker}")
    print()

    while True:
        try:
            raw = input(f"Contesto [{active}]: ").strip()
            if not raw:
                return active
            idx = int(raw) - 1
            if 0 <= idx < len(names):
                return names[idx]
            print(f"Inserisci un numero tra 1 e {len(names)}.")
        except (ValueError, EOFError):
            return active


def _migrate_legacy_config(args) -> bool:
    """Offer to convert an existing plaintext config.json to a named context.

    Called when sshmenuc detects a plaintext config.json at the default path
    and no contexts.json registry exists. The user can convert it interactively
    or keep using it as-is (backward compat).

    Args:
        args: Parsed CLI arguments.

    Returns:
        True if the user chose to convert (app should exit after wizard), False otherwise.
    """
    default_path = os.path.expanduser("~/.config/sshmenuc/config.json")
    enc_path = default_path + ".enc"

    # Only prompt if: using default config path, plaintext exists, no .enc yet
    if args.config != default_path:
        return False
    if not os.path.isfile(default_path):
        return False
    if os.path.isfile(enc_path):
        return False  # Already encrypted; zero-plaintext mode active

    print("\n=== File di configurazione in chiaro trovato ===")
    print(f"  {default_path}")
    print("\nPer proteggere i tuoi host SSH puoi convertirlo in un contesto cifrato.")
    print("Il file in chiaro verrà cifrato con AES-256-GCM e sincronizzato via Git.")
    print("In alternativa, continua a usarlo in chiaro (modalità legacy).\n")

    answer = input("Convertire in contesto cifrato? [s/N]: ").strip().lower()
    if answer != "s":
        return False

    name = input("Nome per il nuovo contesto [default]: ").strip() or "default"
    _add_context_wizard(name, args)
    return True


def main():
    """Main application function.

    Parses command-line arguments, sets up logging, handles context selection
    for multi-profile mode, and launches the connection navigator.
    """
    parser = setup_argument_parser()
    args = parser.parse_args()

    setup_logging(args.loglevel)

    # Export mode: decrypt and materialize config in plaintext, then exit
    if args.export is not None:
        from .sync import SyncManager
        sm = SyncManager(args.config)
        sm.export_config(args.export)
        return

    # Add-context wizard: create a new named profile interactively, then exit
    if args.add_context is not None:
        _add_context_wizard(args.add_context, args)
        return

    # Multi-context mode: check for contexts.json registry
    from .contexts import ContextManager
    ctx_mgr = ContextManager()

    if ctx_mgr.has_contexts():
        # Determine which context to use
        if args.context:
            active_name = args.context
        else:
            names = ctx_mgr.list_contexts()
            if len(names) == 1:
                active_name = names[0]
            else:
                active_name = _select_context(ctx_mgr)

        # Ensure local cache directory exists
        ctx_mgr.ensure_context_dir(active_name)
        config_file = ctx_mgr.get_config_file(active_name)
        sync_cfg_override = ctx_mgr.get_sync_cfg(active_name)

        # Import legacy config if context cache is missing but default config exists
        if not os.path.isfile(config_file) and os.path.isfile(args.config):
            shutil.copy2(args.config, config_file)
            print(f"[CTX] Config importato da {args.config} → contesto '{active_name}'")

        navigator = ConnectionNavigator(
            config_file,
            sync_cfg_override=sync_cfg_override,
            context_manager=ctx_mgr,
            active_context=active_name,
        )
    else:
        # Single-file mode: offer migration to encrypted context on first run
        if _migrate_legacy_config(args):
            return  # User started the wizard; exit and let them restart
        navigator = ConnectionNavigator(args.config)

    navigator.navigate()


if __name__ == "__main__":
    main()
