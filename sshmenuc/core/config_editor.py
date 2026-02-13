"""
Interactive configuration editor for managing targets and connections.
"""
from typing import Dict, Any, Optional
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

        # Build connection dict with only non-empty fields
        connection = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
        }

        if user:
            connection["user"] = user
        if certkey:
            connection["certkey"] = certkey

        # Add connection using the existing method
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

        if not friendly or not host:
            puts(colored.red("Friendly name and host cannot be empty"))
            return False

        self.manager.modify_connection(
            target_name, connection_index,
            friendly=friendly, host=host, user=user or None, certkey=certkey or None
        )
        self.manager.save_config()
        puts(colored.green(f"✓ Connection updated"))
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
