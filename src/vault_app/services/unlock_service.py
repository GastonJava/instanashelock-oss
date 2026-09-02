"""UI-agnostic unlock orchestration shared by v1 and v2."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from typing import TypeAlias

from cryptography.exceptions import InvalidTag

from vault_app.header import VaultHeader
from vault_app.security import RateLimiter
from vault_app.storage import decrypt_with_password, load_vault, vault_path


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


UnlockProbeResult: TypeAlias = VaultReady | MissingVault | CorruptVault
UnlockResult: TypeAlias = UnlockSuccess | UnlockWrongPassword | LockedOut | MissingVault | CorruptVault


class UnlockService:
    """Service that owns existing-vault unlock and cooldown behavior."""

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
