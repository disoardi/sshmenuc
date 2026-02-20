"""Tests for sshmenuc.sync.git_remote."""

import os
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from sshmenuc.sync.git_remote import (
    PullResult,
    PullStatus,
    ensure_repo_initialized,
    is_remote_reachable,
    pull_remote,
    push_remote,
)

SYNC_CFG = {
    "remote_url": "git@github.com:user/sshmenuc-config.git",
    "branch": "main",
    "sync_repo_path": "/tmp/test-sync-repo",
}

ENC_BYTES = b'{"version": 1, "algo": "AES-256-GCM", "ciphertext": "abc123"}'


def _make_run_result(returncode=0, stdout="", stderr=""):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestIsRemoteReachable:
    @patch("subprocess.run")
    def test_returns_true_on_zero_returncode(self, mock_run):
        mock_run.return_value = _make_run_result(returncode=0)
        assert is_remote_reachable("git@github.com:user/repo.git") is True

    @patch("subprocess.run")
    def test_returns_false_on_nonzero_returncode(self, mock_run):
        mock_run.return_value = _make_run_result(returncode=128)
        assert is_remote_reachable("git@github.com:user/repo.git") is False

    @patch("subprocess.run", side_effect=TimeoutError())
    def test_returns_false_on_timeout(self, mock_run):
        assert is_remote_reachable("git@github.com:user/repo.git") is False

    @patch("subprocess.run", side_effect=FileNotFoundError())
    def test_returns_false_when_git_not_found(self, mock_run):
        assert is_remote_reachable("git@github.com:user/repo.git") is False


class TestEnsureRepoInitialized:
    @patch("os.path.isdir", return_value=True)
    def test_returns_true_if_already_initialized(self, mock_isdir):
        assert ensure_repo_initialized(SYNC_CFG) is True
        mock_isdir.assert_called_once_with("/tmp/test-sync-repo/.git")

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("os.path.isdir", return_value=False)
    def test_clones_on_missing_repo(self, mock_isdir, mock_makedirs, mock_run):
        mock_run.return_value = _make_run_result(returncode=0)
        result = ensure_repo_initialized(SYNC_CFG)
        assert result is True
        assert mock_run.call_count == 1
        clone_call = mock_run.call_args[0][0]
        assert "clone" in clone_call

    @patch("subprocess.run")
    @patch("os.makedirs")
    @patch("os.path.isdir", return_value=False)
    def test_falls_back_to_init_on_clone_failure(self, mock_isdir, mock_makedirs, mock_run):
        # First call (clone) fails, subsequent calls (init, remote add) succeed
        mock_run.side_effect = [
            _make_run_result(returncode=128, stderr="repository not found"),
            _make_run_result(returncode=0),  # git init
            _make_run_result(returncode=0),  # git remote add
        ]
        result = ensure_repo_initialized(SYNC_CFG)
        assert result is True

    def test_returns_false_on_missing_remote_url(self):
        assert ensure_repo_initialized({"sync_repo_path": "/tmp/x"}) is False

    def test_returns_false_on_missing_repo_path(self):
        assert ensure_repo_initialized({"remote_url": "git@github.com:x/y.git"}) is False


class TestPullRemote:
    @patch("sshmenuc.sync.git_remote._read_remote_enc", return_value=ENC_BYTES)
    @patch("sshmenuc.sync.git_remote._run_git")
    def test_returns_ok_on_successful_pull(self, mock_git, mock_read):
        mock_git.side_effect = [
            _make_run_result(returncode=0),              # fetch
            _make_run_result(returncode=0),              # ls-remote (branch exists)
            _make_run_result(returncode=0, stdout="config.json.enc\n"),  # diff
            _make_run_result(returncode=0),              # merge
        ]
        result = pull_remote(SYNC_CFG)
        assert result.status == PullStatus.OK
        assert result.remote_enc_bytes == ENC_BYTES

    @patch("sshmenuc.sync.git_remote._run_git")
    def test_returns_offline_on_fetch_failure(self, mock_git):
        mock_git.return_value = _make_run_result(returncode=1, stderr="network error")
        result = pull_remote(SYNC_CFG)
        assert result.status == PullStatus.OFFLINE

    @patch("sshmenuc.sync.git_remote._read_remote_enc", return_value=ENC_BYTES)
    @patch("sshmenuc.sync.git_remote._run_git")
    def test_returns_no_change_on_empty_remote(self, mock_git, mock_read):
        mock_git.side_effect = [
            _make_run_result(returncode=0),   # fetch
            _make_run_result(returncode=2),   # ls-remote: branch not found
        ]
        result = pull_remote(SYNC_CFG)
        assert result.status == PullStatus.NO_CHANGE

    @patch("sshmenuc.sync.git_remote._run_git", side_effect=TimeoutError())
    def test_returns_offline_on_timeout(self, mock_git):
        result = pull_remote(SYNC_CFG)
        assert result.status == PullStatus.OFFLINE


class TestPushRemote:
    @patch("sshmenuc.sync.git_remote._run_git")
    @patch("builtins.open", new=mock_open())
    def test_returns_true_on_successful_push(self, mock_git):
        mock_git.side_effect = [
            _make_run_result(returncode=0),                      # add
            _make_run_result(returncode=0, stdout="M config\n"), # status (has changes)
            _make_run_result(returncode=0),                      # commit
            _make_run_result(returncode=0),                      # push
        ]
        result = push_remote(SYNC_CFG, ENC_BYTES)
        assert result is True

    @patch("sshmenuc.sync.git_remote._run_git")
    @patch("builtins.open", new=mock_open())
    def test_returns_false_on_push_failure(self, mock_git):
        mock_git.side_effect = [
            _make_run_result(returncode=0),                      # add
            _make_run_result(returncode=0, stdout="M config\n"), # status
            _make_run_result(returncode=0),                      # commit
            _make_run_result(returncode=1, stderr="rejected"),   # push fails
        ]
        result = push_remote(SYNC_CFG, ENC_BYTES)
        assert result is False

    @patch("sshmenuc.sync.git_remote._run_git")
    @patch("builtins.open", new=mock_open())
    def test_skips_commit_if_nothing_changed(self, mock_git):
        mock_git.side_effect = [
            _make_run_result(returncode=0),              # add
            _make_run_result(returncode=0, stdout=""),   # status: empty (no changes)
        ]
        result = push_remote(SYNC_CFG, ENC_BYTES)
        assert result is True
        # commit and push should NOT be called
        assert mock_git.call_count == 2

    @patch("builtins.open", side_effect=OSError("disk full"))
    def test_returns_false_on_write_error(self, mock_open):
        result = push_remote(SYNC_CFG, ENC_BYTES)
        assert result is False
