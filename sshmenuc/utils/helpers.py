"""
Funzioni di utilità comuni.
"""
import argparse
import os
import sys
import logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """Configura il parser degli argomenti."""
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
    """Configura il sistema di logging."""
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
    """Restituisce il percorso di default per il file di configurazione."""
    return os.path.expanduser("~/.config/sshmenuc/config.json")


def validate_host_entry(entry: dict) -> bool:
    """Valida una voce host."""
    required_fields = ["host"]
    optional_fields = ["friendly", "user", "port", "identity_file", "certkey"]
    
    if not isinstance(entry, dict):
        return False
    
    # Verifica campi obbligatori
    for field in required_fields:
        if field not in entry:
            return False
    
    # Verifica che tutti i campi siano validi
    all_fields = required_fields + optional_fields
    for key in entry.keys():
        if key not in all_fields:
            return False
    
    return True