"""In-memory passphrase cache for the current session.

The passphrase is asked once per session and kept in memory only.
It is never written to disk.
"""

import getpass
from typing import Optional

# Module-level cache - lives only for the duration of the process
_passphrase: Optional[str] = None


def get_or_prompt(prompt: str = "Enter sync passphrase: ") -> str:
    """Return the cached passphrase, or prompt the user once.

    Args:
        prompt: Text shown when prompting the user (default suitable for CLI).

    Returns:
        The passphrase string.
    """
    global _passphrase
    if _passphrase is None:
        _passphrase = getpass.getpass(prompt)
    return _passphrase


def set_passphrase(passphrase: str) -> None:
    """Set the passphrase directly (used in tests or non-interactive flows)."""
    global _passphrase
    _passphrase = passphrase


def clear() -> None:
    """Clear the cached passphrase (used in tests and session cleanup)."""
    global _passphrase
    _passphrase = None


def has_passphrase() -> bool:
    """Return True if a passphrase is currently cached."""
    return _passphrase is not None
