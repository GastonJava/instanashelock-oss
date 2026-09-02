from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.services.unlock_service import CorruptVault, UnlockSuccess, UnlockWrongPassword
from vault_app.ui.unlock_window import UnlockWindow


class _FakeStringVar:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class _FakeLimiter:
    def __init__(self) -> None:
        self.failures = 0
        self.is_locked = False
        self.seconds_remaining = 0.0

    def record_failure(self) -> float:
        self.failures += 1
        return 2.0

    def record_success(self) -> None:
        self.failures = 0


class _FakeHeader:
    def __init__(self, *, has_recovery: bool = False, salt: bytes = b"salt") -> None:
        self.has_recovery = has_recovery
        self.salt = salt


class _FakeUnlockService:
    def __init__(self, result) -> None:
        self._result = result

    def unlock(self, _password: str):
        return self._result


def _build_unlock_stub() -> UnlockWindow:
    unlock = UnlockWindow.__new__(UnlockWindow)
    unlock.RECOVERY_THRESHOLD = 3
    unlock.status_var = _FakeStringVar()
    unlock._limiter = _FakeLimiter()
    unlock._recovery_limiter = _FakeLimiter()
    unlock._vault_has_recovery = False
    unlock._lockout_shown = False
    unlock._recovery_exhausted_shown = False
    unlock.master_key = None
    unlock.vault_salt = None
    unlock.vault_header = None
    unlock.vault_data = None
    unlock.vault_fingerprint = None
    unlock._start_cooldown = lambda _seconds: None
    unlock._update_attempt_counter = lambda *args, **kwargs: None
    unlock._show_lockout_links = lambda: None
    unlock._show_recovery_exhausted = lambda: None
    unlock._show_corrupt_vault = lambda message: setattr(unlock, "_corrupt_message", message)
    unlock._corrupt_message = None
    return unlock


def test_try_unlock_wrong_password_result_shows_wrong_password_message():
    unlock = _build_unlock_stub()
    unlock._unlock_service = _FakeUnlockService(
        UnlockWrongPassword(
            cooldown_seconds=2.0,
            failures=1,
            has_recovery=False,
            recovery_available=False,
            reset_recommended=False,
        )
    )

    unlock._try_unlock("wrong-pass")

    assert unlock.status_var.get() == "Esa master password no abre este vault."
    assert unlock._corrupt_message is None


def test_try_unlock_corrupt_result_routes_to_corrupt_vault():
    unlock = _build_unlock_stub()
    unlock._unlock_service = _FakeUnlockService(
        CorruptVault(reason="parse_error", detail="Blob cifrado demasiado corto para ser valido.")
    )

    unlock._try_unlock("any-pass")

    assert unlock._corrupt_message == "Blob cifrado demasiado corto para ser valido."


def test_try_unlock_success_sets_unlocked_state():
    unlock = _build_unlock_stub()
    header = _FakeHeader(has_recovery=True, salt=b"salt")
    root_destroyed = []
    unlock.root = type("Root", (), {"destroy": lambda self: root_destroyed.append(True)})()
    unlock._unlock_service = _FakeUnlockService(
        UnlockSuccess(
            header=header,
            vmk=b"vmk",
            data={"entries": [{"service": "Demo"}]},
            fingerprint="fp",
        )
    )

    unlock._try_unlock("correct")

    assert unlock.master_key == b"vmk"
    assert unlock.vault_header is header
    assert unlock.vault_data == {"entries": [{"service": "Demo"}]}
    assert unlock.vault_fingerprint == "fp"
    assert root_destroyed == [True]


def test_start_recovery_value_error_routes_to_corrupt_vault(monkeypatch):
    from vault_app.ui import unlock_window as mod

    unlock = _build_unlock_stub()
    unlock.root = object()
    unlock._active_recovery_dialog = None

    class _Dialog:
        def __init__(self, _parent):
            pass

        def wait(self):
            return "ABCD-EFGH-IJKM-NPQR-STUV-WXYZ-2345-6789-ABCD-EFGH"

    monkeypatch.setattr(mod, "vault_path", lambda: "dummy.vault")
    monkeypatch.setattr(mod, "load_vault", lambda _path: (_FakeHeader(has_recovery=True), b"blob", "fp"))
    monkeypatch.setattr("vault_app.ui.dialogs.RecoveryInputDialog", _Dialog)

    def fake_parse(_raw_input):
        return b"recovery-secret"

    monkeypatch.setattr("vault_app.recovery.parse_recovery_input", fake_parse)

    def fail_recovery(*_args, **_kwargs):
        raise ValueError("Recovery solo disponible en vaults v3.")

    monkeypatch.setattr(mod, "decrypt_with_recovery", fail_recovery)

    unlock._start_recovery()

    assert unlock._corrupt_message == "Recovery solo disponible en vaults v3."


def test_restore_portable_backup_rebuilds_unlock_state(monkeypatch):
    from vault_app.ui import unlock_window as mod

    unlock = _build_unlock_stub()
    unlock.root = object()
    unlock.is_new = True

    monkeypatch.setattr(mod.filedialog, "askopenfilename", lambda **_kwargs: "portable.instanashelock-backup")
    monkeypatch.setattr(mod, "vault_path", lambda: "managed.vault")
    monkeypatch.setattr(mod.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(mod, "import_portable_backup", lambda _path: "fp")

    shown: list[tuple[str, str]] = []
    monkeypatch.setattr(
        mod.messagebox,
        "showinfo",
        lambda title, message, parent=None: shown.append((title, message)),
    )

    seen: list[str] = []
    unlock._rebuild_as_unlock = lambda message: seen.append(message)

    unlock._restore_portable_backup()

    assert shown == [
        (
            "Respaldo restaurado",
            "El vault local fue reemplazado por el respaldo seleccionado.\n\n"
            "El archivo de respaldo original sigue intacto. Conserva esa copia "
            "como resguardo o borralo manualmente si era temporal.",
        )
    ]
    assert seen == ["Respaldo cifrado restaurado. Ingresa tu password."]
