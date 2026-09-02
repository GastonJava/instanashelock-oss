# Third-Party Notices

Instanashelock's own source code, documentation, and project-owned visual
assets are licensed under the repository's MIT License. Dependencies, build
tools, and their bundled components remain under their respective licenses;
the MIT License does not relicense them.

This is a practical inventory of direct declared dependencies, not a legal
opinion or a substitute for reviewing the exact packages included in a release.

| Component | Role | Upstream license information |
| --- | --- | --- |
| `cryptography` | Runtime cryptographic primitives | Apache-2.0 OR BSD-3-Clause |
| `argon2-cffi` | Runtime Argon2id bindings | MIT |
| `pyperclip` | Runtime clipboard integration | BSD |
| `PySide6`, `shiboken6`, and Qt | v2 UI runtime | LGPL-3.0-only OR applicable GPL/commercial terms, plus component-specific notices |
| `pytest` | Development and tests | MIT |
| `pip-audit` | Development dependency audit | Apache-2.0 |
| `Nuitka` | Build tool | AGPL-3.0 with the upstream Nuitka Runtime Library Exception for generated target code |
| `ordered-set` | Nuitka build dependency | MIT |

The licenses above were checked against installed package metadata and upstream
project documentation during OSS preparation. The generated local inventory in
[`docs/dependency_audit.md`](docs/dependency_audit.md) records resolved versions
and transitive packages for the reviewed environment.

## Binary distribution

Before distributing a Windows executable or installer:

1. generate an inventory from the exact clean build environment;
2. inspect which third-party libraries Nuitka actually included;
3. include the corresponding copyright and license notices;
4. satisfy Qt/PySide6 LGPL, GPL, or commercial-license obligations for every Qt
   component that is distributed;
5. retain the Nuitka runtime exception and other notices required by components
   present in the produced artifact.

The current v1 build does not intentionally import PySide6, while v2 does. The
contents of the actual build artifact, rather than that design intention, are
authoritative for release compliance.
