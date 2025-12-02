"""
Tests for ConnectionNavigator class.
"""
import pytest
from unittest.mock import patch, MagicMock
from sshmenuc.core.navigation import ConnectionNavigator


class TestConnectionNavigator:
    
    def test_init(self, temp_config_file):
        """Test ConnectionNavigator initialization."""
        navigator = ConnectionNavigator(temp_config_file)
        assert navigator.config_file == temp_config_file
        assert isinstance(navigator.marked_indices, set)
        assert navigator.display is not None
    
    def test_validate_config_valid(self, temp_config_file):
        """Test config validation with valid config."""
        navigator = ConnectionNavigator(temp_config_file)
        assert navigator.validate_config() is True
    
    def test_validate_config_invalid(self):
        """Test config validation with invalid config."""
        navigator = ConnectionNavigator("/nonexistent/config.json")
        navigator.config_data = "invalid"
        assert navigator.validate_config() is False
    
    def test_get_node_root(self, temp_config_file):
        """Test getting root node."""
        navigator = ConnectionNavigator(temp_config_file)
        node = navigator.get_node([])
        
        assert isinstance(node, dict)
        assert "Production" in node
        assert "Development" in node
    
    def test_get_node_with_path(self, temp_config_file):
        """Test getting node with path."""
        navigator = ConnectionNavigator(temp_config_file)
        # Navigate to Production category
        node = navigator.get_node([0])
        
        assert isinstance(node, list)
        assert len(node) > 0
        assert "friendly" in node[0]
    
    def test_count_elements_dict(self, temp_config_file):
        """Test counting elements in dictionary node."""
        navigator = ConnectionNavigator(temp_config_file)
        count = navigator.count_elements([])
        
        assert count == 2  # Production and Development
    
    def test_count_elements_list(self, temp_config_file):
        """Test counting elements in list node."""
        navigator = ConnectionNavigator(temp_config_file)
        count = navigator.count_elements([0])  # Production hosts
        
        assert count == 1  # One host in Production
    
    def test_move_left_from_root(self):
        """Test moving left from root (should do nothing)."""
        navigator = ConnectionNavigator("/nonexistent/config.json")
        current_path = []
        navigator.move_left(current_path)
        
        assert current_path == []
    
    def test_move_left_from_category(self, temp_config_file):
        """Test moving left from category."""
        navigator = ConnectionNavigator(temp_config_file)
        current_path = [0]  # In Production category
        navigator.move_left(current_path)
        
        assert current_path == []
    
    def test_handle_selection_toggle_on(self, temp_config_file):
        """Test handling selection toggle on."""
        navigator = ConnectionNavigator(temp_config_file)
        current_path = [0]  # In Production hosts list
        
        navigator._handle_selection(current_path, 0)
        
        assert 0 in navigator.marked_indices
    
    def test_handle_selection_toggle_off(self, temp_config_file):
        """Test handling selection toggle off."""
        navigator = ConnectionNavigator(temp_config_file)
        current_path = [0]  # In Production hosts list
        navigator.marked_indices.add(0)
        
        navigator._handle_selection(current_path, 0)
        
        assert 0 not in navigator.marked_indices
    
    def test_handle_selection_max_limit(self, temp_config_file):
        """Test handling selection with max limit."""
        navigator = ConnectionNavigator(temp_config_file)
        current_path = [0]  # In Production hosts list
        
        # Add 6 selections (max limit)
        for i in range(6):
            navigator.marked_indices.add(i)
        
        # Test that selection doesn't exceed limit
        initial_count = len(navigator.marked_indices)
        navigator._handle_selection(current_path, 6)
        assert len(navigator.marked_indices) == initial_count  # Should not add more
    
    @patch('sshmenuc.core.launcher.SSHLauncher.launch_group')
    @patch('os.getlogin')
    def test_launch_multiple_hosts(self, mock_getlogin, mock_launch_group, temp_config_file):
        """Test launching multiple hosts."""
        mock_getlogin.return_value = "testuser"
        navigator = ConnectionNavigator(temp_config_file)
        node = [
            {"host": "host1.com", "user": "user1"},
            {"host": "host2.com", "user": "user2"}
        ]
        navigator.marked_indices = {0, 1}
        
        navigator._launch_multiple_hosts(node)
        
        mock_launch_group.assert_called_once()
        assert len(navigator.marked_indices) == 0  # Should be cleared
    
    @patch('sshmenuc.core.navigation.SSHLauncher')
    @patch('os.getlogin')
    def test_handle_single_selection_host(self, mock_getlogin, mock_launcher_class, temp_config_file):
        """Test handling single selection of a host."""
        mock_getlogin.return_value = "testuser"
        navigator = ConnectionNavigator(temp_config_file)
        node = [{"friendly": "test", "host": "test.com", "user": "testuser"}]
        
        navigator._handle_single_selection(node, 0, [0])
        
        mock_launcher_class.assert_called_once()
    
    def test_handle_single_selection_category(self, temp_config_file):
        """Test handling single selection of a category."""
        navigator = ConnectionNavigator(temp_config_file)
        node = {"Category1": [], "Category2": []}
        current_path = []
        
        navigator._handle_single_selection(node, 0, current_path)
        
        assert current_path == [0]
    
    @patch('sshmenuc.ui.display.MenuDisplay.clear_screen')
    @patch('sshmenuc.ui.display.MenuDisplay.print_instructions')
    @patch('sshmenuc.ui.display.MenuDisplay.print_table')
    def test_print_menu(self, mock_print_table, mock_print_instructions, 
                       mock_clear_screen, temp_config_file):
        """Test printing menu."""
        navigator = ConnectionNavigator(temp_config_file)
        navigator.print_menu(0, [])
        
        mock_clear_screen.assert_called_once()
        mock_print_instructions.assert_called_once()
        mock_print_table.assert_called_once()