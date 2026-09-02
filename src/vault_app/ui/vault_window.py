"""
Main vault window — card list, search, hover actions, copy, reveal, lock.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from cryptography.exceptions import InvalidTag

from vault_app.constants import (
    APP_BRAND_LEAD,
    APP_BRAND_TAIL,
    APP_NAME,
    PORTABLE_BACKUP_EXTENSION,
    APP_TITLE,
    CLIPBOARD_CLEAR_MS,
    REVEAL_CLEAR_MS,
    AUTO_LOCK_MS,
)
from vault_app.errors import VaultConflictError, VaultStorageError
from vault_app.header import VaultHeader
from vault_app.storage import (
    current_vault_fingerprint,
    delete_vault_files,
    export_portable_backup,
    load_unlocked_vault,
    portable_backup_suggested_name,
    vault_path,
    save_vault,
)
from vault_app.security import ManagedClipboard, wipe_secrets
from vault_app.ui.theme import (
    C, FONT_BODY, FONT_MONO, FONT_SMALL, FONT_BUTTON,
    FONT_SERVICE, FONT_USER, avatar_color,
)
from vault_app.ui.dialogs import AddEntryDialog, ShowPasswordDialog


class VaultApp:
    """Password list window.  Sets ``self.relock_requested`` before returning."""

    def __init__(self, data: dict, key: bytes, header: VaultHeader, vault_fingerprint: str | None) -> None:
        self.data = data
        self.key = key
        self.header = header
        self._vault_fingerprint = vault_fingerprint
        self.relock_requested = False

        self._autolock_timer: str | None = None
        self._selected_idx: int | None = None
        self._cards: list[dict] = []
        self._hover_leave_id: str | None = None
        self._hover_card_idx: int | None = None
        self._status_clear_id: str | None = None
        self._stale_requires_reload = False
        self.reset_to_create_requested = False
        self._new_entry_btn: tk.Button | None = None
        self._reload_btn: tk.Button | None = None
        self._recovery_btn: tk.Button | None = None

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("740x540")
        self.root.minsize(620, 420)
        self.root.configure(bg=C["bg"])
        self.root.eval("tk::PlaceWindow . center")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._clipboard = ManagedClipboard(
            self.root.after,
            self.root.after_cancel,
            widget=self.root,
        )

        self._build_ui()
        self._refresh_list()
        self._reset_autolock()

        for event in ("<Motion>", "<KeyPress>", "<ButtonPress>"):
            self.root.bind_all(event, self._on_activity)

        self.root.mainloop()

    # ── Auto-lock ───────────────────────────────────────────────────────

    def _cancel_pending_callbacks(self) -> None:
        for timer_id in (
            self._autolock_timer,
            self._hover_leave_id,
            self._status_clear_id,
        ):
            if timer_id is None:
                continue
            try:
                self.root.after_cancel(timer_id)
            except Exception:
                pass
        self._autolock_timer = None
        self._hover_leave_id = None
        self._status_clear_id = None

    def _reset_autolock(self) -> None:
        if self._autolock_timer:
            self.root.after_cancel(self._autolock_timer)
        self._autolock_timer = self.root.after(AUTO_LOCK_MS, self._do_lock)

    def _on_activity(self, _event: tk.Event | None = None) -> None:
        self._reset_autolock()

    def _do_lock(self) -> None:
        self._cancel_pending_callbacks()
        self._clear_clipboard_now()
        wipe_secrets(self.key, self.data)
        self.key = None  # type: ignore[assignment]
        self.data = None  # type: ignore[assignment]
        self.relock_requested = True
        self.root.destroy()

    def _on_close(self) -> None:
        self._cancel_pending_callbacks()
        self._clear_clipboard_now()
        wipe_secrets(self.key, self.data)
        self.key = None  # type: ignore[assignment]
        self.data = None  # type: ignore[assignment]
        self.root.destroy()

    # ── UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Top bar ────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=C["surface"], height=48)
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)

        tk.Label(
            topbar, text=f"\U0001f510 {APP_BRAND_LEAD}",
            font=("Segoe UI", 13, "bold"),
            bg=C["surface"], fg=C["accent"],
        ).pack(side="left", padx=(16, 0))

        tk.Label(
            topbar, text=APP_BRAND_TAIL,
            font=("Segoe UI", 13), bg=C["surface"], fg=C["muted"],
        ).pack(side="left")

        tb_btn = dict(
            font=FONT_SMALL, relief="flat", cursor="hand2", bd=0,
            pady=4, padx=10,
        )

        tk.Button(
            topbar, text="\U0001f512 Bloquear",
            command=self._do_lock,
            bg=C["surface"], fg=C["muted"],
            activebackground=C["hover"], activeforeground=C["text"],
            **tb_btn,
        ).pack(side="right", padx=(0, 12))

        tk.Button(
            topbar, text="Opciones",
            command=self._open_advanced_actions,
            bg=C["surface"], fg=C["muted"],
            activebackground=C["hover"], activeforeground=C["text"],
            **tb_btn,
        ).pack(side="right", padx=(0, 4))

        recovery_label = "\U0001f511 Recovery" if self.header.has_recovery else "\U0001f511 Activar Recovery"
        self._recovery_btn = tk.Button(
            topbar, text=recovery_label,
            command=self._regenerate_recovery,
            bg=C["surface"], fg=C["warn"],
            activebackground=C["hover"], activeforeground=C["warn"],
            **tb_btn,
        )
        self._recovery_btn.pack(side="right", padx=(0, 4))

        self._reload_btn = tk.Button(
            topbar, text="\u21bb Recargar",
            command=self._reload_from_disk,
            bg=C["surface"], fg=C["accent2"],
            activebackground=C["hover"], activeforeground=C["text"],
            **tb_btn,
        )
        self._reload_btn.pack(side="right", padx=(0, 4))

        self._new_entry_btn = tk.Button(
            topbar, text="+ Nueva entrada",
            command=self._add_entry,
            font=FONT_BUTTON, bg=C["accent"], fg="white",
            activebackground=C["accent2"], activeforeground="white",
            relief="flat", cursor="hand2", bd=0, pady=4, padx=14,
        )
        self._new_entry_btn.pack(side="right", padx=(0, 8))

        # ── Search bar ─────────────────────────────────────────────────
        search_outer = tk.Frame(self.root, bg=C["bg"])
        search_outer.pack(fill="x", padx=24, pady=(12, 0))

        search_frame = tk.Frame(
            search_outer, bg=C["entry_bg"],
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"],
        )
        search_frame.pack(fill="x")

        tk.Label(
            search_frame, text="\U0001f50d",
            font=("Segoe UI Emoji", 10),
            bg=C["entry_bg"], fg=C["muted"],
        ).pack(side="left", padx=(10, 0))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self._search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=FONT_BODY, bg=C["entry_bg"], fg=C["text"],
            insertbackground=C["accent"], relief="flat", bd=8,
        )
        self._search_entry.pack(side="left", fill="x", expand=True)

        hint = tk.Label(
            search_frame, text="Ctrl+K",
            font=("Segoe UI", 8), bg=C["entry_bg"], fg=C["border"],
        )
        hint.pack(side="right", padx=(0, 10))

        self.root.bind("<Control-k>", self._focus_search)
        self.root.bind("<Control-K>", self._focus_search)

        # ── Card list area ─────────────────────────────────────────────
        list_outer = tk.Frame(self.root, bg=C["bg"])
        list_outer.pack(fill="both", expand=True, padx=24, pady=(10, 0))

        self._list_canvas = tk.Canvas(
            list_outer, bg=C["bg"], highlightthickness=0, bd=0,
        )
        self._list_canvas.pack(side="left", fill="both", expand=True)

        self._scrollbar = tk.Scrollbar(
            list_outer, orient="vertical",
            command=self._list_canvas.yview,
            bg=C["border"], troughcolor=C["bg"],
            highlightthickness=0, bd=0, width=8,
        )
        self._scrollbar.pack(side="right", fill="y")
        self._list_canvas.configure(yscrollcommand=self._scrollbar.set)

        self._list_inner = tk.Frame(self._list_canvas, bg=C["bg"])
        self._canvas_window = self._list_canvas.create_window(
            (0, 0), window=self._list_inner, anchor="nw",
        )

        self._list_inner.bind(
            "<Configure>",
            lambda _: self._list_canvas.configure(
                scrollregion=self._list_canvas.bbox("all"),
            ),
        )
        self._list_canvas.bind(
            "<Configure>",
            lambda e: self._list_canvas.itemconfig(
                self._canvas_window, width=e.width,
            ),
        )

        self._list_canvas.bind("<Enter>", self._bind_scroll)
        self._list_canvas.bind("<Leave>", self._unbind_scroll)

        # ── Footer / status bar ────────────────────────────────────────
        footer = tk.Frame(self.root, bg=C["surface"], height=32)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        self.count_var = tk.StringVar()
        tk.Label(
            footer, textvariable=self.count_var,
            font=("Segoe UI", 8), bg=C["surface"], fg=C["muted"],
        ).pack(side="left", padx=24)

        self.status_var = tk.StringVar()
        self._status_label = tk.Label(
            footer, textvariable=self.status_var,
            font=("Segoe UI", 8), bg=C["surface"], fg=C["green"],
        )
        self._status_label.pack(side="right", padx=24)

    # ── Search ──────────────────────────────────────────────────────────

    def _focus_search(self, _event: tk.Event | None = None) -> str:
        self._search_entry.focus_set()
        self._search_entry.select_range(0, "end")
        return "break"

    # ── Scroll ──────────────────────────────────────────────────────────

    def _bind_scroll(self, _event: tk.Event | None = None) -> None:
        self._list_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._list_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units",
            ),
        )

    def _unbind_scroll(self, _event: tk.Event | None = None) -> None:
        self._list_canvas.unbind_all("<MouseWheel>")

    # ── Card list ───────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        for widget in self._list_inner.winfo_children():
            widget.destroy()
        self._cards.clear()
        self._selected_idx = None

        query = self.search_var.get().lower()
        visible = 0
        for i, entry in enumerate(self.data["entries"]):
            service = entry.get("service", "")
            username = entry.get("username", "")
            if query and query not in service.lower() and query not in username.lower():
                continue
            self._build_card(self._list_inner, i, entry)
            visible += 1

        if visible == 0 and not query:
            tk.Label(
                self._list_inner,
                text="No hay entradas todavia.\nUsa  + Nueva entrada  para agregar una.",
                font=FONT_BODY, bg=C["bg"], fg=C["muted"],
                justify="center",
            ).pack(expand=True, pady=60)
        elif visible == 0:
            tk.Label(
                self._list_inner,
                text="Sin resultados.",
                font=FONT_BODY, bg=C["bg"], fg=C["muted"],
            ).pack(expand=True, pady=60)

        total = len(self.data["entries"])
        self.count_var.set(f"{total} entrada{'s' if total != 1 else ''}")

    def _build_card(self, parent: tk.Frame, idx: int, entry: dict) -> None:
        service = entry.get("service", "")
        username = entry.get("username", "")
        letter = service[0].upper() if service else "?"
        bg = C["surface"]

        card = tk.Frame(parent, bg=bg, padx=12, pady=10)
        card.pack(fill="x", pady=(0, 2))

        # Avatar
        av_color = avatar_color(service)
        avatar = tk.Label(
            card, text=letter,
            font=("Segoe UI", 13, "bold"), fg="white", bg=av_color,
            width=2, height=1,
        )
        avatar.pack(side="left", padx=(0, 12))

        # Text
        text_frame = tk.Frame(card, bg=bg)
        text_frame.pack(side="left", fill="x", expand=True)

        lbl_service = tk.Label(
            text_frame, text=service,
            font=FONT_SERVICE, bg=bg, fg=C["text"], anchor="w",
        )
        lbl_service.pack(fill="x")

        lbl_user = tk.Label(
            text_frame, text=username if username else "\u2014",
            font=FONT_USER, bg=bg, fg=C["muted"], anchor="w",
        )
        lbl_user.pack(fill="x")

        # Action buttons (always packed, subtle until hover)
        actions = tk.Frame(card, bg=bg)
        actions.pack(side="right", padx=(8, 0))

        action_icons = [
            ("\U0001f4cb", C["border"], C["accent2"], lambda: self._copy_password_at(idx)),
            ("\U0001f441", C["border"], C["accent2"], lambda: self._show_password_at(idx)),
            ("\u270e",     C["border"], C["text"],    lambda: self._edit_entry_at(idx)),
            ("\U0001f5d1", C["border"], C["danger"],  lambda: self._delete_entry_at(idx)),
        ]

        action_labels: list[tk.Label] = []
        for char, idle_fg, hover_fg, cmd in action_icons:
            lbl = tk.Label(
                actions, text=char,
                font=("Segoe UI Emoji", 12), bg=bg, fg=idle_fg,
                cursor="hand2", padx=4,
            )
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda _e, c=cmd: c())
            lbl._hover_fg = hover_fg  # type: ignore[attr-defined]
            lbl._idle_fg = idle_fg    # type: ignore[attr-defined]
            action_labels.append(lbl)

        card_data = {
            "frame": card,
            "idx": idx,
            "avatar": avatar,
            "text_frame": text_frame,
            "lbl_service": lbl_service,
            "lbl_user": lbl_user,
            "actions": actions,
            "action_labels": action_labels,
            "bg": bg,
        }
        self._cards.append(card_data)

        all_widgets = [card, avatar, text_frame, lbl_service, lbl_user, actions] + action_labels
        for w in all_widgets:
            w.bind("<Enter>", lambda _e, cd=card_data: self._card_enter(cd))
            w.bind("<Leave>", lambda _e, cd=card_data: self._card_leave(cd))
            if w not in action_labels:
                w.bind("<Button-1>", lambda _e, i=idx: self._select_card(i))
                w.bind("<Double-1>", lambda _e, i=idx: self._show_password_at(i))

    def _card_enter(self, card_data: dict) -> None:
        if self._hover_leave_id is not None:
            self.root.after_cancel(self._hover_leave_id)
            self._hover_leave_id = None

        idx = card_data["idx"]
        if self._hover_card_idx == idx:
            return
        if self._hover_card_idx is not None:
            self._set_card_hover(self._hover_card_idx, False)
        self._hover_card_idx = idx
        self._set_card_hover(idx, True)

    def _card_leave(self, card_data: dict) -> None:
        idx = card_data["idx"]
        if self._hover_leave_id is not None:
            self.root.after_cancel(self._hover_leave_id)
        self._hover_leave_id = self.root.after(
            50, lambda: self._actually_leave(idx),
        )

    def _actually_leave(self, idx: int) -> None:
        self._hover_leave_id = None
        if self._hover_card_idx == idx:
            self._set_card_hover(idx, False)
            self._hover_card_idx = None

    def _set_card_hover(self, idx: int, hovering: bool) -> None:
        for cd in self._cards:
            if cd["idx"] != idx:
                continue
            is_selected = self._selected_idx == idx
            bg = C["hover"] if (hovering or is_selected) else cd["bg"]
            for w in (cd["frame"], cd["text_frame"], cd["lbl_service"],
                      cd["lbl_user"], cd["actions"]):
                w.config(bg=bg)
            for lbl in cd["action_labels"]:
                lbl.config(
                    bg=bg,
                    fg=lbl._hover_fg if hovering else lbl._idle_fg,  # type: ignore[attr-defined]
                )
            break

    def _select_card(self, idx: int) -> None:
        prev = self._selected_idx
        self._selected_idx = idx
        if prev is not None and prev != idx:
            self._set_card_hover(prev, False)
        self._set_card_hover(idx, self._hover_card_idx == idx)

    def _selected_index(self) -> int | None:
        return self._selected_idx

    # ── CRUD ────────────────────────────────────────────────────────────

    def _open_advanced_actions(self) -> None:
        from vault_app.app_lifecycle import find_local_uninstaller
        from vault_app.ui.dialogs import AdvancedVaultActionsDialog

        dialog = AdvancedVaultActionsDialog(
            self.root,
            uninstall_available=find_local_uninstaller() is not None,
            show_export_backup=True,
        )
        action = dialog.wait()
        if action == "export":
            self._export_portable_backup()
        elif action == "destroy":
            self._destroy_vault_from_session()
        elif action == "uninstall":
            self._start_uninstall_flow()

    def _export_portable_backup(self) -> None:
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exportar respaldo cifrado",
            defaultextension=PORTABLE_BACKUP_EXTENSION,
            initialfile=portable_backup_suggested_name(),
            filetypes=[
                ("Respaldo cifrado Instanashelock", f"*{PORTABLE_BACKUP_EXTENSION}"),
                ("Vault cifrado", "*.vault"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not destination:
            return

        try:
            export_portable_backup(destination)
        except (ValueError, VaultStorageError, OSError) as exc:
            messagebox.showerror(
                "No se pudo exportar el respaldo",
                str(exc),
                parent=self.root,
            )
            self._set_status("Exportacion fallida", color=C["danger"])
            return

        messagebox.showinfo(
            "Respaldo exportado",
            "Se guardo una copia cifrada del vault.\n\n"
            "Ese archivo sigue protegido y solo puede abrirse con "
            f"{APP_NAME} usando la password correcta.\n\n"
            "La app no lo sube ni lo elimina por ti. Si fue una exportacion "
            "temporal, borralo manualmente.",
            parent=self.root,
        )
        self._set_status("Respaldo cifrado exportado")

    def _start_uninstall_flow(self) -> None:
        from vault_app.app_lifecycle import find_local_uninstaller, launch_local_uninstaller

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

        self._cancel_pending_callbacks()
        self._clear_clipboard_now()
        wipe_secrets(self.key, self.data)
        self.key = None  # type: ignore[assignment]
        self.data = None  # type: ignore[assignment]
        self.root.destroy()

    def _destroy_vault_from_session(self) -> None:
        first = messagebox.askyesno(
            "Destruir vault y datos",
            "Esto eliminara permanentemente tu vault local y\n"
            "todas las passwords guardadas.\n\n"
            "Se eliminara:\n"
            "\u2022 El vault principal\n"
            "\u2022 El backup local\n"
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

        self._cancel_pending_callbacks()
        self._clear_clipboard_now()
        wipe_secrets(self.key, self.data)
        self.key = None  # type: ignore[assignment]
        self.data = None  # type: ignore[assignment]
        delete_vault_files()
        self.reset_to_create_requested = True
        self.root.destroy()

    def _save(self) -> bool:
        try:
            self._vault_fingerprint = save_vault(
                vault_path(),
                self.header,
                self.data,
                self.key,
                expected_fingerprint=self._vault_fingerprint,
            )
        except VaultConflictError as exc:
            self._handle_conflict(str(exc))
            return False
        except VaultStorageError as exc:
            messagebox.showerror(
                "No se pudo guardar",
                str(exc),
                parent=self.root,
            )
            self._set_status("Guardado fallido", color=C["danger"])
            return False
        return True

    def _handle_conflict(self, message: str) -> None:
        should_reload = messagebox.askyesno(
            "Vault desactualizado",
            f"{message}\n\nQuieres recargar la ultima version desde disco ahora?",
            parent=self.root,
        )
        self._enter_stale_mode()
        if should_reload:
            self._reload_from_disk(confirm=False)

    def _ensure_fresh_for_write(self, action_text: str) -> bool:
        if self._stale_requires_reload:
            should_reload = messagebox.askyesno(
                "Recarga requerida",
                "Esta ventana quedo desactualizada frente al vault en disco.\n\n"
                f"Para {action_text} necesitas recargar primero.\n\n"
                "Quieres recargar la ultima version ahora?",
                parent=self.root,
            )
            if should_reload:
                return self._reload_from_disk(confirm=False)
            self._enter_stale_mode()
            return False

        current = current_vault_fingerprint(vault_path())
        if self._vault_fingerprint is not None and current != self._vault_fingerprint:
            should_reload = messagebox.askyesno(
                "Vault desactualizado",
                "Esta ventana ya no coincide con la ultima version guardada en disco.\n\n"
                f"Para {action_text} debes recargar primero y evitar merges ambiguos.\n\n"
                "Quieres recargar la ultima version ahora?",
                parent=self.root,
            )
            self._enter_stale_mode()
            if should_reload:
                return self._reload_from_disk(confirm=False)
            return False

        return True

    def _enter_stale_mode(self) -> None:
        self._stale_requires_reload = True
        if self._new_entry_btn is not None:
            self._new_entry_btn.config(state="disabled")
        if self._recovery_btn is not None:
            self._recovery_btn.config(state="disabled")
        if self._reload_btn is not None:
            self._reload_btn.config(
                bg=C["danger"],
                fg="white",
                activebackground=C["danger"],
                activeforeground="white",
            )
        self._set_status(
            "Esta ventana quedo desactualizada. Recarga desde disco para seguir editando con seguridad.",
            color=C["danger"],
            persist=True,
            force=True,
        )

    def _exit_stale_mode(self) -> None:
        self._stale_requires_reload = False
        if self._new_entry_btn is not None:
            self._new_entry_btn.config(state="normal")
        if self._recovery_btn is not None:
            self._recovery_btn.config(state="normal")
        if self._reload_btn is not None:
            self._reload_btn.config(
                bg=C["surface"],
                fg=C["accent2"],
                activebackground=C["hover"],
                activeforeground=C["text"],
            )

    def _reload_from_disk(self, *, confirm: bool = True) -> bool:
        if confirm:
            should_reload = messagebox.askyesno(
                "Recargar desde disco",
                "Se volvera a leer el vault desde disco y esta ventana mostrara "
                "la ultima version guardada.\n\nContinuar?",
                parent=self.root,
            )
            if not should_reload:
                return False

        try:
            header, data, fingerprint = load_unlocked_vault(vault_path(), self.key)
        except InvalidTag:
            messagebox.showerror(
                "No se pudo recargar",
                "El vault actual ya no se puede abrir con la clave en memoria. "
                "Bloquea y vuelve a abrir la aplicacion.",
                parent=self.root,
            )
            self._set_status("Recarga fallida", color=C["danger"])
            return False
        except (ValueError, VaultStorageError, OSError) as exc:
            messagebox.showerror(
                "No se pudo recargar",
                str(exc),
                parent=self.root,
            )
            self._set_status("Recarga fallida", color=C["danger"])
            return False

        self._clear_clipboard_now()
        self.header = header
        self.data = data
        self._vault_fingerprint = fingerprint
        self._exit_stale_mode()
        self._selected_idx = None
        self._hover_card_idx = None
        self._refresh_list()
        self._set_status("Vault recargado desde disco", force=True)
        return True

    def _add_entry(self) -> None:
        if not self._ensure_fresh_for_write("crear una nueva entrada"):
            return
        AddEntryDialog(self.root, self._on_add)

    def _on_add(self, service: str, username: str, password: str, notes: str) -> None:
        self.data["entries"].append({
            "service": service,
            "username": username,
            "password": password,
            "notes": notes,
        })
        if not self._save():
            self.data["entries"].pop()
            return
        self._refresh_list()
        self._set_status(f"'{service}' guardado")

    def _edit_entry_at(self, idx: int) -> None:
        if not self._ensure_fresh_for_write("editar una entrada"):
            return
        entry = self.data["entries"][idx]
        AddEntryDialog(
            self.root,
            lambda s, u, p, n: self._on_edit(idx, s, u, p, n),
            mode="edit", initial=entry,
        )

    def _on_edit(self, idx: int, service: str, username: str, password: str, notes: str) -> None:
        previous = self.data["entries"][idx]
        self.data["entries"][idx] = {
            "service": service,
            "username": username,
            "password": password,
            "notes": notes,
        }
        if not self._save():
            self.data["entries"][idx] = previous
            return
        self._refresh_list()
        self._set_status(f"'{service}' actualizado")

    def _delete_entry_at(self, idx: int) -> None:
        if not self._ensure_fresh_for_write("eliminar una entrada"):
            return
        entry = self.data["entries"][idx]
        if messagebox.askyesno(
            "Eliminar",
            f"Eliminar '{entry['service']}'?\nEsta accion es permanente.",
            parent=self.root,
        ):
            deleted_entry = self.data["entries"][idx]
            del self.data["entries"][idx]
            self._selected_idx = None
            if not self._save():
                self.data["entries"].insert(idx, deleted_entry)
                self._selected_idx = idx
                return
            self._refresh_list()
            self._set_status("Entrada eliminada")

    # ── Clipboard ───────────────────────────────────────────────────────

    def _clear_clipboard_now(self) -> None:
        self._clipboard.clear_now()

    def _copy_password_at(self, idx: int) -> None:
        pw = self.data["entries"][idx]["password"]
        self._clipboard.copy(pw, ttl_ms=CLIPBOARD_CLEAR_MS, on_clear=self._auto_clear)
        self._set_status("Copiado \u2014 se borra en 30s")

    def _auto_clear(self) -> None:
        self._set_status("Clipboard limpiado", color=C["warn"])

    def _show_password_at(self, idx: int) -> None:
        entry = self.data["entries"][idx]

        def on_edit():
            self._edit_entry_at(idx)

        def on_copy(pw: str):
            self._clipboard.copy(pw, ttl_ms=CLIPBOARD_CLEAR_MS, on_clear=self._auto_clear)
            self._set_status("Copiado \u2014 se borra en 30s")

        ShowPasswordDialog(
            self.root, entry,
            auto_close_ms=REVEAL_CLEAR_MS,
            on_edit=on_edit,
            on_copy=on_copy,
        )

    # ── Recovery regeneration ───────────────────────────────────────────

    def _regenerate_recovery(self) -> None:
        from vault_app.storage import setup_recovery
        from vault_app.ui.dialogs import RecoveryCodesDialog

        if not self._ensure_fresh_for_write("actualizar recovery"):
            return

        if self.header.has_recovery:
            msg = "Esto invalida los codigos de recuperacion anteriores.\nContinuar?"
            title = "Regenerar Recovery"
        else:
            msg = "Esto generara codigos de emergencia para recuperar tu vault.\nContinuar?"
            title = "Activar Recovery"

        if not messagebox.askyesno(title, msg, parent=self.root):
            return

        try:
            self.header, display_codes, self._vault_fingerprint = setup_recovery(
                vault_path(),
                self.header,
                self.data,
                self.key,
                expected_fingerprint=self._vault_fingerprint,
            )
        except VaultConflictError as exc:
            self._handle_conflict(str(exc))
            return
        except VaultStorageError as exc:
            messagebox.showerror(
                "No se pudo actualizar recovery",
                str(exc),
                parent=self.root,
            )
            self._set_status("Recovery no actualizado", color=C["danger"])
            return
        dialog = RecoveryCodesDialog(self.root, display_codes)
        dialog.wait()
        self._recovery_btn.config(text="\U0001f511 Recovery")
        self._set_status("Recovery keys configurados")

    # ── Status bar ──────────────────────────────────────────────────────

    def _set_status(
        self,
        msg: str,
        color: str | None = None,
        *,
        persist: bool = False,
        force: bool = False,
    ) -> None:
        if self._stale_requires_reload and not force:
            return
        if self._status_clear_id:
            try:
                self.root.after_cancel(self._status_clear_id)
            except Exception:
                pass
            self._status_clear_id = None
        self.status_var.set(msg)
        self._status_label.config(fg=color or C["green"])
        if not persist:
            self._status_clear_id = self.root.after(4000, self._clear_status)

    def _clear_status(self) -> None:
        self._status_clear_id = None
        if self._stale_requires_reload:
            return
        self.status_var.set("")
        self._status_label.config(fg=C["green"])
