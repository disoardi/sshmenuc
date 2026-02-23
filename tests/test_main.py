"""Tests for sshmenuc.main - legacy config import and context selection."""

import json
import os
import pytest

from unittest.mock import patch, MagicMock


SAMPLE_CONFIG = {
    "targets": [
        {"Production": [{"host": "prod.example.com", "user": "admin"}]}
    ]
}

SAMPLE_CONTEXTS = {
    "version": 1,
    "active": "home",
    "contexts": {
        "home": {
            "remote_url": "git@github.com:user/config.git",
            "remote_file": "home.enc",
            "branch": "main",
            "sync_repo_path": "/tmp/sync_repo",
            "auto_pull": True,
            "auto_push": True,
        }
    },
}


@pytest.fixture
def legacy_config(tmp_path):
    """Write a legacy config.json (single-file mode) and return its path."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps(SAMPLE_CONFIG, indent=2))
    return str(p)


@pytest.fixture
def contexts_file(tmp_path):
    """Write contexts.json and return its path."""
    p = tmp_path / "contexts.json"
    p.write_text(json.dumps(SAMPLE_CONTEXTS, indent=4))
    return str(p)


class TestLegacyImport:
    """Verify that an existing config.json is imported into the context cache."""

    def _run_main(self, args_config, contexts_path, context_cache_dir):
        """Call main() with patched dependencies."""
        from sshmenuc.main import main

        mock_navigator = MagicMock()
        mock_navigator_cls = MagicMock(return_value=mock_navigator)

        with patch("sshmenuc.main.setup_argument_parser") as mock_parser, \
             patch("sshmenuc.main.setup_logging"), \
             patch("sshmenuc.contexts.context_manager.CONTEXTS_CONFIG_PATH", contexts_path), \
             patch("sshmenuc.contexts.context_manager.CONTEXTS_BASE_DIR", context_cache_dir), \
             patch("sshmenuc.main.ConnectionNavigator", mock_navigator_cls):

            mock_args = MagicMock()
            mock_args.export = None
            mock_args.add_context = None
            mock_args.context = None
            mock_args.config = args_config
            mock_args.loglevel = "default"
            mock_parser.return_value.parse_args.return_value = mock_args

            main()

        return mock_navigator_cls

    def test_imports_legacy_config_when_cache_missing(self, tmp_path, legacy_config, contexts_file):
        """If context cache is absent but legacy config exists, it should be copied."""
        cache_dir = str(tmp_path / "contexts")
        os.makedirs(os.path.join(cache_dir, "home"), exist_ok=True)

        self._run_main(legacy_config, contexts_file, cache_dir)

        expected_cache = os.path.join(cache_dir, "home", "config.json")
        assert os.path.isfile(expected_cache), "Legacy config was not imported into context cache"

        imported = json.loads(open(expected_cache).read())
        assert imported == SAMPLE_CONFIG

    def test_does_not_overwrite_existing_cache(self, tmp_path, legacy_config, contexts_file):
        """If context cache already exists, it must NOT be overwritten by the legacy config."""
        cache_dir = str(tmp_path / "contexts")
        ctx_dir = os.path.join(cache_dir, "home")
        os.makedirs(ctx_dir, exist_ok=True)

        existing_config = {"targets": [{"existing": True}]}
        cache_path = os.path.join(ctx_dir, "config.json")
        with open(cache_path, "w") as f:
            json.dump(existing_config, f)

        self._run_main(legacy_config, contexts_file, cache_dir)

        preserved = json.loads(open(cache_path).read())
        assert preserved == existing_config, "Existing cache was incorrectly overwritten"

    def test_no_error_when_both_missing(self, tmp_path, contexts_file):
        """No import and no crash when both legacy config and cache are absent."""
        cache_dir = str(tmp_path / "contexts")
        nonexistent_config = str(tmp_path / "config.json")

        # Should not raise
        self._run_main(nonexistent_config, contexts_file, cache_dir)

    def test_single_file_mode_unchanged(self, tmp_path, legacy_config):
        """Without contexts.json the original config path is used as-is (backward compat)."""
        from sshmenuc.main import main

        mock_navigator = MagicMock()
        mock_navigator_cls = MagicMock(return_value=mock_navigator)
        nonexistent_contexts = str(tmp_path / "contexts.json")

        with patch("sshmenuc.main.setup_argument_parser") as mock_parser, \
             patch("sshmenuc.main.setup_logging"), \
             patch("sshmenuc.contexts.context_manager.CONTEXTS_CONFIG_PATH", nonexistent_contexts), \
             patch("sshmenuc.main.ConnectionNavigator", mock_navigator_cls):

            mock_args = MagicMock()
            mock_args.export = None
            mock_args.add_context = None
            mock_args.context = None
            mock_args.config = legacy_config
            mock_args.loglevel = "default"
            mock_parser.return_value.parse_args.return_value = mock_args

            main()

        # In single-file mode, ConnectionNavigator receives args.config directly
        mock_navigator_cls.assert_called_once_with(legacy_config)


class TestAddContextWizard:
    """Tests for _add_context_wizard() - interactive context creation."""

    def _run_wizard(self, name, args_config, contexts_path, cache_dir, inputs,
                    do_push=False, push_ok=True):
        """Run _add_context_wizard() with mocked I/O and sync modules.

        The sync functions are imported locally inside _add_context_wizard, so
        we patch the source modules directly (not sshmenuc.main.*).
        """
        from sshmenuc.main import _add_context_wizard

        mock_args = MagicMock()
        mock_args.config = args_config

        with patch("sshmenuc.contexts.context_manager.CONTEXTS_CONFIG_PATH", contexts_path), \
             patch("sshmenuc.contexts.context_manager.CONTEXTS_BASE_DIR", cache_dir), \
             patch("builtins.input", side_effect=inputs), \
             patch("sshmenuc.sync.git_remote.ensure_repo_initialized", return_value=True) as mock_init, \
             patch("sshmenuc.sync.git_remote.push_remote", return_value=push_ok) as mock_push, \
             patch("sshmenuc.sync.crypto.encrypt_config", return_value=b"ENCRYPTED") as mock_enc, \
             patch("sshmenuc.sync.passphrase_cache.set_passphrase") as mock_set_pp, \
             patch("getpass.getpass", return_value="secret"):

            _add_context_wizard(name, mock_args)

        return mock_init, mock_push, mock_enc, mock_set_pp

    def test_abort_when_no_url(self, tmp_path):
        """Wizard aborts without creating anything when user presses Enter on URL."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        # Empty URL → abort
        self._run_wizard(
            name="personal",
            args_config=str(tmp_path / "config.json"),
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=[""],  # empty URL
        )

        assert not os.path.isfile(contexts_path), "contexts.json should not be created on abort"

    def test_creates_context_entry(self, tmp_path, legacy_config):
        """Wizard adds the context to contexts.json with correct fields."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            # remote_url, branch, remote_file, sync_repo_path, no first push
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "n"],
        )

        saved = json.loads(open(contexts_path).read())
        assert "personal" in saved["contexts"]
        ctx = saved["contexts"]["personal"]
        assert ctx["remote_url"] == "git@github.com:user/cfg.git"
        assert ctx["remote_file"] == "personal.enc"

    def test_default_remote_file_is_name_dot_enc(self, tmp_path):
        """When user skips remote_file, it defaults to '<name>.enc'."""
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

    def test_imports_legacy_config(self, tmp_path, legacy_config):
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

    def test_push_called_on_first_sync(self, tmp_path, legacy_config):
        """When user chooses first push, encrypt_config and push_remote are invoked."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        _, mock_push, mock_enc, mock_set_pp = self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            # URL, branch, remote_file, repo_path, yes push
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "s"],
            do_push=True,
        )

        mock_enc.assert_called_once()
        mock_push.assert_called_once()

    def test_no_push_when_user_declines(self, tmp_path, legacy_config):
        """When user declines first push, push_remote is never called."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")

        _, mock_push, mock_enc, _ = self._run_wizard(
            name="personal",
            args_config=legacy_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "n"],
        )

        mock_push.assert_not_called()
        mock_enc.assert_not_called()

    def test_push_skipped_when_no_config_to_encrypt(self, tmp_path):
        """Push is not attempted when the context cache has no config to encrypt."""
        contexts_path = str(tmp_path / "contexts.json")
        cache_dir = str(tmp_path / "contexts")
        nonexistent_config = str(tmp_path / "config.json")  # does not exist

        _, mock_push, mock_enc, _ = self._run_wizard(
            name="personal",
            args_config=nonexistent_config,
            contexts_path=contexts_path,
            cache_dir=cache_dir,
            inputs=["git@github.com:user/cfg.git", "main", "personal.enc", "", "s"],
        )

        mock_push.assert_not_called()
        mock_enc.assert_not_called()
