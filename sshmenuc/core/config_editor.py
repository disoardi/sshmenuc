"""
Interactive configuration editor for managing targets and connections.
"""
from typing import Dict, Any, List, Optional
from clint.textui import puts, colored
from .config import ConnectionManager


class ConfigEditor:
    """Interactive editor for SSH configuration.

    Provides forms and dialogs for creating, editing, and deleting
    targets and connections within the configuration.
    """

    def __init__(self, config_manager: ConnectionManager):
        """Initialize the config editor.

        Args:
            config_manager: ConnectionManager instance to modify
        """
        self.manager = config_manager

    def prompt_input(self, prompt: str, default: str = "") -> str:
        """Prompt user for input with optional default value.

        Args:
            prompt: Prompt message to display
            default: Default value if user presses enter

        Returns:
            User input string
        """
        if default:
            result = input(f"{prompt} [{default}]: ").strip()
            return result if result else default
        return input(f"{prompt}: ").strip()

    def confirm(self, message: str) -> bool:
        """Ask user for confirmation.

        Args:
            message: Confirmation message

        Returns:
            True if user confirms, False otherwise
        """
        response = input(f"{message} [y/N]: ").strip().lower()
        return response == 'y'

    def add_target(self) -> bool:
        """Interactive form to add a new target.

        Returns:
            True if target was added, False if cancelled
        """
        puts(colored.cyan("\n=== Add New Target ==="))
        target_name = self.prompt_input("Target name (e.g., Production, Development)")

        if not target_name:
            puts(colored.red("Target name cannot be empty"))
            return False

        # Check if target already exists
        if self.manager._find_target(target_name):
            puts(colored.red(f"Target '{target_name}' already exists"))
            return False

        self.manager.create_target(target_name, [])
        self.manager.save_config()
        puts(colored.green(f"✓ Target '{target_name}' created successfully"))
        return True

    def delete_target(self, target_name: str) -> bool:
        """Delete a target with confirmation.

        Args:
            target_name: Name of target to delete

        Returns:
            True if deleted, False if cancelled
        """
        if not self.confirm(f"Delete target '{target_name}' and all its connections?"):
            puts(colored.yellow("Cancelled"))
            return False

        self.manager.delete_target(target_name)
        self.manager.save_config()
        puts(colored.green(f"✓ Target '{target_name}' deleted"))
        return True

    def rename_target(self, target_name: str) -> bool:
        """Rename a target.

        Args:
            target_name: Current name of target

        Returns:
            True if renamed, False if cancelled
        """
        puts(colored.cyan(f"\n=== Rename Target '{target_name}' ==="))
        new_name = self.prompt_input("New name", target_name)

        if not new_name or new_name == target_name:
            puts(colored.yellow("Cancelled"))
            return False

        # Check if new name already exists
        if self.manager._find_target(new_name):
            puts(colored.red(f"Target '{new_name}' already exists"))
            return False

        self.manager.modify_target(target_name, new_target_name=new_name)
        self.manager.save_config()
        puts(colored.green(f"✓ Target renamed to '{new_name}'"))
        return True

    def add_connection(self, target_name: str) -> bool:
        """Interactive form to add a connection to a target.

        Args:
            target_name: Target to add connection to

        Returns:
            True if connection added, False if cancelled
        """
        puts(colored.cyan(f"\n=== Add Connection to '{target_name}' ==="))

        friendly = self.prompt_input("Friendly name (display name)")
        if not friendly:
            puts(colored.red("Friendly name cannot be empty"))
            return False

        host = self.prompt_input("Host (IP or hostname)")
        if not host:
            puts(colored.red("Host cannot be empty"))
            return False

        user = self.prompt_input("Username (optional, leave empty for current user)", "")
        certkey = self.prompt_input("SSH key path (optional)", "")
        connection_type = self.prompt_input("Connection type", "ssh")

        tags_raw = self.prompt_input("Tags (comma-separated, optional)", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        connection: Dict[str, Any] = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
        }

        if user:
            connection["user"] = user
        if certkey:
            connection["certkey"] = certkey
        if tags:
            connection["tags"] = tags

        target = self.manager._find_target(target_name)
        if target:
            target[target_name].append(connection)
            self.manager.save_config()
            puts(colored.green(f"✓ Connection '{friendly}' added to '{target_name}'"))
            return True

        puts(colored.red(f"Target '{target_name}' not found"))
        return False

    def edit_connection(self, target_name: str, connection_index: int,
                       connection: Dict[str, Any]) -> bool:
        """Interactive form to edit a connection.

        Args:
            target_name: Target containing the connection
            connection_index: Index of connection to edit
            connection: Current connection data

        Returns:
            True if edited, False if cancelled
        """
        puts(colored.cyan(f"\n=== Edit Connection '{connection.get('friendly', 'Unknown')}' ==="))

        friendly = self.prompt_input("Friendly name", connection.get("friendly", ""))
        host = self.prompt_input("Host", connection.get("host", ""))
        user = self.prompt_input("Username", connection.get("user", ""))
        certkey = self.prompt_input("SSH key path", connection.get("certkey", ""))
        tags_raw = self.prompt_input("Tags (comma-separated)", ",".join(connection.get("tags", [])))
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        if not friendly or not host:
            puts(colored.red("Friendly name and host cannot be empty"))
            return False

        self.manager.modify_connection(
            target_name, connection_index,
            friendly=friendly, host=host, user=user or None, certkey=certkey or None
        )
        # Update tags separately (modify_connection doesn't know about tags)
        target = self.manager._find_target(target_name)
        if target:
            conn = target[target_name][connection_index]
            if tags:
                conn["tags"] = tags
            elif "tags" in conn:
                del conn["tags"]
        self.manager.save_config()
        puts(colored.green("✓ Connection updated"))
        return True

    def delete_connection(self, target_name: str, connection_index: int,
                         connection: Dict[str, Any]) -> bool:
        """Delete a connection with confirmation.

        Args:
            target_name: Target containing the connection
            connection_index: Index of connection to delete
            connection: Connection data (for display)

        Returns:
            True if deleted, False if cancelled
        """
        friendly = connection.get("friendly", "Unknown")
        if not self.confirm(f"Delete connection '{friendly}'?"):
            puts(colored.yellow("Cancelled"))
            return False

        self.manager.delete_connection(target_name, connection_index)
        self.manager.save_config()
        puts(colored.green(f"✓ Connection '{friendly}' deleted"))
        return True

    # --- Path-based operations for arbitrary-depth hierarchy ---

    def add_subgroup(self, path: List[int]) -> bool:
        """Interactive form to create a subgroup at path.

        Args:
            path: Navigation path to the parent list node.

        Returns:
            True if subgroup created, False if cancelled.
        """
        puts(colored.cyan("\n=== Add Subgroup ==="))
        name = self.prompt_input("Subgroup name")
        if not name:
            puts(colored.red("Name cannot be empty"))
            return False
        if self.manager.add_subgroup_at_path(path, name):
            puts(colored.green(f"✓ Subgroup '{name}' created"))
            return True
        puts(colored.red("Failed to create subgroup"))
        return False

    def add_connection_to_path(self, path: List[int]) -> bool:
        """Interactive form to add a connection to the list node at path.

        Args:
            path: Navigation path to the target list node.

        Returns:
            True if connection added, False if cancelled.
        """
        puts(colored.cyan("\n=== Add Connection ==="))
        friendly = self.prompt_input("Friendly name (display name)")
        if not friendly:
            puts(colored.red("Friendly name cannot be empty"))
            return False
        host = self.prompt_input("Host (IP or hostname)")
        if not host:
            puts(colored.red("Host cannot be empty"))
            return False
        user = self.prompt_input("Username (optional, leave empty for current user)", "")
        certkey = self.prompt_input("SSH key path (optional)", "")
        connection_type = self.prompt_input("Connection type", "ssh")
        tags_raw = self.prompt_input("Tags (comma-separated, optional)", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        connection: Dict[str, Any] = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
        }
        if user:
            connection["user"] = user
        if certkey:
            connection["certkey"] = certkey
        if tags:
            connection["tags"] = tags

        if self.manager.add_connection_at_path(path, connection):
            puts(colored.green(f"✓ Connection '{friendly}' added"))
            return True
        puts(colored.red("Failed to add connection"))
        return False

    def edit_connection_at_path(self, path: List[int], index: int,
                                connection: Dict[str, Any]) -> bool:
        """Interactive form to edit an existing connection at path[index].

        Args:
            path: Navigation path to the parent list node.
            index: Index of the connection within that list.
            connection: Current connection data.

        Returns:
            True if edited, False if cancelled.
        """
        puts(colored.cyan(f"\n=== Edit Connection '{connection.get('friendly', 'Unknown')}' ==="))
        friendly = self.prompt_input("Friendly name", connection.get("friendly", ""))
        host = self.prompt_input("Host", connection.get("host", ""))
        user = self.prompt_input("Username", connection.get("user", ""))
        certkey = self.prompt_input("SSH key path", connection.get("certkey", ""))
        tags_raw = self.prompt_input(
            "Tags (comma-separated)", ",".join(connection.get("tags", []))
        )
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        if not friendly or not host:
            puts(colored.red("Friendly name and host cannot be empty"))
            return False

        node = self.manager.get_node_at_path(path)
        if isinstance(node, list) and 0 <= index < len(node):
            node[index].update({
                "friendly": friendly,
                "host": host,
            })
            if user:
                node[index]["user"] = user
            elif "user" in node[index]:
                del node[index]["user"]
            if certkey:
                node[index]["certkey"] = certkey
            elif "certkey" in node[index]:
                del node[index]["certkey"]
            if tags:
                node[index]["tags"] = tags
            elif "tags" in node[index]:
                del node[index]["tags"]
            self.manager.save_config()
            puts(colored.green("✓ Connection updated"))
            return True
        return False

    def delete_connection_at_path(self, path: List[int], index: int,
                                  connection: Dict[str, Any]) -> bool:
        """Confirm and delete a host connection at path[index].

        Args:
            path: Navigation path to the parent list node.
            index: Index of the connection within that list.
            connection: Connection data (for display).

        Returns:
            True if deleted, False if cancelled.
        """
        friendly = connection.get("friendly", "Unknown")
        if not self.confirm(f"Delete connection '{friendly}'?"):
            puts(colored.yellow("Cancelled"))
            return False
        if self.manager.delete_at_path(path, index):
            puts(colored.green(f"✓ Connection '{friendly}' deleted"))
            return True
        return False

    def delete_subgroup(self, path: List[int], index: int, name: str) -> bool:
        """Confirm and delete a subgroup at path[index].

        Args:
            path: Navigation path to the parent list node.
            index: Index of the subgroup within that list.
            name: Display name of the subgroup.

        Returns:
            True if deleted, False if cancelled.
        """
        if not self.confirm(f"Delete subgroup '{name}' and all its contents?"):
            puts(colored.yellow("Cancelled"))
            return False
        if self.manager.delete_at_path(path, index):
            puts(colored.green(f"✓ Subgroup '{name}' deleted"))
            return True
        return False

    def rename_subgroup(self, path: List[int], index: int, current_name: str) -> bool:
        """Interactive form to rename a subgroup at path[index].

        Args:
            path: Navigation path to the parent list node.
            index: Index of the subgroup within that list.
            current_name: Current key name of the subgroup.

        Returns:
            True if renamed, False if cancelled.
        """
        puts(colored.cyan(f"\n=== Rename Subgroup '{current_name}' ==="))
        new_name = self.prompt_input("New name", current_name)
        if not new_name or new_name == current_name:
            puts(colored.yellow("Cancelled"))
            return False
        if self.manager.rename_subgroup_at_path(path, index, new_name):
            puts(colored.green(f"✓ Subgroup renamed to '{new_name}'"))
            return True
        return False
