"""Git remote operations for config sync.

All git operations use subprocess to avoid additional dependencies.
The sync repo is a dedicated local clone (sync_repo_path) distinct from
the main project directory.
"""

import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class PullStatus(Enum):
    OK = auto()         # Remote pulled, decrypted data available
    NO_CHANGE = auto()  # Remote matches local, no action needed
    CONFLICT = auto()   # Both local and remote changed since last sync
    OFFLINE = auto()    # Remote not reachable


@dataclass
class PullResult:
    status: PullStatus
    remote_enc_bytes: Optional[bytes] = field(default=None)


def _run_git(args: list, cwd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command in the given directory."""
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def is_remote_reachable(remote_url: str, timeout: int = 10) -> bool:
    """Check if the remote git repository is reachable.

    Args:
        remote_url: Git remote URL (SSH or HTTPS).
        timeout: Seconds before considering the remote unreachable.

    Returns:
        True if the remote responds, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", "--quiet", remote_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def ensure_repo_initialized(sync_cfg: dict) -> bool:
    """Ensure the local sync repo exists and is initialized.

    Clones the remote repo if the local directory does not exist yet.
    If the remote is empty (new repo), initializes it with an empty commit.

    Args:
        sync_cfg: Sync configuration dict with remote_url, branch, sync_repo_path.

    Returns:
        True if the repo is ready, False on error.
    """
    remote_url = sync_cfg.get("remote_url", "")
    branch = sync_cfg.get("branch", "main")
    repo_path = os.path.expanduser(sync_cfg.get("sync_repo_path", ""))

    if not remote_url or not repo_path:
        logging.error("Missing remote_url or sync_repo_path in sync config")
        return False

    if os.path.isdir(os.path.join(repo_path, ".git")):
        return True  # Already initialized

    os.makedirs(repo_path, exist_ok=True)

    # Try cloning
    result = subprocess.run(
        ["git", "clone", "--branch", branch, "--depth", "1", remote_url, repo_path],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode == 0:
        return True

    # Clone failed - could be an empty remote repo. Try init + remote add.
    logging.warning(f"Clone failed ({result.stderr.strip()}), initializing empty repo")
    try:
        _run_git(["init", "-b", branch], cwd=repo_path)
        _run_git(["remote", "add", "origin", remote_url], cwd=repo_path)
        return True
    except Exception as e:
        logging.error(f"Failed to initialize sync repo: {e}")
        return False


def pull_remote(sync_cfg: dict) -> PullResult:
    """Fetch the latest encrypted config from the remote repo.

    Args:
        sync_cfg: Sync configuration dict.

    Returns:
        PullResult with status and optional remote encrypted bytes.
    """
    repo_path = os.path.expanduser(sync_cfg.get("sync_repo_path", ""))
    branch = sync_cfg.get("branch", "main")

    try:
        result = _run_git(["fetch", "origin", branch], cwd=repo_path)
        if result.returncode != 0:
            logging.warning(f"git fetch failed: {result.stderr.strip()}")
            return PullResult(status=PullStatus.OFFLINE)

        # Check if remote has the branch
        check = _run_git(["ls-remote", "--exit-code", "origin", branch], cwd=repo_path)
        if check.returncode != 0:
            # Branch doesn't exist on remote yet (empty repo)
            return PullResult(status=PullStatus.NO_CHANGE)

        remote_file = sync_cfg.get("remote_file", "config.json.enc")

        # Check if there are any differences between local and remote
        diff = _run_git(["diff", f"HEAD..origin/{branch}", "--name-only"], cwd=repo_path)
        if diff.returncode != 0 or not diff.stdout.strip():
            # No remote changes or diff failed (e.g. no local commits yet)
            remote_enc_bytes = _read_remote_enc(repo_path, branch, remote_file)
            if remote_enc_bytes:
                return PullResult(status=PullStatus.OK, remote_enc_bytes=remote_enc_bytes)
            return PullResult(status=PullStatus.NO_CHANGE)

        # Merge remote into local
        merge = _run_git(["merge", f"origin/{branch}", "--ff-only"], cwd=repo_path)
        if merge.returncode != 0:
            logging.warning(f"git merge failed: {merge.stderr.strip()}")
            return PullResult(status=PullStatus.OFFLINE)

        remote_enc_bytes = _read_remote_enc(repo_path, branch, remote_file)
        return PullResult(status=PullStatus.OK, remote_enc_bytes=remote_enc_bytes)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logging.warning(f"Git pull error: {e}")
        return PullResult(status=PullStatus.OFFLINE)


def _read_remote_enc(repo_path: str, branch: str, remote_file: str = "config.json.enc") -> Optional[bytes]:
    """Read the encrypted config file from the local sync repo after pull."""
    enc_file = os.path.join(repo_path, remote_file)
    if not os.path.isfile(enc_file):
        return None
    with open(enc_file, "rb") as f:
        return f.read()


def push_remote(sync_cfg: dict, enc_bytes: bytes) -> bool:
    """Write encrypted config to the sync repo and push to remote.

    Args:
        sync_cfg: Sync configuration dict.
        enc_bytes: Encrypted config bytes to push.

    Returns:
        True if push succeeded, False otherwise.
    """
    repo_path = os.path.expanduser(sync_cfg.get("sync_repo_path", ""))
    branch = sync_cfg.get("branch", "main")
    remote_file = sync_cfg.get("remote_file", "config.json.enc")
    enc_file = os.path.join(repo_path, remote_file)

    try:
        # Write encrypted file
        with open(enc_file, "wb") as f:
            f.write(enc_bytes)

        # Git add + commit + push
        _run_git(["add", remote_file], cwd=repo_path)

        # Check if there's anything to commit
        status = _run_git(["status", "--porcelain"], cwd=repo_path)
        if not status.stdout.strip():
            return True  # Nothing changed, no push needed

        _run_git(
            ["commit", "-m", "sync: update config"],
            cwd=repo_path,
            timeout=15,
        )

        result = _run_git(
            ["push", "origin", branch, "--set-upstream"],
            cwd=repo_path,
            timeout=30,
        )
        if result.returncode != 0:
            logging.warning(f"git push failed: {result.stderr.strip()}")
            return False

        return True

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logging.warning(f"Git push error: {e}")
        return False
