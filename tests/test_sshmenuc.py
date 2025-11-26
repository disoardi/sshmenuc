import pytest
from sshmenuc import SSHMenuC

def test_config_present(sshmenu):
    assert sshmenu.config is not None
    assert sshmenu.config.is_readable()

