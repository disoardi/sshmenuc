"""Tests for sshmenuc.contexts.context_manager - ContextManager."""

import json
import os
import pytest

from sshmenuc.contexts.context_manager import ContextManager


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
        },
        "isp": {
            "remote_url": "git@github.com:user/config.git",
            "remote_file": "isp.enc",
            "branch": "main",
            "sync_repo_path": "/tmp/sync_repo",
            "auto_pull": True,
            "auto_push": True,
        },
        "poste": {
            "remote_url": "git@github.com:user/poste.git",
            "remote_file": "config.enc",
            "branch": "main",
            "sync_repo_path": "/tmp/sync_repo_poste",
            "auto_pull": True,
            "auto_push": True,
        },
    },
}


@pytest.fixture
def contexts_file(tmp_path):
    """Write sample contexts.json and return its path."""
    path = tmp_path / "contexts.json"
    path.write_text(json.dumps(SAMPLE_CONTEXTS, indent=4))
    return str(path)


@pytest.fixture
def ctx(contexts_file):
    """Return a ContextManager pointing at the temp contexts.json."""
    return ContextManager(contexts_config_path=contexts_file)


@pytest.fixture
def empty_ctx(tmp_path):
    """Return a ContextManager with no contexts.json present."""
    return ContextManager(contexts_config_path=str(tmp_path / "contexts.json"))


class TestHasContexts:
    def test_returns_false_when_file_absent(self, empty_ctx):
        assert empty_ctx.has_contexts() is False

    def test_returns_true_when_file_has_contexts(self, ctx):
        assert ctx.has_contexts() is True

    def test_returns_false_for_empty_contexts(self, tmp_path):
        path = tmp_path / "contexts.json"
        path.write_text(json.dumps({"version": 1, "contexts": {}}))
        m = ContextManager(contexts_config_path=str(path))
        assert m.has_contexts() is False


class TestListContexts:
    def test_returns_sorted_names(self, ctx):
        assert ctx.list_contexts() == ["home", "isp", "poste"]

    def test_returns_empty_list_when_no_file(self, empty_ctx):
        assert empty_ctx.list_contexts() == []


class TestGetActive:
    def test_returns_active_context(self, ctx):
        assert ctx.get_active() == "home"

    def test_falls_back_to_first_when_active_missing(self, tmp_path):
        data = dict(SAMPLE_CONTEXTS)
        data.pop("active", None)
        path = tmp_path / "contexts.json"
        path.write_text(json.dumps(data))
        m = ContextManager(contexts_config_path=str(path))
        assert m.get_active() == "home"  # alphabetically first

    def test_falls_back_when_active_not_in_contexts(self, tmp_path):
        data = dict(SAMPLE_CONTEXTS)
        data["active"] = "nonexistent"
        path = tmp_path / "contexts.json"
        path.write_text(json.dumps(data))
        m = ContextManager(contexts_config_path=str(path))
        assert m.get_active() in ["home", "isp", "poste"]

    def test_returns_empty_string_when_no_contexts(self, empty_ctx):
        assert empty_ctx.get_active() == ""


class TestGetConfigFile:
    def test_returns_path_with_context_name(self, ctx):
        path = ctx.get_config_file("isp")
        assert path.endswith("/isp/config.json")

    def test_paths_differ_per_context(self, ctx):
        assert ctx.get_config_file("home") != ctx.get_config_file("isp")


class TestGetSyncCfg:
    def test_returns_dict_for_known_context(self, ctx):
        cfg = ctx.get_sync_cfg("home")
        assert cfg["remote_url"] == "git@github.com:user/config.git"
        assert cfg["remote_file"] == "home.enc"

    def test_remote_file_differs_per_context(self, ctx):
        assert ctx.get_sync_cfg("home")["remote_file"] == "home.enc"
        assert ctx.get_sync_cfg("isp")["remote_file"] == "isp.enc"

    def test_returns_empty_dict_for_unknown_context(self, ctx):
        assert ctx.get_sync_cfg("unknown") == {}

    def test_returns_copy_not_reference(self, ctx):
        cfg = ctx.get_sync_cfg("home")
        cfg["remote_url"] = "tampered"
        assert ctx.get_sync_cfg("home")["remote_url"] != "tampered"


class TestSetActive:
    def test_persists_active_to_file(self, ctx, contexts_file):
        ctx.set_active("isp")
        saved = json.loads(open(contexts_file).read())
        assert saved["active"] == "isp"

    def test_raises_for_unknown_context(self, ctx):
        with pytest.raises(ValueError):
            ctx.set_active("unknown_context")

    def test_get_active_reflects_change(self, ctx):
        ctx.set_active("poste")
        assert ctx.get_active() == "poste"


class TestUpdateContextMeta:
    def test_persists_last_sync_and_hash(self, ctx, contexts_file):
        ctx.update_context_meta("isp", "2026-01-01T00:00:00Z", "abc123")
        saved = json.loads(open(contexts_file).read())
        assert saved["contexts"]["isp"]["last_sync"] == "2026-01-01T00:00:00Z"
        assert saved["contexts"]["isp"]["last_config_hash"] == "abc123"

    def test_silently_ignores_unknown_context(self, ctx):
        ctx.update_context_meta("nonexistent", "ts", "hash")  # Should not raise


class TestAddRemoveContext:
    def test_add_creates_new_context(self, ctx, contexts_file):
        new_cfg = {"remote_url": "git@github.com:user/new.git", "remote_file": "new.enc",
                   "branch": "main", "sync_repo_path": "/tmp/new"}
        ctx.add_context("new_ctx", new_cfg)
        assert "new_ctx" in ctx.list_contexts()

    def test_remove_deletes_context(self, ctx):
        ctx.remove_context("poste")
        assert "poste" not in ctx.list_contexts()

    def test_remove_active_resets_to_first_remaining(self, ctx):
        ctx.remove_context("home")
        # 'home' was active, should now fall back to alphabetically first of remaining
        assert ctx.get_active() in ["isp", "poste"]

    def test_remove_unknown_does_not_raise(self, ctx):
        ctx.remove_context("nonexistent")  # Should not raise


class TestEnsureContextDir:
    def test_creates_directory(self, empty_ctx, tmp_path):
        # Override CONTEXTS_BASE_DIR is not possible without monkeypatching,
        # so test via the path returned by get_config_file
        import sshmenuc.contexts.context_manager as cm_module
        original = cm_module.CONTEXTS_BASE_DIR
        cm_module.CONTEXTS_BASE_DIR = str(tmp_path / "contexts")
        try:
            empty_ctx.ensure_context_dir("test_ctx")
            assert os.path.isdir(str(tmp_path / "contexts" / "test_ctx"))
        finally:
            cm_module.CONTEXTS_BASE_DIR = original
