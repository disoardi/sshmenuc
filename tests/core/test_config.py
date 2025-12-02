"""
Tests for ConnectionManager class.
"""
import pytest
from sshmenuc.core.config import ConnectionManager


class TestConnectionManager:
    
    def test_init_with_config_file(self, temp_config_file):
        """Test initialization with config file."""
        manager = ConnectionManager(temp_config_file)
        assert manager.config_file == temp_config_file
        assert "targets" in manager.config_data
    
    def test_validate_config_valid(self, temp_config_file):
        """Test config validation with valid config."""
        manager = ConnectionManager(temp_config_file)
        assert manager.validate_config() is True
    
    def test_validate_config_invalid(self):
        """Test config validation with invalid config."""
        manager = ConnectionManager()
        manager.config_data = "invalid"
        assert manager.validate_config() is False
        
        manager.config_data = {"invalid": "structure"}
        assert manager.validate_config() is False
    
    def test_create_target(self):
        """Test creating a new target."""
        manager = ConnectionManager()
        connections = [{"friendly": "test", "host": "test.com"}]
        manager.create_target("TestTarget", connections)
        
        assert len(manager.config_data["targets"]) == 1
        assert "TestTarget" in manager.config_data["targets"][0]
        assert manager.config_data["targets"][0]["TestTarget"] == connections
    
    def test_modify_target_name(self):
        """Test modifying target name."""
        manager = ConnectionManager()
        manager.create_target("OldName", [])
        manager.modify_target("OldName", new_target_name="NewName")
        
        assert "NewName" in manager.config_data["targets"][0]
        assert "OldName" not in manager.config_data["targets"][0]
    
    def test_modify_target_connections(self):
        """Test modifying target connections."""
        manager = ConnectionManager()
        manager.create_target("TestTarget", [])
        new_connections = [{"friendly": "new", "host": "new.com"}]
        manager.modify_target("TestTarget", connections=new_connections)
        
        assert manager.config_data["targets"][0]["TestTarget"] == new_connections
    
    def test_delete_target(self):
        """Test deleting a target."""
        manager = ConnectionManager()
        manager.create_target("ToDelete", [])
        manager.create_target("ToKeep", [])
        
        manager.delete_target("ToDelete")
        
        assert len(manager.config_data["targets"]) == 1
        assert "ToKeep" in manager.config_data["targets"][0]
    
    def test_create_connection(self):
        """Test creating a connection in a target."""
        manager = ConnectionManager()
        manager.create_target("TestTarget", [])
        
        manager.create_connection(
            "TestTarget", 
            "test-server", 
            "test.com",
            connection_type="ssh",
            command="ssh"
        )
        
        connections = manager.config_data["targets"][0]["TestTarget"]
        assert len(connections) == 1
        assert connections[0]["friendly"] == "test-server"
        assert connections[0]["host"] == "test.com"
    
    def test_modify_connection(self):
        """Test modifying an existing connection."""
        manager = ConnectionManager()
        manager.create_target("TestTarget", [])
        manager.create_connection("TestTarget", "old-name", "old.com")
        
        manager.modify_connection(
            "TestTarget", 
            0, 
            friendly="new-name", 
            host="new.com"
        )
        
        connection = manager.config_data["targets"][0]["TestTarget"][0]
        assert connection["friendly"] == "new-name"
        assert connection["host"] == "new.com"
    
    def test_delete_connection(self):
        """Test deleting a connection."""
        manager = ConnectionManager()
        manager.create_target("TestTarget", [])
        manager.create_connection("TestTarget", "conn1", "host1.com")
        manager.create_connection("TestTarget", "conn2", "host2.com")
        
        manager.delete_connection("TestTarget", 0)
        
        connections = manager.config_data["targets"][0]["TestTarget"]
        assert len(connections) == 1
        assert connections[0]["friendly"] == "conn2"