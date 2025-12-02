"""
Tests for helper functions.
"""
import pytest
import argparse
import logging
from unittest.mock import patch
from sshmenuc.utils.helpers import (
    setup_argument_parser,
    setup_logging,
    get_default_config_path,
    validate_host_entry
)


class TestHelpers:
    
    def test_setup_argument_parser(self):
        """Test argument parser setup."""
        parser = setup_argument_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        
        # Test parsing with default values
        args = parser.parse_args([])
        assert args.config.endswith('config.json')
        assert args.loglevel == 'default'
        
        # Test parsing with custom values
        args = parser.parse_args(['-c', 'custom.json', '-l', 'debug'])
        assert args.config == 'custom.json'
        assert args.loglevel == 'debug'
    
    def test_setup_logging_debug(self):
        """Test logging setup with debug level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('debug')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.DEBUG)
    
    def test_setup_logging_info(self):
        """Test logging setup with info level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('info')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.INFO)
    
    def test_setup_logging_warning(self):
        """Test logging setup with warning level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('warning')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.WARNING)
    
    def test_setup_logging_error(self):
        """Test logging setup with error level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('error')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.ERROR)
    
    def test_setup_logging_critical(self):
        """Test logging setup with critical level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('critical')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.CRITICAL)
    
    def test_setup_logging_default(self):
        """Test logging setup with default level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('default')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.INFO)
    
    def test_setup_logging_invalid(self):
        """Test logging setup with invalid level."""
        with patch('logging.basicConfig') as mock_config:
            setup_logging('invalid')
            mock_config.assert_called_with(stream=logging.sys.stderr, level=logging.INFO)
    
    def test_get_default_config_path(self):
        """Test getting default config path."""
        path = get_default_config_path()
        assert path.endswith('.config/sshmenuc/config.json')
        assert path.startswith('/')
    
    def test_validate_host_entry_valid(self, sample_host_entry):
        """Test validating valid host entry."""
        # Remove invalid field for this test
        valid_entry = {k: v for k, v in sample_host_entry.items() if k != 'connection_type'}
        assert validate_host_entry(valid_entry) is True
    
    def test_validate_host_entry_minimal_valid(self):
        """Test validating minimal valid host entry."""
        entry = {"host": "test.com"}
        assert validate_host_entry(entry) is True
    
    def test_validate_host_entry_missing_host(self):
        """Test validating host entry missing required host field."""
        entry = {"friendly": "test", "user": "admin"}
        assert validate_host_entry(entry) is False
    
    def test_validate_host_entry_not_dict(self):
        """Test validating non-dictionary host entry."""
        assert validate_host_entry("not a dict") is False
        assert validate_host_entry(["not", "a", "dict"]) is False
        assert validate_host_entry(None) is False
    
    def test_validate_host_entry_invalid_field(self):
        """Test validating host entry with invalid field."""
        entry = {
            "host": "test.com",
            "invalid_field": "value"
        }
        assert validate_host_entry(entry) is False
    
    def test_validate_host_entry_all_optional_fields(self):
        """Test validating host entry with all optional fields."""
        entry = {
            "host": "test.com",
            "friendly": "Test Server",
            "user": "admin",
            "port": 2222,
            "identity_file": "/path/to/key",
            "certkey": "/path/to/cert"
        }
        assert validate_host_entry(entry) is True