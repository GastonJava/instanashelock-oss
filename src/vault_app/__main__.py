"""
Entry point:  python -m vault_app

Flat loop that handles the unlock -> vault -> lock cycle without recursion.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from vault_app.errors import VaultStorageError
from vault_app.ui.unlock_window import UnlockWindow
from vault_app.ui.vault_window import VaultApp


def _show_startup_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror(
            "No se pudo preparar el almacenamiento",
            message,
            parent=root,
        )
    finally:
        root.destroy()


def main() -> None:
    relocked = False
    while True:
        try:
            unlock = UnlockWindow(relocked=relocked)
        except VaultStorageError as exc:
            _show_startup_error(str(exc))
            break

        if unlock.vault_data is None:
            break

        app = VaultApp(
            unlock.vault_data,
            unlock.master_key,
            unlock.vault_header,
            unlock.vault_fingerprint,
        )

        if app.reset_to_create_requested:
            relocked = False
            continue

        if not app.relock_requested:
            break

        relocked = True


if __name__ == "__main__":
    main()
