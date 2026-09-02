"""Generate deterministic application-icon derivatives from project-owned SVG."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "app" / "instanashelock_icon.svg"
PNG_OUTPUT = ROOT / "assets" / "app" / "instanashelock_icon.png"
ICO_OUTPUT = ROOT / "assets" / "app" / "instanashelock.ico"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(size: int) -> bytes:
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG source: {SOURCE}")

    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()

    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.WriteOnly):
        raise RuntimeError("Could not open PNG buffer")
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Could not encode {size}x{size} PNG")
    buffer.close()
    return bytes(data)


def build_ico() -> bytes:
    images = [(size, render_png(size)) for size in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + (16 * len(images))
    entries: list[bytes] = []
    payloads: list[bytes] = []

    for size, payload in images:
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    return header + b"".join(entries) + b"".join(payloads)


def expected_outputs() -> dict[Path, bytes]:
    return {
        PNG_OUTPUT: render_png(512),
        ICO_OUTPUT: build_ico(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that committed derivatives match the SVG source",
    )
    args = parser.parse_args()

    failures: list[Path] = []
    for path, expected in expected_outputs().items():
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                failures.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
            print(f"Wrote {path.relative_to(ROOT)}")

    if failures:
        for path in failures:
            print(f"Outdated derivative: {path.relative_to(ROOT)}")
        return 1

    if args.check:
        print("Asset derivatives match project-owned SVG sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
