"""
Tests for the base class BaseSSHMenuC.
"""
import pytest
import tempfile
import json
from sshmenuc.core.base import BaseSSHMenuC


class ConcreteBaseSSHMenuC(BaseSSHMenuC):
    """Concrete implementation for testing the abstract base class."""
    
    def validate_config(self) -> bool:
        return isinstance(self.config_data, dict) and "targets" in self.config_data


class TestBaseSSHMenuC:
    
    def test_init_with_config_file(self, temp_config_file):
        """Test initialization with config file."""
        base = ConcreteBaseSSHMenuC(temp_config_file)
        assert base.config_file == temp_config_file
        assert isinstance(base.config_data, dict)
    
    def test_init_without_config_file(self):
        """Test initialization without config file."""
        base = ConcreteBaseSSHMenuC()
        assert base.config_file is None
        assert base.config_data == {"targets": []}
    
    def test_load_config_valid_file(self, temp_config_file):
        """Test loading valid config file."""
        base = ConcreteBaseSSHMenuC(temp_config_file)
        base.load_config()
        assert "targets" in base.config_data
        assert len(base.config_data["targets"]) == 2
    
    def test_load_config_nonexistent_file(self):
        """Test loading non-existent config file."""
        base = ConcreteBaseSSHMenuC("/nonexistent/path/config.json")
        base.load_config()
        assert base.config_data == {"targets": []}
    
    def test_save_config(self, temp_config_file):
        """Test saving config to file."""
        base = ConcreteBaseSSHMenuC(temp_config_file)
        base.config_data = {"targets": [{"test": []}]}
        base.save_config()
        
        # Verify file was saved
        with open(temp_config_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data == {"targets": [{"test": []}]}
    
    def test_get_set_config(self):
        """Test config getter and setter."""
        base = ConcreteBaseSSHMenuC()
        test_config = {"targets": [{"test": []}]}
        base.set_config(test_config)
        assert base.get_config() == test_config
    
    def test_has_global_hosts_true(self, temp_config_file):
        """Test has_global_hosts returns True when hosts exist."""
        base = ConcreteBaseSSHMenuC(temp_config_file)
        base.load_config()
        assert base.has_global_hosts() is True
    
    def test_has_global_hosts_false(self):
        """Test has_global_hosts returns False when no hosts exist."""
        base = ConcreteBaseSSHMenuC()
        base.config_data = {"targets": []}
        assert base.has_global_hosts() is False
    
    def test_validate_config_implementation(self):
        """Test that validate_config is properly implemented."""
        base = ConcreteBaseSSHMenuC()
        assert base.validate_config() is True
        
        base.config_data = "invalid"
        assert base.validate_config() is False