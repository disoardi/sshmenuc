"""Encryption/decryption layer for config sync.

Uses AES-256-GCM with Scrypt key derivation.
All functions are pure (no side effects, no I/O).
"""

import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Scrypt parameters - balanced for interactive use (~0.1s on modern hardware)
_SCRYPT_N = 32768  # 2^15
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LENGTH = 32   # 256 bits for AES-256
_IV_LENGTH = 12    # 96 bits, recommended for GCM


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from passphrase using Scrypt."""
    kdf = Scrypt(salt=salt, length=_KEY_LENGTH, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_config(data: dict, passphrase: str) -> bytes:
    """Encrypt a config dict and return JSON-encoded encrypted bytes.

    Args:
        data: Config dictionary to encrypt.
        passphrase: User passphrase for key derivation.

    Returns:
        JSON-encoded bytes with crypto metadata and ciphertext.
    """
    salt = os.urandom(16)
    iv = os.urandom(_IV_LENGTH)
    key = _derive_key(passphrase, salt)

    aesgcm = AESGCM(key)
    plaintext = json.dumps(data, indent=4).encode("utf-8")
    # AESGCM.encrypt appends the 16-byte GCM tag to the ciphertext
    ciphertext = aesgcm.encrypt(iv, plaintext, None)

    envelope = {
        "version": 1,
        "algo": "AES-256-GCM",
        "kdf": "scrypt",
        "kdf_params": {
            "n": _SCRYPT_N,
            "r": _SCRYPT_R,
            "p": _SCRYPT_P,
            "salt": base64.b64encode(salt).decode("ascii"),
        },
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, indent=2).encode("utf-8")


def decrypt_config(enc_bytes: bytes, passphrase: str) -> dict:
    """Decrypt encrypted config bytes and return the config dict.

    Args:
        enc_bytes: JSON-encoded encrypted bytes (output of encrypt_config).
        passphrase: User passphrase for key derivation.

    Returns:
        Decrypted config dictionary.

    Raises:
        ValueError: If the encrypted data format is invalid or unsupported.
        cryptography.exceptions.InvalidTag: If passphrase is wrong or data is tampered.
    """
    try:
        envelope = json.loads(enc_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid encrypted config format: {e}") from e

    if envelope.get("version") != 1:
        raise ValueError(f"Unsupported encrypted config version: {envelope.get('version')}")

    try:
        salt = base64.b64decode(envelope["kdf_params"]["salt"])
        iv = base64.b64decode(envelope["iv"])
        ciphertext = base64.b64decode(envelope["ciphertext"])
    except (KeyError, Exception) as e:
        raise ValueError(f"Malformed encrypted config fields: {e}") from e

    key = _derive_key(passphrase, salt)
    aesgcm = AESGCM(key)

    # Raises InvalidTag if passphrase is wrong or data is tampered
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
