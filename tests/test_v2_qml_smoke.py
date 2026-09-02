from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication

from vault_app_v2.services.auth_service import CreateVaultSuccess, MissingVault, UnlockSuccess, VaultReady
from vault_app_v2.app import bootstrap_application, build_engine
from vault_app_v2.controllers.unlock_controller import UnlockController


class _FakeLimiter:
    def __init__(self) -> None:
        self.seconds_remaining = 0.0


class _FakeService:
    def __init__(self) -> None:
        self.limiter = _FakeLimiter()

    def probe_vault(self):
        return VaultReady(has_recovery=False, fingerprint="fp")

    def unlock(self, _password: str):
        return UnlockSuccess(header=None, vmk=b"vmk", data={"entries": []}, fingerprint="fp")


class _FakeCreateService:
    def __init__(self) -> None:
        self.calls = []

    def create_vault(self, password: str, *, recovery_enabled: bool):
        self.calls.append((password, recovery_enabled))
        return CreateVaultSuccess(
            header=None,
            vmk=b"vmk",
            data={"entries": []},
            fingerprint="fp",
            recovery_codes="ABCD-EFGH-JKMP-QRST-UVWX-2345-6789-ABCD-EFGH-JKMP",
            recovery_enabled=True,
        )


def _app() -> QGuiApplication:
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


def test_bootstrap_application_keeps_engine_alive(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()

    engine, controller = bootstrap_application(app, UnlockController(service=_FakeService()))

    assert engine.rootObjects()
    assert app._instanashelock_v2_engine is engine
    assert app._instanashelock_v2_controller is controller


def test_v2_qml_unlock_screen_loads_and_wires_controller(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()
    controller = UnlockController(service=_FakeService())
    engine, _ = build_engine(controller)
    root = engine.rootObjects()[0]
    app.processEvents()

    password_field = root.findChild(object, "unlockPasswordField")
    assert password_field is not None
    assert controller.currentRoute == "unlock"

    password_field.setProperty("text", "hello")
    controller.submitPassword("hello")
    app.processEvents()

    assert controller.currentRoute == "unlocked"


def test_v2_qml_forgot_screen_loads(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()
    controller = UnlockController(service=_FakeService())
    engine, _ = build_engine(controller)
    root = engine.rootObjects()[0]
    app.processEvents()

    controller.goToForgotPassword()
    app.processEvents()

    action_button = root.findChild(object, "forgotPrimaryActionButton")
    assert action_button is not None
    assert controller.currentRoute == "forgot"


def test_v2_qml_recovery_unlock_screen_loads(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()
    controller = UnlockController(service=_FakeService())
    engine, _ = build_engine(controller)
    root = engine.rootObjects()[0]
    app.processEvents()

    controller.goToRecoveryUnlock()
    app.processEvents()

    code_input = root.findChild(object, "recoveryUnlockCodeInput")
    action_button = root.findChild(object, "recoveryUnlockActionButton")
    assert code_input is not None
    assert action_button is not None
    assert controller.currentRoute == "recoveryUnlock"


def test_v2_qml_create_screen_loads_for_missing_vault(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()

    class _MissingVaultService:
        def __init__(self) -> None:
            self.limiter = _FakeLimiter()

        def probe_vault(self):
            return MissingVault()

        def unlock(self, _password: str):
            return MissingVault()

    controller = UnlockController(service=_MissingVaultService())
    engine, _ = build_engine(controller)
    root = engine.rootObjects()[0]
    app.processEvents()

    create_password_field = root.findChild(object, "createVaultPasswordField")
    assert create_password_field is not None
    assert controller.currentRoute == "create"


def test_v2_qml_recovery_codes_screen_loads_after_create(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = _app()

    class _MissingVaultService:
        def __init__(self) -> None:
            self.limiter = _FakeLimiter()

        def probe_vault(self):
            return MissingVault()

        def unlock(self, _password: str):
            return MissingVault()

    create_service = _FakeCreateService()
    controller = UnlockController(
        service=_MissingVaultService(),
        create_service=create_service,
    )
    engine, _ = build_engine(controller)
    root = engine.rootObjects()[0]
    app.processEvents()

    controller.createVault("correct horse battery staple", "correct horse battery staple", True)
    app.processEvents()

    acknowledge_button = root.findChild(object, "recoveryCodesAcknowledgeButton")
    assert acknowledge_button is not None
    assert controller.currentRoute == "recoveryCodes"
    assert create_service.calls == [("correct horse battery staple", True)]
