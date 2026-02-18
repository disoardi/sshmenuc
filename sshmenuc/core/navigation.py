"""
Menu navigation management.
"""
import os
import logging
from typing import List, Any, Dict, Union
import readchar
from clint.textui import puts, colored

from .base import BaseSSHMenuC
from .launcher import SSHLauncher
from .config import ConnectionManager
from .config_editor import ConfigEditor
from ..ui.display import MenuDisplay
from ..utils.helpers import get_current_user


# Constants
MAX_MARKED_SELECTIONS = 6  # Maximum number of hosts that can be marked for multi-connection


class ConnectionNavigator(BaseSSHMenuC):
    """Manages navigation through the connection menu.

    Provides interactive keyboard navigation with support for multiple selection
    and tmux integration for group connections.
    """
    
    def __init__(self, config_file: str):
        super().__init__(config_file)
        self.load_config()
        self.marked_indices = set()
        self.display = MenuDisplay()
        self.config_manager = ConnectionManager(config_file)
        self.editor = ConfigEditor(self.config_manager)
    
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
        self.display.print_instructions()
        
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
