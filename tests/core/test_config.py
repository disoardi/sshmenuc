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


class TestPathBasedOperations:
    """Tests for arbitrary-depth hierarchy methods added in issue #8."""

    def _manager_with_nested(self):
        """Helper: ConnectionManager with 3-level config."""
        m = ConnectionManager()
        m.config_data = {"targets": [
            {"HDP": [
                {"friendly": "nn-01", "host": "hdp-nn.local"},
                {"Prod": [
                    {"friendly": "rm-01", "host": "hdp-rm.local"}
                ]}
            ]}
        ]}
        return m

    def test_get_node_at_path_root(self):
        m = self._manager_with_nested()
        node = m.get_node_at_path([])
        assert isinstance(node, dict)
        assert "HDP" in node

    def test_get_node_at_path_depth1(self):
        m = self._manager_with_nested()
        node = m.get_node_at_path([0])
        assert isinstance(node, list)
        assert len(node) == 2

    def test_get_node_at_path_depth2_subgroup(self):
        m = self._manager_with_nested()
        node = m.get_node_at_path([0, 1])
        assert isinstance(node, dict)
        assert "Prod" in node

    def test_get_node_at_path_depth3_list(self):
        m = self._manager_with_nested()
        node = m.get_node_at_path([0, 1, 0])
        assert isinstance(node, list)
        assert node[0]["friendly"] == "rm-01"

    def test_add_subgroup_at_path(self):
        m = ConnectionManager()
        m.config_data = {"targets": [{"HDP": []}]}
        # Suppress save_config side effects
        m.save_config = lambda: None
        result = m.add_subgroup_at_path([0], "Prod")
        assert result is True
        node = m.get_node_at_path([0])
        assert {"Prod": []} in node

    def test_add_connection_at_path(self):
        m = ConnectionManager()
        m.config_data = {"targets": [{"HDP": []}]}
        m.save_config = lambda: None
        conn = {"friendly": "nn-01", "host": "nn.local", "connection_type": "ssh"}
        result = m.add_connection_at_path([0], conn)
        assert result is True
        assert m.get_node_at_path([0, 0]) == conn

    def test_delete_at_path(self):
        m = self._manager_with_nested()
        m.save_config = lambda: None
        result = m.delete_at_path([0], 0)
        assert result is True
        node = m.get_node_at_path([0])
        assert len(node) == 1
        assert "Prod" in node[0]

    def test_rename_subgroup_at_path(self):
        m = self._manager_with_nested()
        m.save_config = lambda: None
        result = m.rename_subgroup_at_path([0], 1, "Staging")
        assert result is True
        node = m.get_node_at_path([0])
        assert "Staging" in node[1]
        assert "Prod" not in node[1]

    def test_rename_subgroup_refuses_host_entry(self):
        m = self._manager_with_nested()
        m.save_config = lambda: None
        # index 0 is a host, not a subgroup
        result = m.rename_subgroup_at_path([0], 0, "NewName")
        assert result is False

    def test_search_hosts_by_friendly(self):
        m = self._manager_with_nested()
        results = m.search_hosts("nn-01")
        assert len(results) == 1
        assert results[0][1]["friendly"] == "nn-01"

    def test_search_hosts_by_host(self):
        m = self._manager_with_nested()
        results = m.search_hosts("hdp-rm")
        assert len(results) == 1
        assert results[0][1]["host"] == "hdp-rm.local"

    def test_search_hosts_by_tag(self):
        m = ConnectionManager()
        m.config_data = {"targets": [{"HDP": [
            {"friendly": "nn-01", "host": "nn.local", "tags": ["hadoop", "namenode"]},
            {"friendly": "rm-01", "host": "rm.local", "tags": ["hadoop", "admin"]},
        ]}]}
        results = m.search_hosts("namenode")
        assert len(results) == 1
        assert results[0][1]["friendly"] == "nn-01"

    def test_search_hosts_no_match(self):
        m = self._manager_with_nested()
        results = m.search_hosts("zzz_nonexistent")
        assert results == []

    def test_search_hosts_case_insensitive(self):
        m = self._manager_with_nested()
        results = m.search_hosts("NN-01")
        assert len(results) == 1