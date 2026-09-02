"""
Dialogs: add/edit entry, show password, password generator.
"""

from __future__ import annotations

import math
import secrets
import string
import tkinter as tk
from tkinter import messagebox

from vault_app.security import ManagedClipboard
from vault_app.constants import APP_NAME
from vault_app.ui.theme import C, FONT_BODY, FONT_MONO, FONT_SMALL, FONT_BUTTON
from vault_app.ui.strength_bar import StrengthBar
from vault_app.wordlist import WORDLIST


# ── Add / Edit entry ────────────────────────────────────────────────────────


class AddEntryDialog:
    """Dialog for creating or editing a vault entry.

    *mode* is ``"add"`` or ``"edit"``.  When editing, *initial* supplies the
    current values.
    """

    def __init__(
        self,
        parent: tk.Tk,
        callback,
        *,
        mode: str = "add",
        initial: dict | None = None,
    ) -> None:
        self.callback = callback
        self.mode = mode

        self.win = tk.Toplevel(parent)
        self.win.title("Nueva entrada" if mode == "add" else "Editar entrada")
        self.win.geometry("420x460")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self._initial = initial or {}
        self._build()

    def _field(self, label_text: str, show: str | None = None, initial: str = "") -> tuple[tk.StringVar, tk.Entry]:
        tk.Label(self.win, text=label_text, font=FONT_SMALL,
                 bg=C["bg"], fg=C["muted"], anchor="w").pack(fill="x", padx=28)
        frame = tk.Frame(self.win, bg=C["surface"],
                         highlightthickness=1, highlightbackground=C["border"])
        frame.pack(fill="x", padx=28, pady=(2, 8))
        var = tk.StringVar(value=initial)
        entry = tk.Entry(frame, textvariable=var, show=show,
                         font=FONT_MONO if show else FONT_BODY,
                         bg=C["entry_bg"], fg=C["text"],
                         insertbackground=C["accent"], relief="flat", bd=7)
        entry.pack(fill="x")
        return var, entry

    def _build(self) -> None:
        title = "Nueva entrada" if self.mode == "add" else "Editar entrada"
        tk.Label(self.win, text=title, font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(16, 10))

        self.service_var, _ = self._field("Servicio / Sitio",
                                          initial=self._initial.get("service", ""))
        self.username_var, _ = self._field("Usuario / Email",
                                           initial=self._initial.get("username", ""))
        self.password_var, pentry = self._field("Password", show="\u2022",
                                                initial=self._initial.get("password", ""))

        # Row: show toggle + generate button
        row = tk.Frame(self.win, bg=C["bg"])
        row.pack(fill="x", padx=28)

        self.show_pw = tk.BooleanVar()
        def toggle():
            pentry.config(show="" if self.show_pw.get() else "\u2022")
        tk.Checkbutton(row, text="Mostrar", variable=self.show_pw, command=toggle,
                       bg=C["bg"], fg=C["muted"], activebackground=C["bg"],
                       selectcolor=C["surface"], font=FONT_SMALL,
                       bd=0, cursor="hand2").pack(side="left")

        tk.Button(row, text="Generar", font=FONT_SMALL,
                  bg=C["accent"], fg="white", relief="flat",
                  activebackground=C["accent2"], cursor="hand2", bd=0, padx=10,
                  command=self._open_generator).pack(side="right")

        # Strength bar
        self._strength = StrengthBar(self.win, width=364, height=8)
        self._strength.pack(padx=28, pady=(4, 2))
        self.password_var.trace_add("write", lambda *_: self._strength.update(self.password_var.get()))

        self.notes_var, _ = self._field("Notas (opcional)",
                                        initial=self._initial.get("notes", ""))

        btn_text = "Guardar" if self.mode == "add" else "Guardar cambios"
        tk.Button(self.win, text=btn_text, font=FONT_BUTTON,
                  bg=C["accent"], fg="white", relief="flat",
                  activebackground=C["accent2"], cursor="hand2",
                  bd=0, pady=8, command=self._save).pack(fill="x", padx=28, pady=10)

        # Trigger initial strength calculation
        self._strength.update(self.password_var.get())

    def _open_generator(self) -> None:
        PasswordGeneratorDialog(self.win, self.password_var)

    def _save(self) -> None:
        service = self.service_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        notes = self.notes_var.get().strip()

        if not service:
            messagebox.showwarning("Falta dato", "El servicio no puede estar vacio.",
                                   parent=self.win)
            return
        if not password:
            messagebox.showwarning("Falta dato", "La password no puede estar vacia.",
                                   parent=self.win)
            return

        self.win.destroy()
        self.callback(service, username, password, notes)


# ── Password generator ──────────────────────────────────────────────────────


class PasswordGeneratorDialog:
    """Configurable password generator dialog."""

    def __init__(self, parent: tk.Toplevel, target_var: tk.StringVar) -> None:
        self.target_var = target_var

        self.win = tk.Toplevel(parent)
        self.win.title("Generar password")
        self.win.geometry("380x420")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self._build()
        self._regenerate()

    def _build(self) -> None:
        tk.Label(self.win, text="Generador", font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(16, 10))

        # Mode
        self.mode_var = tk.StringVar(value="chars")
        mode_frame = tk.Frame(self.win, bg=C["bg"])
        mode_frame.pack(fill="x", padx=28)
        for val, txt in [("chars", "Caracteres"), ("passphrase", "Passphrase")]:
            tk.Radiobutton(mode_frame, text=txt, variable=self.mode_var, value=val,
                           bg=C["bg"], fg=C["text"], selectcolor=C["surface"],
                           activebackground=C["bg"], font=FONT_SMALL,
                           command=self._regenerate).pack(side="left", padx=(0, 16))

        # Length slider
        tk.Label(self.win, text="Longitud", font=FONT_SMALL,
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28, pady=(10, 0))
        self.length_var = tk.IntVar(value=20)
        self.length_label = tk.Label(self.win, text="20", font=FONT_SMALL,
                                     bg=C["bg"], fg=C["text"])
        self.length_label.pack(anchor="e", padx=28)
        tk.Scale(self.win, from_=12, to=64, orient="horizontal",
                 variable=self.length_var, bg=C["surface"], fg=C["text"],
                 troughcolor=C["entry_bg"], highlightthickness=0,
                 sliderrelief="flat", bd=0, font=FONT_SMALL,
                 command=lambda _: self._regenerate()).pack(fill="x", padx=28)

        # Charset checkboxes (only for chars mode)
        self.upper_var = tk.BooleanVar(value=True)
        self.lower_var = tk.BooleanVar(value=True)
        self.digit_var = tk.BooleanVar(value=True)
        self.symbol_var = tk.BooleanVar(value=True)

        checks = tk.Frame(self.win, bg=C["bg"])
        checks.pack(fill="x", padx=28, pady=(4, 0))
        for var, text in [
            (self.upper_var, "A-Z"), (self.lower_var, "a-z"),
            (self.digit_var, "0-9"), (self.symbol_var, "!@#$"),
        ]:
            tk.Checkbutton(checks, text=text, variable=var,
                           bg=C["bg"], fg=C["muted"], activebackground=C["bg"],
                           selectcolor=C["surface"], font=FONT_SMALL, bd=0,
                           command=self._regenerate).pack(side="left", padx=(0, 8))

        # Passphrase words count
        tk.Label(self.win, text="Palabras (passphrase)", font=FONT_SMALL,
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28, pady=(8, 0))
        self.words_var = tk.IntVar(value=5)
        tk.Scale(self.win, from_=3, to=10, orient="horizontal",
                 variable=self.words_var, bg=C["surface"], fg=C["text"],
                 troughcolor=C["entry_bg"], highlightthickness=0,
                 sliderrelief="flat", bd=0, font=FONT_SMALL,
                 command=lambda _: self._regenerate()).pack(fill="x", padx=28)

        # Preview
        tk.Label(self.win, text="Preview", font=FONT_SMALL,
                 bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28, pady=(8, 0))
        self.preview_var = tk.StringVar()
        prev_frame = tk.Frame(self.win, bg=C["surface"], highlightthickness=1,
                              highlightbackground=C["border"])
        prev_frame.pack(fill="x", padx=28, pady=(2, 4))
        tk.Entry(prev_frame, textvariable=self.preview_var, font=FONT_MONO,
                 bg=C["entry_bg"], fg=C["green"], relief="flat", bd=6,
                 readonlybackground=C["entry_bg"], state="readonly").pack(fill="x")

        # Buttons
        btn_row = tk.Frame(self.win, bg=C["bg"])
        btn_row.pack(fill="x", padx=28, pady=10)
        tk.Button(btn_row, text="Regenerar", font=FONT_SMALL,
                  bg=C["border"], fg=C["text"], relief="flat", cursor="hand2",
                  bd=0, padx=12, command=self._regenerate).pack(side="left")
        tk.Button(btn_row, text="Usar", font=FONT_BUTTON,
                  bg=C["accent"], fg="white", relief="flat",
                  activebackground=C["accent2"], cursor="hand2",
                  bd=0, padx=16, command=self._accept).pack(side="right")

    def _regenerate(self, *_) -> None:
        if self.mode_var.get() == "passphrase":
            n = self.words_var.get()
            pw = "-".join(secrets.choice(WORDLIST) for _ in range(n))
        else:
            length = self.length_var.get()
            charset = ""
            if self.upper_var.get():
                charset += string.ascii_uppercase
            if self.lower_var.get():
                charset += string.ascii_lowercase
            if self.digit_var.get():
                charset += string.digits
            if self.symbol_var.get():
                charset += "!@#$%^&*()-_=+[]{}|;:,.<>?"
            if not charset:
                charset = string.ascii_letters + string.digits
            pw = "".join(secrets.choice(charset) for _ in range(length))

        self.preview_var.set(pw)
        self.length_label.config(text=str(self.length_var.get()))

    def _accept(self) -> None:
        self.target_var.set(self.preview_var.get())
        self.win.destroy()


# ── Show password ───────────────────────────────────────────────────────────


class ShowPasswordDialog:
    """Reveals entry details for a limited time then auto-closes.

    Optionally provides an *on_edit* callback — if given, an "Editar" button
    is shown that closes this dialog and triggers the edit flow.
    """

    def __init__(
        self,
        parent: tk.Tk,
        entry: dict,
        auto_close_ms: int = 20_000,
        on_edit=None,
        on_copy=None,
    ) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title(entry.get("service", "Entrada"))

        has_notes = bool(entry.get("notes"))
        height = 340 if has_notes else 300
        self.win.geometry(f"380x{height}")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self._on_edit = on_edit
        self._on_copy = on_copy
        self._entry = entry

        tk.Label(self.win, text=entry.get("service", ""),
                 font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(18, 4))

        def row(label: str, value: str, mono: bool = False) -> None:
            tk.Label(self.win, text=label, font=FONT_SMALL,
                     bg=C["bg"], fg=C["muted"]).pack(anchor="w", padx=28)
            tk.Label(self.win, text=value,
                     font=FONT_MONO if mono else FONT_BODY,
                     bg=C["surface"], fg=C["text"], relief="flat",
                     anchor="w", padx=8, pady=5).pack(fill="x", padx=28, pady=(2, 8))

        row("Usuario", entry.get("username") or "\u2014")
        row("Password", entry.get("password", ""), mono=True)
        if has_notes:
            row("Notas", entry["notes"])

        secs = auto_close_ms // 1000
        self.countdown_var = tk.StringVar(value=f"Se cierra en {secs}s")
        tk.Label(self.win, textvariable=self.countdown_var,
                 font=FONT_SMALL, bg=C["bg"], fg=C["warn"]).pack(pady=(2, 0))

        btn_row = tk.Frame(self.win, bg=C["bg"])
        btn_row.pack(fill="x", padx=28, pady=(8, 10))

        tk.Button(btn_row, text="Cerrar", font=FONT_BUTTON,
                  bg=C["border"], fg=C["text"], relief="flat",
                  cursor="hand2", bd=0, pady=7, padx=12,
                  command=self.win.destroy).pack(side="left")

        if on_copy:
            tk.Button(btn_row, text="Copiar", font=FONT_BUTTON,
                      bg=C["surface"], fg=C["accent2"], relief="flat",
                      cursor="hand2", bd=0, pady=7, padx=12,
                      command=self._do_copy).pack(side="left", padx=(8, 0))

        if on_edit:
            tk.Button(btn_row, text="Editar", font=FONT_BUTTON,
                      bg=C["accent"], fg="white", relief="flat",
                      activebackground=C["accent2"], cursor="hand2",
                      bd=0, pady=7, padx=12,
                      command=self._do_edit).pack(side="right")

        self._remaining = secs
        self._tick()
        self.win.after(auto_close_ms, self._close)

    def _do_edit(self) -> None:
        self.win.destroy()
        if self._on_edit:
            self._on_edit()

    def _do_copy(self) -> None:
        if self._on_copy:
            self._on_copy(self._entry.get("password", ""))

    def _tick(self) -> None:
        if not self.win.winfo_exists():
            return
        self._remaining -= 1
        self.countdown_var.set(f"Se cierra en {self._remaining}s")
        if self._remaining > 0:
            self.win.after(1000, self._tick)

    def _close(self) -> None:
        if self.win.winfo_exists():
            self.win.destroy()


# ── Recovery codes display ──────────────────────────────────────────────────


class RecoveryCodesDialog:
    """Shows the 10 recovery codes.  User must confirm before closing."""

    def __init__(self, parent: tk.Tk | tk.Toplevel, codes: str) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("Codigos de recuperacion")
        self.win.geometry("460x480")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        self._codes = codes
        self._confirmed = False
        self._clipboard_countdown_id: str | None = None
        self._clipboard_secs_left: int = 0
        self._copy_revert_id: str | None = None
        self._clipboard = ManagedClipboard(
            self.win.after,
            self.win.after_cancel,
            widget=self.win,
        )
        self._build()
        self.win.bind("<Destroy>", self._on_destroy)

    def _build(self) -> None:
        tk.Label(self.win, text="Codigos de recuperacion",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["accent"]).pack(pady=(16, 4))

        tk.Label(self.win,
                 text="Guarda estos codigos en un lugar seguro.\n"
                      "Son tu UNICA forma de recuperar el vault\n"
                      "si olvidas la master password.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["warn"],
                 justify="center").pack(pady=(0, 12))

        groups = self._codes.split("-")
        grid = tk.Frame(self.win, bg=C["surface"], padx=16, pady=12)
        grid.pack(padx=40)

        for i, code in enumerate(groups):
            row, col = divmod(i, 2)
            lbl = tk.Label(grid, text=f"  {i+1:2d}.  {code}  ",
                           font=("Consolas", 13, "bold"),
                           bg=C["surface"], fg=C["green"], anchor="w")
            lbl.grid(row=row, column=col, padx=8, pady=3, sticky="w")

        tk.Label(self.win,
                 text="NO guardes estos codigos en tu PC.\n"
                      "Imprimilos o escribilos en papel.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["danger"],
                 justify="center").pack(pady=(12, 4))

        self._copy_btn = tk.Button(
            self.win, text="Copiar codigos", font=FONT_SMALL,
            bg=C["border"], fg=C["text"], relief="flat",
            cursor="hand2", bd=0, padx=12,
            command=self._copy,
        )
        self._copy_btn.pack(pady=(4, 2))

        self._clipboard_timer_var = tk.StringVar()
        tk.Label(self.win, textvariable=self._clipboard_timer_var,
                 font=("Segoe UI", 8), bg=C["bg"], fg=C["muted"],
                 ).pack(pady=(0, 6))

        self._confirm_var = tk.BooleanVar()
        tk.Checkbutton(self.win,
                       text="Ya guarde mis codigos de recuperacion",
                       variable=self._confirm_var,
                       bg=C["bg"], fg=C["text"],
                       activebackground=C["bg"], selectcolor=C["surface"],
                       font=FONT_SMALL, bd=0, cursor="hand2",
                       command=self._check_confirm).pack(pady=(0, 8))

        self._close_btn = tk.Button(
            self.win, text="Continuar", font=FONT_BUTTON,
            bg=C["accent"], fg="white", relief="flat",
            activebackground=C["accent2"], cursor="hand2",
            bd=0, pady=8, state="disabled",
            command=self._close,
        )
        self._close_btn.pack(fill="x", padx=40, pady=(0, 12))

    def _copy(self) -> None:
        self._clipboard.copy(
            self._codes,
            ttl_ms=60_000,
            on_clear=self._on_clipboard_cleared,
        )

        self._copy_btn.config(text="\u2714 Copiado!", fg=C["green"])
        if self._copy_revert_id is not None:
            self.win.after_cancel(self._copy_revert_id)
        self._copy_revert_id = self.win.after(
            2000, lambda: self._copy_btn.config(text="Copiar codigos", fg=C["text"]),
        )

        self._clipboard_secs_left = 60
        if self._clipboard_countdown_id is not None:
            self.win.after_cancel(self._clipboard_countdown_id)
        self._tick_clipboard_countdown()

    def _on_clipboard_cleared(self) -> None:
        self._clipboard_secs_left = 0
        self._clipboard_timer_var.set("")

    def _tick_clipboard_countdown(self) -> None:
        if self._clipboard_secs_left <= 0:
            self._clipboard_timer_var.set("")
            self._clipboard_countdown_id = None
            return
        self._clipboard_timer_var.set(
            f"Clipboard se limpia en {self._clipboard_secs_left}s"
        )
        self._clipboard_secs_left -= 1
        self._clipboard_countdown_id = self.win.after(
            1000, self._tick_clipboard_countdown,
        )

    def _on_destroy(self, _event: object = None) -> None:
        for timer_id in (self._clipboard_countdown_id, self._copy_revert_id):
            if timer_id is not None:
                try:
                    self.win.after_cancel(timer_id)
                except Exception:
                    pass
        self._clipboard_countdown_id = None
        self._copy_revert_id = None
        self._clipboard.clear_now()

    def _check_confirm(self) -> None:
        self._close_btn.config(state="normal" if self._confirm_var.get() else "disabled")

    def _close(self) -> None:
        self._confirmed = True
        self.win.destroy()

    def wait(self) -> bool:
        """Block until the dialog is closed.  Returns True if confirmed."""
        self.win.wait_window()
        return self._confirmed


# ── Recovery codes input ────────────────────────────────────────────────────


class RecoveryInputDialog:
    """Dialog where the user enters 10 recovery code groups.

    Supports pasting a full code (e.g. ``AAAA-BBBB-CCCC-...``) into any box;
    the text is split and distributed across all boxes automatically.  Each box
    is limited to ``RECOVERY_GROUP_LEN`` characters and auto-advances to the
    next box when full.
    """

    def __init__(self, parent: tk.Tk | tk.Toplevel) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("Recuperar vault")
        self.win.geometry("440x440")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self.result: str | None = None
        self._entries: list[tk.Entry] = []
        self._vars: list[tk.StringVar] = []
        self._indicators: list[tk.Label] = []
        self._submit_btn: tk.Button | None = None
        self._build()

    def _build(self) -> None:
        from vault_app.constants import RECOVERY_CODE_GROUPS, RECOVERY_GROUP_LEN, RECOVERY_CHARSET

        tk.Label(self.win, text="Ingresa tus codigos de recuperacion",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(16, 4))

        tk.Label(self.win,
                 text="Ingresa los 10 grupos tal como los guardaste.\n"
                      "Podes pegar el codigo completo en cualquier casilla.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
                 justify="center").pack(pady=(0, 12))

        grid = tk.Frame(self.win, bg=C["bg"])
        grid.pack(padx=40)

        self._group_len = RECOVERY_GROUP_LEN

        self._charset = RECOVERY_CHARSET

        for i in range(RECOVERY_CODE_GROUPS):
            row, col = divmod(i, 2)

            frame = tk.Frame(grid, bg=C["bg"])
            frame.grid(row=row, column=col, padx=6, pady=4, sticky="w")

            tk.Label(frame, text=f"{i+1:2d}.", font=FONT_SMALL,
                     bg=C["bg"], fg=C["muted"], width=3).pack(side="left")

            var = tk.StringVar()
            entry = tk.Entry(frame, textvariable=var,
                             font=("Consolas", 12), width=6,
                             bg=C["entry_bg"], fg=C["text"],
                             insertbackground=C["accent"], relief="flat", bd=4)
            entry.pack(side="left")

            indicator = tk.Label(frame, text="", font=("Segoe UI", 10),
                                 bg=C["bg"], width=2)
            indicator.pack(side="left", padx=(2, 0))

            idx = i
            var.trace_add("write", lambda *_a, _idx=idx: self._on_change(_idx))
            entry.bind("<<Paste>>", lambda e, _idx=idx: self._on_paste(e, _idx))

            self._entries.append(entry)
            self._vars.append(var)
            self._indicators.append(indicator)

        if self._entries:
            self._entries[0].focus()

        self.status_var = tk.StringVar()
        tk.Label(self.win, textvariable=self.status_var, font=FONT_SMALL,
                 bg=C["bg"], fg=C["danger"]).pack(pady=(8, 0))

        btn_row = tk.Frame(self.win, bg=C["bg"])
        btn_row.pack(fill="x", padx=40, pady=(8, 12))

        tk.Button(btn_row, text="Cancelar", font=FONT_BUTTON,
                  bg=C["border"], fg=C["text"], relief="flat",
                  cursor="hand2", bd=0, pady=7, padx=12,
                  command=self.win.destroy).pack(side="left")

        self._submit_btn = tk.Button(
            btn_row, text="Recuperar", font=FONT_BUTTON,
            bg=C["accent"], fg="white", relief="flat",
            activebackground=C["accent2"], cursor="hand2",
            bd=0, pady=7, padx=12, state="disabled",
            command=self._submit,
        )
        self._submit_btn.pack(side="right")

    def _on_change(self, idx: int) -> None:
        """Enforce max length, filter invalid chars, update indicator, auto-advance."""
        raw = self._vars[idx].get().upper()
        filtered = "".join(ch for ch in raw if ch in self._charset)

        if filtered != self._vars[idx].get():
            self._vars[idx].set(filtered)
            return

        if len(filtered) > self._group_len:
            self._vars[idx].set(filtered[:self._group_len])
            return

        self._update_indicator(idx)
        self._update_submit_state()

        if len(self._vars[idx].get()) == self._group_len:
            nxt = idx + 1
            if nxt < len(self._entries):
                self._entries[nxt].focus()
                self._entries[nxt].icursor("end")

    def _validate_field(self, idx: int) -> str:
        """Return 'valid', 'partial', or 'empty' for the given field."""
        val = self._vars[idx].get()
        if not val:
            return "empty"
        if len(val) == self._group_len:
            return "valid"
        return "partial"

    def _update_indicator(self, idx: int) -> None:
        state = self._validate_field(idx)
        if state == "valid":
            self._indicators[idx].config(text="\u2713", fg=C["green"])
        elif state == "partial":
            self._indicators[idx].config(text="\u2027\u2027\u2027", fg=C["muted"])
        else:
            self._indicators[idx].config(text="")

    def _update_submit_state(self) -> None:
        all_valid = all(self._validate_field(i) == "valid" for i in range(len(self._vars)))
        if self._submit_btn is not None:
            self._submit_btn.config(state="normal" if all_valid else "disabled")

    def _on_paste(self, event: tk.Event, idx: int) -> str:
        """Intercept paste: only auto-distribute if the pasted text contains
        exactly all 10 groups (the full recovery code).  Always fills from
        box 1 regardless of which box is focused.

        Partial pastes are left as normal single-box input (truncated to
        ``RECOVERY_GROUP_LEN`` by ``_on_change``), since there's no way to
        know which box a partial group belongs to.
        """
        try:
            clipboard = event.widget.clipboard_get()
        except tk.TclError:
            return ""

        cleaned = clipboard.strip().upper().replace(" ", "")
        total_boxes = len(self._entries)

        if "-" in cleaned:
            groups = [g for g in cleaned.split("-") if g]
        else:
            groups = [
                cleaned[i:i + self._group_len]
                for i in range(0, len(cleaned), self._group_len)
            ]

        if len(groups) != total_boxes:
            return ""

        for i, group in enumerate(groups):
            self._vars[i].set(group[:self._group_len])

        for i in range(total_boxes):
            self._update_indicator(i)
        self._update_submit_state()

        self._entries[-1].focus()
        self._entries[-1].icursor("end")
        return "break"

    def _submit(self) -> None:
        groups = [e.get().strip().upper() for e in self._entries]
        if any(len(g) == 0 for g in groups):
            self.status_var.set("Completa todos los campos.")
            return
        self.result = "-".join(groups)
        self.win.destroy()

    def wait(self) -> str | None:
        """Block until closed.  Returns the joined code string or None."""
        self.win.wait_window()
        return self.result


# ── New password dialog (for recovery flow) ─────────────────────────────────


class NewPasswordDialog:
    """Force the user to set a new master password after recovery."""

    def __init__(self, parent: tk.Tk | tk.Toplevel) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("Nueva master password")
        self.win.geometry("420x280")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        self.result: str | None = None
        self._build()

    def _build(self) -> None:
        tk.Label(self.win, text="Establece una nueva master password",
                 font=("Segoe UI", 13, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(20, 4))

        tk.Label(self.win,
                 text="Tu vault fue recuperado. Debes crear una nueva password.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
                 wraplength=340).pack(pady=(0, 12))

        def field(label: str) -> tk.StringVar:
            tk.Label(self.win, text=label, font=FONT_SMALL,
                     bg=C["bg"], fg=C["muted"], anchor="w").pack(fill="x", padx=40)
            frame = tk.Frame(self.win, bg=C["surface"],
                             highlightthickness=1, highlightbackground=C["border"])
            frame.pack(fill="x", padx=40, pady=(2, 8))
            var = tk.StringVar()
            tk.Entry(frame, textvariable=var, show="\u2022",
                     font=FONT_MONO, bg=C["entry_bg"], fg=C["text"],
                     insertbackground=C["accent"], relief="flat", bd=7).pack(fill="x")
            return var

        self.pw_var = field("Nueva password")
        self.pw2_var = field("Confirmar password")

        self.status_var = tk.StringVar()
        tk.Label(self.win, textvariable=self.status_var, font=FONT_SMALL,
                 bg=C["bg"], fg=C["danger"]).pack()

        tk.Button(self.win, text="Guardar", font=FONT_BUTTON,
                  bg=C["accent"], fg="white", relief="flat",
                  activebackground=C["accent2"], cursor="hand2",
                  bd=0, pady=8, command=self._submit).pack(fill="x", padx=40, pady=8)

    def _submit(self) -> None:
        pw = self.pw_var.get()
        pw2 = self.pw2_var.get()
        if len(pw) < 12:
            self.status_var.set("Minimo 12 caracteres.")
            return
        if pw != pw2:
            self.status_var.set("Las passwords no coinciden.")
            return
        self.result = pw
        self.win.destroy()

    def wait(self) -> str | None:
        self.win.wait_window()
        return self.result


# ── Typed confirmation dialog (destructive reset) ───────────────────────────


class ConfirmDeleteDialog:
    """Requires the user to type ELIMINAR to confirm vault deletion."""

    CONFIRM_WORD = "ELIMINAR"

    def __init__(self, parent: tk.Tk | tk.Toplevel) -> None:
        self.win = tk.Toplevel(parent)
        self.win.title("Confirmar eliminacion")
        self.win.geometry("420x280")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self.result = False
        self._build()

    def _build(self) -> None:
        tk.Label(self.win, text="ULTIMA CONFIRMACION",
                 font=("Segoe UI", 14, "bold"),
                 bg=C["bg"], fg=C["danger"]).pack(pady=(20, 4))

        tk.Label(self.win,
                 text="Vas a perder TODAS tus passwords.\n"
                      "Esta accion NO se puede deshacer.",
                 font=FONT_SMALL, bg=C["bg"], fg=C["warn"],
                 justify="center").pack(pady=(0, 12))

        tk.Label(self.win,
                 text=f"Escribe {self.CONFIRM_WORD} para confirmar:",
                 font=FONT_SMALL, bg=C["bg"], fg=C["text"],
                 anchor="w").pack(fill="x", padx=40)

        frame = tk.Frame(self.win, bg=C["surface"],
                         highlightthickness=1, highlightbackground=C["border"])
        frame.pack(fill="x", padx=40, pady=(4, 12))
        self._input_var = tk.StringVar()
        self._input_var.trace_add("write", lambda *_: self._check())
        entry = tk.Entry(frame, textvariable=self._input_var,
                         font=FONT_MONO, bg=C["entry_bg"], fg=C["danger"],
                         insertbackground=C["danger"], relief="flat", bd=7)
        entry.pack(fill="x")
        entry.focus()

        btn_row = tk.Frame(self.win, bg=C["bg"])
        btn_row.pack(fill="x", padx=40, pady=(0, 16))

        tk.Button(btn_row, text="Cancelar", font=FONT_BUTTON,
                  bg=C["border"], fg=C["text"], relief="flat",
                  cursor="hand2", bd=0, pady=7, padx=12,
                  command=self.win.destroy).pack(side="left")

        self._delete_btn = tk.Button(
            btn_row, text="Destruir vault", font=FONT_BUTTON,
            bg=C["danger"], fg="white", relief="flat",
            activebackground="#e74c3c", cursor="hand2",
            bd=0, pady=7, padx=12, state="disabled",
            command=self._confirm,
        )
        self._delete_btn.pack(side="right")

    def _check(self) -> None:
        matches = self._input_var.get().strip().upper() == self.CONFIRM_WORD
        self._delete_btn.config(state="normal" if matches else "disabled")

    def _confirm(self) -> None:
        self.result = True
        self.win.destroy()

    def wait(self) -> bool:
        """Block until closed.  Returns True if confirmed."""
        self.win.wait_window()
        return self.result


class AdvancedVaultActionsDialog:
    """Secondary menu for uninstall vs vault-destruction flows."""

    MIN_WIDTH = 470
    MIN_HEIGHT = 430

    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        *,
        uninstall_available: bool,
        show_export_backup: bool = False,
    ) -> None:
        self._uninstall_available = uninstall_available
        self._show_export_backup = show_export_backup
        self.result: str | None = None

        self.win = tk.Toplevel(parent)
        self.win.title("Opciones avanzadas")
        self.win.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
        self.win.resizable(False, False)
        self.win.configure(bg=C["bg"])
        self.win.grab_set()
        self.win.transient(parent)

        self._build()
        self._fit_to_content()

    def _build(self) -> None:
        tk.Label(
            self.win, text="Opciones avanzadas",
            font=("Segoe UI", 14, "bold"),
            bg=C["bg"], fg=C["text"],
        ).pack(pady=(18, 6))

        tk.Label(
            self.win,
            text="Estas acciones no forman parte del uso normal del vault.\n"
                 "Desinstalar la app y destruir el vault son cosas distintas.",
            font=FONT_SMALL, bg=C["bg"], fg=C["muted"],
            justify="center",
        ).pack(pady=(0, 10))

        tk.Label(
            self.win,
            text="Desinstalar la app NO elimina tu vault ni tus datos cifrados.",
            font=("Segoe UI", 9, "bold"),
            bg=C["bg"], fg=C["danger"],
            justify="center",
        ).pack(pady=(0, 10))

        if self._show_export_backup:
            self._build_action_card(
                title="Exportar respaldo cifrado",
                body="Guarda una copia portable del vault cifrado para moverla o "
                     "subirla manualmente a tu nube. Sigue requiriendo tu password.",
                button_text="Exportar respaldo...",
                button_bg=C["accent"],
                button_fg="white",
                action="export",
            )

        self._build_action_card(
            title="Desinstalar app",
            body=f"Quita {APP_NAME} de este equipo. El vault local queda intacto.",
            button_text=(
                "Abrir desinstalador"
                if self._uninstall_available
                else "Como desinstalar"
            ),
            button_bg=C["surface"],
            button_fg=C["accent2"],
            action="uninstall",
        )

        self._build_action_card(
            title="Destruir vault y datos",
            body="Elimina el vault local, el backup local y el lock local de este "
                 "dispositivo. Esta accion no se puede deshacer.",
            button_text="Destruir vault...",
            button_bg=C["danger"],
            button_fg="white",
            action="destroy",
        )

        tk.Button(
            self.win, text="Cerrar", font=FONT_BUTTON,
            bg=C["border"], fg=C["text"], relief="flat",
            cursor="hand2", bd=0, pady=8,
            command=self.win.destroy,
        ).pack(fill="x", padx=34, pady=(4, 14))

    def _fit_to_content(self) -> None:
        self.win.update_idletasks()
        width = max(self.MIN_WIDTH, self.win.winfo_reqwidth())
        height = max(self.MIN_HEIGHT, self.win.winfo_reqheight())
        self.win.geometry(f"{width}x{height}")

    def _build_action_card(
        self,
        *,
        title: str,
        body: str,
        button_text: str,
        button_bg: str,
        button_fg: str,
        action: str,
    ) -> None:
        card = tk.Frame(
            self.win, bg=C["surface"],
            highlightthickness=1, highlightbackground=C["border"],
            padx=14, pady=10,
        )
        card.pack(fill="x", padx=34, pady=(0, 8))

        tk.Label(
            card, text=title, font=("Segoe UI", 11, "bold"),
            bg=C["surface"], fg=C["text"], anchor="w",
        ).pack(fill="x")

        tk.Label(
            card, text=body, font=FONT_SMALL,
            bg=C["surface"], fg=C["muted"], justify="left",
            wraplength=380, anchor="w",
        ).pack(fill="x", pady=(4, 8))

        tk.Button(
            card, text=button_text, font=FONT_BUTTON,
            bg=button_bg, fg=button_fg, relief="flat",
            activebackground=button_bg,
            activeforeground=button_fg,
            cursor="hand2", bd=0, pady=7, padx=12,
            command=lambda: self._choose(action),
        ).pack(anchor="e")

    def _choose(self, action: str) -> None:
        self.result = action
        self.win.destroy()

    def wait(self) -> str | None:
        self.win.wait_window()
        return self.result
