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