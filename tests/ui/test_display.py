"""
Tests for MenuDisplay class.
"""
import pytest
from unittest.mock import patch
from sshmenuc.ui.display import MenuDisplay


class TestMenuDisplay:
    
    def test_init(self):
        """Test MenuDisplay initialization."""
        display = MenuDisplay()
        assert display.colors is not None
    
    @patch('os.system')
    def test_clear_screen_unix(self, mock_system):
        """Test clear screen on Unix systems."""
        with patch('os.name', 'posix'):
            display = MenuDisplay()
            display.clear_screen()
            mock_system.assert_called_once_with('clear')
    
    @patch('os.system')
    def test_clear_screen_windows(self, mock_system):
        """Test clear screen on Windows systems."""
        with patch('os.name', 'nt'):
            display = MenuDisplay()
            display.clear_screen()
            mock_system.assert_called_once_with('cls')
    
    @patch('builtins.print')
    def test_print_instructions(self, mock_print):
        """Test printing instructions."""
        display = MenuDisplay()
        display.print_instructions()
        mock_print.assert_called_once()
        args = mock_print.call_args[0][0]
        assert "Navigate:" in args
        assert "SPACE" in args
        assert "ENTER" in args
        assert "[a]dd" in args
        assert "[e]dit" in args
        assert "[d]elete" in args
        assert "[r]ename" in args
    
    @patch('builtins.print')
    def test_print_header(self, mock_print):
        """Test printing table header."""
        display = MenuDisplay()
        display.print_header(["Description"])
        
        # Should print 3 lines: top border, header, bottom border
        assert mock_print.call_count == 3
    
    @patch('builtins.print')
    def test_print_row_category(self, mock_print):
        """Test printing category row."""
        display = MenuDisplay()
        display.print_row([0, "Test Category"], True, False, False)
        
        mock_print.assert_called_once()
        printed_text = mock_print.call_args[0][0]
        assert "Test Category" in printed_text
    
    @patch('builtins.print')
    def test_print_row_host_marked(self, mock_print):
        """Test printing marked host row."""
        display = MenuDisplay()
        host_dict = {"friendly": "test-host", "host": "test.com"}
        display.print_row([0, host_dict], False, True, True)
        
        mock_print.assert_called_once()
        printed_text = mock_print.call_args[0][0]
        assert "test-host" in printed_text
        assert "[x]" in printed_text
    
    @patch('builtins.print')
    def test_print_row_host_unmarked(self, mock_print):
        """Test printing unmarked host row."""
        display = MenuDisplay()
        host_dict = {"friendly": "test-host", "host": "test.com"}
        display.print_row([0, host_dict], False, True, False)
        
        mock_print.assert_called_once()
        printed_text = mock_print.call_args[0][0]
        assert "test-host" in printed_text
        assert "[ ]" in printed_text
    
    @patch('builtins.print')
    def test_print_footer(self, mock_print):
        """Test printing table footer."""
        display = MenuDisplay()
        display.print_footer()
        
        mock_print.assert_called_once()
        printed_text = mock_print.call_args[0][0]
        assert "+" in printed_text
        assert "-" in printed_text
    
    @patch('builtins.print')
    def test_print_table_dict(self, mock_print):
        """Test printing table with dictionary data."""
        display = MenuDisplay()
        data = {"Category1": [], "Category2": []}
        display.print_table(data, 0, set(), 0)
        
        # Should print header + 2 rows + footer
        assert mock_print.call_count >= 4
    
    @patch('builtins.print')
    def test_print_table_list(self, mock_print):
        """Test printing table with list data."""
        display = MenuDisplay()
        data = [
            {"friendly": "host1", "host": "host1.com"},
            {"friendly": "host2", "host": "host2.com"}
        ]
        display.print_table(data, 0, {1}, 0)
        
        # Should print header + 2 rows + footer
        assert mock_print.call_count >= 4
    
    @patch('builtins.print')
    def test_print_table_empty_list(self, mock_print):
        """Test printing table with empty list."""
        display = MenuDisplay()
        display.print_table([], 0, set(), 0)
        
        # Should print header + footer only
        assert mock_print.call_count >= 2