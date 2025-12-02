"""
Tests for SSHLauncher class.
"""
import pytest
from unittest.mock import patch, MagicMock
from sshmenuc.core.launcher import SSHLauncher


class TestSSHLauncher:
    
    def test_init(self):
        """Test SSHLauncher initialization."""
        launcher = SSHLauncher("test.com", "user", 2222, "/path/to/key")
        assert launcher.host == "test.com"
        assert launcher.username == "user"
        assert launcher.port == 2222
        assert launcher.identity_file == "/path/to/key"
    
    def test_init_defaults(self):
        """Test SSHLauncher initialization with defaults."""
        launcher = SSHLauncher("test.com", "user")
        assert launcher.host == "test.com"
        assert launcher.username == "user"
        assert launcher.port == 22
        assert launcher.identity_file is None
    
    def test_sanitize_session_name(self):
        """Test session name sanitization."""
        launcher = SSHLauncher("test.com", "user")
        
        # Test normal case
        assert launcher._sanitize_session_name("test-host") == "test-host"
        
        # Test with special characters
        assert launcher._sanitize_session_name("test@host.com:22") == "test-host-com-22"
        
        # Test with spaces and symbols
        assert launcher._sanitize_session_name("test host & server") == "test-host-server"
    
    @patch('subprocess.run')
    def test_list_tmux_sessions_success(self, mock_run):
        """Test listing tmux sessions successfully."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "session1: 1 windows\nsession2: 2 windows\n"
        
        launcher = SSHLauncher("test.com", "user")
        sessions = launcher._list_tmux_sessions()
        
        assert sessions == ["session1", "session2"]
    
    @patch('subprocess.run')
    def test_list_tmux_sessions_failure(self, mock_run):
        """Test listing tmux sessions when tmux fails."""
        mock_run.return_value.returncode = 1
        
        launcher = SSHLauncher("test.com", "user")
        sessions = launcher._list_tmux_sessions()
        
        assert sessions == []
    
    def test_build_ssh_command_basic(self):
        """Test building basic SSH command."""
        launcher = SSHLauncher("test.com", "user")
        cmd = launcher._build_ssh_command()
        
        expected = ["ssh", "user@test.com", "-p", "22"]
        assert cmd == expected
    
    def test_build_ssh_command_with_identity(self):
        """Test building SSH command with identity file."""
        launcher = SSHLauncher("test.com", "user", 22, "/path/to/key")
        cmd = launcher._build_ssh_command()
        
        expected = ["ssh", "-i", "/path/to/key", "user@test.com", "-p", "22"]
        assert cmd == expected
    
    @patch('subprocess.run')
    def test_handle_existing_sessions_none(self, mock_run):
        """Test handling when no existing sessions."""
        launcher = SSHLauncher("test.com", "user")
        launcher._list_tmux_sessions = MagicMock(return_value=[])
        result = launcher._handle_existing_sessions("test-com")
        assert result is False
    
    @patch('subprocess.run')
    @patch('builtins.input', return_value='a')
    def test_handle_existing_sessions_single_attach(self, mock_input, mock_run):
        """Test handling single existing session with attach choice."""
        launcher = SSHLauncher("test.com", "user")
        launcher._list_tmux_sessions = MagicMock(return_value=["test-com-123"])
        
        result = launcher._handle_existing_sessions("test-com")
        assert result is True
        mock_run.assert_called_once()
    
    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('logging.getLogger')
    def test_launch_without_tmux(self, mock_logger, mock_run, mock_which):
        """Test launching without tmux available."""
        mock_which.return_value = None
        mock_logger.return_value.level = 30  # WARNING level
        
        launcher = SSHLauncher("test.com", "user")
        launcher.launch()
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["ssh", "user@test.com", "-p", "22"]
    
    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('builtins.print')
    def test_launch_group_without_tmux(self, mock_print, mock_run, mock_which):
        """Test launching group without tmux."""
        mock_which.return_value = None
        
        hosts = [{"host": "test.com", "user": "user"}]
        SSHLauncher.launch_group(hosts)
        
        # Should not call subprocess.run since tmux is not available
        mock_run.assert_not_called()
    
    def test_launch_group_empty_hosts(self):
        """Test launching group with empty host list."""
        # Should not raise exception
        SSHLauncher.launch_group([])
    
    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('os.getlogin')
    @patch('clint.textui.puts')
    def test_launch_group_max_hosts(self, mock_puts, mock_getlogin, mock_run, mock_which):
        """Test launching group with more than 6 hosts."""
        mock_which.return_value = "/usr/bin/tmux"
        mock_getlogin.return_value = "testuser"
        
        hosts = [{"host": f"host{i}.com", "user": "user"} for i in range(8)]
        SSHLauncher.launch_group(hosts)
        
        # Should be called 4 times: new-session + 5 split-window + select-layout + attach-session
        assert mock_run.call_count == 8