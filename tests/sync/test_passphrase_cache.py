"""Tests for sshmenuc.sync.passphrase_cache."""

from unittest.mock import patch

import pytest

import sshmenuc.sync.passphrase_cache as cache


@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure the passphrase cache is cleared before and after each test."""
    cache.clear()
    yield
    cache.clear()


class TestPassphraseCache:
    def test_has_passphrase_false_initially(self):
        assert cache.has_passphrase() is False

    def test_set_passphrase_caches_value(self):
        cache.set_passphrase("mysecret")
        assert cache.has_passphrase() is True

    def test_get_or_prompt_uses_cache_if_set(self):
        cache.set_passphrase("cached-pass")
        with patch("getpass.getpass") as mock_getpass:
            result = cache.get_or_prompt()
            mock_getpass.assert_not_called()
        assert result == "cached-pass"

    def test_get_or_prompt_calls_getpass_once(self):
        with patch("getpass.getpass", return_value="prompted-pass") as mock_getpass:
            result1 = cache.get_or_prompt()
            result2 = cache.get_or_prompt()
            assert mock_getpass.call_count == 1
        assert result1 == "prompted-pass"
        assert result2 == "prompted-pass"

    def test_get_or_prompt_uses_custom_prompt(self):
        with patch("getpass.getpass", return_value="pass") as mock_getpass:
            cache.get_or_prompt(prompt="Custom: ")
            mock_getpass.assert_called_once_with("Custom: ")

    def test_clear_removes_passphrase(self):
        cache.set_passphrase("secret")
        cache.clear()
        assert cache.has_passphrase() is False

    def test_clear_forces_new_prompt(self):
        with patch("getpass.getpass", return_value="first") as mock_getpass:
            cache.get_or_prompt()
        cache.clear()
        with patch("getpass.getpass", return_value="second") as mock_getpass:
            result = cache.get_or_prompt()
            mock_getpass.assert_called_once()
        assert result == "second"
