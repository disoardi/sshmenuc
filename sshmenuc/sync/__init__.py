"""Sync module for sshmenuc - remote Git-based config synchronization."""

from .sync_manager import SyncManager, SyncState

__all__ = ["SyncManager", "SyncState"]
