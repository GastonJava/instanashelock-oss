from __future__ import annotations

import sys

try:
    from vault_app_v2.app import main
except ImportError as exc:  # pragma: no cover - friendly runtime path
    raise SystemExit(
        "PySide6 is required to run Instanashelock 2.0. "
        "Install requirements/dev.txt first."
    ) from exc


if __name__ == "__main__":
    sys.exit(main())
