"""Unit tests for security helpers."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.security import ClipboardGuard, ManagedClipboard, RateLimiter, wipe_bytes


class _FakeScheduler:
    def __init__(self) -> None:
        self._callbacks: dict[int, object] = {}
        self._next_id = 1

    def after(self, _delay_ms: int, callback) -> int:
        token = self._next_id
        self._next_id += 1
        self._callbacks[token] = callback
        return token

    def after_cancel(self, token: int) -> None:
        self._callbacks.pop(token, None)

    def run(self, token: int) -> None:
        callback = self._callbacks.pop(token)
        callback()


class TestClipboardGuard:
    def test_marks_and_matches(self):
        g = ClipboardGuard()
        g.mark("secret123")
        assert g.should_clear("secret123")
        assert not g.should_clear("something-else")

    def test_reset_clears_state(self):
        g = ClipboardGuard()
        g.mark("abc")
        g.reset()
        assert not g.should_clear("abc")

    def test_empty_guard(self):
        g = ClipboardGuard()
        assert not g.should_clear("anything")


class TestRateLimiter:
    def test_exponential_backoff(self):
        r = RateLimiter()
        d1 = r.record_failure()
        d2 = r.record_failure()
        d3 = r.record_failure()
        assert d1 == 2
        assert d2 == 4
        assert d3 == 8

    def test_max_delay(self):
        r = RateLimiter()
        for _ in range(20):
            d = r.record_failure()
        assert d <= RateLimiter.MAX_DELAY

    def test_success_resets(self):
        r = RateLimiter()
        r.record_failure()
        r.record_failure()
        r.record_success()
        assert not r.is_locked
        d = r.record_failure()
        assert d == 2


class TestManagedClipboard:
    def test_timeout_clears_only_owned_content(self):
        scheduler = _FakeScheduler()
        state = {"text": ""}
        cleared: list[str] = []
        clipboard = ManagedClipboard(
            scheduler.after,
            scheduler.after_cancel,
            copy_text=lambda text: state.__setitem__("text", text),
            read_text=lambda: state["text"],
        )

        clipboard.copy("secret123", ttl_ms=30_000, on_clear=lambda: cleared.append("done"))

        assert state["text"] == "secret123"
        scheduler.run(1)

        assert state["text"] == ""
        assert cleared == ["done"]

    def test_timeout_preserves_external_clipboard_changes(self):
        scheduler = _FakeScheduler()
        state = {"text": ""}
        clipboard = ManagedClipboard(
            scheduler.after,
            scheduler.after_cancel,
            copy_text=lambda text: state.__setitem__("text", text),
            read_text=lambda: state["text"],
        )

        clipboard.copy("secret123", ttl_ms=30_000)
        state["text"] = "user-overrode-this"
        scheduler.run(1)

        assert state["text"] == "user-overrode-this"


class TestWipeBytes:
    def test_wipe_bytearray(self):
        ba = bytearray(b"secret-key-material")
        wipe_bytes(ba)
        assert all(b == 0 for b in ba)

    def test_wipe_none_is_safe(self):
        wipe_bytes(None)

    def test_wipe_empty_is_safe(self):
        wipe_bytes(b"")
        wipe_bytes(bytearray())
