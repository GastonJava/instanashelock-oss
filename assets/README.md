# Asset provenance and licensing

All visual assets currently tracked in this repository were created
specifically for Instanashelock using original vector geometry. The repository
does not contain third-party character, game, fan-art, photograph, logo, or icon
pack material.

Unless a file states otherwise, the project-owned assets listed here are
distributed under the same [MIT License](../LICENSE) as the repository's own
source code and documentation. This statement does not claim ownership of
third-party trademarks, dependencies, fonts, or platform artwork.

## Source artwork

| Asset | Provenance | Method |
| --- | --- | --- |
| `assets/app/instanashelock_icon.svg` | Created specifically for Instanashelock | Original geometric SVG: abstract circular vault and lock |
| `assets/v2/auth/common/vault_artwork.svg` | Created specifically for Instanashelock | Original geometric SVG: abstract vault and grid |
| `assets/v2/auth/common/help_icon.svg` | Created specifically for Instanashelock | Original geometric help icon |
| `assets/v2/auth/common/settings_icon.svg` | Created specifically for Instanashelock | Original geometric settings icon |

Each SVG contains `data-origin="instanashelock-project"` and readable metadata.
These SVG files are the editable source artwork and the versioned source of
truth.

## Reproducible derivatives

| Derivative | Source | Generator | Use |
| --- | --- | --- | --- |
| `assets/app/instanashelock_icon.png` | `assets/app/instanashelock_icon.svg` | `scripts/generate_assets.py` | Reference raster icon |
| `assets/app/instanashelock.ico` | `assets/app/instanashelock_icon.svg` | `scripts/generate_assets.py` | Windows executable and installer |

The generator renders the SVG through `PySide6.QtSvg` and creates the
multi-resolution ICO from those rendered PNG frames:

```powershell
python .\scripts\generate_assets.py
python .\scripts\generate_assets.py --check
```

The QML interface consumes the SVG sources directly. The recovery button is
drawn with native QML rectangles, gradients, and borders rather than an image
skin.

## New assets

A new asset must include an editable source and documented provenance. Assets
with uncertain redistribution rights are rejected or replaced with original
project artwork. A contributor must not submit third-party trademarks or
artwork without explicit, compatible licensing and attribution information.
