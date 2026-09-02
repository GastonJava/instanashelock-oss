from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMessageBox

from vault_app.errors import VaultStorageError
from vault_app_v2.controllers.unlock_controller import UnlockController


QML_ROOT = Path(__file__).resolve().parent / "qml"
APP_QML = QML_ROOT / "App.qml"


def configure_qtquick_style() -> None:
    """Force a customizable Qt Quick Controls style for the v2 prototype."""
    QQuickStyle.setStyle("Basic")


def build_engine(controller: UnlockController | None = None) -> tuple[QQmlApplicationEngine, UnlockController]:
    engine = QQmlApplicationEngine()
    unlock_controller = controller or UnlockController()
    engine.rootContext().setContextProperty("unlockController", unlock_controller)
    engine.addImportPath(str(QML_ROOT))
    engine.load(str(APP_QML))
    if not engine.rootObjects():
        raise RuntimeError(f"Failed to load QML app from {APP_QML}")
    return engine, unlock_controller


def _show_startup_error(message: str) -> None:
    QMessageBox.critical(
        None,
        "Instanashelock 2.0",
        f"Could not prepare local storage.\n\n{message}",
    )


def bootstrap_application(
    app: QApplication,
    controller: UnlockController | None = None,
) -> tuple[QQmlApplicationEngine, UnlockController]:
    """Create and retain the QML engine for the lifetime of the app."""
    engine, unlock_controller = build_engine(controller)

    # Keep strong Python references so the QML engine/window is not garbage-
    # collected immediately after startup. Without this, the window can flash
    # and disappear as soon as main() returns from build_engine().
    app._instanashelock_v2_engine = engine
    app._instanashelock_v2_controller = unlock_controller
    return engine, unlock_controller


def main(argv: list[str] | None = None) -> int:
    configure_qtquick_style()
    app = QApplication(argv or sys.argv)
    app.setApplicationDisplayName("Instanashelock 2.0")
    try:
        bootstrap_application(app)
    except VaultStorageError as exc:
        _show_startup_error(str(exc))
        return 1
    return app.exec()
