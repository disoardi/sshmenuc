"""
Tests for Colors class.
"""
import pytest
from sshmenuc.ui.colors import Colors


class TestColors:
    
    def test_color_constants(self):
        """Test that color constants are defined."""
        assert Colors.HEADER == "\033[95m"
        assert Colors.OKBLUE == "\033[94m"
        assert Colors.OKCYAN == "\033[96m"
        assert Colors.OKGREEN == "\033[92m"
        assert Colors.WARNING == "\033[93m"
        assert Colors.FAIL == "\033[91m"
        assert Colors.ENDC == "\033[0m"
        assert Colors.BOLD == "\033[1m"
        assert Colors.UNDERLINE == "\033[4m"
    
    def test_colorize(self):
        """Test colorize method."""
        text = "test text"
        colored = Colors.colorize(text, Colors.OKGREEN)
        expected = f"{Colors.OKGREEN}{text}{Colors.ENDC}"
        assert colored == expected
    
    def test_header(self):
        """Test header method."""
        text = "header text"
        colored = Colors.header(text)
        expected = f"{Colors.HEADER}{text}{Colors.ENDC}"
        assert colored == expected
    
    def test_success(self):
        """Test success method."""
        text = "success text"
        colored = Colors.success(text)
        expected = f"{Colors.OKGREEN}{text}{Colors.ENDC}"
        assert colored == expected
    
    def test_warning(self):
        """Test warning method."""
        text = "warning text"
        colored = Colors.warning(text)
        expected = f"{Colors.WARNING}{text}{Colors.ENDC}"
        assert colored == expected
    
    def test_error(self):
        """Test error method."""
        text = "error text"
        colored = Colors.error(text)
        expected = f"{Colors.FAIL}{text}{Colors.ENDC}"
        assert colored == expected
    
    def test_colorize_empty_string(self):
        """Test colorizing empty string."""
        colored = Colors.colorize("", Colors.OKGREEN)
        expected = f"{Colors.OKGREEN}{Colors.ENDC}"
        assert colored == expected
    
    def test_colorize_multiline(self):
        """Test colorizing multiline text."""
        text = "line1\nline2\nline3"
        colored = Colors.colorize(text, Colors.OKBLUE)
        expected = f"{Colors.OKBLUE}{text}{Colors.ENDC}"
        assert colored == expected