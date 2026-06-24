"""
Interactive navigation tests with mocked input.
"""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, call
import readchar
from sshmenuc.core.navigation import ConnectionNavigator


@pytest.fixture
def multi_category_config_file():
    """Config with 3 categories to allow navigating past index 0."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "targets": [
                {"Alpha": [{"friendly": "a1", "host": "a1.example.com", "user": "u"}]},
                {"Beta":  [{"friendly": "b1", "host": "b1.example.com", "user": "u"}]},
                {"Gamma": [{"friendly": "g1", "host": "g1.example.com", "user": "u"}]},
            ]
        }
        json.dump(config_data, f, indent=2)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestNavigationInteractive:
    """Test interactive navigation with keyboard input."""

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_quit_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation exits on 'q' key confirmed with 'y'."""
        mock_readkey.side_effect = ['q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_print_menu.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_down_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles DOWN key."""
        mock_readkey.side_effect = [readchar.key.DOWN, readchar.key.DOWN, 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        assert mock_print_menu.call_count == 3

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_up_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles UP key."""
        mock_readkey.side_effect = [readchar.key.UP, 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        assert mock_print_menu.call_count == 2

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_left_key(self, mock_print_menu, mock_readkey, temp_config_file):
        """Test navigation handles LEFT key."""
        mock_readkey.side_effect = [readchar.key.LEFT, 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        # marked_indices should be cleared
        assert len(navigator.marked_indices) == 0

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_selection')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_space_key(self, mock_print_menu, mock_handle_selection, mock_readkey, temp_config_file):
        """Test navigation handles SPACE key for selection."""
        mock_readkey.side_effect = [' ', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_selection.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_enter')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_enter_key(self, mock_print_menu, mock_handle_enter, mock_readkey, temp_config_file):
        """Test navigation handles ENTER key."""
        mock_readkey.side_effect = [readchar.key.ENTER, 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_enter.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_add')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_add_key(self, mock_print_menu, mock_handle_add, mock_readkey, temp_config_file):
        """Test navigation handles 'a' key for add."""
        mock_readkey.side_effect = ['a', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_add.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_edit')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_edit_key(self, mock_print_menu, mock_handle_edit, mock_readkey, temp_config_file):
        """Test navigation handles 'e' key for edit."""
        mock_readkey.side_effect = ['e', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_edit.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_delete')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_delete_key(self, mock_print_menu, mock_handle_delete, mock_readkey, temp_config_file):
        """Test navigation handles 'd' key for delete."""
        mock_readkey.side_effect = ['d', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

        mock_handle_delete.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_rename')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_navigate_rename_key(self, mock_print_menu, mock_handle_rename, mock_readkey, temp_config_file):
        """Test navigation handles 'r' key for rename."""
        mock_readkey.side_effect = ['r', 'q', 'y']
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


class TestCursorReset:
    """Tests for issue #3: cursor must reset to 0 when entering a sub-menu."""

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_cursor_resets_to_zero_after_entering_submenu(
        self, mock_print_menu, mock_readkey, multi_category_config_file
    ):
        """Entering a sub-menu via ENTER must reset selected_target to 0.

        Steps: DOWN x2 (cursor at 2) → ENTER (navigate to Gamma) → q
        The print_menu call AFTER navigation must be invoked with selected_target=0.
        """
        mock_readkey.side_effect = [
            readchar.key.DOWN,   # cursor → 1
            readchar.key.DOWN,   # cursor → 2
            readchar.key.ENTER,  # enter Gamma group (path = [2])
            'q', 'y',            # exit with confirmation
        ]
        navigator = ConnectionNavigator(multi_category_config_file)
        navigator.navigate()

        # print_menu is called at the TOP of each loop iteration.
        # Calls: (0,[]) → (1,[]) → (2,[]) → (AFTER ENTER: must be 0,[2]) → exits on q
        calls = mock_print_menu.call_args_list
        assert len(calls) == 4
        # The 4th call (index 3) is the first render inside the sub-menu — cursor MUST be 0
        selected_after_enter = calls[3][0][0]  # positional arg 0 of 4th call
        assert selected_after_enter == 0, (
            f"Expected cursor=0 after entering sub-menu, got {selected_after_enter}"
        )

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_cursor_at_zero_unaffected_by_enter(
        self, mock_print_menu, mock_readkey, multi_category_config_file
    ):
        """When cursor is already at 0 and ENTER is pressed, cursor stays 0 after navigation."""
        mock_readkey.side_effect = [
            readchar.key.ENTER,  # enter Alpha group (cursor was 0, path = [0])
            'q', 'y',
        ]
        navigator = ConnectionNavigator(multi_category_config_file)
        navigator.navigate()

        calls = mock_print_menu.call_args_list
        assert len(calls) == 2
        selected_after_enter = calls[1][0][0]
        assert selected_after_enter == 0


class TestQuitConfirmation:
    """Tests for issue #4: pressing q must ask for confirmation before exiting."""

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_quit_confirmed_with_y(self, mock_print_menu, mock_readkey, temp_config_file):
        """Pressing q then y should exit: readkey must be called twice (q + confirmation)."""
        mock_readkey.side_effect = ['q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
        # readkey must be called twice: once for 'q', once to read the confirmation key
        assert mock_readkey.call_count == 2
        mock_print_menu.assert_called_once()

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_quit_cancelled_with_n_stays_in_menu(
        self, mock_print_menu, mock_readkey, temp_config_file
    ):
        """Pressing q then n should cancel the exit and remain in the navigation loop."""
        mock_readkey.side_effect = ['q', 'n', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
        # print_menu is called twice: once before q-n (cancel), once before q-y (confirm)
        assert mock_print_menu.call_count == 2

    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_quit_confirmed_with_uppercase_Y(
        self, mock_print_menu, mock_readkey, temp_config_file
    ):
        """Pressing q then Y (uppercase) should also exit: readkey called twice."""
        mock_readkey.side_effect = ['q', 'Y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
        assert mock_readkey.call_count == 2
        mock_print_menu.assert_called_once()

    @patch('sshmenuc.core.navigation.puts')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_quit_prints_prompt(self, mock_print_menu, mock_readkey, mock_puts, temp_config_file):
        """Pressing q must display a visible confirmation prompt."""
        mock_readkey.side_effect = ['q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
        # puts must be called at least once to show the prompt
        assert mock_puts.called
        # The prompt must contain 'Uscire?' and '[y/N]'
        all_args = ' '.join(str(c) for c in mock_puts.call_args_list)
        assert 'Uscire?' in all_args
        assert '[y/N]' in all_args

    @patch('sshmenuc.core.navigation.puts')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    @patch('sshmenuc.core.navigation.ConnectionNavigator._run_startup_pull')
    def test_quit_prompt_shows_decrypt_warning_when_sync_configured(
        self, mock_startup, mock_print_menu, mock_readkey, mock_puts, temp_config_file
    ):
        """When sync is configured, quit prompt must warn about decrypt password on next startup."""
        mock_readkey.side_effect = ['q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.sync_manager._sync_cfg = {"remote_url": "git@github.com:user/repo.git"}
        navigator.navigate()
        all_args = ' '.join(str(c) for c in mock_puts.call_args_list)
        assert 'decrypt' in all_args.lower() or 'password' in all_args.lower()

    @patch('sshmenuc.core.navigation.puts')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_quit_prompt_no_decrypt_warning_without_sync(
        self, mock_print_menu, mock_readkey, mock_puts, temp_config_file
    ):
        """Without sync configured, the quit prompt must NOT mention decrypt/password."""
        mock_readkey.side_effect = ['q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
        all_args = ' '.join(str(c) for c in mock_puts.call_args_list)
        assert 'decrypt' not in all_args.lower()
        assert 'password' not in all_args.lower()


class TestKeyboardInterruptHandling:
    """Tests for graceful Ctrl+C handling in all input() calls.

    Regression for crash: pressing Ctrl+C during 'Press Enter to continue...'
    caused an unhandled KeyboardInterrupt traceback instead of returning to menu.
    """

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_add')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_ctrl_c_during_handle_add_does_not_crash(
        self, mock_print_menu, mock_readkey, mock_handle_add, mock_input, temp_config_file
    ):
        """Ctrl+C during _handle_add must not propagate as uncaught KeyboardInterrupt."""
        mock_handle_add.side_effect = KeyboardInterrupt
        mock_readkey.side_effect = ['a', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()  # must complete without raising
        mock_print_menu.call_count >= 2

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_edit')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_ctrl_c_during_handle_edit_does_not_crash(
        self, mock_print_menu, mock_readkey, mock_handle_edit, mock_input, temp_config_file
    ):
        """Ctrl+C during _handle_edit must not crash."""
        mock_handle_edit.side_effect = KeyboardInterrupt
        mock_readkey.side_effect = ['e', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_delete')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_ctrl_c_during_handle_delete_does_not_crash(
        self, mock_print_menu, mock_readkey, mock_handle_delete, mock_input, temp_config_file
    ):
        """Ctrl+C during _handle_delete must not crash."""
        mock_handle_delete.side_effect = KeyboardInterrupt
        mock_readkey.side_effect = ['d', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_rename')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_ctrl_c_during_handle_rename_does_not_crash(
        self, mock_print_menu, mock_readkey, mock_handle_rename, mock_input, temp_config_file
    ):
        """Ctrl+C during _handle_rename must not crash."""
        mock_handle_rename.side_effect = KeyboardInterrupt
        mock_readkey.side_effect = ['r', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('sshmenuc.core.navigation.ConnectionNavigator._handle_sync_status')
    @patch('readchar.readkey')
    @patch('sshmenuc.core.navigation.ConnectionNavigator.print_menu')
    def test_ctrl_c_during_sync_status_does_not_crash(
        self, mock_print_menu, mock_readkey, mock_sync, mock_input, temp_config_file
    ):
        """Ctrl+C during sync status panel must not crash."""
        mock_sync.side_effect = KeyboardInterrupt
        mock_readkey.side_effect = ['s', 'q', 'y']
        navigator = ConnectionNavigator(temp_config_file)
        navigator.navigate()
