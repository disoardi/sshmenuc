"""
Gestione della configurazione SSH.
"""
from typing import List, Dict, Any
from .base import BaseSSHMenuC


class ConnectionManager(BaseSSHMenuC):
    """Gestisce la configurazione delle connessioni SSH."""
    
    def __init__(self, config_file: str = None):
        super().__init__(config_file)
        if config_file:
            self.load_config()
    
    def validate_config(self) -> bool:
        """Valida la struttura della configurazione."""
        if not isinstance(self.config_data, dict):
            return False
        if "targets" not in self.config_data:
            return False
        if not isinstance(self.config_data["targets"], list):
            return False
        return True
    
    def create_target(self, target_name: str, connections: List[Dict[str, Any]]):
        """Crea un nuovo target di connessioni."""
        target = {target_name: connections}
        self.config_data["targets"].append(target)
    
    def modify_target(self, target_name: str, new_target_name: str = None, 
                     connections: List[Dict[str, Any]] = None):
        """Modifica un target esistente."""
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                if new_target_name:
                    target[new_target_name] = target.pop(target_name)
                if connections:
                    key = list(target.keys())[0]
                    target[key] = connections
                break
    
    def delete_target(self, target_name: str):
        """Elimina un target."""
        self.config_data["targets"] = [
            target for target in self.config_data["targets"]
            if list(target.keys())[0] != target_name
        ]
    
    def create_connection(self, target_name: str, friendly: str, host: str,
                         connection_type: str = "ssh", command: str = "ssh",
                         zone: str = "", project: str = ""):
        """Crea una nuova connessione in un target."""
        connection = {
            "friendly": friendly,
            "host": host,
            "connection_type": connection_type,
            "command": command,
            "zone": zone,
            "project": project,
        }
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                target[target_name].append(connection)
                break
    
    def modify_connection(self, target_name: str, connection_index: int, **kwargs):
        """Modifica una connessione esistente."""
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                connection = target[target_name][connection_index]
                for key, value in kwargs.items():
                    if value is not None:
                        connection[key] = value
                break
    
    def delete_connection(self, target_name: str, connection_index: int):
        """Elimina una connessione."""
        for target in self.config_data["targets"]:
            if list(target.keys())[0] == target_name:
                target[target_name].pop(connection_index)
                break