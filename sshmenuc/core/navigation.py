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
        self._run_startup_pull()

    def _run_startup_pull(self) -> None:
        """Pull config from remote at startup and show sync status."""
        state = self.sync_manager.startup_pull()
        if state == SyncState.SYNC_OK:
            # Remote config may have updated the file: reload from disk
            self.load_config()
            self.config_manager.load_config()
        elif state == SyncState.SYNC_OFFLINE:
            puts(colored.yellow("[SYNC] Remote non raggiungibile - uso backup locale criptato"))
        elif state == SyncState.LOCAL_ONLY:
            puts(colored.red("[SYNC] Remote non raggiungibile e nessun backup locale trovato"))
    
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

        puts(colored.yellow(f"[CTX] Caricamento contesto '{new_name}'..."))

        # Build a temporary SyncManager for the new context
        sync_cfg = self._context_manager.get_sync_cfg(new_name)
        self._context_manager.ensure_context_dir(new_name)
        new_config_file = self._context_manager.get_config_file(new_name)
        temp_sm = SyncManager(new_config_file, sync_cfg_override=sync_cfg)

        state = temp_sm.startup_pull()

        if state in (SyncState.SYNC_OK, SyncState.SYNC_OFFLINE, SyncState.NO_SYNC):
            # Accept even NO_SYNC (context has no remote configured yet)
            prev_context = self._active_context
            self._active_context = new_name
            self._context_manager.set_active(new_name)
            self.config_file = new_config_file
            self.sync_manager = temp_sm
            self.config_manager = ConnectionManager(new_config_file)
            self.editor = ConfigEditor(self.config_manager)
            self.config_manager._post_save_hook = lambda: self.sync_manager.post_save_push()
            self.load_config()
            self.config_manager.load_config()
            puts(colored.green(f"[CTX] Contesto cambiato: {prev_context} → {new_name}"))
        else:
            puts(colored.red(f"[CTX] Impossibile caricare il contesto '{new_name}' - fallback su '{self._active_context}'"))

        input("\nPress Enter to continue...")
