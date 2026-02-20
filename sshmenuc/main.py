"""
Main entry point for sshmenuc application.
"""
from .core import ConnectionNavigator
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

        navigator = ConnectionNavigator(
            config_file,
            sync_cfg_override=sync_cfg_override,
            context_manager=ctx_mgr,
            active_context=active_name,
        )
    else:
        # Single-file mode (backward compatible)
        navigator = ConnectionNavigator(args.config)

    navigator.navigate()


if __name__ == "__main__":
    main()
