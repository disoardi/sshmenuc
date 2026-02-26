"""
Main entry point for sshmenuc application.
"""
import os
import shutil

from .core import ConnectionNavigator
from .contexts.wizard import add_context_wizard
from .utils import setup_argument_parser, setup_logging


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
    add_context_wizard(name, default_config_path=args.config)
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
        add_context_wizard(args.add_context, default_config_path=args.config)
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
