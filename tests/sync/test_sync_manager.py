"""Tests for sshmenuc.sync.sync_manager - SyncManager orchestration."""

import json
import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

import sshmenuc.sync.passphrase_cache as cache
from sshmenuc.sync.git_remote import PullResult, PullStatus
from sshmenuc.sync.sync_manager import SyncManager, SyncState

SAMPLE_CONFIG = {"targets": [{"Prod": [{"friendly": "web", "host": "web.local"}]}]}
PASSPHRASE = "test-passphrase"

SYNC_CFG = {
    "version": 1,
    "remote_url": "git@github.com:user/sshmenuc-config.git",
    "branch": "main",
    "sync_repo_path": "/tmp/test-sync-repo",
    "auto_push": True,
    "auto_pull": True,
    "last_config_hash": "",
}


@pytest.fixture(autouse=True)
def reset_passphrase():
    """Reset passphrase cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def config_file(tmp_path):
    """Create a temp config.json with sample data."""
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
    return str(cfg)


@pytest.fixture
def sync_cfg_file(tmp_path):
    """Create a temp sync.json."""
    s = tmp_path / "sync.json"
    s.write_text(json.dumps(SYNC_CFG, indent=4))
    return str(s)


@pytest.fixture
def manager(config_file, sync_cfg_file):
    return SyncManager(config_file, sync_cfg_path=sync_cfg_file)


# Patch constructor keyword arg name to match implementation
@pytest.fixture
def make_manager(tmp_path):
    def _make(config_data=None, sync_cfg=None):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(config_data or SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(sync_cfg or {}, indent=4))
        return SyncManager(str(cfg), sync_config_path=str(s))
    return _make


class TestSyncManagerInit:
    def test_initial_state_is_no_sync(self, make_manager):
        m = make_manager()
        assert m.get_state() == SyncState.NO_SYNC

    def test_status_label_no_sync(self, make_manager):
        m = make_manager()
        assert m.get_status_label() == ""


class TestStartupPull:
    def test_returns_no_sync_without_remote_url(self, make_manager):
        m = make_manager(sync_cfg={})
        state = m.startup_pull()
        assert state == SyncState.NO_SYNC

    def test_returns_no_sync_with_empty_remote_url(self, make_manager):
        m = make_manager(sync_cfg={"remote_url": ""})
        state = m.startup_pull()
        assert state == SyncState.NO_SYNC

    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=False)
    def test_returns_offline_when_enc_backup_exists(self, mock_reach, mock_pass, make_manager):
        m = make_manager(sync_cfg=SYNC_CFG)
        # Create a fake .enc backup
        open(m._enc_path, "wb").close()
        state = m.startup_pull()
        assert state == SyncState.SYNC_OFFLINE

    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=False)
    def test_returns_local_only_when_no_enc_backup(self, mock_reach, mock_pass, make_manager):
        m = make_manager(sync_cfg=SYNC_CFG)
        # Ensure no .enc file exists
        if os.path.exists(m._enc_path):
            os.remove(m._enc_path)
        state = m.startup_pull()
        assert state == SyncState.LOCAL_ONLY

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    def test_returns_sync_ok_on_no_change(self, mock_pass, mock_reach, mock_ensure, mock_pull, make_manager):
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        m = make_manager(sync_cfg=SYNC_CFG)
        state = m.startup_pull()
        assert state == SyncState.SYNC_OK

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    def test_overwrites_local_when_unchanged_and_remote_differs(
        self, mock_pass, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        import hashlib
        from sshmenuc.sync.crypto import encrypt_config

        # Compute the real hash of the local config
        local_data = SAMPLE_CONFIG
        local_text = json.dumps(local_data, indent=4).encode()
        real_hash = hashlib.sha256(local_text).hexdigest()

        # Build sync.json with last_config_hash matching current config
        sync_cfg = {**SYNC_CFG, "last_config_hash": real_hash}

        # Write config and sync files
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps(local_data, indent=4))
        s_file = tmp_path / "sync.json"
        s_file.write_text(json.dumps(sync_cfg, indent=4))

        # Setup remote pull result
        remote_data = {"targets": [{"Dev": [{"host": "dev.local"}]}]}
        remote_enc = encrypt_config(remote_data, PASSPHRASE)
        mock_pull.return_value = PullResult(status=PullStatus.OK, remote_enc_bytes=remote_enc)

        m = SyncManager(str(cfg_file), sync_config_path=str(s_file))
        state = m.startup_pull()

        assert state == SyncState.SYNC_OK
        with open(str(cfg_file), "r") as f:
            written = json.load(f)
        assert written == remote_data


class TestPassphraseVerification:
    """Wrong-passphrase scenarios in startup_pull."""

    def _make_with_enc(self, tmp_path, passphrase=PASSPHRASE):
        """Create a manager with a valid local enc backup."""
        from sshmenuc.sync.crypto import encrypt_config

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(SYNC_CFG, indent=4))
        m = SyncManager(str(cfg), sync_config_path=str(s))
        # Write a valid encrypted backup
        enc = encrypt_config(SAMPLE_CONFIG, passphrase)
        with open(m._enc_path, "wb") as f:
            f.write(enc)
        return m

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    def test_no_change_wrong_passphrase_returns_offline(
        self, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        """Wrong passphrase on NO_CHANGE with local enc → SYNC_OFFLINE after all retries."""
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        m = self._make_with_enc(tmp_path, passphrase=PASSPHRASE)

        # All three prompts return the wrong passphrase
        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value="wrong"):
            state = m.startup_pull()

        assert state == SyncState.SYNC_OFFLINE

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    def test_no_change_correct_passphrase_returns_ok(
        self, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        """Correct passphrase on NO_CHANGE with local enc → SYNC_OK."""
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        m = self._make_with_enc(tmp_path, passphrase=PASSPHRASE)

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE):
            state = m.startup_pull()

        assert state == SyncState.SYNC_OK

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    def test_no_change_no_enc_backup_skips_verification(
        self, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        """NO_CHANGE without a local enc backup → no verification, SYNC_OK."""
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(SYNC_CFG, indent=4))
        m = SyncManager(str(cfg), sync_config_path=str(s))
        # No enc file created

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value="wrong"):
            state = m.startup_pull()

        assert state == SyncState.SYNC_OK

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    def test_ok_wrong_passphrase_returns_offline_after_retries(
        self, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        """Wrong passphrase on PullStatus.OK → SYNC_OFFLINE after all retries."""
        from sshmenuc.sync.crypto import encrypt_config
        remote_enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        mock_pull.return_value = PullResult(status=PullStatus.OK, remote_enc_bytes=remote_enc)

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(SYNC_CFG, indent=4))
        m = SyncManager(str(cfg), sync_config_path=str(s))

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value="wrong"):
            state = m.startup_pull()

        assert state == SyncState.SYNC_OFFLINE

    @patch("sshmenuc.sync.sync_manager.pull_remote")
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    def test_ok_correct_on_second_attempt_returns_sync_ok(
        self, mock_reach, mock_ensure, mock_pull, tmp_path
    ):
        """Wrong then correct passphrase on PullStatus.OK → SYNC_OK."""
        import hashlib
        from sshmenuc.sync.crypto import encrypt_config

        local_bytes = json.dumps(SAMPLE_CONFIG, indent=4).encode()
        real_hash = hashlib.sha256(local_bytes).hexdigest()
        sync_cfg = {**SYNC_CFG, "last_config_hash": real_hash}

        remote_enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        mock_pull.return_value = PullResult(status=PullStatus.OK, remote_enc_bytes=remote_enc)

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(sync_cfg, indent=4))
        m = SyncManager(str(cfg), sync_config_path=str(s))

        # First call returns wrong, subsequent calls return correct passphrase.
        # _update_local_enc_backup() makes a third call after successful decrypt.
        prompts = iter(["wrong", PASSPHRASE, PASSPHRASE])
        with patch("sshmenuc.sync.sync_manager.get_or_prompt", side_effect=prompts):
            state = m.startup_pull()

        assert state == SyncState.SYNC_OK


class TestPostSavePush:
    def test_does_nothing_on_no_sync(self, make_manager):
        m = make_manager(sync_cfg={})
        m.startup_pull()  # sets NO_SYNC
        m.post_save_push()  # should not raise
        assert m.get_state() == SyncState.NO_SYNC

    @patch("sshmenuc.sync.sync_manager.push_remote", return_value=True)
    @patch("sshmenuc.sync.sync_manager.has_passphrase", return_value=True)
    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.pull_remote")
    def test_updates_state_to_ok_on_push_success(
        self, mock_pull, mock_ensure, mock_reach, mock_prompt, mock_has, mock_push, make_manager
    ):
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        m = make_manager(sync_cfg=SYNC_CFG)
        m.startup_pull()
        m.post_save_push()
        assert m.get_state() == SyncState.SYNC_OK

    @patch("sshmenuc.sync.sync_manager.push_remote", return_value=False)
    @patch("sshmenuc.sync.sync_manager.has_passphrase", return_value=True)
    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    @patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True)
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    @patch("sshmenuc.sync.sync_manager.pull_remote")
    def test_updates_state_to_offline_on_push_failure(
        self, mock_pull, mock_ensure, mock_reach, mock_prompt, mock_has, mock_push, make_manager
    ):
        mock_pull.return_value = PullResult(status=PullStatus.NO_CHANGE)
        m = make_manager(sync_cfg=SYNC_CFG)
        m.startup_pull()
        m.post_save_push()
        assert m.get_state() == SyncState.SYNC_OFFLINE


class TestExportConfig:
    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    def test_export_to_file(self, mock_pass, make_manager, tmp_path):
        from sshmenuc.sync.crypto import encrypt_config
        m = make_manager(sync_cfg=SYNC_CFG)
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        with open(m._enc_path, "wb") as f:
            f.write(enc)

        output_path = str(tmp_path / "exported.json")
        m.export_config(output_path)

        with open(output_path, "r") as f:
            exported = json.load(f)
        assert exported == SAMPLE_CONFIG

    @patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE)
    def test_export_to_stdout(self, mock_pass, make_manager, tmp_path, capsys):
        from sshmenuc.sync.crypto import encrypt_config
        m = make_manager(sync_cfg=SYNC_CFG)
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        with open(m._enc_path, "wb") as f:
            f.write(enc)

        m.export_config("-")
        captured = capsys.readouterr()
        exported = json.loads(captured.out)
        assert exported == SAMPLE_CONFIG

    def test_export_missing_enc_prints_error(self, make_manager, tmp_path, capsys):
        m = make_manager(sync_cfg=SYNC_CFG)
        if os.path.exists(m._enc_path):
            os.remove(m._enc_path)
        m.export_config(str(tmp_path / "out.json"))
        captured = capsys.readouterr()
        assert "Nessun backup" in captured.err


class TestStatusLabel:
    def test_label_sync_ok(self, make_manager):
        m = make_manager()
        m._state = SyncState.SYNC_OK
        assert m.get_status_label() == "SYNC:OK"

    def test_label_offline(self, make_manager):
        m = make_manager()
        m._state = SyncState.SYNC_OFFLINE
        assert m.get_status_label() == "SYNC:OFFLINE"

    def test_label_local_only(self, make_manager):
        m = make_manager()
        m._state = SyncState.LOCAL_ONLY
        assert m.get_status_label() == "SYNC:NO-BACKUP"


class TestSetupWizard:
    """Tests for the interactive setup wizard."""

    def test_wizard_aborts_on_empty_url(self, make_manager):
        """Pressing Enter without typing a URL cancels the wizard."""
        m = make_manager(sync_cfg={})
        with patch("builtins.input", return_value=""):
            result = m.setup_wizard()
        assert result is False
        assert not os.path.isfile(m._sync_config_path) or \
               json.loads(open(m._sync_config_path).read()) == {}

    def test_wizard_writes_sync_json_and_returns_true(self, make_manager, tmp_path):
        """Providing a URL and declining first sync writes sync.json."""
        m = make_manager(sync_cfg={})
        inputs = iter([
            "git@github.com:user/repo.git",  # remote URL
            "main",                           # branch
            "",                               # sync_repo_path (use default)
            "N",                              # decline first sync
        ])
        with patch("builtins.input", side_effect=inputs):
            result = m.setup_wizard()

        assert result is True
        saved = json.loads(open(m._sync_config_path).read())
        assert saved["remote_url"] == "git@github.com:user/repo.git"
        assert saved["branch"] == "main"
        assert saved["auto_pull"] is True
        assert saved["auto_push"] is True

    def test_wizard_uses_default_branch_when_empty(self, make_manager):
        """Empty branch input defaults to 'main'."""
        m = make_manager(sync_cfg={})
        inputs = iter([
            "git@github.com:user/repo.git",
            "",   # empty branch → defaults to 'main'
            "",
            "N",
        ])
        with patch("builtins.input", side_effect=inputs):
            result = m.setup_wizard()

        assert result is True
        saved = json.loads(open(m._sync_config_path).read())
        assert saved["branch"] == "main"

    @patch("sshmenuc.sync.sync_manager.push_remote", return_value=True)
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    def test_wizard_first_sync_mismatched_passphrase_no_push(
        self, mock_ensure, mock_push, make_manager
    ):
        """Mismatched passphrases skip the push but still return True (sync.json written)."""
        m = make_manager(sync_cfg={})
        inputs = iter([
            "git@github.com:user/repo.git",
            "main",
            "",
            "s",  # accept first sync
        ])
        passphrases = iter(["secret1", "secret2"])  # mismatch
        with patch("builtins.input", side_effect=inputs), \
             patch("getpass.getpass", side_effect=passphrases):
            result = m.setup_wizard()

        assert result is True
        mock_push.assert_not_called()

    @patch("sshmenuc.sync.sync_manager.push_remote", return_value=True)
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    def test_wizard_first_sync_push_success(
        self, mock_ensure, mock_push, make_manager
    ):
        """Matching passphrases + successful push → state SYNC_OK."""
        m = make_manager(sync_cfg={})
        inputs = iter([
            "git@github.com:user/repo.git",
            "main",
            "",
            "s",  # accept first sync
        ])
        passphrases = iter(["secret", "secret"])  # matching
        with patch("builtins.input", side_effect=inputs), \
             patch("getpass.getpass", side_effect=passphrases):
            result = m.setup_wizard()

        assert result is True
        mock_push.assert_called_once()
        assert m.get_state() == SyncState.SYNC_OK

    @patch("sshmenuc.sync.sync_manager.push_remote", return_value=False)
    @patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True)
    def test_wizard_first_sync_push_failure(
        self, mock_ensure, mock_push, make_manager
    ):
        """Push failure during wizard → state SYNC_OFFLINE, but wizard still returns True."""
        m = make_manager(sync_cfg={})
        inputs = iter([
            "git@github.com:user/repo.git",
            "main",
            "",
            "s",
        ])
        passphrases = iter(["secret", "secret"])
        with patch("builtins.input", side_effect=inputs), \
             patch("getpass.getpass", side_effect=passphrases):
            result = m.setup_wizard()

        assert result is True
        assert m.get_state() == SyncState.SYNC_OFFLINE


class TestSyncMetaCallback:
    """Verify that _sync_meta_callback is invoked in override mode."""

    def _make_override_manager(self, tmp_path, sync_cfg_override):
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        return SyncManager(str(cfg), sync_cfg_override=sync_cfg_override)

    def test_callback_called_after_successful_pull(self, tmp_path):
        """_sync_meta_callback receives (timestamp, hash) after a successful startup_pull."""
        from sshmenuc.sync.crypto import encrypt_config
        import hashlib

        # Set last_config_hash matching local config so no conflict
        local_bytes = json.dumps(SAMPLE_CONFIG, indent=4).encode()
        real_hash = hashlib.sha256(local_bytes).hexdigest()
        override = {**SYNC_CFG, "last_config_hash": real_hash}

        remote_data = {"targets": [{"Dev": [{"host": "dev.local"}]}]}
        remote_enc = encrypt_config(remote_data, PASSPHRASE)

        callback_calls = []

        m = self._make_override_manager(tmp_path, override)
        m._sync_meta_callback = lambda ts, h: callback_calls.append((ts, h))

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE), \
             patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True), \
             patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True), \
             patch("sshmenuc.sync.sync_manager.pull_remote",
                   return_value=MagicMock(status=PullStatus.OK, remote_enc_bytes=remote_enc)):
            m.startup_pull()

        assert len(callback_calls) == 1, "Callback should be called exactly once"
        ts, h = callback_calls[0]
        assert isinstance(ts, str) and "T" in ts   # ISO timestamp
        assert isinstance(h, str) and len(h) == 64  # SHA-256 hex

    def test_callback_not_called_in_normal_mode(self, tmp_path):
        """In non-override (single-file) mode, callback is never invoked."""
        import hashlib

        local_bytes = json.dumps(SAMPLE_CONFIG, indent=4).encode()
        real_hash = hashlib.sha256(local_bytes).hexdigest()
        sync_cfg = {**SYNC_CFG, "last_config_hash": real_hash}

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps(SAMPLE_CONFIG, indent=4))
        s = tmp_path / "sync.json"
        s.write_text(json.dumps(sync_cfg, indent=4))
        m = SyncManager(str(cfg), sync_config_path=str(s))

        callback_calls = []
        m._sync_meta_callback = lambda ts, h: callback_calls.append((ts, h))

        from sshmenuc.sync.crypto import encrypt_config
        remote_data = {"targets": [{"Dev": [{"host": "dev.local"}]}]}
        remote_enc = encrypt_config(remote_data, PASSPHRASE)

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE), \
             patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True), \
             patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True), \
             patch("sshmenuc.sync.sync_manager.pull_remote",
                   return_value=MagicMock(status=PullStatus.OK, remote_enc_bytes=remote_enc)):
            m.startup_pull()

        assert callback_calls == [], "Callback must NOT be called in single-file mode"

    def test_no_false_conflict_when_last_hash_empty(self, tmp_path):
        """First launch with empty last_config_hash must NOT trigger a conflict dialog."""
        from sshmenuc.sync.crypto import encrypt_config

        # last_config_hash is "" (first run / never synced)
        override = {**SYNC_CFG, "last_config_hash": ""}
        # Remote has the same content as local
        remote_enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)

        conflict_called = []
        m = self._make_override_manager(tmp_path, override)

        with patch("sshmenuc.sync.sync_manager.get_or_prompt", return_value=PASSPHRASE), \
             patch("sshmenuc.sync.sync_manager.is_remote_reachable", return_value=True), \
             patch("sshmenuc.sync.sync_manager.ensure_repo_initialized", return_value=True), \
             patch("sshmenuc.sync.sync_manager.pull_remote",
                   return_value=MagicMock(status=PullStatus.OK, remote_enc_bytes=remote_enc)), \
             patch.object(m, "_resolve_conflict",
                          side_effect=lambda *a: conflict_called.append(True) or "abort"):
            m.startup_pull()

        assert conflict_called == [], "No conflict dialog expected on first launch"
