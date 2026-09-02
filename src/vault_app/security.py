"""
Operational security helpers: memory wipe, smart clipboard, rate limiter.
"""

from __future__ import annotations

import ctypes
import gc
import hashlib
import sys
import time
from collections.abc import Callable


# ── Memory wipe (best-effort) ──────────────────────────────────────────────


def wipe_bytes(b: bytes | bytearray | None) -> None:
    """Overwrite the internal buffer of *b* with zeros.  CPython-specific, best-effort."""
    if b is None or len(b) == 0:
        return
    try:
        if isinstance(b, bytearray):
            for i in range(len(b)):
                b[i] = 0
        else:
            # bytes objects are immutable but we can reach the buffer via ctypes
            buf_offset = sys.getsizeof(b"") - 1  # offset to the internal ob_sval
            ctypes.memset(id(b) + buf_offset, 0, len(b))
    except Exception:
        pass


def wipe_secrets(key: bytes | None, data: dict | None) -> None:
    """Best-effort wipe of the master key and all passwords held in *data*."""
    wipe_bytes(key)
    if data:
        for entry in data.get("entries", []):
            for k in list(entry.keys()):
                entry[k] = ""
        data.clear()
    gc.collect()


# ── Smart clipboard ─────────────────────────────────────────────────────────


class ClipboardGuard:
    """Tracks what we put on the clipboard so we only clear our own content."""

    def __init__(self) -> None:
        self._hash: bytes | None = None

    def mark(self, text: str) -> None:
        self._hash = hashlib.sha256(text.encode("utf-8")).digest()

    def should_clear(self, current_text: str) -> bool:
        if self._hash is None:
            return False
        return hashlib.sha256(current_text.encode("utf-8")).digest() == self._hash

    def reset(self) -> None:
        self._hash = None


def set_clipboard_text(text: str, *, widget=None) -> None:
    """Copy text to the clipboard using pyperclip when available."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return
    except Exception:
        if widget is None:
            raise

    widget.clipboard_clear()
    widget.clipboard_append(text)


def get_clipboard_text(*, widget=None) -> str:
    """Read clipboard text using pyperclip when available."""
    try:
        import pyperclip

        return pyperclip.paste()
    except Exception:
        if widget is None:
            raise

    return widget.clipboard_get()


class ManagedClipboard:
    """Clipboard helper that only clears content previously copied by the app."""

    def __init__(
        self,
        schedule: Callable[[int, Callable[[], None]], object],
        cancel: Callable[[object], None],
        *,
        widget=None,
        copy_text: Callable[[str], None] | None = None,
        read_text: Callable[[], str] | None = None,
    ) -> None:
        self._schedule = schedule
        self._cancel = cancel
        self._widget = widget
        self._copy_text = copy_text or (lambda text: set_clipboard_text(text, widget=widget))
        self._read_text = read_text or (lambda: get_clipboard_text(widget=widget))
        self._guard = ClipboardGuard()
        self._timer_id: object | None = None
        self._on_clear: Callable[[], None] | None = None

    def copy(self, text: str, *, ttl_ms: int, on_clear: Callable[[], None] | None = None) -> None:
        self._copy_text(text)
        self._guard.mark(text)
        self.cancel_timer()
        self._on_clear = on_clear
        self._timer_id = self._schedule(ttl_ms, self._clear_on_timeout)

    def clear_now(self, *, notify: bool = False) -> None:
        callback = self._on_clear if notify else None
        self._on_clear = None
        try:
            current = self._read_text()
        except Exception:
            current = None

        try:
            if current is not None and self._guard.should_clear(current):
                self._copy_text("")
        except Exception:
            pass
        finally:
            self._guard.reset()
            self.cancel_timer()

        if callback is not None:
            callback()

    def cancel_timer(self) -> None:
        if self._timer_id is not None:
            try:
                self._cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

    def _clear_on_timeout(self) -> None:
        self._timer_id = None
        self.clear_now(notify=True)


# ── Rate limiter ────────────────────────────────────────────────────────────


class RateLimiter:
    """Exponential back-off after failed unlock attempts."""

    MAX_DELAY = 30  # seconds

    def __init__(self) -> None:
        self._failures = 0
        self._locked_until: float = 0.0

    def record_failure(self) -> float:
        """Record a failed attempt and return the cooldown in seconds."""
        self._failures += 1
        delay = min(2 ** self._failures, self.MAX_DELAY)
        self._locked_until = time.monotonic() + delay
        return delay

    def record_success(self) -> None:
        self._failures = 0
        self._locked_until = 0.0

    @property
    def failures(self) -> int:
        return self._failures

    @property
    def seconds_remaining(self) -> float:
        return max(0.0, self._locked_until - time.monotonic())

    @property
    def is_locked(self) -> bool:
        return time.monotonic() < self._locked_until
