from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_original_asset_sources_are_present_and_marked() -> None:
    svg_sources = [
        ROOT / "assets" / "app" / "instanashelock_icon.svg",
        ROOT / "assets" / "v2" / "auth" / "common" / "vault_artwork.svg",
        ROOT / "assets" / "v2" / "auth" / "common" / "help_icon.svg",
        ROOT / "assets" / "v2" / "auth" / "common" / "settings_icon.svg",
    ]

    for path in svg_sources:
        assert path.is_file()
        assert 'data-origin="instanashelock-project"' in path.read_text(encoding="utf-8")


def test_application_icon_derivatives_are_present() -> None:
    assert (ROOT / "assets" / "app" / "instanashelock_icon.png").is_file()
    assert (ROOT / "assets" / "app" / "instanashelock.ico").is_file()


def test_original_assets_load_with_the_runtime_image_stack() -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QImageReader
    from PySide6.QtSvg import QSvgRenderer

    for path in (ROOT / "assets").rglob("*.svg"):
        assert QSvgRenderer(str(path)).isValid(), path

    for relative_path in (
        "assets/app/instanashelock_icon.png",
        "assets/app/instanashelock.ico",
    ):
        reader = QImageReader(str(ROOT / relative_path))
        assert reader.canRead(), relative_path
        assert not reader.read().isNull(), relative_path


def test_qml_references_only_the_original_asset_layout() -> None:
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src" / "vault_app_v2" / "qml").rglob("*.qml")
    )
    assert "assets/v2/auth/common/" in qml_text
    assert "assets/app/instanashelock_icon.svg" in qml_text
