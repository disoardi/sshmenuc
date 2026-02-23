"""Tests for sshmenuc.sync.crypto - pure encryption/decryption functions."""

import json

import pytest
from cryptography.exceptions import InvalidTag

from sshmenuc.sync.crypto import decrypt_config, encrypt_config

# Sample config data for testing
SAMPLE_CONFIG = {
    "targets": [
        {"Production": [{"friendly": "web", "host": "web.example.com", "user": "admin"}]}
    ]
}
PASSPHRASE = "test-passphrase-123"


class TestEncryptConfig:
    def test_returns_bytes(self):
        result = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        assert isinstance(result, bytes)

    def test_output_is_valid_json(self):
        result = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        envelope = json.loads(result.decode("utf-8"))
        assert isinstance(envelope, dict)

    def test_envelope_has_required_fields(self):
        result = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        envelope = json.loads(result.decode("utf-8"))
        assert envelope["version"] == 1
        assert envelope["algo"] == "AES-256-GCM"
        assert envelope["kdf"] == "scrypt"
        assert "kdf_params" in envelope
        assert "salt" in envelope["kdf_params"]
        assert "iv" in envelope
        assert "ciphertext" in envelope

    def test_different_salt_each_call(self):
        enc1 = json.loads(encrypt_config(SAMPLE_CONFIG, PASSPHRASE).decode("utf-8"))
        enc2 = json.loads(encrypt_config(SAMPLE_CONFIG, PASSPHRASE).decode("utf-8"))
        assert enc1["kdf_params"]["salt"] != enc2["kdf_params"]["salt"]

    def test_different_iv_each_call(self):
        enc1 = json.loads(encrypt_config(SAMPLE_CONFIG, PASSPHRASE).decode("utf-8"))
        enc2 = json.loads(encrypt_config(SAMPLE_CONFIG, PASSPHRASE).decode("utf-8"))
        assert enc1["iv"] != enc2["iv"]

    def test_plaintext_not_visible_in_output(self):
        result = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        # Hostname should not be visible in the encrypted output
        assert b"web.example.com" not in result


class TestDecryptConfig:
    def test_roundtrip_returns_original_data(self):
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        result = decrypt_config(enc, PASSPHRASE)
        assert result == SAMPLE_CONFIG

    def test_wrong_passphrase_raises_invalid_tag(self):
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        with pytest.raises(InvalidTag):
            decrypt_config(enc, "wrong-passphrase")

    def test_empty_config_roundtrip(self):
        empty = {"targets": []}
        enc = encrypt_config(empty, PASSPHRASE)
        assert decrypt_config(enc, PASSPHRASE) == empty

    def test_complex_config_roundtrip(self):
        complex_config = {
            "targets": [
                {
                    "Prod": [
                        {
                            "friendly": "server",
                            "host": "192.168.1.1",
                            "user": "root",
                            "port": 2222,
                            "extra_args": "-t bash",
                            "certkey": "/home/user/.ssh/id_rsa",
                        }
                    ]
                },
                {"Dev": [{"friendly": "dev", "host": "dev.local"}]},
            ]
        }
        enc = encrypt_config(complex_config, PASSPHRASE)
        assert decrypt_config(enc, PASSPHRASE) == complex_config

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid encrypted config format"):
            decrypt_config(b"not valid json", PASSPHRASE)

    def test_wrong_version_raises_value_error(self):
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        envelope = json.loads(enc.decode("utf-8"))
        envelope["version"] = 99
        bad_enc = json.dumps(envelope).encode("utf-8")
        with pytest.raises(ValueError, match="Unsupported encrypted config version"):
            decrypt_config(bad_enc, PASSPHRASE)

    def test_tampered_ciphertext_raises_invalid_tag(self):
        enc = encrypt_config(SAMPLE_CONFIG, PASSPHRASE)
        envelope = json.loads(enc.decode("utf-8"))
        # Flip some bytes in the ciphertext
        import base64
        ct = bytearray(base64.b64decode(envelope["ciphertext"]))
        ct[0] ^= 0xFF
        envelope["ciphertext"] = base64.b64encode(bytes(ct)).decode("ascii")
        tampered = json.dumps(envelope).encode("utf-8")
        with pytest.raises(InvalidTag):
            decrypt_config(tampered, PASSPHRASE)
