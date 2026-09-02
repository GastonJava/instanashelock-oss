"""Unit tests for crypto, header, recovery, VMK, strict mode, and rate limiter."""

from __future__ import annotations

import os
import secrets
import struct
import tempfile
import time
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.constants import (
    SALT_SIZE, KEY_SIZE, KDF_PBKDF2_SHA256, KDF_ARGON2ID,
    VAULT_MAGIC, VAULT_VERSION, VAULT_VERSION_2, VAULT_VERSION_LEGACY,
    PBKDF2_ITERATIONS, ARGON2_MEMORY_COST, ARGON2_TIME_COST, ARGON2_PARALLELISM,
)
from vault_app.crypto import derive_key, encrypt_vault, decrypt_vault, generate_vmk, wrap_vmk, unwrap_vmk
from vault_app.header import VaultHeader, parse_header, default_header, default_v3_header
from vault_app.recovery import generate_recovery_secret, parse_recovery_input, derive_recovery_key
from vault_app.security import RateLimiter


class TestDeriveKey:
    def test_pbkdf2_deterministic(self):
        salt = secrets.token_bytes(SALT_SIZE)
        k1 = derive_key("test-pass", salt, KDF_PBKDF2_SHA256, iterations=100_000)
        k2 = derive_key("test-pass", salt, KDF_PBKDF2_SHA256, iterations=100_000)
        assert k1 == k2
        assert len(k1) == KEY_SIZE

    def test_pbkdf2_different_passwords(self):
        salt = secrets.token_bytes(SALT_SIZE)
        k1 = derive_key("alpha", salt, KDF_PBKDF2_SHA256, iterations=100_000)
        k2 = derive_key("bravo", salt, KDF_PBKDF2_SHA256, iterations=100_000)
        assert k1 != k2

    def test_argon2id_deterministic(self):
        salt = secrets.token_bytes(SALT_SIZE)
        params = {"memory_cost": 16384, "time_cost": 1, "parallelism": 1}
        k1 = derive_key("test-pass", salt, KDF_ARGON2ID, argon2_params=params)
        k2 = derive_key("test-pass", salt, KDF_ARGON2ID, argon2_params=params)
        assert k1 == k2
        assert len(k1) == KEY_SIZE

    def test_unknown_kdf_raises(self):
        with pytest.raises(ValueError, match="KDF desconocida"):
            derive_key("x", b"0" * 32, 99)


class TestEncryptDecrypt:
    def _roundtrip(self, aad: bytes | None):
        key = secrets.token_bytes(KEY_SIZE)
        data = {"entries": [{"service": "test", "password": "s3cret"}]}
        blob = encrypt_vault(data, key, aad=aad)
        result = decrypt_vault(blob, key, aad=aad)
        assert result == data

    def test_roundtrip_no_aad(self):
        self._roundtrip(None)

    def test_roundtrip_with_aad(self):
        self._roundtrip(b"some-header-bytes")

    def test_wrong_key_raises(self):
        from cryptography.exceptions import InvalidTag
        key = secrets.token_bytes(KEY_SIZE)
        blob = encrypt_vault({"x": 1}, key)
        wrong = secrets.token_bytes(KEY_SIZE)
        with pytest.raises(InvalidTag):
            decrypt_vault(blob, wrong)

    def test_tampered_aad_raises(self):
        from cryptography.exceptions import InvalidTag
        key = secrets.token_bytes(KEY_SIZE)
        aad = b"original"
        blob = encrypt_vault({"x": 1}, key, aad=aad)
        with pytest.raises(InvalidTag):
            decrypt_vault(blob, key, aad=b"tampered")


class TestVMK:
    def test_generate_vmk_size(self):
        vmk = generate_vmk()
        assert len(vmk) == KEY_SIZE

    def test_wrap_unwrap_roundtrip(self):
        vmk = generate_vmk()
        wrapping_key = secrets.token_bytes(KEY_SIZE)
        wrapped = wrap_vmk(vmk, wrapping_key)
        recovered = unwrap_vmk(wrapped, wrapping_key)
        assert recovered == vmk

    def test_wrong_wrapping_key_raises(self):
        from cryptography.exceptions import InvalidTag
        vmk = generate_vmk()
        key1 = secrets.token_bytes(KEY_SIZE)
        key2 = secrets.token_bytes(KEY_SIZE)
        wrapped = wrap_vmk(vmk, key1)
        with pytest.raises(InvalidTag):
            unwrap_vmk(wrapped, key2)

    def test_wrapped_size(self):
        vmk = generate_vmk()
        key = secrets.token_bytes(KEY_SIZE)
        wrapped = wrap_vmk(vmk, key)
        assert len(wrapped) == 12 + 32 + 16  # nonce + key + GCM tag


class TestRecovery:
    def test_generate_and_parse_roundtrip(self):
        display, raw = generate_recovery_secret()
        assert len(raw) == 20
        groups = display.split("-")
        assert len(groups) == 10
        assert all(len(g) == 4 for g in groups)
        recovered = parse_recovery_input(display)
        assert recovered == raw

    def test_parse_case_insensitive(self):
        display, raw = generate_recovery_secret()
        recovered = parse_recovery_input(display.lower())
        assert recovered == raw

    def test_parse_without_dashes(self):
        display, raw = generate_recovery_secret()
        recovered = parse_recovery_input(display.replace("-", ""))
        assert recovered == raw

    def test_parse_with_spaces(self):
        display, raw = generate_recovery_secret()
        spaced = display.replace("-", " ")
        recovered = parse_recovery_input(spaced)
        assert recovered == raw

    def test_parse_invalid_length(self):
        with pytest.raises(ValueError, match="Se esperan"):
            parse_recovery_input("ABCD-EFGH")

    def test_parse_invalid_char(self):
        with pytest.raises(ValueError, match="Caracter invalido"):
            parse_recovery_input("OOOO-" * 10)  # O is excluded

    def test_derive_recovery_key_deterministic(self):
        _, raw = generate_recovery_secret()
        salt = secrets.token_bytes(SALT_SIZE)
        k1 = derive_recovery_key(raw, salt)
        k2 = derive_recovery_key(raw, salt)
        assert k1 == k2
        assert len(k1) == KEY_SIZE


class TestHeaderV3:
    def test_v3_roundtrip_argon2id_with_recovery(self):
        salt_pw = secrets.token_bytes(SALT_SIZE)
        vmk = generate_vmk()
        pw_key = secrets.token_bytes(KEY_SIZE)
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        salt_rec = secrets.token_bytes(SALT_SIZE)
        rec_key = secrets.token_bytes(KEY_SIZE)
        enc_vmk_rec = wrap_vmk(vmk, rec_key)

        h = default_v3_header(
            salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw,
            has_recovery=True, salt_rec=salt_rec, enc_vmk_rec=enc_vmk_rec,
        )
        raw = h.serialise() + b"fake-blob"
        parsed, blob = parse_header(raw)

        assert parsed.version == VAULT_VERSION
        assert parsed.kdf_id == KDF_ARGON2ID
        assert parsed.salt == salt_pw
        assert parsed.enc_vmk_pw == enc_vmk_pw
        assert parsed.has_recovery is True
        assert parsed.salt_rec == salt_rec
        assert parsed.enc_vmk_rec == enc_vmk_rec
        assert blob == b"fake-blob"

        # Verify VMK can be recovered from both paths
        assert unwrap_vmk(parsed.enc_vmk_pw, pw_key) == vmk
        assert unwrap_vmk(parsed.enc_vmk_rec, rec_key) == vmk

    def test_v3_roundtrip_without_recovery(self):
        salt_pw = secrets.token_bytes(SALT_SIZE)
        enc_vmk_pw = wrap_vmk(generate_vmk(), secrets.token_bytes(KEY_SIZE))

        h = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        raw = h.serialise() + b"data"
        parsed, blob = parse_header(raw)

        assert parsed.version == VAULT_VERSION
        assert parsed.has_recovery is False
        assert parsed.enc_vmk_rec == b""
        assert blob == b"data"

    def test_v1_still_parseable(self):
        salt = secrets.token_bytes(SALT_SIZE)
        raw = (
            VAULT_MAGIC
            + struct.pack("<B", VAULT_VERSION_LEGACY)
            + struct.pack("<B", KDF_PBKDF2_SHA256)
            + struct.pack("<I", PBKDF2_ITERATIONS)
            + struct.pack("<B", len(salt))
            + salt
            + b"encrypted-data"
        )
        parsed, blob = parse_header(raw)
        assert parsed.version == VAULT_VERSION_LEGACY
        assert blob == b"encrypted-data"

    def test_v2_still_parseable(self):
        salt = secrets.token_bytes(SALT_SIZE)
        kdf_params = struct.pack("<III", ARGON2_MEMORY_COST, ARGON2_TIME_COST, ARGON2_PARALLELISM)
        raw = (
            VAULT_MAGIC
            + struct.pack("<B", VAULT_VERSION_2)
            + struct.pack("<B", KDF_ARGON2ID)
            + struct.pack("<H", len(kdf_params))
            + kdf_params
            + struct.pack("<B", len(salt))
            + salt
            + b"v2-blob"
        )
        parsed, blob = parse_header(raw)
        assert parsed.version == VAULT_VERSION_2
        assert blob == b"v2-blob"

    def test_bad_magic_raises(self):
        with pytest.raises(ValueError, match="magic"):
            parse_header(b"XXXX" + b"\x00" * 20)

    def test_unsupported_version_raises(self):
        raw = VAULT_MAGIC + struct.pack("<B", 99) + b"\x00" * 20
        with pytest.raises(ValueError, match="no soportada"):
            parse_header(raw)

    def test_iterations_out_of_range_raises(self):
        salt = secrets.token_bytes(SALT_SIZE)
        raw = (
            VAULT_MAGIC
            + struct.pack("<B", VAULT_VERSION_LEGACY)
            + struct.pack("<B", KDF_PBKDF2_SHA256)
            + struct.pack("<I", 50)
            + struct.pack("<B", len(salt))
            + salt
            + b"data"
        )
        with pytest.raises(ValueError, match="fuera de rango"):
            parse_header(raw)

    def test_v3_requires_encrypted_payload(self):
        salt_pw = secrets.token_bytes(SALT_SIZE)
        enc_vmk_pw = wrap_vmk(generate_vmk(), secrets.token_bytes(KEY_SIZE))
        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)

        with pytest.raises(ValueError, match="payload cifrado"):
            parse_header(header.serialise())

    def test_v3_rejects_invalid_has_recovery_flag(self):
        salt_pw = secrets.token_bytes(SALT_SIZE)
        enc_vmk_pw = wrap_vmk(generate_vmk(), secrets.token_bytes(KEY_SIZE))
        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        raw = bytearray(header.serialise() + b"blob")
        raw[len(header.serialise()) - 1] = 2

        with pytest.raises(ValueError, match="has_recovery invalido"):
            parse_header(bytes(raw))


class TestFullVMKFlow:
    """End-to-end: create v3 vault, encrypt, decrypt via both paths."""

    def test_password_and_recovery_both_unlock(self):
        password = "example-only-password-do-not-use"
        data = {"entries": [{"service": "GitHub", "password": "ghp_secret"}]}

        # Setup
        vmk = generate_vmk()
        salt_pw = secrets.token_bytes(SALT_SIZE)
        pw_key = derive_key(password, salt_pw, KDF_ARGON2ID,
                            argon2_params={"memory_cost": 16384, "time_cost": 1, "parallelism": 1})
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        display_codes, raw_secret = generate_recovery_secret()
        salt_rec = secrets.token_bytes(SALT_SIZE)
        rec_key = derive_recovery_key(raw_secret, salt_rec)
        enc_vmk_rec = wrap_vmk(vmk, rec_key)

        header = default_v3_header(
            salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw,
            has_recovery=True, salt_rec=salt_rec, enc_vmk_rec=enc_vmk_rec,
        )
        # Override KDF params for fast test
        header.argon2_memory_cost = 16384
        header.argon2_time_cost = 1
        header.argon2_parallelism = 1

        header_bytes = header.serialise()
        encrypted_blob = encrypt_vault(data, vmk, aad=header_bytes)

        # Decrypt via password path
        vmk_from_pw = unwrap_vmk(enc_vmk_pw, pw_key)
        data_from_pw = decrypt_vault(encrypted_blob, vmk_from_pw, aad=header_bytes)
        assert data_from_pw == data

        # Decrypt via recovery path
        raw_recovered = parse_recovery_input(display_codes)
        rec_key_2 = derive_recovery_key(raw_recovered, salt_rec)
        vmk_from_rec = unwrap_vmk(enc_vmk_rec, rec_key_2)
        data_from_rec = decrypt_vault(encrypted_blob, vmk_from_rec, aad=header_bytes)
        assert data_from_rec == data

        # Both VMKs are the same
        assert vmk_from_pw == vmk_from_rec == vmk


class TestStrictMode:
    """Tests for strict-mode vaults (no recovery material)."""

    def test_v3_strict_mode_no_recovery_material(self):
        salt_pw = secrets.token_bytes(SALT_SIZE)
        vmk = generate_vmk()
        pw_key = secrets.token_bytes(KEY_SIZE)
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        h = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        assert h.has_recovery is False

        raw = h.serialise() + b"payload"
        parsed, blob = parse_header(raw)

        assert parsed.version == VAULT_VERSION
        assert parsed.has_recovery is False
        assert parsed.enc_vmk_rec == b""
        assert parsed.salt_rec == b""
        assert blob == b"payload"

        # Password path still works
        recovered_vmk = unwrap_vmk(parsed.enc_vmk_pw, pw_key)
        assert recovered_vmk == vmk

    def test_v3_strict_to_recovery_upgrade(self, tmp_path):
        from vault_app.storage import save_vault, load_vault, setup_recovery

        vault_file = str(tmp_path / "test.vault")
        password = "test-passphrase-strict"
        data = {"entries": [{"service": "Strict", "password": "abc"}]}

        vmk = generate_vmk()
        salt_pw = secrets.token_bytes(SALT_SIZE)
        pw_key = derive_key(password, salt_pw, KDF_ARGON2ID,
                            argon2_params={"memory_cost": 16384, "time_cost": 1, "parallelism": 1})
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        header.argon2_memory_cost = 16384
        header.argon2_time_cost = 1
        header.argon2_parallelism = 1
        assert header.has_recovery is False

        fingerprint = save_vault(vault_file, header, data, vmk)

        # Upgrade to recovery mode
        new_header, display_codes, fingerprint = setup_recovery(
            vault_file,
            header,
            data,
            vmk,
            expected_fingerprint=fingerprint,
        )
        assert new_header.has_recovery is True
        assert len(display_codes.split("-")) == 10

        # Verify recovery codes actually work
        raw_recovered = parse_recovery_input(display_codes)
        rec_key = derive_recovery_key(raw_recovered, new_header.salt_rec)
        vmk_from_rec = unwrap_vmk(new_header.enc_vmk_rec, rec_key)
        assert vmk_from_rec == vmk

        # Verify password path still works after upgrade
        parsed, enc_blob, loaded_fingerprint = load_vault(vault_file)
        assert parsed.has_recovery is True
        assert loaded_fingerprint == fingerprint
        vmk_from_pw = unwrap_vmk(parsed.enc_vmk_pw, pw_key)
        assert vmk_from_pw == vmk


class TestRecoveryRateLimiter:
    """Tests for the rate limiter used in the recovery flow."""

    def test_initial_state_not_locked(self):
        limiter = RateLimiter()
        assert not limiter.is_locked
        assert limiter.seconds_remaining == 0.0

    def test_exponential_backoff(self):
        limiter = RateLimiter()
        d1 = limiter.record_failure()
        assert d1 == 2  # 2^1
        d2 = limiter.record_failure()
        assert d2 == 4  # 2^2
        d3 = limiter.record_failure()
        assert d3 == 8  # 2^3

    def test_max_delay_cap(self):
        limiter = RateLimiter()
        for _ in range(10):
            delay = limiter.record_failure()
        assert delay == RateLimiter.MAX_DELAY

    def test_is_locked_after_failure(self):
        limiter = RateLimiter()
        limiter.record_failure()
        assert limiter.is_locked
        assert limiter.seconds_remaining > 0

    def test_success_resets(self):
        limiter = RateLimiter()
        limiter.record_failure()
        limiter.record_failure()
        limiter.record_success()
        assert not limiter.is_locked
        assert limiter.seconds_remaining == 0.0
        # Next failure starts fresh
        d = limiter.record_failure()
        assert d == 2


class TestBackupAndDelete:
    """Tests for backup_exists, restore_from_backup, delete_vault_files."""

    def test_backup_exists_false_when_missing(self, tmp_path, monkeypatch):
        from vault_app import storage
        monkeypatch.setattr(storage, "vault_dir", lambda: str(tmp_path))
        from vault_app.storage import backup_exists
        assert backup_exists() is False

    def test_backup_restore_roundtrip(self, tmp_path, monkeypatch):
        from vault_app import storage
        monkeypatch.setattr(storage, "vault_dir", lambda: str(tmp_path))
        from vault_app.storage import (
            save_vault, load_vault, backup_exists,
            restore_from_backup, delete_vault_files,
        )

        vmk = generate_vmk()
        salt_pw = secrets.token_bytes(SALT_SIZE)
        pw_key = derive_key("test-pw-backup-1234", salt_pw, KDF_ARGON2ID,
                            argon2_params={"memory_cost": 16384, "time_cost": 1, "parallelism": 1})
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        header.argon2_memory_cost = 16384
        header.argon2_time_cost = 1
        header.argon2_parallelism = 1
        data = {"entries": [{"service": "BackupTest", "password": "secret"}]}

        vp = storage.vault_path()
        fingerprint = save_vault(vp, header, data, vmk)
        # First save creates no backup (no pre-existing file)
        assert not backup_exists()

        # Second save creates backup of first version
        data2 = {"entries": [{"service": "BackupTest", "password": "updated"}]}
        save_vault(vp, header, data2, vmk, expected_fingerprint=fingerprint)
        assert backup_exists()

        # Corrupt the main vault
        with open(vp, "wb") as f:
            f.write(b"CORRUPT")

        with pytest.raises(ValueError):
            load_vault(vp)

        # Restore from backup (contains original data)
        assert restore_from_backup() is True

        restored_header, enc_blob, _ = load_vault(vp)
        assert restored_header.version == VAULT_VERSION

    def test_delete_vault_files(self, tmp_path, monkeypatch):
        from vault_app import storage
        monkeypatch.setattr(storage, "vault_dir", lambda: str(tmp_path))
        from vault_app.storage import delete_vault_files

        vp = storage.vault_path()
        bak = vp + ".bak"
        lock = vp + ".lock"

        for p in (vp, bak, lock):
            with open(p, "wb") as f:
                f.write(b"dummy")

        assert os.path.exists(vp)
        assert os.path.exists(bak)
        assert os.path.exists(lock)

        delete_vault_files()

        assert not os.path.exists(vp)
        assert not os.path.exists(bak)
        assert not os.path.exists(lock)

    def test_delete_vault_files_no_error_when_missing(self, tmp_path, monkeypatch):
        from vault_app import storage
        monkeypatch.setattr(storage, "vault_dir", lambda: str(tmp_path))
        from vault_app.storage import delete_vault_files
        delete_vault_files()  # should not raise
