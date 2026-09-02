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
FORBIDDEN_PNG_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"eXIf"}


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


def png_chunks(payload: bytes) -> list[bytes]:
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG signature")

    chunks: list[bytes] = []
    offset = 8
    while offset + 12 <= len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(payload):
            raise ValueError("Truncated PNG chunk")
        chunks.append(chunk_type)
        offset = chunk_end
        if chunk_type == b"IEND":
            break
    if not chunks or chunks[-1] != b"IEND" or offset != len(payload):
        raise ValueError("Incomplete PNG payload")
    return chunks


def normalized_png(payload: bytes) -> tuple[int, int, bytes]:
    chunks = png_chunks(payload)
    if FORBIDDEN_PNG_CHUNKS.intersection(chunks):
        raise ValueError("PNG contains textual or EXIF metadata")

    image = QImage()
    if not image.loadFromData(QByteArray(payload), "PNG"):
        raise ValueError("Could not decode PNG payload")
    normalized = image.convertToFormat(QImage.Format_RGBA8888)
    return normalized.width(), normalized.height(), bytes(normalized.constBits())


def normalized_ico(payload: bytes) -> tuple[tuple[int, int, bytes], ...]:
    if len(payload) < 6:
        raise ValueError("Truncated ICO header")
    reserved, image_type, count = struct.unpack("<HHH", payload[:6])
    if reserved != 0 or image_type != 1 or count != len(ICO_SIZES):
        raise ValueError("Unexpected ICO header")

    images: list[tuple[int, int, bytes]] = []
    for index, expected_size in enumerate(ICO_SIZES):
        entry_offset = 6 + (16 * index)
        entry = payload[entry_offset : entry_offset + 16]
        if len(entry) != 16:
            raise ValueError("Truncated ICO directory")
        width, height, colors, reserved_byte, planes, bits, length, offset = struct.unpack(
            "<BBBBHHII", entry
        )
        decoded_width = 256 if width == 0 else width
        decoded_height = 256 if height == 0 else height
        if (
            decoded_width != expected_size
            or decoded_height != expected_size
            or colors != 0
            or reserved_byte != 0
            or planes != 1
            or bits != 32
            or offset + length > len(payload)
        ):
            raise ValueError("Unexpected ICO directory entry")
        images.append(normalized_png(payload[offset : offset + length]))
    return tuple(images)


def derivative_matches(path: Path, committed: bytes, generated: bytes) -> bool:
    """Compare visual content while ignoring environment-specific PNG compression."""

    try:
        if path.suffix.lower() == ".png":
            return normalized_png(committed) == normalized_png(generated)
        if path.suffix.lower() == ".ico":
            return normalized_ico(committed) == normalized_ico(generated)
    except ValueError:
        return False
    return committed == generated


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
            if (
                not path.is_file()
                or not derivative_matches(path, path.read_bytes(), expected)
            ):
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
