# Dependency Audit

Inventario local reproducible del entorno revisado para desarrollo y release de Instanashelock.

## Direct requirements

### Runtime

| Requirement | Resolved | License | Summary |
| --- | --- | --- | --- |
| `cryptography>=43.0` | `50.0.1` | Apache-2.0 OR BSD-3-Clause | cryptography is a package which provides cryptographic recipes and primitives to Python developers. |
| `argon2-cffi>=23.1` | `25.1.0` | MIT | Argon2 for Python |
| `pyperclip>=1.9` | `1.11.0` | BSD | A cross-platform clipboard module for Python. (Only handles plain text for now.) |
| `PySide6>=6.8` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework |

### Development

| Requirement | Resolved | License | Summary |
| --- | --- | --- | --- |
| `cryptography>=43.0` | `50.0.1` | Apache-2.0 OR BSD-3-Clause | cryptography is a package which provides cryptographic recipes and primitives to Python developers. |
| `argon2-cffi>=23.1` | `25.1.0` | MIT | Argon2 for Python |
| `pyperclip>=1.9` | `1.11.0` | BSD | A cross-platform clipboard module for Python. (Only handles plain text for now.) |
| `PySide6>=6.8` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework |
| `pytest>=8.0` | `9.1.1` | MIT | pytest: simple powerful testing with Python |

### Build

| Requirement | Resolved | License | Summary |
| --- | --- | --- | --- |
| `cryptography>=43.0` | `50.0.1` | Apache-2.0 OR BSD-3-Clause | cryptography is a package which provides cryptographic recipes and primitives to Python developers. |
| `argon2-cffi>=23.1` | `25.1.0` | MIT | Argon2 for Python |
| `pyperclip>=1.9` | `1.11.0` | BSD | A cross-platform clipboard module for Python. (Only handles plain text for now.) |
| `PySide6>=6.8` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Python bindings for the Qt cross-platform application and UI framework |
| `nuitka>=2.1` | `4.2` | GNU Affero General Public License v3 | Python compiler with full language support and CPython compatibility |
| `ordered-set>=4.1` | `4.1.0` | (not declared in package metadata) | An OrderedSet is a custom MutableSet that remembers its order, so that every |

### Installed inventory

| Package | Version | License |
| --- | --- | --- |
| `argon2-cffi` | `25.1.0` | MIT |
| `argon2-cffi-bindings` | `26.1.0` | MIT |
| `boolean.py` | `5.0` | BSD-2-Clause |
| `CacheControl` | `0.14.4` | Apache-2.0 |
| `certifi` | `2026.7.22` | MPL-2.0 |
| `cffi` | `2.1.1` | MIT-0 |
| `charset-normalizer` | `3.5.1` | MIT |
| `colorama` | `0.4.6` |  |
| `cryptography` | `50.0.1` | Apache-2.0 OR BSD-3-Clause |
| `cyclonedx-python-lib` | `11.12.0` | Apache-2.0 |
| `defusedxml` | `0.7.1` | PSFL |
| `filelock` | `3.32.5` | MIT |
| `idna` | `3.19` | BSD-3-Clause |
| `iniconfig` | `2.3.0` | MIT |
| `license-expression` | `30.4.4` | Apache-2.0 |
| `markdown-it-py` | `4.2.0` |  |
| `mdurl` | `0.1.2` |  |
| `msgpack` | `1.2.2` | Apache-2.0 |
| `Nuitka` | `4.2` | GNU Affero General Public License v3 |
| `ordered-set` | `4.1.0` |  |
| `packageurl-python` | `0.17.6` | MIT |
| `packaging` | `26.3` | Apache-2.0 OR BSD-2-Clause |
| `pip` | `26.2.1` | MIT |
| `pip-api` | `0.0.34` |  |
| `pip_audit` | `2.10.1` |  |
| `pip-requirements-parser` | `32.0.1` | MIT |
| `platformdirs` | `4.11.7` | MIT |
| `pluggy` | `1.6.0` | MIT |
| `py-serializable` | `2.1.0` | Apache-2.0 |
| `pycparser` | `3.0` | BSD-3-Clause |
| `Pygments` | `2.21.0` | BSD-2-Clause |
| `pyparsing` | `3.3.2` | MIT |
| `pyperclip` | `1.11.0` | BSD |
| `PySide6` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| `PySide6_Addons` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| `PySide6_Essentials` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| `pytest` | `9.1.1` | MIT |
| `requests` | `2.34.2` | Apache-2.0 |
| `rich` | `15.0.0` | MIT |
| `shiboken6` | `6.11.2` | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| `sortedcontainers` | `2.4.0` | Apache 2.0 |
| `tomli` | `2.4.1` | MIT |
| `tomli_w` | `1.2.0` |  |
| `typing_extensions` | `4.16.0` | PSF-2.0 |
| `urllib3` | `2.7.0` | MIT |

## Findings

- Todas las dependencias runtime declaradas estan presentes en el venv local.
- Las dependencias runtime usan minimos (`>=`) y no estan pinneadas; el entorno no es totalmente reproducible todavia.
- Este archivo es un inventario del entorno que lo genero. La verificacion de advisories se ejecuta por separado con `python -m pip_audit -r requirements\audit.txt`.
- Las licencias se leen de `License-Expression` o `License` en los metadatos instalados. Un campo vacio requiere consultar la distribucion upstream.
- La licencia MIT de Instanashelock no relicencia dependencias ni herramientas de build; consulte `THIRD_PARTY_NOTICES.md`.

## Regeneration

```powershell
.\scripts\audit.ps1
```

La regeneracion tambien ejecuta `pip-audit`; un resultado limpio no garantiza ausencia de vulnerabilidades.
