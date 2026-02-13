"""
SSH configuration management.
"""
from typing import List, Dict, Any, Optional
from .base import BaseSSHMenuC


class ConnectionManager(BaseSSHMenuC):
    """Manages SSH connection configurations.

    Provides CRUD operations for targets and connections within the configuration.
    """

    def __init__(self, config_file: Optional[str] = None):
        super().__init__(config_file)
        if config_file:
            self.load_config()

    def _get_target_key(self, target: Dict[str, Any]) -> str:
        """Extract the first (and only) key from a target dictionary.

        Args:
            target: Target dictionary with single key

        Returns:
            The target key name
        """
        return next(iter(target.keys()))

    def _find_target(self, target_name: str) -> Optional[Dict[str, Any]]:
        """Find and return the target dictionary by name.

        Args:
            target_name: Name of the target to find

        Returns:
            Target dictionary if found, None otherwise
        """
        for target in self.config_data["targets"]:
            if self._get_target_key(target) == target_name:
                return target
        return None

    def validate_config(self) -> bool:
        """Validate the configuration structure.

        Returns:
            True if config has valid structure with 'targets' key, False otherwise
        """
        if not isinstance(self.config_data, dict):
            return False
        if "targets" not in self.config_data:
            return False
        if not isinstance(self.config_data["targets"], list):
            return False
        return True
    
    def create_target(self, target_name: str, connections: List[Dict[str, Any]]):
        """Create a new connection target.

        Args:
            target_name: Name of the target to create
            connections: List of connection configuration dictionaries
        """
        target = {target_name: connections}
        self.config_data["targets"].append(target)
    
    def modify_target(self, target_name: str, new_target_name: str = None,
                     connections: List[Dict[str, Any]] = None):
        """Modify an existing target.

        Args:
            target_name: Current name of the target
            new_target_name: New name for the target (optional, if renaming)
            connections: New connection list (optional, if updating connections)
        """
        target = self._find_target(target_name)
        if target:
            if new_target_name:
                target[new_target_name] = target.pop(target_name)
            if connections:
                key = self._get_target_key(target)
                target[key] = connections
    
    def delete_target(self, target_name: str):
        """Delete a target.

        Args:
            target_name: Name of the target to delete
        """
        self.config_data["targets"] = [
            target for target in self.config_data["targets"]
            if self._get_target_key(target) != target_name
        ]
    
    def create_connection(self, target_name: str, friendly: str, host: str,
                         connection_type: str = "ssh", command: str = "ssh",
                         zone: str = "", project: str = ""):
        """Create a new connection within a target.

        Args:
            target_name: Name of the target to add connection to
            friendly: Friendly name for the connection
            host: Host address to connect to
            connection_type: Type of connection (ssh, gssh, docker)
            command: Command to execute for connection
            zone: Cloud zone (for gssh connections)
            project: Cloud project (for gssh connections)
        """
        connection = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
            "command": command,
            "zone": zone,
            "project": project,
        }
        target = self._find_target(target_name)
        if target:
            target[target_name].append(connection)
    
    def modify_connection(self, target_name: str, connection_index: int, **kwargs):
        """Modify an existing connection.

        Args:
            target_name: Name of the target containing the connection
            connection_index: Index of the connection to modify
            **kwargs: Connection fields to update (host, user, certkey, etc.)
        """
        target = self._find_target(target_name)
        if target:
            connection = target[target_name][connection_index]
            for key, value in kwargs.items():
                if value is not None:
                    connection[key] = value
    
    def delete_connection(self, target_name: str, connection_index: int):
        """Delete a connection.

        Args:
            target_name: Name of the target containing the connection
            connection_index: Index of the connection to delete
        """
        target = self._find_target(target_name)
        if target:
            target[target_name].pop(connection_index)