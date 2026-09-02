from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import secrets
from typing import TypeAlias

from cryptography.exceptions import InvalidTag

from vault_app.constants import KDF_ARGON2ID, SALT_SIZE
from vault_app.crypto import derive_key, generate_vmk, wrap_vmk
from vault_app.errors import VaultStorageError
from vault_app.header import VaultHeader, default_v3_header
from vault_app.security import RateLimiter
from vault_app.storage import (
    decrypt_with_password,
    load_vault,
    save_vault,
    setup_recovery,
    vault_path,
)


@dataclass(frozen=True)
class VaultReady:
    has_recovery: bool
    fingerprint: str


@dataclass(frozen=True)
class MissingVault:
    pass


@dataclass(frozen=True)
class CorruptVault:
    reason: str
    detail: str


@dataclass(frozen=True)
class UnlockWrongPassword:
    cooldown_seconds: float
    failures: int
    has_recovery: bool
    recovery_available: bool
    reset_recommended: bool


@dataclass(frozen=True)
class LockedOut:
    cooldown_seconds: float
    has_recovery: bool


@dataclass(frozen=True)
class UnlockSuccess:
    header: VaultHeader
    vmk: bytes
    data: dict
    fingerprint: str


@dataclass(frozen=True)
class CreateVaultSuccess:
    header: VaultHeader
    vmk: bytes
    data: dict
    fingerprint: str
    recovery_codes: str
    recovery_enabled: bool
    warning: str = ""


@dataclass(frozen=True)
class CreateVaultValidationError:
    message: str


@dataclass(frozen=True)
class CreateVaultAlreadyExists:
    path: str


@dataclass(frozen=True)
class CreateVaultStorageFailure:
    message: str


UnlockProbeResult: TypeAlias = VaultReady | MissingVault | CorruptVault
UnlockResult: TypeAlias = UnlockSuccess | UnlockWrongPassword | LockedOut | MissingVault | CorruptVault
CreateVaultResult: TypeAlias = (
    CreateVaultSuccess
    | CreateVaultValidationError
    | CreateVaultAlreadyExists
    | CreateVaultStorageFailure
)


class UnlockService:
    def __init__(
        self,
        *,
        path: str | None = None,
        limiter: RateLimiter | None = None,
        recovery_threshold: int = 3,
    ) -> None:
        self._path = path
        self._limiter = limiter or RateLimiter()
        self._recovery_threshold = recovery_threshold
        self._last_has_recovery = False

    @property
    def limiter(self) -> RateLimiter:
        return self._limiter

    @property
    def last_has_recovery(self) -> bool:
        return self._last_has_recovery

    def probe_vault(self) -> UnlockProbeResult:
        vault_file = self._vault_file()
        if not os.path.exists(vault_file):
            self._last_has_recovery = False
            return MissingVault()

        try:
            header, _enc_blob, fingerprint = load_vault(vault_file)
        except (OSError, IOError) as exc:
            self._last_has_recovery = False
            return CorruptVault(reason="load_error", detail=str(exc))
        except ValueError as exc:
            self._last_has_recovery = False
            return CorruptVault(reason="parse_error", detail=str(exc))

        self._last_has_recovery = header.has_recovery
        return VaultReady(has_recovery=header.has_recovery, fingerprint=fingerprint)

    def unlock(self, password: str) -> UnlockResult:
        if self._limiter.is_locked:
            return LockedOut(
                cooldown_seconds=self._limiter.seconds_remaining,
                has_recovery=self._last_has_recovery,
            )

        vault_file = self._vault_file()
        if not os.path.exists(vault_file):
            self._last_has_recovery = False
            return MissingVault()

        try:
            header, encrypted_blob, fingerprint = load_vault(vault_file)
        except (OSError, IOError) as exc:
            self._last_has_recovery = False
            return CorruptVault(reason="load_error", detail=str(exc))
        except ValueError as exc:
            self._last_has_recovery = False
            return CorruptVault(reason="parse_error", detail=str(exc))

        self._last_has_recovery = header.has_recovery

        try:
            header, vmk, data = decrypt_with_password(vault_file, header, encrypted_blob, password)
        except InvalidTag:
            delay = self._limiter.record_failure()
            failures = self._limiter.failures
            return UnlockWrongPassword(
                cooldown_seconds=delay,
                failures=failures,
                has_recovery=header.has_recovery,
                recovery_available=header.has_recovery and failures >= self._recovery_threshold,
                reset_recommended=(not header.has_recovery) and failures >= self._recovery_threshold,
            )
        except ValueError as exc:
            return CorruptVault(reason="decrypt_error", detail=str(exc))
        except json.JSONDecodeError:
            return CorruptVault(
                reason="invalid_json",
                detail="Vault desencriptado pero contenido corrupto (JSON invalido).",
            )

        self._limiter.record_success()
        return UnlockSuccess(header=header, vmk=vmk, data=data, fingerprint=fingerprint)

    def seconds_remaining_label(self) -> int:
        return self._seconds_label(self._limiter.seconds_remaining)

    @staticmethod
    def _seconds_label(seconds: float) -> int:
        if seconds <= 0:
            return 0
        return max(1, math.ceil(seconds))

    def _vault_file(self) -> str:
        return os.path.abspath(self._path or vault_path())


class CreateVaultService:
    def __init__(self, *, path: str | None = None) -> None:
        self._path = path

    def create_vault(self, password: str, *, recovery_enabled: bool) -> CreateVaultResult:
        if len(password) < 12:
            return CreateVaultValidationError(
                "Use at least 12 characters or a longer passphrase."
            )

        vault_file = self._vault_file()
        if os.path.exists(vault_file):
            return CreateVaultAlreadyExists(path=vault_file)

        salt_pw = secrets.token_bytes(SALT_SIZE)
        pw_key = derive_key(password, salt_pw, kdf_id=KDF_ARGON2ID)
        vmk = generate_vmk()
        enc_vmk_pw = wrap_vmk(vmk, pw_key)
        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        data: dict = {"entries": []}

        try:
            fingerprint = save_vault(vault_file, header, data, vmk)
        except VaultStorageError as exc:
            return CreateVaultStorageFailure(message=str(exc))

        if not recovery_enabled:
            return CreateVaultSuccess(
                header=header,
                vmk=vmk,
                data=data,
                fingerprint=fingerprint,
                recovery_codes="",
                recovery_enabled=False,
            )

        try:
            header, display_codes, fingerprint = setup_recovery(
                vault_file,
                header,
                data,
                vmk,
                expected_fingerprint=fingerprint,
            )
        except VaultStorageError as exc:
            return CreateVaultSuccess(
                header=header,
                vmk=vmk,
                data=data,
                fingerprint=fingerprint,
                recovery_codes="",
                recovery_enabled=False,
                warning=(
                    "The vault was created, but recovery codes could not be saved. "
                    f"{exc}"
                ),
            )

        return CreateVaultSuccess(
            header=header,
            vmk=vmk,
            data=data,
            fingerprint=fingerprint,
            recovery_codes=display_codes,
            recovery_enabled=True,
        )

    def _vault_file(self) -> str:
        return os.path.abspath(self._path or vault_path())
