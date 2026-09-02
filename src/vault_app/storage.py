"""
Vault file I/O: paths, atomic save, load with migration.

v3 introduces a Vault Master Key (VMK). The vault data is always encrypted
with the VMK; the VMK itself is wrapped (encrypted) with the password-derived
key and, optionally, with a recovery-derived key.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
import secrets as _secrets
import shutil
import subprocess
import sys
import tempfile

from vault_app.constants import (
    APP_DIR_NAME,
    PORTABLE_BACKUP_EXTENSION,
    VAULT_VERSION,
    VAULT_VERSION_2,
    VAULT_VERSION_LEGACY,
    KDF_PBKDF2_SHA256,
    KDF_ARGON2ID,
    SALT_SIZE,
)
from vault_app.header import VaultHeader, parse_header, default_v3_header
from vault_app.errors import (
    VaultBackupError,
    VaultBusyError,
    VaultConflictError,
    VaultStorageError,
)
from vault_app.crypto import (
    derive_key,
    encrypt_vault,
    decrypt_vault,
    generate_vmk,
    wrap_vmk,
    unwrap_vmk,
)


# Paths


def vault_dir() -> str:
    """Return (and create) the platform-appropriate vault storage directory."""
    if sys.platform == "win32":
        d = _windows_canonical_vault_dir()
        created = not os.path.isdir(d)
        os.makedirs(d, exist_ok=True)
        _set_private_permissions(d, strict=created, is_dir=True)
        _migrate_legacy_windows_vault(d)
    else:
        d = os.path.join(os.path.expanduser("~"), ".local", "share", "vault")
        os.makedirs(d, exist_ok=True)
    return d


def vault_path() -> str:
    return os.path.join(vault_dir(), "passwords.vault")


def _resolve_path(path: str | None = None) -> str:
    return os.path.abspath(path or vault_path())


def _backup_path(path: str | None = None) -> str:
    return f"{_resolve_path(path)}.bak"


def _lock_path(path: str | None = None) -> str:
    return f"{_resolve_path(path)}.lock"


def legacy_vault_dir() -> str | None:
    """Return the legacy Windows roaming directory when applicable."""
    if sys.platform != "win32":
        return None

    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(base, "Vault")


def _ensure_parent_dir(path: str) -> str:
    directory = os.path.dirname(_resolve_path(path))
    if directory:
        created = not os.path.isdir(directory)
        os.makedirs(directory, exist_ok=True)
        if created:
            _set_private_permissions(directory, strict=True, is_dir=True)
    return directory


def _set_private_permissions(path: str, *, strict: bool, is_dir: bool = False) -> None:
    if sys.platform == "win32":
        _set_windows_private_permissions(path, strict=strict, is_dir=is_dir)
        return

    mode = 0o700 if is_dir else 0o600
    try:
        os.chmod(path, mode)
    except OSError as exc:
        if strict:
            raise VaultStorageError(
                f"No se pudieron ajustar los permisos privados para '{path}'."
            ) from exc


def _fsync_dir(path: str) -> None:
    if sys.platform == "win32":
        return
    try:
        dirfd = os.open(os.path.dirname(path), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except OSError:
        pass


def _cleanup_file(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _windows_canonical_vault_dir() -> str:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(base, APP_DIR_NAME)


def _windows_hidden_subprocess_kwargs() -> dict[str, object]:
    """Hide helper console tools when the app runs as a GUI process."""
    if sys.platform != "win32":
        return {}

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        return {"creationflags": creationflags}
    return {}


def _resolve_windows_principal() -> str:
    try:
        result = subprocess.run(
            ["whoami"],
            check=True,
            capture_output=True,
            text=True,
            **_windows_hidden_subprocess_kwargs(),
        )
    except OSError as exc:
        raise VaultStorageError(
            "No se pudo resolver el usuario actual para endurecer permisos en Windows."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise VaultStorageError(
            "No se pudo resolver el usuario actual para endurecer permisos en Windows."
        ) from exc

    principal = result.stdout.strip()
    if not principal:
        raise VaultStorageError(
            "No se pudo resolver el usuario actual para endurecer permisos en Windows."
        )
    return principal


def _set_windows_private_permissions(path: str, *, strict: bool, is_dir: bool) -> None:
    rights = "(OI)(CI)F" if is_dir else "F"
    principal = _resolve_windows_principal()
    try:
        subprocess.run(
            [
                "icacls",
                path,
                "/inheritance:r",
                "/grant:r",
                f"{principal}:{rights}",
            ],
            check=True,
            capture_output=True,
            text=True,
            **_windows_hidden_subprocess_kwargs(),
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if strict and _should_enforce_windows_acl(path):
            raise VaultStorageError(
                f"No se pudieron endurecer los permisos de '{path}' en Windows."
            ) from exc


def _should_enforce_windows_acl(path: str) -> bool:
    resolved = os.path.abspath(path)
    managed_roots = [os.path.abspath(_windows_canonical_vault_dir())]
    legacy_dir = legacy_vault_dir()
    if legacy_dir:
        managed_roots.append(os.path.abspath(legacy_dir))

    for root in managed_roots:
        try:
            if os.path.commonpath([resolved, root]) == root:
                return True
        except ValueError:
            continue
    return False


def _migrate_legacy_windows_vault(canonical_dir: str) -> None:
    if sys.platform != "win32":
        return

    legacy_dir = legacy_vault_dir()
    if not legacy_dir:
        return

    canonical_vault = os.path.join(canonical_dir, "passwords.vault")
    if os.path.exists(canonical_vault):
        return

    canonical_backup = f"{canonical_vault}.bak"
    if os.path.exists(canonical_backup):
        raise VaultStorageError(
            "Se encontro un backup en la nueva ruta de Instanashelock sin vault principal. "
            "Revisa la carpeta local antes de continuar."
        )

    legacy_vault = os.path.join(legacy_dir, "passwords.vault")
    if not os.path.exists(legacy_vault):
        return

    legacy_backup = f"{legacy_vault}.bak"
    legacy_lock = _lock_path(legacy_vault)
    copied_targets: list[str] = []
    copied_sources: list[str] = []

    try:
        with _vault_lock(legacy_vault):
            with open(legacy_vault, "rb") as f:
                raw_vault = f.read()
            _atomic_restore(canonical_vault, raw_vault)
            copied_targets.append(canonical_vault)
            copied_sources.append(legacy_vault)

            if os.path.exists(legacy_backup):
                with open(legacy_backup, "rb") as f:
                    raw_backup = f.read()
                _atomic_restore(canonical_backup, raw_backup)
                copied_targets.append(canonical_backup)
                copied_sources.append(legacy_backup)
    except VaultStorageError as exc:
        for target in copied_targets:
            _cleanup_file(target)
        raise VaultStorageError(
            "No se pudo migrar el vault legacy desde %APPDATA% a %LOCALAPPDATA%. "
            "Los archivos originales quedaron intactos."
        ) from exc
    except OSError as exc:
        for target in copied_targets:
            _cleanup_file(target)
        raise VaultStorageError(
            "No se pudo migrar el vault legacy desde %APPDATA% a %LOCALAPPDATA%. "
            "Los archivos originales quedaron intactos."
        ) from exc

    for source in copied_sources:
        try:
            os.remove(source)
        except OSError as exc:
            raise VaultStorageError(
                "El vault se migro a la nueva ruta local, pero no se pudieron eliminar "
                "los archivos antiguos de %APPDATA%."
            ) from exc

    # El lock del vault legacy es solo un detalle operacional de la migracion.
    # Si queda remanente, genera ruido visual aunque el vault ya no viva ahi.
    _cleanup_file(legacy_lock)


def _fingerprint_raw(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _current_fingerprint(path: str) -> str | None:
    target = _resolve_path(path)
    if not os.path.exists(target):
        return None
    with open(target, "rb") as f:
        return _fingerprint_raw(f.read())


def current_vault_fingerprint(path: str | None = None) -> str | None:
    """Return the current on-disk fingerprint for a vault path."""
    return _current_fingerprint(path or vault_path())


@contextmanager
def _vault_lock(path: str):
    target = _resolve_path(path)
    lock_path = _lock_path(target)
    _ensure_parent_dir(target)

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    _set_private_permissions(lock_path, strict=False)
    locked = False
    try:
        if sys.platform == "win32":
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise VaultBusyError(
                    "El vault ya esta siendo usado por otra instancia. "
                    "Cierra la otra ventana e intenta de nuevo."
                ) from exc
        else:
            import fcntl

            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise VaultBusyError(
                    "El vault ya esta siendo usado por otra instancia. "
                    "Cierra la otra ventana e intenta de nuevo."
                ) from exc
        locked = True
        yield
    finally:
        if locked:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)


# Save


def save_vault(
    path: str,
    header: VaultHeader,
    data: dict,
    vmk: bytes,
    *,
    expected_fingerprint: str | None = None,
) -> str:
    """Encrypt *data* with *vmk* and write atomically to *path*.

    The *header* must already contain ``enc_vmk_pw`` (and optionally
    ``enc_vmk_rec``). The vault data is encrypted with the VMK, using
    the serialised header as AAD.
    """
    header_bytes = header.serialise()
    encrypted_blob = encrypt_vault(data, vmk, aad=header_bytes)
    with _vault_lock(path):
        _check_expected_fingerprint(path, expected_fingerprint)
        return _atomic_write(path, header_bytes + encrypted_blob)


def _check_expected_fingerprint(path: str, expected_fingerprint: str | None) -> None:
    if expected_fingerprint is None:
        return
    current = _current_fingerprint(path)
    if current != expected_fingerprint:
        raise VaultConflictError(
            "El vault cambio en disco desde que esta ventana lo abrio. "
            "Recarga la aplicacion antes de guardar para no perder cambios."
        )


def _atomic_write(path: str, raw: bytes) -> str:
    target = _resolve_path(path)
    bak = _backup_path(target)
    parent_dir = _ensure_parent_dir(target)
    fd, tmp = tempfile.mkstemp(
        prefix=f"{os.path.basename(target)}.",
        suffix=".tmp",
        dir=parent_dir,
    )
    replaced = False
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        _set_private_permissions(tmp, strict=True)

        if os.path.exists(target):
            try:
                shutil.copy2(target, bak)
                _set_private_permissions(bak, strict=True)
            except OSError as exc:
                raise VaultBackupError(
                    "No se pudo crear o actualizar el backup del vault."
                ) from exc

        os.replace(tmp, target)
        replaced = True

        try:
            with open(target, "rb+") as f:
                os.fsync(f.fileno())
        except OSError as exc:
            raise VaultStorageError(
                "El vault se escribio pero no se pudo confirmar en disco."
            ) from exc

        _fsync_dir(target)
        _set_private_permissions(target, strict=True)
        return _fingerprint_raw(raw)
    except VaultBackupError:
        if not replaced:
            _cleanup_file(tmp)
        raise
    except VaultStorageError:
        if not replaced:
            _cleanup_file(tmp)
        raise
    except OSError as exc:
        if not replaced:
            _cleanup_file(tmp)
        raise VaultStorageError("No se pudo guardar el vault en disco.") from exc
    except Exception:
        if not replaced:
            _cleanup_file(tmp)
        raise


# Backup helpers


def backup_exists(path: str | None = None) -> bool:
    """Return True if a backup vault file exists."""
    return os.path.isfile(_backup_path(path))


def restore_from_backup(path: str | None = None) -> bool:
    """Replace the main vault with the backup file. Returns True on success."""
    vp = _resolve_path(path)
    bak = _backup_path(vp)
    if not os.path.isfile(bak):
        return False
    with _vault_lock(vp):
        with open(bak, "rb") as f:
            raw = f.read()
        _atomic_restore(vp, raw)
    return True


def export_portable_backup(
    destination_path: str,
    *,
    source_path: str | None = None,
) -> str:
    """Export the encrypted vault as a portable backup file."""
    source = _resolve_path(source_path or vault_path())
    if not os.path.isfile(source):
        raise VaultStorageError("No existe un vault local para exportar.")

    target = os.path.abspath(destination_path)
    if not target:
        raise VaultStorageError("Debes elegir una ruta valida para exportar el respaldo.")

    try:
        with open(source, "rb") as f:
            raw = f.read()
    except OSError as exc:
        raise VaultStorageError("No se pudo leer el vault local para exportarlo.") from exc

    parse_header(raw)
    _atomic_export(target, raw)
    return target


def import_portable_backup(
    source_path: str,
    *,
    destination_path: str | None = None,
) -> str:
    """Import a portable encrypted backup into the local managed vault path."""
    source = os.path.abspath(source_path)
    if not os.path.isfile(source):
        raise VaultStorageError("No existe el archivo de respaldo seleccionado.")

    try:
        with open(source, "rb") as f:
            raw = f.read()
    except OSError as exc:
        raise VaultStorageError("No se pudo leer el archivo de respaldo seleccionado.") from exc

    parse_header(raw)

    target = _resolve_path(destination_path or vault_path())
    with _vault_lock(target):
        return _atomic_write(target, raw)


def portable_backup_suggested_name() -> str:
    """Return a stable suggested filename for portable encrypted backups."""
    return f"instanashelock-backup{PORTABLE_BACKUP_EXTENSION}"


def _atomic_restore(path: str, raw: bytes) -> None:
    target = _resolve_path(path)
    parent_dir = _ensure_parent_dir(target)
    fd, tmp = tempfile.mkstemp(
        prefix=f"{os.path.basename(target)}.",
        suffix=".restore.tmp",
        dir=parent_dir,
    )
    replaced = False
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        _set_private_permissions(tmp, strict=True)

        os.replace(tmp, target)
        replaced = True

        try:
            with open(target, "rb+") as f:
                os.fsync(f.fileno())
        except OSError as exc:
            raise VaultStorageError(
                "El backup se restauro pero no se pudo confirmar en disco."
            ) from exc

        _fsync_dir(target)
        _set_private_permissions(target, strict=True)
    except VaultStorageError:
        if not replaced:
            _cleanup_file(tmp)
        raise
    except OSError as exc:
        if not replaced:
            _cleanup_file(tmp)
        raise VaultStorageError("No se pudo restaurar el backup.") from exc
    except Exception:
        if not replaced:
            _cleanup_file(tmp)
        raise


def _atomic_export(path: str, raw: bytes) -> None:
    target = os.path.abspath(path)
    parent_dir = _ensure_parent_dir(target)
    fd, tmp = tempfile.mkstemp(
        prefix=f"{os.path.basename(target)}.",
        suffix=".export.tmp",
        dir=parent_dir,
    )
    replaced = False
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        _set_private_permissions(tmp, strict=False)

        os.replace(tmp, target)
        replaced = True

        try:
            with open(target, "rb+") as f:
                os.fsync(f.fileno())
        except OSError as exc:
            raise VaultStorageError(
                "El respaldo se escribio pero no se pudo confirmar en disco."
            ) from exc

        _fsync_dir(target)
        _set_private_permissions(target, strict=False)
    except VaultStorageError:
        if not replaced:
            _cleanup_file(tmp)
        raise
    except OSError as exc:
        if not replaced:
            _cleanup_file(tmp)
        raise VaultStorageError("No se pudo exportar el respaldo cifrado.") from exc
    except Exception:
        if not replaced:
            _cleanup_file(tmp)
        raise


def delete_vault_files(path: str | None = None) -> None:
    """Remove the vault, its backup, and local lock file."""
    target = _resolve_path(path)
    for p in (target, _backup_path(target), _lock_path(target)):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


# Load


def load_vault(path: str) -> tuple[VaultHeader, bytes, str]:
    """Read and parse the vault file. Returns ``(header, encrypted_blob, fingerprint)``."""
    with open(_resolve_path(path), "rb") as f:
        raw = f.read()
    header, encrypted_blob = parse_header(raw)
    return header, encrypted_blob, _fingerprint_raw(raw)


def load_unlocked_vault(path: str, vmk: bytes) -> tuple[VaultHeader, dict, str]:
    """Read the current vault from disk using an already unlocked VMK."""
    header, encrypted_blob, fingerprint = load_vault(path)
    data = decrypt_vault(encrypted_blob, vmk, aad=header.serialise())
    return header, data, fingerprint


# Decrypt (with migration)


def decrypt_with_password(
    path: str,
    header: VaultHeader,
    encrypted_blob: bytes,
    password: str,
) -> tuple[VaultHeader, bytes, dict]:
    """Decrypt the vault using the master password.

    Handles v1, v2, and v3 formats. v1/v2 vaults are migrated to v3 on the fly
    (the migration does NOT set up recovery keys, that happens in the UI).

    Returns ``(header, vmk, data)``.
    """
    if header.version == VAULT_VERSION_LEGACY:
        return _migrate_v1(path, header, encrypted_blob, password)

    if header.version == VAULT_VERSION_2:
        return _migrate_v2(path, header, encrypted_blob, password)

    pw_key = _derive_pw_key(password, header)
    vmk = unwrap_vmk(header.enc_vmk_pw, pw_key)
    aad = header.serialise()
    data = decrypt_vault(encrypted_blob, vmk, aad=aad)
    return header, vmk, data


def decrypt_with_recovery(
    path: str,
    header: VaultHeader,
    encrypted_blob: bytes,
    recovery_raw: bytes,
) -> tuple[VaultHeader, bytes, dict]:
    """Decrypt the vault using recovery codes (v3 only).

    Returns ``(header, vmk, data)``.
    Raises ``ValueError`` if the vault has no recovery data.
    Raises ``InvalidTag`` if the codes are wrong.
    """
    if header.version != VAULT_VERSION:
        raise ValueError("Recovery solo disponible en vaults v3.")
    if not header.has_recovery:
        raise ValueError("Este vault no tiene recovery keys configurados.")

    from vault_app.recovery import derive_recovery_key

    rec_key = derive_recovery_key(recovery_raw, header.salt_rec)
    vmk = unwrap_vmk(header.enc_vmk_rec, rec_key)
    aad = header.serialise()
    data = decrypt_vault(encrypted_blob, vmk, aad=aad)
    return header, vmk, data


# Re-wrap helpers (for password change / recovery regeneration)


def rewrap_vmk_for_new_password(
    path: str,
    header: VaultHeader,
    data: dict,
    vmk: bytes,
    new_password: str,
    *,
    expected_fingerprint: str | None = None,
) -> tuple[VaultHeader, str]:
    """Re-wrap VMK with a new master password and save. Returns updated header and fingerprint."""
    new_salt_pw = _secrets.token_bytes(SALT_SIZE)
    new_pw_key = derive_key(new_password, new_salt_pw, kdf_id=KDF_ARGON2ID)
    new_enc_vmk_pw = wrap_vmk(vmk, new_pw_key)

    new_header = default_v3_header(
        salt_pw=new_salt_pw,
        enc_vmk_pw=new_enc_vmk_pw,
        has_recovery=header.has_recovery,
        salt_rec=header.salt_rec,
        enc_vmk_rec=header.enc_vmk_rec,
    )
    new_fingerprint = save_vault(
        path,
        new_header,
        data,
        vmk,
        expected_fingerprint=expected_fingerprint,
    )
    return new_header, new_fingerprint


def setup_recovery(
    path: str,
    header: VaultHeader,
    data: dict,
    vmk: bytes,
    *,
    expected_fingerprint: str | None = None,
) -> tuple[VaultHeader, str, str]:
    """Generate new recovery codes, wrap VMK, save. Returns ``(new_header, display_codes, fingerprint)``."""
    from vault_app.recovery import generate_recovery_secret, derive_recovery_key

    display_codes, raw_secret = generate_recovery_secret()
    salt_rec = _secrets.token_bytes(SALT_SIZE)
    rec_key = derive_recovery_key(raw_secret, salt_rec)
    enc_vmk_rec = wrap_vmk(vmk, rec_key)

    new_header = default_v3_header(
        salt_pw=header.salt,
        enc_vmk_pw=header.enc_vmk_pw,
        has_recovery=True,
        salt_rec=salt_rec,
        enc_vmk_rec=enc_vmk_rec,
    )
    # Preserve KDF params from current header
    new_header.kdf_id = header.kdf_id
    new_header.iterations = header.iterations
    new_header.argon2_memory_cost = header.argon2_memory_cost
    new_header.argon2_time_cost = header.argon2_time_cost
    new_header.argon2_parallelism = header.argon2_parallelism

    new_fingerprint = save_vault(
        path,
        new_header,
        data,
        vmk,
        expected_fingerprint=expected_fingerprint,
    )
    return new_header, display_codes, new_fingerprint


# Migration helpers


def _derive_pw_key(password: str, header: VaultHeader) -> bytes:
    if header.kdf_id == KDF_ARGON2ID:
        return derive_key(
            password,
            header.salt,
            kdf_id=header.kdf_id,
            argon2_params=header.argon2_params,
        )
    return derive_key(
        password,
        header.salt,
        kdf_id=header.kdf_id,
        iterations=header.iterations,
    )


def _migrate_v1(
    path: str, header: VaultHeader, encrypted_blob: bytes, password: str,
) -> tuple[VaultHeader, bytes, dict]:
    """v1 -> v3: PBKDF2 hardcoded, no AAD -> Argon2id + VMK + AAD."""
    key = derive_key(
        password,
        header.salt,
        kdf_id=header.kdf_id,
        iterations=header.iterations,
    )
    data = decrypt_vault(encrypted_blob, key, aad=None)
    return _create_v3_from_data(path, password, data)


def _migrate_v2(
    path: str, header: VaultHeader, encrypted_blob: bytes, password: str,
) -> tuple[VaultHeader, bytes, dict]:
    """v2 -> v3: direct key -> VMK wrapper."""
    pw_key = _derive_pw_key(password, header)
    aad = header.serialise()
    data = decrypt_vault(encrypted_blob, pw_key, aad=aad)
    return _create_v3_from_data(path, password, data)


def _create_v3_from_data(
    path: str, password: str, data: dict,
) -> tuple[VaultHeader, bytes, dict]:
    """Shared migration: create a fresh v3 vault (no recovery yet)."""
    new_salt_pw = _secrets.token_bytes(SALT_SIZE)
    pw_key = derive_key(password, new_salt_pw, kdf_id=KDF_ARGON2ID)
    vmk = generate_vmk()
    enc_vmk_pw = wrap_vmk(vmk, pw_key)
    new_header = default_v3_header(salt_pw=new_salt_pw, enc_vmk_pw=enc_vmk_pw)
    save_vault(path, new_header, data, vmk)
    return new_header, vmk, data
