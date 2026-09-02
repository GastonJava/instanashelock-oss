"""
Unlock / first-run window.

State machine:
  A  App init         → B (no vault) or C (vault exists) or G (corrupt)
  B  Create vault     → D
  C  Unlock vault     → D, E (strict lockout), F (recovery available), G (corrupt)
  D  Vault unlocked   (exits this window)
  E  Strict lockout   → B (after reset)
  F  Recovery avail   → D (success), H (exhausted)
  G  Corrupt vault    → C (after backup restore) or B (after reset)
  H  Recovery exhaust → B (after reset)
"""

from __future__ import annotations

import os
import secrets
import tkinter as tk
from tkinter import filedialog, messagebox

from cryptography.exceptions import InvalidTag

from vault_app.constants import (
    APP_NAME,
    PORTABLE_BACKUP_EXTENSION,
    APP_TITLE,
    SALT_SIZE,
    KDF_ARGON2ID,
    VAULT_VERSION,
)
from vault_app.crypto import derive_key, generate_vmk, wrap_vmk
from vault_app.errors import VaultStorageError
from vault_app.header import default_v3_header, VaultHeader
from vault_app.app_lifecycle import find_local_uninstaller, launch_local_uninstaller
from vault_app.storage import (
    vault_path,
    import_portable_backup,
    portable_backup_suggested_name,
    save_vault,
    load_vault,
    decrypt_with_recovery,
    rewrap_vmk_for_new_password,
    setup_recovery,
    backup_exists,
    restore_from_backup,
    delete_vault_files,
)
from vault_app.security import RateLimiter
from vault_app.services.unlock_service import (
    CorruptVault,
    MissingVault,
    UnlockService,
    UnlockSuccess,
    UnlockWrongPassword,
)
from vault_app.ui.theme import C, FONT_TITLE, FONT_SMALL, FONT_MONO, FONT_BUTTON


class UnlockWindow:
    """Modal window that blocks until the user unlocks or creates a vault."""

    RECOVERY_THRESHOLD = 3

    def __init__(self, relocked: bool = False) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])
        self.root.eval("tk::PlaceWindow . center")

        self.vault_data: dict | None = None
        self.master_key: bytes | None = None
        self.vault_salt: bytes | None = None
        self.vault_header: VaultHeader | None = None
        self.vault_fingerprint: str | None = None

        self.is_new = not os.path.exists(vault_path())
        self.relocked = relocked

        self._limiter = RateLimiter()
        self._unlock_service = UnlockService(
            limiter=self._limiter,
            recovery_threshold=self.RECOVERY_THRESHOLD,
        )
        self._recovery_limiter = RateLimiter()
        self._cooldown_id: str | None = None
        self._cooldown_total: float = 0.0
        self._vault_has_recovery: bool = False
        self._lockout_shown: bool = False
        self._recovery_exhausted_shown: bool = False
        self._active_recovery_dialog = None

        height = 560 if self.is_new else 420
        self.root.geometry(f"420x{height}")

        self._build_ui()
        self.root.mainloop()

    # ── UI (State B / C) ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = {"padx": 44, "pady": 0}

        tk.Label(self.root, text="\U0001f510", font=("Segoe UI Emoji", 36),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(18, 4))

        if self.relocked:
            title, subtitle = f"{APP_NAME} bloqueado", "Ingresa tu master password para continuar"
        elif self.is_new:
            title, subtitle = "Crear vault", "Elegi una passphrase larga y memorable"
        else:
            title, subtitle = "Desbloquear", "Ingresa tu master password"

        tk.Label(self.root, text=title, font=FONT_TITLE,
                 bg=C["bg"], fg=C["text"]).pack()
        tk.Label(self.root, text=subtitle, font=FONT_SMALL,
                 bg=C["bg"], fg=C["muted"]).pack(pady=(2, 10))

        frame = tk.Frame(self.root, bg=C["surface"], bd=0,
                         highlightthickness=1, highlightbackground=C["border"])
        frame.pack(fill="x", **pad)
        self.pw_var = tk.StringVar()
        self.pw_entry = tk.Entry(frame, textvariable=self.pw_var, show="\u2022",
                                 font=FONT_MONO, bg=C["entry_bg"], fg=C["text"],
                                 insertbackground=C["accent"], relief="flat", bd=8)
        self.pw_entry.pack(fill="x")
        self.pw_entry.focus()
        self.pw_entry.bind("<Return>", lambda _: self._submit())

        if self.is_new:
            frame2 = tk.Frame(self.root, bg=C["surface"], bd=0,
                              highlightthickness=1, highlightbackground=C["border"])
            frame2.pack(fill="x", padx=44, pady=(8, 0))
            self.pw2_var = tk.StringVar()
            tk.Entry(frame2, textvariable=self.pw2_var, show="\u2022",
                     font=FONT_MONO, bg=C["entry_bg"], fg=C["text"],
                     insertbackground=C["accent"], relief="flat", bd=8).pack(fill="x")

            tk.Label(
                self.root,
                text="\U0001f4a1 Tip: usa una passphrase, ej. \u00abgato-violeta-lluvia-88\u00bb",
                font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
                wraplength=320,
            ).pack(pady=(6, 0))

            self._passphrase_link = tk.Label(
                self.root,
                text="\u00bfQue es una passphrase?",
                font=("Segoe UI", 8, "underline"), bg=C["bg"], fg=C["accent2"],
                cursor="hand2",
            )
            self._passphrase_link.pack(pady=(2, 0))
            self._passphrase_link.bind("<Button-1>", lambda _: self._toggle_passphrase_help())

            self._passphrase_help = tk.Label(
                self.root,
                text="Una passphrase es una frase de palabras al azar separadas\n"
                     "por guiones. Es mas facil de recordar y mas segura que\n"
                     "una password corta con simbolos.\n"
                     "Ejemplo: gato-violeta-lluvia-88 (4+ palabras)",
                font=("Segoe UI", 8), bg=C["surface"], fg=C["text"],
                justify="left", padx=10, pady=6, wraplength=300,
            )
            self._passphrase_help_visible = False

            mode_frame = tk.Frame(self.root, bg=C["bg"])
            mode_frame.pack(fill="x", padx=44, pady=(10, 0))

            tk.Label(mode_frame, text="Proteccion del vault",
                     font=("Segoe UI", 10, "bold"),
                     bg=C["bg"], fg=C["text"]).pack(anchor="w")

            self._recovery_mode = tk.BooleanVar(value=True)

            tk.Radiobutton(
                mode_frame, text="Modo estricto \u2014 sin recuperacion",
                variable=self._recovery_mode, value=False,
                bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                selectcolor=C["surface"], font=FONT_SMALL,
                command=self._update_mode_hint,
            ).pack(anchor="w")

            tk.Radiobutton(
                mode_frame, text="Modo recuperacion \u2014 con codigos de emergencia",
                variable=self._recovery_mode, value=True,
                bg=C["bg"], fg=C["text"], activebackground=C["bg"],
                selectcolor=C["surface"], font=FONT_SMALL,
                command=self._update_mode_hint,
            ).pack(anchor="w")

            self._mode_hint_var = tk.StringVar()
            self._mode_hint_label = tk.Label(
                mode_frame, textvariable=self._mode_hint_var,
                font=("Segoe UI", 8), bg=C["bg"], wraplength=300, justify="left",
            )
            self._mode_hint_label.pack(anchor="w", pady=(2, 0))
            self._update_mode_hint()

        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var, font=FONT_SMALL,
                 bg=C["bg"], fg=C["danger"]).pack(pady=(6, 0))

        self._attempt_var = tk.StringVar()
        self._attempt_label = tk.Label(
            self.root, textvariable=self._attempt_var,
            font=("Segoe UI", 8), bg=C["bg"], fg=C["muted"],
        )

        btn_text = "Crear vault" if self.is_new else "Entrar"
        self.submit_btn = tk.Button(
            self.root, text=btn_text, font=FONT_BUTTON,
            bg=C["accent"], fg="white", relief="flat",
            activebackground=C["accent2"], activeforeground="white",
            cursor="hand2", bd=0, pady=8, command=self._submit,
        )
        self.submit_btn.pack(fill="x", padx=44, pady=10)

        self._portable_backup_link = tk.Label(
            self.root,
            text="Restaurar respaldo cifrado",
            font=("Segoe UI", 8, "underline"), bg=C["bg"], fg=C["accent2"],
            cursor="hand2",
        )
        self._portable_backup_link.pack()
        self._portable_backup_link.bind("<Button-1>", lambda _: self._restore_portable_backup())

        self._cooldown_canvas = tk.Canvas(
            self.root, height=4, bg=C["border"],
            highlightthickness=0, bd=0,
        )
        self._cooldown_rect = None

        # Lockout / recovery area — populated dynamically after failures
        self._recovery_frame = tk.Frame(self.root, bg=C["bg"])
        self._recovery_frame.pack(fill="x", padx=44)

        self._recovery_link = tk.Label(
            self._recovery_frame,
            text="Olvidaste tu password? Usa tus codigos de recuperacion",
            font=("Segoe UI", 9, "underline"), bg=C["bg"], fg=C["accent2"],
            cursor="hand2",
        )
        self._recovery_link.bind("<Button-1>", lambda _: self._start_recovery())

        self._no_recovery_label = tk.Label(
            self._recovery_frame,
            text="Este vault no tiene codigos de recuperacion.",
            font=("Segoe UI", 9), bg=C["bg"], fg=C["muted"],
        )

        self._recovery_exhausted_label = tk.Label(
            self._recovery_frame,
            text="No puedo recuperar este vault.",
            font=("Segoe UI", 9), bg=C["bg"], fg=C["muted"],
        )

        self._reset_link = tk.Label(
            self._recovery_frame,
            text="Eliminar vault local y crear uno nuevo",
            font=("Segoe UI", 9, "underline"), bg=C["bg"], fg=C["danger"],
            cursor="hand2",
        )
        self._reset_link.bind("<Button-1>", lambda _: self._reset_vault())

        if not self.is_new:
            self._advanced_link = tk.Label(
                self.root,
                text="Opciones avanzadas",
                font=("Segoe UI", 8, "underline"), bg=C["bg"], fg=C["accent2"],
                cursor="hand2",
            )
            self._advanced_link.pack(pady=(10, 0))
            self._advanced_link.bind("<Button-1>", lambda _: self._open_advanced_actions())

    def _toggle_passphrase_help(self) -> None:
        if self._passphrase_help_visible:
            self._passphrase_help.pack_forget()
            self._passphrase_link.config(text="\u00bfQue es una passphrase?")
        else:
            self._passphrase_help.pack(after=self._passphrase_link, padx=44, pady=(2, 0))
            self._passphrase_link.config(text="Ocultar ayuda")
        self._passphrase_help_visible = not self._passphrase_help_visible

    def _update_mode_hint(self) -> None:
        if self._recovery_mode.get():
            self._mode_hint_var.set(
                "Se generan 10 codigos de emergencia. Guardalos en papel fuera del dispositivo."
            )
            self._mode_hint_label.config(fg=C["green"])
        else:
            self._mode_hint_var.set(
                "Si olvidas tu password, no hay recuperacion posible. Elegilo si confias en tu memoria."
            )
            self._mode_hint_label.config(fg=C["warn"])

    # ── State E / F transitions ────────────────────────────────────────

    def _show_lockout_links(self) -> None:
        """Show the appropriate links after RECOVERY_THRESHOLD password failures."""
        if self._lockout_shown:
            return
        self._lockout_shown = True

        if self._vault_has_recovery:
            self._recovery_link.pack(pady=(4, 0))
        else:
            self._no_recovery_label.pack(pady=(4, 0))
            self._reset_link.pack(pady=(4, 0))

    def _show_recovery_exhausted(self) -> None:
        """State H: recovery attempts exhausted, show reset option.

        Closes any open recovery input dialog and removes the recovery link.
        """
        if self._recovery_exhausted_shown:
            return
        self._recovery_exhausted_shown = True
        self._recovery_link.pack_forget()
        self._recovery_exhausted_label.pack(pady=(8, 0))
        self._reset_link.pack(pady=(4, 0))

    # ── State G: Corrupt vault ─────────────────────────────────────────

    def _show_corrupt_vault(self, error_msg: str) -> None:
        """Replace the UI with the corrupt-vault error screen."""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.geometry("420x380")

        tk.Label(self.root, text="\u26a0\ufe0f", font=("Segoe UI Emoji", 36),
                 bg=C["bg"], fg=C["danger"]).pack(pady=(24, 4))

        tk.Label(self.root, text="El vault local parece dañado",
                 font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack()

        tk.Label(self.root,
                 text="No pude validar el archivo en disco.\n"
                      "Puede estar incompleto, dañado o no ser compatible\n"
                      f"con esta version de {APP_NAME}.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
                 justify="center").pack(pady=(4, 6))

        tk.Label(self.root,
                 text=f"Detalle: {error_msg}",
                 font=("Segoe UI", 8), bg=C["bg"], fg=C["muted"],
                 wraplength=340).pack(pady=(0, 20))

        if backup_exists():
            tk.Button(
                self.root, text="Intentar abrir backup local",
                font=FONT_BUTTON, bg=C["accent"], fg="white",
                relief="flat", activebackground=C["accent2"],
                cursor="hand2", bd=0, pady=8,
                command=self._try_restore_backup,
            ).pack(fill="x", padx=44, pady=(0, 8))

        tk.Button(
            self.root, text="Restaurar respaldo cifrado",
            font=FONT_BUTTON, bg=C["surface"], fg=C["accent2"],
            relief="flat", activebackground=C["surface"],
            activeforeground=C["accent2"], cursor="hand2", bd=0, pady=8,
            command=self._restore_portable_backup,
        ).pack(fill="x", padx=44, pady=(0, 8))

        tk.Button(
            self.root, text="Eliminar vault y crear uno nuevo",
            font=FONT_BUTTON, bg=C["danger"], fg="white",
            relief="flat", activebackground="#e74c3c",
            cursor="hand2", bd=0, pady=8,
            command=self._reset_vault,
        ).pack(fill="x", padx=44)

    def _try_restore_backup(self) -> None:
        try:
            restored = restore_from_backup()
        except VaultStorageError as exc:
            messagebox.showerror(
                "Error",
                str(exc),
                parent=self.root,
            )
            return

        if not restored:
            messagebox.showerror(
                "Error", "No se pudo restaurar el backup.",
                parent=self.root,
            )
            return

        try:
            load_vault(vault_path())
        except (ValueError, OSError) as exc:
            messagebox.showerror(
                "Backup invalido",
                f"El backup tampoco es valido:\n{exc}",
                parent=self.root,
            )
            return

        self._rebuild_as_unlock("Backup restaurado. Ingresa tu password.")

    def _show_password_mismatch(self) -> None:
        self.status_var.set("Esa master password no abre este vault.")

    # ── Actions ─────────────────────────────────────────────────────────

    def _open_advanced_actions(self) -> None:
        from vault_app.ui.dialogs import AdvancedVaultActionsDialog

        if self.is_new:
            return

        dialog = AdvancedVaultActionsDialog(
            self.root,
            uninstall_available=find_local_uninstaller() is not None,
        )
        action = dialog.wait()
        if action == "destroy":
            self._reset_vault()
        elif action == "uninstall":
            self._start_uninstall_flow()

    def _restore_portable_backup(self) -> None:
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Restaurar respaldo cifrado",
            initialfile=portable_backup_suggested_name(),
            filetypes=[
                ("Respaldo cifrado Instanashelock", f"*{PORTABLE_BACKUP_EXTENSION}"),
                ("Vault cifrado", "*.vault"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not source:
            return

        current_vault_exists = os.path.exists(vault_path())
        if current_vault_exists:
            should_continue = messagebox.askyesno(
                "Restaurar respaldo cifrado",
                "Esto reemplazara el vault local actual por el respaldo seleccionado.\n\n"
                "El vault actual quedara como backup local .bak si la restauracion "
                "se completa.\n\n"
                "El archivo de respaldo original NO se elimina automaticamente.\n\n"
                "Continuar?",
                icon="warning",
                parent=self.root,
            )
            if not should_continue:
                return

        try:
            import_portable_backup(source)
        except ValueError as exc:
            messagebox.showerror(
                "Respaldo invalido",
                str(exc),
                parent=self.root,
            )
            return
        except VaultStorageError as exc:
            messagebox.showerror(
                "No se pudo restaurar el respaldo",
                str(exc),
                parent=self.root,
            )
            return

        messagebox.showinfo(
            "Respaldo restaurado",
            "El vault local fue reemplazado por el respaldo seleccionado.\n\n"
            "El archivo de respaldo original sigue intacto. Conserva esa copia "
            "como resguardo o borralo manualmente si era temporal.",
            parent=self.root,
        )
        self._rebuild_as_unlock("Respaldo cifrado restaurado. Ingresa tu password.")

    def _start_uninstall_flow(self) -> None:
        uninstaller = find_local_uninstaller()
        if uninstaller is None:
            messagebox.showinfo(
                "Desinstalacion manual",
                "Esta copia no expone un desinstalador local.\n\n"
                "Si la instalaste, usa Configuracion > Aplicaciones de Windows.\n"
                "Si es portable, elimina la carpeta de la app.\n\n"
                "Desinstalar la app NO elimina tu vault ni tus datos cifrados.",
                parent=self.root,
            )
            return

        should_continue = messagebox.askyesno(
            "Abrir desinstalador",
            f"Se abrira el desinstalador de {APP_NAME}.\n\n"
            "Desinstalar la app NO elimina tu vault ni tus datos cifrados.\n\n"
            "Si continuas, esta ventana se cerrara.\n\n"
            "Continuar?",
            icon="warning",
            parent=self.root,
        )
        if not should_continue:
            return

        try:
            launch_local_uninstaller(uninstaller)
        except OSError:
            messagebox.showerror(
                "No se pudo abrir el desinstalador",
                "No se pudo abrir el desinstalador local en esta copia.",
                parent=self.root,
            )
            return

        self.root.destroy()

    def _submit(self) -> None:
        if self._limiter.is_locked:
            return

        pw = self.pw_var.get()
        if not pw:
            self.status_var.set("Ingresa una password.")
            return

        if self.is_new:
            self._create_vault(pw)
        else:
            self._try_unlock(pw)

    def _create_vault(self, pw: str) -> None:
        pw2 = self.pw2_var.get()
        if pw != pw2:
            self.status_var.set("Las passwords no coinciden.")
            return
        if len(pw) < 12:
            self.status_var.set("Minimo 12 caracteres (o usa una passphrase).")
            return

        salt_pw = secrets.token_bytes(SALT_SIZE)
        pw_key = derive_key(pw, salt_pw, kdf_id=KDF_ARGON2ID)
        vmk = generate_vmk()
        enc_vmk_pw = wrap_vmk(vmk, pw_key)

        header = default_v3_header(salt_pw=salt_pw, enc_vmk_pw=enc_vmk_pw)
        data: dict = {"entries": []}
        try:
            fingerprint = save_vault(vault_path(), header, data, vmk)
        except VaultStorageError as exc:
            messagebox.showerror(
                "No se pudo crear el vault",
                str(exc),
                parent=self.root,
            )
            return

        if self._recovery_mode.get():
            try:
                header, display_codes, fingerprint = setup_recovery(
                    vault_path(),
                    header,
                    data,
                    vmk,
                    expected_fingerprint=fingerprint,
                )
            except VaultStorageError as exc:
                messagebox.showwarning(
                    "Vault creado sin recovery",
                    "El vault se creo, pero no se pudieron guardar los codigos "
                    f"de recovery.\n\n{exc}",
                    parent=self.root,
                )
            else:
                from vault_app.ui.dialogs import RecoveryCodesDialog

                dialog = RecoveryCodesDialog(self.root, display_codes)
                dialog.wait()
        else:
            messagebox.showwarning(
                "Modo estricto",
                "Este vault NO tiene codigos de recuperacion.\n\n"
                "Si olvidas tu master password, el vault sera irrecuperable.\n\n"
                "Podes activar recovery mas adelante desde el menu del vault.",
                parent=self.root,
            )

        self.master_key = vmk
        self.vault_salt = salt_pw
        self.vault_header = header
        self.vault_data = data
        self.vault_fingerprint = fingerprint
        self.root.destroy()

    def _try_unlock(self, pw: str) -> None:
        result = self._unlock_service.unlock(pw)

        if isinstance(result, MissingVault):
            self.status_var.set("No existe un vault local para desbloquear.")
            return

        if isinstance(result, CorruptVault):
            self._show_corrupt_vault(result.detail)
            return

        if isinstance(result, UnlockWrongPassword):
            self._vault_has_recovery = result.has_recovery
            self._start_cooldown(result.cooldown_seconds)
            self._show_password_mismatch()
            self._update_attempt_counter(self._limiter)
            if self._limiter.failures >= self.RECOVERY_THRESHOLD:
                self._show_lockout_links()
            return

        if isinstance(result, UnlockSuccess):
            self._vault_has_recovery = result.header.has_recovery
            self.master_key = result.vmk
            self.vault_salt = result.header.salt
            self.vault_header = result.header
            self.vault_data = result.data
            self.vault_fingerprint = result.fingerprint
            self.root.destroy()
            return

        self.status_var.set("No se pudo desbloquear este vault.")

    # ── Recovery flow (State F → D or H) ───────────────────────────────

    def _start_recovery(self) -> None:
        if self._recovery_exhausted_shown:
            return

        if self._recovery_limiter.is_locked:
            remaining = int(self._recovery_limiter.seconds_remaining) + 1
            self.status_var.set(f"Recovery bloqueado. Reintenta en {remaining}s")
            return

        from vault_app.ui.dialogs import RecoveryInputDialog, NewPasswordDialog
        from vault_app.recovery import parse_recovery_input

        input_dialog = RecoveryInputDialog(self.root)
        self._active_recovery_dialog = input_dialog
        raw_input = input_dialog.wait()
        self._active_recovery_dialog = None
        if raw_input is None:
            return

        try:
            raw_secret = parse_recovery_input(raw_input)
        except ValueError as exc:
            self.status_var.set(f"Codigo invalido: {exc}")
            return

        try:
            header, enc_blob, fingerprint = load_vault(vault_path())
        except (OSError, ValueError) as exc:
            self.status_var.set(str(exc))
            return

        try:
            header, vmk, data = decrypt_with_recovery(
                vault_path(), header, enc_blob, raw_secret,
            )
        except InvalidTag:
            delay = self._recovery_limiter.record_failure()
            self.status_var.set(
                f"Codigos incorrectos. Reintenta en {int(delay)}s"
            )
            self._update_attempt_counter(self._recovery_limiter, recovery=True)
            if self._recovery_limiter.failures >= self.RECOVERY_THRESHOLD:
                self._show_recovery_exhausted()
            return
        except ValueError as exc:
            self._show_corrupt_vault(str(exc))
            return

        self._recovery_limiter.record_success()

        pw_dialog = NewPasswordDialog(self.root)
        new_pw = pw_dialog.wait()
        if new_pw is None:
            return

        # Invalidate old recovery codes by generating new ones
        from vault_app.ui.dialogs import RecoveryCodesDialog
        try:
            header, fingerprint = rewrap_vmk_for_new_password(
                vault_path(),
                header,
                data,
                vmk,
                new_pw,
                expected_fingerprint=fingerprint,
            )
            header, display_codes, fingerprint = setup_recovery(
                vault_path(),
                header,
                data,
                vmk,
                expected_fingerprint=fingerprint,
            )
        except VaultStorageError as exc:
            messagebox.showerror(
                "No se pudo guardar el cambio de password",
                str(exc),
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Recovery codes invalidados",
            "Tus codigos de recuperacion anteriores ya no funcionan.\n\n"
            "Se generaron nuevos codigos. Guardalos en un lugar seguro.",
            parent=self.root,
        )
        codes_dialog = RecoveryCodesDialog(self.root, display_codes)
        codes_dialog.wait()

        self._limiter.record_success()
        self.master_key = vmk
        self.vault_salt = header.salt
        self.vault_header = header
        self.vault_data = data
        self.vault_fingerprint = fingerprint
        self.root.destroy()

    # ── Reset vault (destructive, States E/G/H → B) ───────────────────

    def _reset_vault(self) -> None:
        first = messagebox.askyesno(
            "Destruir vault y datos",
            "Esto eliminara permanentemente tu vault local y\n"
            "todas las passwords guardadas.\n\n"
            "Se eliminara:\n"
            "\u2022 El vault principal\n"
            "\u2022 El backup local\n\n"
            "\u2022 El lock local\n\n"
            "Esta accion NO se puede deshacer.\n\n"
            "Continuar?",
            icon="warning",
            parent=self.root,
        )
        if not first:
            return

        from vault_app.ui.dialogs import ConfirmDeleteDialog
        confirm_dialog = ConfirmDeleteDialog(self.root)
        if not confirm_dialog.wait():
            return

        delete_vault_files()
        self._rebuild_as_create("Vault local destruido. Crea uno nuevo.")

    # ── UI rebuild helpers ─────────────────────────────────────────────

    def _clear_ui(self) -> None:
        for widget in self.root.winfo_children():
            widget.destroy()

    def _reset_state(self) -> None:
        self._limiter = RateLimiter()
        self._unlock_service = UnlockService(
            limiter=self._limiter,
            recovery_threshold=self.RECOVERY_THRESHOLD,
        )
        self._recovery_limiter = RateLimiter()
        self._cooldown_total = 0.0
        self._vault_has_recovery = False
        self._lockout_shown = False
        self._recovery_exhausted_shown = False
        self._active_recovery_dialog = None

    def _rebuild_as_create(self, status_msg: str) -> None:
        self._clear_ui()
        self._reset_state()
        self.is_new = True
        self.relocked = False
        self.root.geometry("420x560")
        self._build_ui()
        self.status_var.set(status_msg)

    def _rebuild_as_unlock(self, status_msg: str) -> None:
        self._clear_ui()
        self._reset_state()
        self.is_new = False
        self.relocked = False
        self.root.geometry("420x420")
        self._build_ui()
        self.status_var.set(status_msg)

    # ── Attempt counter ──────────────────────────────────────────────

    def _update_attempt_counter(self, limiter: RateLimiter, *, recovery: bool = False) -> None:
        n = limiter.failures
        t = self.RECOVERY_THRESHOLD
        if n >= t:
            self._attempt_label.pack_forget()
            return

        prefix = "Recovery: " if recovery else ""
        if n == t - 1:
            self._attempt_var.set(f"{prefix}Ultimo intento antes de bloqueo")
            self._attempt_label.config(fg=C["warn"])
        else:
            self._attempt_var.set(f"{prefix}Intento {n} de {t}")
            self._attempt_label.config(fg=C["muted"])
        self._attempt_label.pack(after=self.submit_btn, pady=(0, 2))

    # ── Rate-limit cooldown ────────────────────────────────────────────

    def _start_cooldown(self, seconds: float) -> None:
        self._cooldown_total = seconds
        self.submit_btn.config(state="disabled")
        self.pw_entry.config(state="disabled")

        bar_width = 332
        self._cooldown_canvas.config(width=bar_width)
        self._cooldown_canvas.pack(fill="x", padx=44, pady=(0, 4))
        self._cooldown_rect = self._cooldown_canvas.create_rectangle(
            0, 0, bar_width, 4, fill=C["accent"], outline="",
        )
        self._tick_cooldown()

    def _tick_cooldown(self) -> None:
        remaining = self._limiter.seconds_remaining
        if remaining <= 0:
            self.submit_btn.config(state="normal")
            self.pw_entry.config(state="normal")
            self._cooldown_canvas.pack_forget()
            if self._cooldown_rect is not None:
                self._cooldown_canvas.delete(self._cooldown_rect)
                self._cooldown_rect = None
            self.status_var.set("")
            return

        bar_width = 332
        ratio = remaining / self._cooldown_total if self._cooldown_total > 0 else 0
        fill_w = max(1, int(bar_width * ratio))
        if self._cooldown_rect is not None:
            self._cooldown_canvas.coords(self._cooldown_rect, 0, 0, fill_w, 4)

        secs = int(remaining) + 1
        self.status_var.set(f"Bloqueado {secs}s")
        self._cooldown_id = self.root.after(200, self._tick_cooldown)
