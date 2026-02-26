"""Tests for sshmenuc.contexts.wizard - add_context_wizard()."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_CONFIG = {
    "targets": [
        {"Production": [{"host": "prod.example.com", "user": "admin"}]}
    ]
}


@pytest.fixture
def legacy_config(tmp_path):
    """Write a legacy config.json and return its path."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps(SAMPLE_CONFIG, indent=2))
    return str(p)


class TestAddContextWizard:
    """Tests for add_context_wizard() in contexts/wizard.py."""

    def _run_wizard(self, name, args_config, contexts_path, cache_dir, inputs,
                    push_ok=True):
        """Run add_context_wizard() with mocked I/O and sync modules.

        Sync functions are imported inside the wizard function, so patching
        the source modules directly is correct (name lookup happens at import
        time inside the function, after the patches are applied).
        """
        from sshmenuc.contexts.wizard import add_context_wizard

        with patch("sshmenuc.contexts.context_manager.CONTEXTS_CONFIG_PATH", contexts_path), \
             patch("sshmenuc.contexts.context_manager.CONTEXTS_BASE_DIR", cache_dir), \
             patch("builtins.input", side_effect=inputs), \
             patch("sshmenuc.sync.git_remote.ensure_repo_initialized", return_value=True) as mock_init, \
             patch("sshmenuc.sync.git_remote.push_remote", return_value=push_ok) as mock_push, \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENCRYPTED") as mock_enc, \
             patch("sshmenuc.sync.passphrase_cache.set_passphrase") as mock_set_pp, \
             patch("getpass.getpass", return_value="secret"):

            result = add_context_wizard(name, default_config_path=args_config)

        return result, mock_init, mock_push, mock_enc, mock_set_pp

    # ------------------------------------------------------------------
    # Cancellation behaviour
    # ------------------------------------------------------------------

    def test_returns_false_when_url_empty(self, tmp_path):
        """Wizard returns False and creates nothing when user presses Enter on URL."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        result, *_ = self._run_wizard(
            name="personal",
            args_config=str(tmp_path / "config.json"),
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=[""],  # empty URL → cancel
        )

        assert result is False
        assert not os.path.isfile(contexts_path), "contexts.json must not be created on cancel"

    # ------------------------------------------------------------------
    # Context creation
    # ------------------------------------------------------------------

    def test_creates_context_entry(self, tmp_path, legacy_config):
        """Wizard adds the context to contexts.json with correct fields."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        result, *_ = self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            # remote_url, branch, remote_file, sync_repo_path, skip push
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "n"],
        )

        assert result is True
        saved = json.loads(open(contexts_path).read())
        assert "personal" in saved["contexts"]
        ctx = saved["contexts"]["personal"]
        assert ctx["remote_url"] == "git@github.com:user/cfg.git"
        assert ctx["remote_file"] == "personal.enc"

    def test_default_remote_file_is_name_dot_enc(self, tmp_path):
        """When user skips remote_file prompt it defaults to '<name>.enc'."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        self._run_wizard(
            name="isp",
            args_config=str(tmp_path / "config.json"),
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "", "", "", "n"],
        )

        saved = json.loads(open(contexts_path).read())
        assert saved["contexts"]["isp"]["remote_file"] == "isp.enc"

    def test_returns_true_without_push(self, tmp_path, legacy_config):
        """Wizard returns True even when user declines first push."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        result, _, mock_push, *_ = self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "n"],
        )

        assert result is True
        mock_push.assert_not_called()

    # ------------------------------------------------------------------
    # Legacy config import
    # ------------------------------------------------------------------

    def test_imports_legacy_config_when_provided(self, tmp_path, legacy_config):
        """Wizard copies legacy config.json into the new context cache."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "n"],
        )

        expected = os.path.join(cache_dir, "personal", "config.json")
        assert os.path.isfile(expected), "Legacy config not imported into context cache"
        assert json.loads(open(expected).read()) == SAMPLE_CONFIG

    def test_no_import_when_default_config_path_empty(self, tmp_path):
        """No import when default_config_path is empty string."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        self._run_wizard(
            name="new",
            args_config="",
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "", "", "", "n"],
        )

        expected = os.path.join(cache_dir, "new", "config.json")
        assert not os.path.isfile(expected), "Should not create cache without legacy config"

    # ------------------------------------------------------------------
    # First push behaviour
    # ------------------------------------------------------------------

    def test_push_called_on_first_sync(self, tmp_path, legacy_config):
        """When user chooses first push, encrypt_config and push_remote are invoked."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        _, _, mock_push, mock_enc, _ = self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "s"],
        )

        mock_enc.assert_called_once()
        mock_push.assert_called_once()

    def test_push_skipped_when_no_config_to_encrypt(self, tmp_path):
        """Push is not attempted when there is no local config to encrypt."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")
        nonexistent_config = str(tmp_path / "config.json")  # does not exist

        _, _, mock_push, mock_enc, _ = self._run_wizard(
            name="personal",
            args_config=nonexistent_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "s"],
        )

        mock_push.assert_not_called()
        mock_enc.assert_not_called()
