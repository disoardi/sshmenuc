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
            mock_args.context = None
            mock_args.config = legacy_config
            mock_args.loglevel = "default"
            mock_parser.return_value.parse_args.return_value = mock_args

            main()

        # In single-file mode, ConnectionNavigator receives args.config directly
        mock_navigator_cls.assert_called_once_with(legacy_config)
