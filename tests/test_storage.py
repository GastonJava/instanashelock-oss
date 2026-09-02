"""Focused tests for vault storage hardening."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.constants import KDF_ARGON2ID, SALT_SIZE
from vault_app.crypto import derive_key, generate_vmk, wrap_vmk
from vault_app.errors import VaultBackupError, VaultBusyError, VaultConflictError, VaultStorageError
from vault_app.header import default_v3_header
from vault_app.storage import (
    export_portable_backup,
    import_portable_backup,
    load_vault,
    restore_from_backup,
    save_vault,
)


def _build_vault_material() -> tuple[object, bytes, dict]:
    vmk = generate_vmk()
    salt_pw = secrets.token_bytes(SALT_SIZE)
    pw_key = derive_key(
        "test-passphrase-storage",
        salt_pw,
        KDF_ARGON2ID,
        argon2_params={"memory_cost": 16384, "time_cost": 1, "parallelism": 1},
    )
    enc_vmk_pw = wrap_vmk(vmk, pw_key)
    header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
    header.argon2_memory_cost = 16384
    header.argon2_time_cost = 1
    header.argon2_parallelism = 1
    data = {"entries": [{"service": "Storage", "password": "secret"}]}
    return header, vmk, data


def _windows_acl_success(cmd, check, capture_output, text, **_kwargs):
    if cmd[0] == "whoami":
        return subprocess.CompletedProcess(cmd, 0, stdout="TEST\\alice\n", stderr="")
    if cmd[0] == "icacls":
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
    raise AssertionError(f"Comando inesperado: {cmd}")


def test_backup_failure_raises_and_preserves_current_vault(tmp_path, monkeypatch):
    from vault_app import storage

    vault_file = str(tmp_path / "backup-failure.vault")
    header, vmk, data = _build_vault_material()
    fingerprint = save_vault(vault_file, header, data, vmk)
    original_raw = Path(vault_file).read_bytes()

    def fail_copy2(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(storage.shutil, "copy2", fail_copy2)

    with pytest.raises(VaultBackupError, match="backup"):
        save_vault(
            vault_file,
            header,
            {"entries": [{"service": "Storage", "password": "updated"}]},
            vmk,
            expected_fingerprint=fingerprint,
        )

    assert Path(vault_file).read_bytes() == original_raw
    assert not list(tmp_path.glob("*.tmp"))


def test_export_portable_backup_writes_identical_encrypted_vault(tmp_path):
    vault_file = str(tmp_path / "portable-source.vault")
    export_file = tmp_path / "portable-export.instanashelock-backup"
    header, vmk, data = _build_vault_material()
    save_vault(vault_file, header, data, vmk)

    exported_path = export_portable_backup(str(export_file), source_path=vault_file)

    assert exported_path == str(export_file.resolve())
    assert export_file.read_bytes() == Path(vault_file).read_bytes()


def test_import_portable_backup_restores_encrypted_vault_and_creates_backup(tmp_path):
    source_vault = str(tmp_path / "portable-source.vault")
    target_vault = str(tmp_path / "portable-target.vault")
    portable_file = tmp_path / "portable-backup.instanashelock-backup"
    header, vmk, data = _build_vault_material()
    save_vault(source_vault, header, data, vmk)
    export_portable_backup(str(portable_file), source_path=source_vault)

    target_header, target_vmk, target_data = _build_vault_material()
    save_vault(target_vault, target_header, target_data, target_vmk)
    previous_target_raw = Path(target_vault).read_bytes()

    import_portable_backup(str(portable_file), destination_path=target_vault)

    assert Path(target_vault).read_bytes() == portable_file.read_bytes()
    assert Path(f"{target_vault}.bak").read_bytes() == previous_target_raw


def test_import_portable_backup_rejects_invalid_file_without_overwriting_target(tmp_path):
    target_vault = str(tmp_path / "portable-target.vault")
    portable_file = tmp_path / "portable-invalid.instanashelock-backup"
    header, vmk, data = _build_vault_material()
    save_vault(target_vault, header, data, vmk)
    original_raw = Path(target_vault).read_bytes()
    portable_file.write_bytes(b"not-a-vault")

    with pytest.raises(ValueError, match="vault valido|magic incorrecto|Archivo demasiado corto"):
        import_portable_backup(str(portable_file), destination_path=target_vault)

    assert Path(target_vault).read_bytes() == original_raw


def test_save_vault_fails_fast_when_another_process_holds_the_lock(tmp_path):
    vault_file = str(tmp_path / "locked.vault")
    ready_file = tmp_path / "lock-ready.txt"
    header, vmk, data = _build_vault_material()
    fingerprint = save_vault(vault_file, header, data, vmk)

    src_dir = str((Path(__file__).resolve().parents[1] / "src"))
    script = """
import sys
import time
sys.path.insert(0, sys.argv[3])
from vault_app.storage import _vault_lock

with _vault_lock(sys.argv[1]):
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write("ready")
    time.sleep(2)
"""

    proc = subprocess.Popen(
        [sys.executable, "-c", script, vault_file, str(ready_file), src_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not ready_file.exists():
            time.sleep(0.05)

        assert ready_file.exists(), "El proceso hijo no llego a tomar el lock."

        with pytest.raises(VaultBusyError, match="otra instancia"):
            save_vault(
                vault_file,
                header,
                {"entries": [{"service": "Storage", "password": "updated"}]},
                vmk,
                expected_fingerprint=fingerprint,
            )
    finally:
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode == 0, stderr or stdout


def test_stale_fingerprint_rejects_silent_overwrite(tmp_path):
    vault_file = str(tmp_path / "stale.vault")
    header, vmk, data = _build_vault_material()
    initial_fingerprint = save_vault(vault_file, header, data, vmk)

    _, _, stale_fingerprint = load_vault(vault_file)

    save_vault(
        vault_file,
        header,
        {"entries": [{"service": "Fresh", "password": "newer"}]},
        vmk,
        expected_fingerprint=initial_fingerprint,
    )

    with pytest.raises(VaultConflictError, match="cambio en disco"):
        save_vault(
            vault_file,
            header,
            {"entries": [{"service": "Stale", "password": "older"}]},
            vmk,
            expected_fingerprint=stale_fingerprint,
        )


def test_windows_vault_dir_uses_localappdata_and_migrates_legacy_files(tmp_path, monkeypatch):
    from vault_app import storage

    local_dir = tmp_path / "local"
    roaming_dir = tmp_path / "roaming"
    legacy_dir = roaming_dir / "Vault"
    legacy_dir.mkdir(parents=True)
    legacy_vault = legacy_dir / "passwords.vault"
    legacy_backup = legacy_dir / "passwords.vault.bak"
    legacy_lock = legacy_dir / "passwords.vault.lock"
    legacy_vault.write_bytes(b"legacy-main")
    legacy_backup.write_bytes(b"legacy-backup")

    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("APPDATA", str(roaming_dir))
    monkeypatch.setattr(storage.subprocess, "run", _windows_acl_success)

    result = storage.vault_dir()

    assert result == str(local_dir / "Instanashelock")
    assert Path(result, "passwords.vault").read_bytes() == b"legacy-main"
    assert Path(result, "passwords.vault.bak").read_bytes() == b"legacy-backup"
    assert not legacy_vault.exists()
    assert not legacy_backup.exists()
    assert not legacy_lock.exists()


def test_windows_vault_dir_does_not_migrate_when_canonical_vault_exists(tmp_path, monkeypatch):
    from vault_app import storage

    local_dir = tmp_path / "local"
    canonical_dir = local_dir / "Instanashelock"
    canonical_dir.mkdir(parents=True)
    canonical_vault = canonical_dir / "passwords.vault"
    canonical_vault.write_bytes(b"canonical-main")

    roaming_dir = tmp_path / "roaming"
    legacy_dir = roaming_dir / "Vault"
    legacy_dir.mkdir(parents=True)
    legacy_vault = legacy_dir / "passwords.vault"
    legacy_vault.write_bytes(b"legacy-main")

    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("APPDATA", str(roaming_dir))
    monkeypatch.setattr(storage.subprocess, "run", _windows_acl_success)

    result = storage.vault_dir()

    assert result == str(canonical_dir)
    assert canonical_vault.read_bytes() == b"canonical-main"
    assert legacy_vault.read_bytes() == b"legacy-main"


def test_windows_existing_vault_dir_tolerates_acl_reapply_failure(tmp_path, monkeypatch):
    from vault_app import storage

    local_dir = tmp_path / "local"
    canonical_dir = local_dir / "Instanashelock"
    canonical_dir.mkdir(parents=True)

    roaming_dir = tmp_path / "roaming"
    roaming_dir.mkdir(parents=True)

    def fail_icacls(cmd, check, capture_output, text, **_kwargs):
        if cmd[0] == "whoami":
            return subprocess.CompletedProcess(cmd, 0, stdout="TEST\\alice\n", stderr="")
        if cmd[0] == "icacls":
            raise subprocess.CalledProcessError(5, cmd, output="", stderr="Access is denied.")
        raise AssertionError(f"Comando inesperado: {cmd}")

    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("APPDATA", str(roaming_dir))
    monkeypatch.setattr(storage.subprocess, "run", fail_icacls)

    result = storage.vault_dir()

    assert result == str(canonical_dir)


def test_save_vault_raises_storage_error_when_windows_acl_hardening_fails(tmp_path, monkeypatch):
    from vault_app import storage

    local_dir = tmp_path / "local"
    roaming_dir = tmp_path / "roaming"
    vault_file = str(local_dir / "Instanashelock" / "acl-failure.vault")
    header, vmk, data = _build_vault_material()

    def fail_icacls(cmd, check, capture_output, text, **_kwargs):
        if cmd[0] == "whoami":
            return subprocess.CompletedProcess(cmd, 0, stdout="TEST\\alice\n", stderr="")
        if cmd[0] == "icacls":
            raise subprocess.CalledProcessError(1, cmd, stderr="access denied")
        raise AssertionError(f"Comando inesperado: {cmd}")

    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("APPDATA", str(roaming_dir))
    monkeypatch.setattr(storage.subprocess, "run", fail_icacls)

    with pytest.raises(VaultStorageError, match="endurecer"):
        save_vault(vault_file, header, data, vmk)

    assert not Path(vault_file).exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_restore_from_backup_raises_storage_error_when_windows_acl_hardening_fails(tmp_path, monkeypatch):
    from vault_app import storage

    local_dir = tmp_path / "local"
    roaming_dir = tmp_path / "roaming"
    vault_file = local_dir / "Instanashelock" / "restore-acl.vault"
    backup_file = tmp_path / "restore-acl.vault.bak"
    vault_file.parent.mkdir(parents=True)
    vault_file.write_bytes(b"current")
    backup_file = vault_file.with_suffix(".vault.bak")
    backup_file.write_bytes(b"backup")

    def fail_icacls(cmd, check, capture_output, text, **_kwargs):
        if cmd[0] == "whoami":
            return subprocess.CompletedProcess(cmd, 0, stdout="TEST\\alice\n", stderr="")
        if cmd[0] == "icacls":
            raise subprocess.CalledProcessError(1, cmd, stderr="access denied")
        raise AssertionError(f"Comando inesperado: {cmd}")

    monkeypatch.setattr(storage.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_dir))
    monkeypatch.setenv("APPDATA", str(roaming_dir))
    monkeypatch.setattr(storage.subprocess, "run", fail_icacls)

    with pytest.raises(VaultStorageError, match="endurecer"):
        restore_from_backup(str(vault_file))

    assert vault_file.read_bytes() == b"current"
    assert not list(tmp_path.glob("*.restore.tmp"))
