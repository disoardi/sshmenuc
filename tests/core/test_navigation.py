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
    
    @patch('sshmenuc.core.navigation.SSHLauncher')
    @patch('os.getlogin')
    def test_handle_single_selection_custom_port(self, mock_getlogin, mock_launcher_class, temp_config_file):
        """Test that custom port is read from config and passed to SSHLauncher."""
        mock_getlogin.return_value = "testuser"
        navigator = ConnectionNavigator(temp_config_file)
        node = [{"friendly": "test", "host": "test.com", "user": "testuser", "port": 2222}]

        navigator._handle_single_selection(node, 0, [0])

        mock_launcher_class.assert_called_once_with("test.com", "testuser", 2222, None, None)

    @patch('sshmenuc.core.navigation.SSHLauncher')
    @patch('os.getlogin')
    def test_handle_single_selection_extra_args(self, mock_getlogin, mock_launcher_class, temp_config_file):
        """Test that extra_args is read from config and passed to SSHLauncher."""
        mock_getlogin.return_value = "testuser"
        navigator = ConnectionNavigator(temp_config_file)
        node = [{"friendly": "test", "host": "test.com", "user": "testuser", "extra_args": "-t bash"}]

        navigator._handle_single_selection(node, 0, [0])

        mock_launcher_class.assert_called_once_with("test.com", "testuser", 22, None, "-t bash")

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


class TestContextManagement:
    """Tests for context management methods: _switch_to_context, _handle_context_manage,
    _handle_new_context, _handle_edit_context_sync."""

    def _make_navigator_with_context_manager(self, temp_config_file):
        """Return a navigator wired with a mock ContextManager."""
        ctx_mgr = MagicMock()
        ctx_mgr.list_contexts.return_value = ["home", "isp"]
        ctx_mgr.get_sync_cfg.return_value = {
            "remote_url": "git@github.com:user/cfg.git",
            "branch": "main",
            "remote_file": "home.enc",
            "sync_repo_path": "/tmp/sync_repo",
            "auto_pull": True,
            "auto_push": True,
        }
        ctx_mgr.get_config_file.return_value = temp_config_file

        nav = ConnectionNavigator(
            temp_config_file,
            context_manager=ctx_mgr,
            active_context="home",
        )
        return nav, ctx_mgr

    # ------------------------------------------------------------------
    # _switch_to_context
    # ------------------------------------------------------------------

    def test_switch_to_context_success(self, temp_config_file):
        """_switch_to_context returns True and updates _active_context on success."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        mock_sm = MagicMock()
        mock_sm.startup_pull.return_value = MagicMock()  # truthy
        mock_sm.get_config_data.return_value = None

        from sshmenuc.sync import SyncState
        mock_sm.startup_pull.return_value = SyncState.SYNC_OK

        with patch("sshmenuc.core.navigation.SyncManager", return_value=mock_sm):
            result = nav._switch_to_context("isp")

        assert result is True
        assert nav._active_context == "isp"
        ctx_mgr.set_active.assert_called_once_with("isp")

    def test_switch_to_context_failure(self, temp_config_file):
        """_switch_to_context returns False and keeps previous context when pull fails."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        mock_sm = MagicMock()
        from sshmenuc.sync import SyncState
        mock_sm.startup_pull.return_value = SyncState.LOCAL_ONLY

        with patch("sshmenuc.core.navigation.SyncManager", return_value=mock_sm):
            result = nav._switch_to_context("isp")

        assert result is False
        assert nav._active_context == "home"

    # ------------------------------------------------------------------
    # _handle_context_manage
    # ------------------------------------------------------------------

    def test_handle_context_manage_cancel(self, temp_config_file):
        """Empty input cancels _handle_context_manage without side effects."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value=""):
            nav._handle_context_manage()  # should not raise

        ctx_mgr.add_context.assert_not_called()
        ctx_mgr.update_sync_config.assert_not_called()

    def test_handle_context_manage_choice_new_context(self, temp_config_file):
        """Choice '1' in _handle_context_manage triggers _handle_new_context."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value="1"), \
             patch.object(nav, "_handle_new_context") as mock_new:
            nav._handle_context_manage()

        mock_new.assert_called_once()

    def test_handle_context_manage_choice_selects_context(self, temp_config_file):
        """Choice '2' selects the first context and calls _handle_context_actions."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value="2"), \
             patch.object(nav, "_handle_context_actions") as mock_actions:
            nav._handle_context_manage()

        mock_actions.assert_called_once_with("home")

    def test_handle_context_manage_invalid_input(self, temp_config_file):
        """Non-numeric input in _handle_context_manage is silently ignored."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value="xyz"):
            nav._handle_context_manage()  # should not raise

    # ------------------------------------------------------------------
    # _handle_new_context
    # ------------------------------------------------------------------

    def test_handle_new_context_cancel_on_empty_name(self, temp_config_file):
        """Empty name cancels _handle_new_context without creating anything."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value=""):
            nav._handle_new_context()

        ctx_mgr.add_context.assert_not_called()

    def test_handle_new_context_reject_duplicate(self, temp_config_file):
        """Existing context name is rejected in _handle_new_context."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)
        # "home" is already in list_contexts()

        with patch("builtins.input", side_effect=["home", ""]):
            nav._handle_new_context()

        ctx_mgr.add_context.assert_not_called()

    def test_handle_new_context_creates_and_offers_switch(self, temp_config_file):
        """Successful wizard creation offers an immediate context switch."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("sshmenuc.core.navigation.ConnectionNavigator._handle_new_context",
                   wraps=nav._handle_new_context):
            # Inputs: name, then "n" for switch offer, then Enter to continue
            with patch("builtins.input", side_effect=["newctx", "n", ""]), \
                 patch("sshmenuc.contexts.wizard.add_context_wizard", return_value=True) as mock_wizard, \
                 patch.object(nav, "_switch_to_context") as mock_switch:
                nav._handle_new_context()

        mock_wizard.assert_called_once_with("newctx")
        mock_switch.assert_not_called()  # user declined switch

    def test_handle_new_context_switches_when_confirmed(self, temp_config_file):
        """When user confirms switch after creation, _switch_to_context is called."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", side_effect=["newctx", "s", ""]), \
             patch("sshmenuc.contexts.wizard.add_context_wizard", return_value=True), \
             patch.object(nav, "_switch_to_context") as mock_switch:
            nav._handle_new_context()

        mock_switch.assert_called_once_with("newctx")

    # ------------------------------------------------------------------
    # _handle_edit_context_sync
    # ------------------------------------------------------------------

    def test_edit_context_sync_no_changes_on_empty_input(self, temp_config_file):
        """No update when user presses Enter for all three fields."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        # url, branch, remote_file all empty → no update; last "" is Enter to continue
        with patch("builtins.input", side_effect=["", "", "", ""]):
            nav._handle_edit_context_sync("isp")

        ctx_mgr.update_sync_config.assert_not_called()

    def test_edit_context_sync_updates_inactive_context(self, temp_config_file):
        """update_sync_config is called with the right partial dict for an inactive context."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)
        nav._active_context = "home"  # "isp" is not active

        # url, branch (empty), remote_file (empty), Enter to continue
        with patch("builtins.input", side_effect=["git@github.com:new/repo.git", "", "", ""]):
            nav._handle_edit_context_sync("isp")

        ctx_mgr.update_sync_config.assert_called_once_with(
            "isp", {"remote_url": "git@github.com:new/repo.git"}
        )

    def test_edit_context_sync_updates_only_branch(self, temp_config_file):
        """Only branch is updated when URL and remote_file fields are left empty."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)
        nav._active_context = "home"

        with patch("builtins.input", side_effect=["", "develop", "", ""]):
            nav._handle_edit_context_sync("isp")

        ctx_mgr.update_sync_config.assert_called_once_with("isp", {"branch": "develop"})

    def test_edit_context_sync_updates_remote_file(self, temp_config_file):
        """remote_file is updated when provided; other fields left empty."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)
        nav._active_context = "home"

        with patch("builtins.input", side_effect=["", "", "isp.enc", ""]):
            nav._handle_edit_context_sync("isp")

        ctx_mgr.update_sync_config.assert_called_once_with("isp", {"remote_file": "isp.enc"})

    def test_edit_active_context_sync_reinitializes_sync_manager(self, temp_config_file):
        """Editing the active context reinitializes the SyncManager in-session."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)
        old_sm = nav.sync_manager

        # url, branch (empty), remote_file (empty), Enter to continue
        with patch("builtins.input", side_effect=["git@github.com:new/repo.git", "", "", ""]), \
             patch("sshmenuc.core.navigation.SyncManager") as MockSM:
            MockSM.return_value = MagicMock()
            nav._handle_edit_context_sync("home")  # "home" is the active context

        assert nav.sync_manager is not old_sm
        MockSM.assert_called_once()

    # ------------------------------------------------------------------
    # _handle_context_actions
    # ------------------------------------------------------------------

    def test_handle_context_actions_cancel(self, temp_config_file):
        """Empty input in _handle_context_actions cancels without side effects."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value=""):
            nav._handle_context_actions("isp")

        ctx_mgr.update_sync_config.assert_not_called()

    def test_handle_context_actions_m_calls_edit_sync(self, temp_config_file):
        """Choice 'm' in _handle_context_actions calls _handle_edit_context_sync."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value="m"), \
             patch.object(nav, "_handle_edit_context_sync") as mock_edit:
            nav._handle_context_actions("isp")

        mock_edit.assert_called_once_with("isp")

    def test_handle_context_actions_i_calls_reimport(self, temp_config_file):
        """Choice 'i' in _handle_context_actions calls _handle_reimport_context."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value="i"), \
             patch.object(nav, "_handle_reimport_context") as mock_reimport:
            nav._handle_context_actions("isp")

        mock_reimport.assert_called_once_with("isp")

    # ------------------------------------------------------------------
    # _handle_reimport_context
    # ------------------------------------------------------------------

    def test_reimport_context_file_not_found(self, temp_config_file):
        """_handle_reimport_context shows error and returns when file is missing."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", side_effect=["/nonexistent/file.json", ""]):
            nav._handle_reimport_context("isp")

        ctx_mgr.update_context_meta.assert_not_called()

    def test_reimport_context_cancel_on_empty_path(self, temp_config_file):
        """Empty file path cancels reimport without any side effects."""
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        with patch("builtins.input", return_value=""):
            nav._handle_reimport_context("isp")

        ctx_mgr.update_context_meta.assert_not_called()

    def test_reimport_context_updates_active_context_in_memory(self, tmp_path, temp_config_file):
        """Reimporting the active context updates in-memory config immediately."""
        import json
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        # Write a plaintext JSON source file
        src = tmp_path / "import_me.json"
        config_data = {"targets": [{"ISP": [{"friendly": "router", "host": "192.168.1.1"}]}]}
        src.write_text(json.dumps(config_data))

        ctx_mgr.get_enc_file.return_value = str(tmp_path / "home.enc")
        ctx_mgr.get_sync_cfg.return_value = {}  # no remote_url → skip push prompt

        with patch("builtins.input", side_effect=[str(src), "n", ""]), \
             patch("sshmenuc.sync.passphrase_cache.get_or_prompt", return_value="secret"), \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENC"):
            nav._handle_reimport_context("home")  # "home" is active

        assert nav.sync_manager._config_data == config_data
        ctx_mgr.update_context_meta.assert_called_once()

    def test_reimport_context_deletes_source_when_confirmed(self, tmp_path, temp_config_file):
        """Source file is deleted after reimport when user confirms."""
        import json
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        src = tmp_path / "plain.json"
        src.write_text(json.dumps({"targets": []}))

        ctx_mgr.get_enc_file.return_value = str(tmp_path / "home.enc")
        ctx_mgr.get_sync_cfg.return_value = {}

        with patch("builtins.input", side_effect=[str(src), "s", ""]), \
             patch("sshmenuc.sync.passphrase_cache.get_or_prompt", return_value="secret"), \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENC"):
            nav._handle_reimport_context("home")

        assert not src.exists(), "Source file should be deleted when user confirms"

    def test_reimport_context_keeps_source_when_declined(self, tmp_path, temp_config_file):
        """Source file is kept after reimport when user declines deletion."""
        import json
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        src = tmp_path / "plain.json"
        src.write_text(json.dumps({"targets": []}))

        ctx_mgr.get_enc_file.return_value = str(tmp_path / "home.enc")
        ctx_mgr.get_sync_cfg.return_value = {}

        with patch("builtins.input", side_effect=[str(src), "n", ""]), \
             patch("sshmenuc.sync.passphrase_cache.get_or_prompt", return_value="secret"), \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENC"):
            nav._handle_reimport_context("home")

        assert src.exists(), "Source file should be kept when user declines"

    def test_reimport_context_pushes_to_remote_when_confirmed(self, tmp_path, temp_config_file):
        """push_remote is called when user confirms push after reimport."""
        import json
        nav, ctx_mgr = self._make_navigator_with_context_manager(temp_config_file)

        src = tmp_path / "plain.json"
        src.write_text(json.dumps({"targets": []}))

        ctx_mgr.get_enc_file.return_value = str(tmp_path / "home.enc")
        ctx_mgr.get_sync_cfg.return_value = {
            "remote_url": "git@github.com:user/cfg.git",
            "branch": "main",
            "remote_file": "home.enc",
            "sync_repo_path": str(tmp_path / "repo"),
        }

        with patch("builtins.input", side_effect=[str(src), "n", "s", ""]), \
             patch("sshmenuc.sync.passphrase_cache.get_or_prompt", return_value="secret"), \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENC"), \
             patch("sshmenuc.sync.git_remote.ensure_repo_initialized", return_value=True) as mock_init, \
             patch("sshmenuc.sync.git_remote.push_remote", return_value=True) as mock_push:
            nav._handle_reimport_context("home")

        mock_init.assert_called_once()
        mock_push.assert_called_once()