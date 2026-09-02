"""
Password strength indicator — entropy-based Canvas bar.
"""

from __future__ import annotations

import math
import string
import tkinter as tk

from vault_app.ui.theme import C

# Thresholds in bits of entropy
_THRESHOLDS = [
    (80, "#2ecc71", "Fuerte"),
    (60, "#f1c40f", "Buena"),
    (40, "#e67e22", "Aceptable"),
    (0,  "#c0392b", "Debil"),
]


def _estimate_entropy(password: str) -> float:
    if not password:
        return 0.0
    pool = 0
    if any(c in string.ascii_lowercase for c in password):
        pool += 26
    if any(c in string.ascii_uppercase for c in password):
        pool += 26
    if any(c in string.digits for c in password):
        pool += 10
    if any(c in string.punctuation for c in password):
        pool += 32
    if pool == 0:
        pool = 128  # unicode fallback
    return len(password) * math.log2(pool)


class StrengthBar(tk.Canvas):
    """Thin bar that reflects estimated password entropy."""

    def __init__(self, parent: tk.Widget, *, width: int = 300, height: int = 8) -> None:
        super().__init__(parent, width=width, height=height,
                         bg=C["bg"], highlightthickness=0, bd=0)
        self._width = width
        self._height = height
        self._label: tk.Label | None = None

    def pack(self, **kw) -> None:  # type: ignore[override]
        super().pack(**kw)
        if self._label is None:
            self._label = tk.Label(self.master, text="", font=("Segoe UI", 8),
                                   bg=C["bg"], fg=C["muted"])
            self._label.pack(anchor="w", padx=kw.get("padx", 0))

    def update(self, password: str) -> None:  # type: ignore[override]
        bits = _estimate_entropy(password)
        self.delete("all")

        ratio = min(bits / 120, 1.0)
        fill_w = int(self._width * ratio)

        color = _THRESHOLDS[-1][1]
        label = _THRESHOLDS[-1][2]
        for threshold, col, lbl in _THRESHOLDS:
            if bits >= threshold:
                color, label = col, lbl
                break

        self.create_rectangle(0, 0, self._width, self._height, fill=C["surface"], outline="")
        if fill_w > 0:
            self.create_rectangle(0, 0, fill_w, self._height, fill=color, outline="")

        if self._label:
            self._label.config(text=f"{label} ({int(bits)} bits)", fg=color)
