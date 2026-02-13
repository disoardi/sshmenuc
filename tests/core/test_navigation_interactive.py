"""
Interactive navigation tests with mocked input.
"""
import pytest
from unittest.mock import patch, MagicMock, call
import readchar
from sshmenuc.core.navigation import ConnectionNavigator


class TestNavigationInteractive:
    """Test interactive navigation with keyboard input."""

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_quit_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation exits on 'q' key."""
        mock_readkey.return_value = 'q'
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_print_menu.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_down_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles DOWN key."""
        mock_readkey.side_effect = [readchar.key.DOWN, readchar.key.DOWN, 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        assert mock_print_menu.call_count == 3

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_up_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles UP key."""
        mock_readkey.side_effect = [readchar.key.UP, 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        assert mock_print_menu.call_count == 2

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_left_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles LEFT key."""
        mock_readkey.side_effect = [readchar.key.LEFT, 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        # marked_indices should be cleared
        assert len(navigator.marked_indices) == 0

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_selection')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_space_key(self, mock_print_menu, mock_handle_selection, mock_readkey, temp_config_file):
        """Test navigation handles SPACE key for selection."""
        mock_readkey.side_effect = [' ', 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_selection.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_enter')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_enter_key(self, mock_print_menu, mock_handle_enter, mock_readkey, temp_config_file):
        """Test navigation handles ENTER key."""
        mock_readkey.side_effect = [readchar.key.ENTER, 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_enter.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_add')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_add_key(self, mock_print_menu, mock_handle_add, mock_readkey, temp_config_file):
        """Test navigation handles 'a' key for add."""
        mock_readkey.side_effect = ['a', 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_add.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_edit')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_edit_key(self, mock_print_menu, mock_handle_edit, mock_readkey, temp_config_file):
        """Test navigation handles 'e' key for edit."""
        mock_readkey.side_effect = ['e', 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_edit.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_delete')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_delete_key(self, mock_print_menu, mock_handle_delete, mock_readkey, temp_config_file):
        """Test navigation handles 'd' key for delete."""
        mock_readkey.side_effect = ['d', 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_delete.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_rename')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_rename_key(self, mock_print_menu, mock_handle_rename, mock_readkey, temp_config_file):
        """Test navigation handles 'r' key for rename."""
        mock_readkey.side_effect = ['r', 'q']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_rename.assert_called_once()

    @patch('sshmenuc.core.navigation.puts')
    def test_launch_multiple_hosts_no_valid(self, mock_puts, temp_config_file):
        """Test launching multiple hosts with no valid hosts selected."""
        navigator = ConnectionNavigator(temp_config_file)
        node = [{"invalid": "entry"}]
        navigator.marked_indices = {0}

        navigator._launch_multiple_hosts(node)

        # Should print error message
        assert mock_puts.called

    @patch('os.getlogin', return_value='testuser')
    @patch('sshmenuc.core.launcher.SSHLauncher.launch_group')
    def test_launch_multiple_hosts_valid(self, mock_launch_group, mock_getlogin, temp_config_file):
        """Test launching multiple valid hosts."""
        navigator = ConnectionNavigator(temp_config_file)
        node = [
            {"friendly": "host1", "host": "host1.com", "user": "user1"},
            {"friendly": "host2", "host": "host2.com", "user": "user2"}
        ]
        navigator.marked_indices = {0, 1}

        navigator._launch_multiple_hosts(node)

        mock_launch_group.assert_called_once()
        # Check that marked_indices is cleared
        assert len(navigator.marked_indices) == 0
