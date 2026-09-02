from __future__ import annotations

import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.constants import KDF_ARGON2ID, SALT_SIZE
from vault_app.crypto import derive_key, generate_vmk, wrap_vmk
from vault_app.header import default_v3_header
from vault_app.services.unlock_service import (
    CorruptVault,
    LockedOut,
    MissingVault,
    UnlockService,
    UnlockSuccess,
    UnlockWrongPassword,
    VaultReady,
)
from vault_app.storage import save_vault


def _build_vault_material(password: str) -> tuple[object, bytes, dict]:
    vmk = generate_vmk()
    salt_pw = secrets.token_bytes(SALT_SIZE)
    pw_key = derive_key(
        password,
        salt_pw,
        KDF_ARGON2ID,
        argon2_params={"memory_cost": 16384, "time_cost": 1, "parallelism": 1},
    )
    enc_vmk_pw = wrap_vmk(vmk, pw_key)
    header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
    header.argon2_memory_cost = 16384
    header.argon2_time_cost = 1
    header.argon2_parallelism = 1
    data = {"entries": [{"service": "Example", "username": "alice", "password": "secret"}]}
    return header, vmk, data


def test_probe_vault_reports_ready_when_vault_exists(tmp_path):
    vault_file = tmp_path / "passwords.vault"
    header, vmk, data = _build_vault_material("test-passphrase")
    save_vault(str(vault_file), header, data, vmk)

    service = UnlockService(path=str(vault_file))
    result = service.probe_vault()

    assert isinstance(result, VaultReady)
    assert result.has_recovery is False


def test_unlock_service_returns_success_for_correct_password(tmp_path):
    vault_file = tmp_path / "passwords.vault"
    header, vmk, data = _build_vault_material("correct horse battery staple")
    save_vault(str(vault_file), header, data, vmk)

    service = UnlockService(path=str(vault_file))
    result = service.unlock("correct horse battery staple")

    assert isinstance(result, UnlockSuccess)
    assert result.data["entries"][0]["service"] == "Example"


def test_unlock_service_returns_wrong_password_and_starts_cooldown(tmp_path):
    vault_file = tmp_path / "passwords.vault"
    header, vmk, data = _build_vault_material("good-passphrase")
    save_vault(str(vault_file), header, data, vmk)

    service = UnlockService(path=str(vault_file))
    result = service.unlock("bad-passphrase")

    assert isinstance(result, UnlockWrongPassword)
    assert result.failures == 1
    assert result.cooldown_seconds >= 1


def test_unlock_service_returns_locked_out_during_active_cooldown(tmp_path):
    vault_file = tmp_path / "passwords.vault"
    header, vmk, data = _build_vault_material("good-passphrase")
    save_vault(str(vault_file), header, data, vmk)

    service = UnlockService(path=str(vault_file))
    first = service.unlock("bad-passphrase")
    second = service.unlock("bad-passphrase")

    assert isinstance(first, UnlockWrongPassword)
    assert isinstance(second, LockedOut)
    assert second.cooldown_seconds > 0


def test_unlock_service_reports_missing_vault_for_absent_file(tmp_path):
    service = UnlockService(path=str(tmp_path / "missing.vault"))
    result = service.unlock("anything")

    assert isinstance(result, MissingVault)


def test_unlock_service_reports_corrupt_vault_for_invalid_file(tmp_path):
    vault_file = tmp_path / "corrupt.vault"
    Path(vault_file).write_bytes(b"not-a-vault")

    service = UnlockService(path=str(vault_file))
    result = service.unlock("anything")

    assert isinstance(result, CorruptVault)
    assert result.reason in {"parse_error", "load_error"}
