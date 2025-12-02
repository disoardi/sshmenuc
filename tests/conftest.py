"""
Pytest configuration and fixtures.
"""
import pytest
import tempfile
import json
import os
from pathlib import Path


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            "targets": [
                {
                    "Production": [
                        {
                            "friendly": "web-server",
                            "host": "web.example.com",
                            "user": "admin",
                            "connection_type": "ssh"
                        }
                    ]
                },
                {
                    "Development": [
                        {
                            "friendly": "dev-server", 
                            "host": "dev.example.com",
                            "user": "developer"
                        }
                    ]
                }
            ]
        }
        json.dump(config_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_host_entry():
    """Sample valid host entry for testing."""
    return {
        "friendly": "test-server",
        "host": "test.example.com",
        "user": "testuser",
        "port": 22,
        "connection_type": "ssh"
    }


@pytest.fixture
def sample_hosts_list():
    """Sample list of hosts for group testing."""
    return [
        {"host": "server1.com", "user": "admin"},
        {"host": "server2.com", "user": "admin", "identity": "/path/to/key.pem"},
        {"host": "server3.com", "user": "root"}
    ]