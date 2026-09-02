from __future__ import annotations

import math

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from vault_app_v2.services.auth_service import (
    CorruptVault,
    CreateVaultAlreadyExists,
    CreateVaultService,
    CreateVaultStorageFailure,
    CreateVaultSuccess,
    CreateVaultValidationError,
    LockedOut,
    MissingVault,
    UnlockService,
    UnlockSuccess,
    UnlockWrongPassword,
    VaultReady,
)


class UnlockController(QObject):
    stateChanged = Signal()
    routeChanged = Signal(str)
    unlockSucceeded = Signal()
    shakeRequested = Signal()

    DEFAULT_HELPER = "The vault is locked. Enter your main password."
    MISSING_VAULT_HELPER = (
        "No local vault yet. Create your local vault on this device "
        "before you can use the unlock flow."
    )

    def __init__(
        self,
        service: UnlockService | None = None,
        create_service: CreateVaultService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service or UnlockService()
        self._create_service = create_service or CreateVaultService()
        self._busy = False
        self._error_text = ""
        self._helper_text = self.DEFAULT_HELPER
        self._cooldown_seconds = 0
        self._windows_hello_available = False
        self._current_route = "unlock"
        self._recovery_codes = ""
        self._created_with_recovery = False
        self._header = None
        self._vmk: bytes | None = None
        self._data: dict | None = None
        self._fingerprint: str | None = None
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(200)
        self._cooldown_timer.timeout.connect(self._tick_cooldown)
        self.sync_initial_route()

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=stateChanged)
    def errorText(self) -> str:
        return self._error_text

    @Property(str, notify=stateChanged)
    def helperText(self) -> str:
        return self._helper_text

    @Property(int, notify=stateChanged)
    def cooldownSeconds(self) -> int:
        return self._cooldown_seconds

    @Property(bool, notify=stateChanged)
    def canSubmit(self) -> bool:
        return not self._busy and self._cooldown_seconds == 0

    @Property(bool, notify=stateChanged)
    def windowsHelloAvailable(self) -> bool:
        return self._windows_hello_available

    @Property(str, notify=stateChanged)
    def recoveryCodes(self) -> str:
        return self._recovery_codes

    @Property(bool, notify=stateChanged)
    def createdWithRecovery(self) -> bool:
        return self._created_with_recovery

    @Property(str, notify=routeChanged)
    def currentRoute(self) -> str:
        return self._current_route

    @Property(str, notify=routeChanged)
    def initialRoute(self) -> str:
        return self._current_route

    @Slot()
    def syncInitialRoute(self) -> None:
        self.sync_initial_route()

    def sync_initial_route(self) -> None:
        probe = self._service.probe_vault()
        if isinstance(probe, MissingVault):
            self._set_status("", self.MISSING_VAULT_HELPER)
            self._set_route("create")
            return

        if isinstance(probe, CorruptVault):
            self._set_status("", "This local vault looks invalid or incompatible.")
            self._set_route("corrupt")
            return

        if isinstance(probe, VaultReady):
            self._set_status("", self.DEFAULT_HELPER)
            self._set_route("unlock")
            return

    @Slot(str)
    def submitPassword(self, password: str) -> None:
        if self._busy:
            return

        self._set_status("", self.DEFAULT_HELPER)
        if not password:
            self._set_status("Enter your main password.", self.DEFAULT_HELPER)
            return

        if self._cooldown_seconds > 0:
            return

        self._busy = True
        self.stateChanged.emit()
        try:
            result = self._service.unlock(password)
        finally:
            self._busy = False

        if isinstance(result, UnlockSuccess):
            self._stop_cooldown()
            self._capture_unlocked_state(result.header, result.vmk, result.data, result.fingerprint)
            self._set_status("", "Vault unlocked. The main shell lands in the next slice.")
            self._set_route("unlocked")
            self.unlockSucceeded.emit()
            self.stateChanged.emit()
            return

        if isinstance(result, MissingVault):
            self._stop_cooldown()
            self._set_status(
                "No local vault yet.",
                self.MISSING_VAULT_HELPER,
            )
            self._set_route("create")
            self.stateChanged.emit()
            return

        if isinstance(result, CorruptVault):
            self._stop_cooldown()
            self._set_status("", "This local vault looks invalid or incompatible.")
            self._set_route("corrupt")
            self.stateChanged.emit()
            return

        if isinstance(result, LockedOut):
            self._set_status("", f"Try again in {self._seconds_label(result.cooldown_seconds)}s.")
            self._start_cooldown()
            self.stateChanged.emit()
            return

        if isinstance(result, UnlockWrongPassword):
            self._set_status(
                "That main password does not unlock this vault.",
                f"Try again in {self._seconds_label(result.cooldown_seconds)}s.",
            )
            self._start_cooldown()
            self.shakeRequested.emit()
        self.stateChanged.emit()
        return

    @Slot(str, str, bool)
    def createVault(self, password: str, confirm_password: str, recovery_enabled: bool) -> None:
        if self._busy:
            return

        self._set_status("", self.MISSING_VAULT_HELPER)
        if not password:
            self._set_status("Enter your main password.", self.MISSING_VAULT_HELPER)
            self.shakeRequested.emit()
            return

        if password != confirm_password:
            self._set_status("Passwords do not match.", self.MISSING_VAULT_HELPER)
            self.shakeRequested.emit()
            return

        self._busy = True
        self.stateChanged.emit()
        try:
            result = self._create_service.create_vault(
                password,
                recovery_enabled=recovery_enabled,
            )
        finally:
            self._busy = False

        if isinstance(result, CreateVaultValidationError):
            self._set_status(result.message, self.MISSING_VAULT_HELPER)
            self.shakeRequested.emit()
            self.stateChanged.emit()
            return

        if isinstance(result, CreateVaultAlreadyExists):
            self._set_status(
                "A local vault already exists.",
                "Use the unlock flow for the vault on this device.",
            )
            self._set_route("unlock")
            self.stateChanged.emit()
            return

        if isinstance(result, CreateVaultStorageFailure):
            self._set_status(result.message, self.MISSING_VAULT_HELPER)
            self.stateChanged.emit()
            return

        if isinstance(result, CreateVaultSuccess):
            self._stop_cooldown()
            self._capture_unlocked_state(result.header, result.vmk, result.data, result.fingerprint)
            self._created_with_recovery = result.recovery_enabled
            self._recovery_codes = result.recovery_codes
            if result.recovery_enabled and result.recovery_codes:
                self._set_status("", "Save these recovery codes before continuing.")
                self._set_route("recoveryCodes")
                self.stateChanged.emit()
                return

            message = result.warning or "Vault created. The main shell lands in the next slice."
            self._set_status("", message)
            self._set_route("unlocked")
            self.unlockSucceeded.emit()
            self.stateChanged.emit()
            return

    @Slot()
    def acknowledgeRecoveryCodes(self) -> None:
        self._recovery_codes = ""
        self._set_status("", "Vault created. The main shell lands in the next slice.")
        self._set_route("unlocked")
        self.unlockSucceeded.emit()
        self.stateChanged.emit()

    @Slot()
    def goToForgotPassword(self) -> None:
        self._set_status("", "Use recovery, restore, or reset from this device.")
        self._set_route("forgot")

    @Slot()
    def goToRecoveryUnlock(self) -> None:
        self._set_status("", "Enter one recovery code generated for this local vault.")
        self._set_route("recoveryUnlock")

    @Slot()
    def goToCreateVault(self) -> None:
        self._set_status("", self.MISSING_VAULT_HELPER)
        self._set_route("create")

    @Slot()
    def goToUnlockPreview(self) -> None:
        self._set_status("", self.DEFAULT_HELPER)
        self._set_route("unlock")

    @Slot()
    def goToUnlock(self) -> None:
        self.sync_initial_route()

    def _set_status(self, error_text: str, helper_text: str) -> None:
        self._error_text = error_text
        self._helper_text = helper_text
        self.stateChanged.emit()

    def _set_route(self, route_name: str) -> None:
        if self._current_route == route_name:
            self.routeChanged.emit(route_name)
            return
        self._current_route = route_name
        self.routeChanged.emit(route_name)

    def _capture_unlocked_state(self, header: object, vmk: bytes, data: dict, fingerprint: str) -> None:
        self._header = header
        self._vmk = vmk
        self._data = data
        self._fingerprint = fingerprint

    def _start_cooldown(self) -> None:
        self._tick_cooldown()
        if self._cooldown_seconds > 0 and not self._cooldown_timer.isActive():
            self._cooldown_timer.start()

    def _stop_cooldown(self) -> None:
        if self._cooldown_timer.isActive():
            self._cooldown_timer.stop()
        self._cooldown_seconds = 0

    def _tick_cooldown(self) -> None:
        remaining = self._seconds_label(self._service.limiter.seconds_remaining)
        self._cooldown_seconds = remaining
        if remaining <= 0:
            if self._cooldown_timer.isActive():
                self._cooldown_timer.stop()
            if not self._error_text:
                self._helper_text = self.DEFAULT_HELPER
        self.stateChanged.emit()

    @staticmethod
    def _seconds_label(seconds: float) -> int:
        if seconds <= 0:
            return 0
        return max(1, math.ceil(seconds))
