# Changelog

This file distinguishes the public open-source history from earlier private
development. Dates and version labels in the pre-OSS section are engineering
records, not claims of public releases.

## Public OSS history

### Unreleased

- Prepared the clean open-source source snapshot.
- Added public licensing, security, maintenance, and contribution policies.
- Added reproducible local validation and GitHub Actions configuration.
- Documented the repository as a dual-track project: stable Tkinter v1 and
  actively developed PySide6/QML v2.
- Kept v2 explicitly at `2.0.0a0`; it is not presented as production-ready or
  as a replacement for v1.

No public tag or GitHub release exists yet.

## Pre-OSS / private development history

### v1.0.0 local milestone — 2026-04-07

The stable Tkinter application reached an internally validated local build
milestone during private development. That milestone included the encrypted
vault core, recovery flows, backup and migration handling, local tests, a
Nuitka build, and an Inno Setup installer smoke test.

This was not a public release, public tag, or public repository state. Its
technical record is preserved in
[`docs/v1_closeout.md`](docs/v1_closeout.md) and
[`docs/release_smoke_test_note.md`](docs/release_smoke_test_note.md).
