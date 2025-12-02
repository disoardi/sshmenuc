"""
Classe base comune per tutte le classi del progetto sshmenuc.
Fornisce funzionalità condivise e pattern comuni.
"""
import json
import os
import logging
from typing import Dict, Any, List, Union
from abc import ABC, abstractmethod


class BaseSSHMenuC(ABC):
    """Classe base astratta con funzionalità comuni."""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {"targets": []}
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup base del logging."""
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO)
    
    def load_config(self):
        """Carica e normalizza il file di configurazione."""
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "targets" not in data:
                    targets = []
                    for k, v in data.items():
                        targets.append({k: v})
                    self.config_data = {"targets": targets}
                else:
                    self.config_data = data
        except FileNotFoundError:
            self._create_config_directory()
            self.config_data = {"targets": []}
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON in '{self.config_file}'. Using empty configuration.")
            self.config_data = {"targets": []}
    
    def _create_config_directory(self):
        """Crea la directory di configurazione se non esiste."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        except Exception as e:
            logging.warning(f"Could not create config directory: {e}")
    
    def save_config(self):
        """Salva la configurazione su file."""
        try:
            with open(self.config_file, "w") as file:
                json.dump(self.config_data, file, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Restituisce la configurazione corrente."""
        return self.config_data
    
    def set_config(self, config_data: Dict[str, Any]):
        """Imposta una nuova configurazione."""
        self.config_data = config_data
    
    def has_global_hosts(self) -> bool:
        """Verifica se esistono host nella configurazione."""
        targets = self.config_data.get("targets", [])
        for t in targets:
            if isinstance(t, dict):
                for v in t.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and ("friendly" in item or "host" in item):
                                return True
        return False
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Metodo astratto per validare la configurazione."""
        pass