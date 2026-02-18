"""
Common base class for all classes in the sshmenuc project.
Provides shared functionality and common patterns.
"""
import json
import os
import shlex
import logging
from typing import Dict, Any, List, Union, Optional
from abc import ABC, abstractmethod


class BaseSSHMenuC(ABC):
    """Abstract base class with common functionality for all sshmenuc classes."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {"targets": []}
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup basic logging configuration."""
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO)
    
    def load_config(self):
        """Load and normalize the configuration file.

        Handles both new format (with 'targets' key) and legacy format.
        If the file doesn't exist or is corrupted, creates an empty config.
        """
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
        else:
            self._validate_host_entries()
    
    def _validate_host_entries(self):
        """Validate host entry fields and log warnings for invalid values.

        Checks extra_args (shlex parseable) and port (integer 1-65535).
        Does not abort loading; only warns to allow partial use of valid entries.
        """
        for target in self.config_data.get("targets", []):
            if not isinstance(target, dict):
                continue
            for entries in target.values():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    friendly = entry.get("friendly", entry.get("host", "unknown"))

                    extra_args = entry.get("extra_args")
                    if extra_args is not None:
                        try:
                            shlex.split(extra_args)
                        except ValueError as e:
                            logging.warning(f"[{friendly}] Invalid extra_args '{extra_args}': {e}")

                    port = entry.get("port")
                    if port is not None:
                        if not isinstance(port, int) or not (1 <= port <= 65535):
                            logging.warning(f"[{friendly}] Invalid port '{port}': must be integer 1-65535")

    def _create_config_directory(self):
        """Create configuration directory if it doesn't exist."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        except Exception as e:
            logging.warning(f"Could not create config directory: {e}")
    
    def save_config(self):
        """Save configuration to file.

        Raises:
            OSError: If file cannot be written (permission denied, disk full, etc.)
        """
        try:
            with open(self.config_file, "w") as file:
                json.dump(self.config_data, file, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Return the current configuration.

        Returns:
            Configuration dictionary with 'targets' key
        """
        return self.config_data
    
    def set_config(self, config_data: Dict[str, Any]):
        """Set a new configuration.

        Args:
            config_data: New configuration dictionary to set
        """
        self.config_data = config_data
    
    def has_global_hosts(self) -> bool:
        """Check if there are any hosts in the configuration.

        Returns:
            True if at least one host entry exists, False otherwise
        """
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
        """Abstract method to validate the configuration.

        Must be implemented by subclasses to provide specific validation logic.

        Returns:
            True if configuration is valid, False otherwise
        """
        pass