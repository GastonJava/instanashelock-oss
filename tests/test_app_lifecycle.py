"""Focused tests for uninstall helper discovery."""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_find_local_uninstaller_returns_adjacent_file(tmp_path, monkeypatch):
    from vault_app import app_lifecycle

    exe_path = tmp_path / "instanashelock.exe"
    uninstaller = tmp_path / "unins000.exe"
    exe_path.write_bytes(b"")
    uninstaller.write_bytes(b"")

    monkeypatch.setattr(app_lifecycle.sys, "executable", str(exe_path))
    monkeypatch.setattr(app_lifecycle.sys, "argv", [str(exe_path)])

    assert app_lifecycle.find_local_uninstaller() == str(uninstaller.resolve())


def test_find_local_uninstaller_returns_none_when_missing(tmp_path, monkeypatch):
    from vault_app import app_lifecycle

    exe_path = tmp_path / "instanashelock.exe"
    exe_path.write_bytes(b"")

    monkeypatch.setattr(app_lifecycle.sys, "executable", str(exe_path))
    monkeypatch.setattr(app_lifecycle.sys, "argv", [str(exe_path)])

    assert app_lifecycle.find_local_uninstaller() is None


def test_launch_local_uninstaller_uses_detected_path(tmp_path, monkeypatch):
    from vault_app import app_lifecycle

    exe_path = tmp_path / "instanashelock.exe"
    uninstaller = tmp_path / "unins000.exe"
    exe_path.write_bytes(b"")
    uninstaller.write_bytes(b"")

    monkeypatch.setattr(app_lifecycle.sys, "executable", str(exe_path))
    monkeypatch.setattr(app_lifecycle.sys, "argv", [str(exe_path)])

    seen: list[list[str]] = []

    def fake_popen(cmd):
        seen.append(cmd)
        class _DummyProcess:
            pass
        return _DummyProcess()

    monkeypatch.setattr(app_lifecycle.subprocess, "Popen", fake_popen)

    launched = app_lifecycle.launch_local_uninstaller()

    assert launched == str(uninstaller.resolve())
    assert seen == [[str(uninstaller.resolve())]]
