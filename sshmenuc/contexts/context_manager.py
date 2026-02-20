"""ContextManager - manages named SSH config profiles.

Each context (profile) maps to:
  - A local plaintext config cache: ~/.config/sshmenuc/contexts/<name>/config.json
  - A local encrypted backup:        ~/.config/sshmenuc/contexts/<name>/config.json.enc
  - A set of sync settings (remote_url, remote_file, branch, sync_repo_path, ...)

All contexts are stored in a single registry: ~/.config/sshmenuc/contexts.json

This module is backward-compatible: if contexts.json does not exist, all callers
fall back to single-file mode (the original behavior).
"""

import json
import logging
import os
from typing import Dict, List, Optional


CONTEXTS_CONFIG_PATH = os.path.expanduser("~/.config/sshmenuc/contexts.json")
CONTEXTS_BASE_DIR = os.path.expanduser("~/.config/sshmenuc/contexts")


class ContextManager:
    """Manages named SSH config profiles stored in contexts.json."""

    def __init__(self, contexts_config_path: Optional[str] = None):
        self._path = contexts_config_path or CONTEXTS_CONFIG_PATH
        self._data: Dict = {}
        self._loaded = False

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def has_contexts(self) -> bool:
        """Return True if contexts.json exists and contains at least one context."""
        data = self._load()
        return bool(data.get("contexts"))

    def list_contexts(self) -> List[str]:
        """Return context names sorted alphabetically."""
        return sorted(self._load().get("contexts", {}).keys())

    def get_active(self) -> str:
        """Return the name of the active context.

        Falls back to the first context alphabetically if 'active' is missing
        or points to a non-existent context.
        """
        data = self._load()
        active = data.get("active", "")
        contexts = data.get("contexts", {})
        if active in contexts:
            return active
        names = sorted(contexts.keys())
        return names[0] if names else ""

    def get_config_file(self, name: str) -> str:
        """Return the local plaintext config.json path for a context."""
        return os.path.join(CONTEXTS_BASE_DIR, name, "config.json")

    def get_enc_file(self, name: str) -> str:
        """Return the local encrypted backup path for a context."""
        return os.path.join(CONTEXTS_BASE_DIR, name, "config.json.enc")

    def get_sync_cfg(self, name: str) -> dict:
        """Return the sync configuration dict for a context.

        The returned dict mirrors the structure expected by SyncManager, with
        the addition of 'remote_file' for multi-file repos.
        """
        data = self._load()
        ctx = data.get("contexts", {}).get(name, {})
        return dict(ctx)  # Copy to avoid mutation of internal state

    def set_active(self, name: str) -> None:
        """Set the active context and persist to contexts.json."""
        data = self._load()
        if name not in data.get("contexts", {}):
            raise ValueError(f"Context '{name}' not found in contexts.json")
        data["active"] = name
        self._save(data)

    def update_context_meta(self, name: str, last_sync: str, last_hash: str) -> None:
        """Persist last_sync and last_config_hash for a context."""
        data = self._load()
        ctx = data.get("contexts", {}).get(name)
        if ctx is None:
            logging.warning(f"[CTX] Cannot update meta for unknown context '{name}'")
            return
        ctx["last_sync"] = last_sync
        ctx["last_config_hash"] = last_hash
        self._save(data)

    def add_context(self, name: str, cfg: dict) -> None:
        """Add or replace a context entry and persist."""
        data = self._load()
        data.setdefault("contexts", {})[name] = cfg
        if not data.get("active"):
            data["active"] = name
        self._save(data)

    def remove_context(self, name: str) -> None:
        """Remove a context entry. If it was active, reset to first remaining."""
        data = self._load()
        contexts = data.get("contexts", {})
        contexts.pop(name, None)
        if data.get("active") == name:
            remaining = sorted(contexts.keys())
            data["active"] = remaining[0] if remaining else ""
        self._save(data)

    def ensure_context_dir(self, name: str) -> None:
        """Create the local cache directory for a context if it does not exist."""
        os.makedirs(os.path.join(CONTEXTS_BASE_DIR, name), exist_ok=True)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _load(self) -> dict:
        """Load and cache contexts.json from disk. Returns empty dict if absent."""
        if not self._loaded:
            try:
                with open(self._path, "r") as f:
                    self._data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self._data = {}
            self._loaded = True
        return self._data

    def _save(self, data: dict) -> None:
        """Persist data to contexts.json, creating parent directory if needed."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w") as f:
                json.dump(data, f, indent=4)
            self._data = data  # Update cache
        except OSError as e:
            logging.error(f"[CTX] Cannot write contexts.json: {e}")
