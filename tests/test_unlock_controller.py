from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication

from vault_app_v2.services.auth_service import (
    CorruptVault,
    CreateVaultSuccess,
    MissingVault,
    UnlockSuccess,
    UnlockWrongPassword,
    VaultReady,
)
from vault_app_v2.controllers.unlock_controller import UnlockController


class _FakeLimiter:
    def __init__(self) -> None:
        self.seconds_remaining = 0.0


class _FakeService:
    def __init__(self, probe_result, unlock_results):
        self._probe_result = probe_result
        self._unlock_results = list(unlock_results)
        self.limiter = _FakeLimiter()
        self.unlock_calls = 0

    def probe_vault(self):
        return self._probe_result

    def unlock(self, _password: str):
        self.unlock_calls += 1
        result = self._unlock_results.pop(0)
        if isinstance(result, UnlockWrongPassword):
            self.limiter.seconds_remaining = result.cooldown_seconds
        else:
            self.limiter.seconds_remaining = 0.0
        return result


class _FakeCreateService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_vault(self, password: str, *, recovery_enabled: bool):
        self.calls.append((password, recovery_enabled))
        return self.result


def _app() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


def test_unlock_controller_maps_ready_probe_to_unlock_route():
    _app()
    controller = UnlockController(service=_FakeService(VaultReady(has_recovery=False, fingerprint="fp"), []))

    assert controller.currentRoute == "unlock"
    assert controller.helperText == controller.DEFAULT_HELPER


def test_unlock_controller_maps_wrong_password_to_error_and_cooldown():
    _app()
    fake_service = _FakeService(
        VaultReady(has_recovery=False, fingerprint="fp"),
        [
            UnlockWrongPassword(
                cooldown_seconds=2.0,
                failures=1,
                has_recovery=False,
                recovery_available=False,
                reset_recommended=False,
            )
        ],
    )
    controller = UnlockController(service=fake_service)

    controller.submitPassword("wrong")

    assert controller.errorText == "That main password does not unlock this vault."
    assert controller.cooldownSeconds == 2
    assert controller.canSubmit is False


def test_unlock_controller_clears_stale_error_on_new_submission():
    _app()
    fake_service = _FakeService(
        VaultReady(has_recovery=False, fingerprint="fp"),
        [
            UnlockWrongPassword(
                cooldown_seconds=1.0,
                failures=1,
                has_recovery=False,
                recovery_available=False,
                reset_recommended=False,
            ),
            UnlockSuccess(header=None, vmk=b"vmk", data={"entries": []}, fingerprint="fp"),
        ],
    )
    controller = UnlockController(service=fake_service)

    controller.submitPassword("wrong")
    controller._cooldown_seconds = 0
    fake_service.limiter.seconds_remaining = 0.0
    controller.submitPassword("correct")

    assert controller.errorText == ""
    assert controller.currentRoute == "unlocked"


def test_unlock_controller_missing_vault_submit_routes_to_create():
    _app()
    fake_service = _FakeService(MissingVault(), [MissingVault()])
    controller = UnlockController(service=fake_service)

    controller.submitPassword("anything")

    assert controller.currentRoute == "create"
    assert controller.errorText == "No local vault yet."


def test_unlock_controller_ignores_submit_when_busy():
    _app()
    fake_service = _FakeService(VaultReady(has_recovery=False, fingerprint="fp"), [])
    controller = UnlockController(service=fake_service)
    controller._busy = True

    controller.submitPassword("anything")

    assert fake_service.unlock_calls == 0


def test_unlock_controller_routes_missing_and_corrupt_states():
    _app()
    missing = UnlockController(service=_FakeService(MissingVault(), []))
    corrupt = UnlockController(service=_FakeService(CorruptVault(reason="parse_error", detail="bad"), []))

    assert missing.currentRoute == "create"
    assert "No local vault yet" in missing.helperText
    assert corrupt.currentRoute == "corrupt"


def test_unlock_controller_navigation_helpers_cover_create_and_unlock_preview():
    _app()
    controller = UnlockController(service=_FakeService(MissingVault(), []))

    controller.goToUnlockPreview()
    assert controller.currentRoute == "unlock"
    assert controller.helperText == controller.DEFAULT_HELPER

    controller.goToCreateVault()
    assert controller.currentRoute == "create"
    assert controller.helperText == controller.MISSING_VAULT_HELPER


def test_unlock_controller_create_strict_routes_to_unlocked():
    _app()
    create_service = _FakeCreateService(
        CreateVaultSuccess(
            header=None,
            vmk=b"vmk",
            data={"entries": []},
            fingerprint="fp",
            recovery_codes="",
            recovery_enabled=False,
        )
    )
    controller = UnlockController(
        service=_FakeService(MissingVault(), []),
        create_service=create_service,
    )

    controller.createVault("correct horse battery staple", "correct horse battery staple", False)

    assert create_service.calls == [("correct horse battery staple", False)]
    assert controller.currentRoute == "unlocked"


def test_unlock_controller_create_recovery_routes_to_codes_then_unlocked():
    _app()
    create_service = _FakeCreateService(
        CreateVaultSuccess(
            header=None,
            vmk=b"vmk",
            data={"entries": []},
            fingerprint="fp",
            recovery_codes="ABCD-EFGH-JKMP-QRST-UVWX-2345-6789-ABCD-EFGH-JKMP",
            recovery_enabled=True,
        )
    )
    controller = UnlockController(
        service=_FakeService(MissingVault(), []),
        create_service=create_service,
    )

    controller.createVault("correct horse battery staple", "correct horse battery staple", True)

    assert controller.currentRoute == "recoveryCodes"
    assert controller.recoveryCodes.startswith("ABCD")

    controller.acknowledgeRecoveryCodes()

    assert controller.currentRoute == "unlocked"
    assert controller.recoveryCodes == ""
