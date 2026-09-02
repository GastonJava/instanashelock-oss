"""Small helpers for local install / uninstall lifecycle flows."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def find_local_uninstaller() -> str | None:
    """Return the adjacent Inno Setup uninstaller when available."""
    candidates: list[Path] = []

    executable = getattr(sys, "executable", None)
    if executable:
        candidates.append(Path(executable).resolve().with_name("unins000.exe"))

    argv0 = sys.argv[0] if sys.argv else None
    if argv0:
        candidates.append(Path(argv0).resolve().with_name("unins000.exe"))

    seen: set[str] = set()
    for candidate in candidates:
        raw = str(candidate)
        if raw in seen:
            continue
        seen.add(raw)
        if candidate.is_file():
            return raw
    return None


def launch_local_uninstaller(path: str | None = None) -> str:
    """Launch the local uninstaller and return the path used."""
    uninstaller = path or find_local_uninstaller()
    if not uninstaller:
        raise FileNotFoundError("No hay desinstalador local disponible.")

    subprocess.Popen([uninstaller])
    return uninstaller
