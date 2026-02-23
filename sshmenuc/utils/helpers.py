"""
Common utility functions.
"""
import argparse
import getpass
import os
import sys
import logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """Configure command-line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(description="SSH Connection Manager")
    parser.add_argument(
        "-c",
        "--config",
        help="Path to the config file",
        default=os.path.expanduser("~") + "/.config/sshmenuc/config.json",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        help="Severity of log level: debug, info (default), warning, error and critical",
        default="default",
    )
    parser.add_argument(
        "--export",
        metavar="FILE",
        help="Decrypt local encrypted backup and export config in plaintext. Use '-' for stdout.",
        default=None,
    )
    parser.add_argument(
        "--context",
        metavar="NAME",
        help="Load a specific context (profile) defined in contexts.json. "
             "If omitted and multiple contexts exist, a selection menu is shown.",
        default=None,
    )
    parser.add_argument(
        "--add-context",
        metavar="NAME",
        dest="add_context",
        help="Interactively create a new context (profile) in contexts.json "
             "and configure its remote sync settings. Existing config.json is "
             "imported automatically if present.",
        default=None,
    )
    return parser


def setup_logging(loglevel: str):
    """Configure logging system.

    Args:
        loglevel: Log level string (debug, info, warning, error, critical)
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "default": logging.INFO
    }
    
    level = level_map.get(loglevel.lower(), logging.INFO)
    logging.basicConfig(stream=sys.stderr, level=level)


def get_default_config_path() -> str:
    """Return the default path for the configuration file.

    Returns:
        Default config file path in user's home directory
    """
    return os.path.expanduser("~/.config/sshmenuc/config.json")


def get_current_user() -> str:
    """Get current username with fallback for Docker/containerized environments.

    Tries multiple methods to get the current username:
    1. os.getlogin() - works in normal TTY environments
    2. os.getenv('USER') - fallback for containers
    3. getpass.getuser() - additional fallback
    4. 'user' - final fallback if all else fails

    Returns:
        Current username string
    """
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        # OSError: happens in Docker/no-TTY environments
        # AttributeError: happens on some systems without getlogin
        pass

    # Try environment variable
    user = os.getenv('USER') or os.getenv('USERNAME')
    if user:
        return user

    # Try getpass module
    try:
        return getpass.getuser()
    except Exception:
        pass

    # Final fallback
    return 'user'


def get_sync_config_path() -> str:
    """Return the default path for the sync configuration file.

    Returns:
        Default sync config file path in user's home directory
    """
    return os.path.expanduser("~/.config/sshmenuc/sync.json")


def get_enc_path(config_path: str) -> str:
    """Return the path for the local encrypted backup of a config file.

    Args:
        config_path: Path to the plaintext config file.

    Returns:
        Path with .enc suffix (e.g. ~/.config/sshmenuc/config.json.enc)
    """
    return config_path + ".enc"


def get_contexts_config_path() -> str:
    """Return the default path for the multi-context registry file."""
    return os.path.expanduser("~/.config/sshmenuc/contexts.json")


def get_context_dir(name: str) -> str:
    """Return the local cache directory for a given context name."""
    return os.path.expanduser(f"~/.config/sshmenuc/contexts/{name}")


def get_context_config_file(name: str) -> str:
    """Return the local plaintext config path for a given context name."""
    return os.path.expanduser(f"~/.config/sshmenuc/contexts/{name}/config.json")


def validate_host_entry(entry: dict) -> bool:
    """Validate a host entry.

    Args:
        entry: Host entry dictionary to validate

    Returns:
        True if entry is valid, False otherwise
    """
    required_fields = ["host"]
    optional_fields = ["friendly", "user", "port", "identity_file", "certkey"]

    if not isinstance(entry, dict):
        return False

    # Check required fields
    for field in required_fields:
        if field not in entry:
            return False

    # Check that all fields are valid
    all_fields = required_fields + optional_fields
    for key in entry.keys():
        if key not in all_fields:
            return False

    return True