# Instanashelock

Instanashelock is a local-first password manager for Windows built in Python.
It encrypts vault data with AES-256-GCM and derives password-based keys with
Argon2id.

The application is intended for local vault storage. It does not provide cloud
sync, browser autofill, account recovery by a service operator, or protection
from a compromised operating system.

## Status

- **v1** is the current stable local application, implemented with Tkinter.
- **v2** is an ongoing PySide6/QML rework. It reuses the existing vault core but
  is not yet a replacement for v1.
- No public versioned release has been published from this repository yet.

This open-source repository begins with a clean source snapshot prepared from
earlier private development. That private engineering history predates this Git
repository and is intentionally not included in its ancestry. The single root
commit must not be interpreted as the project's complete development history.
Documents labeled **pre-OSS** or **pre-open-source** preserve useful private
engineering milestones; they do not describe earlier public releases.

## Security model

The current vault implementation includes:

- AES-256-GCM authenticated encryption with a fresh nonce for each operation;
- Argon2id password-based key derivation;
- authenticated vault metadata using additional authenticated data (AAD);
- a random vault master key wrapped separately for password and optional
  recovery access;
- atomic writes, a local encrypted backup, and migration handling for legacy
  vault formats;
- automatic locking after inactivity;
- clipboard time-to-live handling that only clears content copied by the app;
- best-effort secret cleanup when the vault locks or the application closes.

The deeper design notes are in
[`docs/vault_lifecycle_policy.md`](docs/vault_lifecycle_policy.md),
[`docs/memory_limits.md`](docs/memory_limits.md), and
[`docs/auth_flow_v2.md`](docs/auth_flow_v2.md).

### Security boundaries and limitations

- CPython cannot guarantee complete erasure of passwords, keys, or other
  secret values from RAM.
- An administrator, debugger, malware, kernel-level compromise, screen
  capture, or other compromise of the host operating system is outside the
  application's security boundary.
- Clipboard contents are exposed to other software while present.
- Local encrypted backups remain sensitive and depend on the strength of the
  master password.
- The project has not received an independent professional security audit.
- Passing tests, dependency scans, or secret scans is not a guarantee that the
  software is free of vulnerabilities.

See [`SECURITY.md`](SECURITY.md) before reporting a security issue. Never place
real vaults, credentials, recovery codes, or other secrets in an issue or test.

## Features

- Local encrypted password vault
- Strict and recovery-enabled vault modes
- Recovery-code rotation
- Encrypted portable backup import and export
- Automatic clipboard clearing and auto-lock
- Local backup restoration and legacy vault migration
- Stale-window detection when more than one instance accesses a vault
- Separate v1 and v2 user interfaces over a shared security core

## Architecture

```text
src/vault_app/         Shared vault core and stable Tkinter v1 application
  services/            UI-independent application orchestration
  ui/                  Tkinter windows and dialogs
src/vault_app_v2/      PySide6/QML v2 work in progress
  controllers/         Python/QML bridges
  qml/                 Theme, components, and authentication screens
tests/                 pytest suite
scripts/               Development, validation, audit, and build helpers
packaging/             Nuitka and Inno Setup configuration
assets/                Project-owned source artwork and generated derivatives
```

The v2 architecture is described in
[`docs/v2_architecture.md`](docs/v2_architecture.md).

## Development setup

The supported development baseline is Windows with Python 3.12 and PowerShell.
From a fresh clone:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\audit.txt
```

Run the stable v1 application:

```powershell
.\run.ps1
```

Run the v2 work in progress:

```powershell
.\runv2.ps1
```

The root `run`, `run.cmd`, and `run.ps1` families are convenience wrappers for
Windows, Command Prompt, and Git Bash/WSL-style shells. They do not install
global aliases.

## Tests and local validation

After installing `requirements\audit.txt`, run the complete local validation:

```powershell
.\scripts\ci.ps1
```

That command checks generated asset reproducibility, Markdown links, pytest,
Python compilation, runtime logging/printing hygiene, and dependencies with
`pip-audit`.

Individual commands are also available:

```powershell
python .\scripts\generate_assets.py --check
python .\scripts\check_markdown_links.py
python -m pytest -q
python -m compileall -q src tests scripts
python -m pip_audit -r requirements\audit.txt
```

## Secret scanning

Install [Gitleaks](https://github.com/gitleaks/gitleaks) and run:

```powershell
.\scripts\security_scan.ps1
```

The script scans the current tree and all reachable Git history with redacted
output. It detects patterns; it does not prove that no sensitive information
exists. A credential exposed in any repository must still be rotated even if a
later commit removes it.

## Dependency inventory

Regenerate the local dependency inventory and basic SBOM, then run the live
dependency audit:

```powershell
.\scripts\audit.ps1
```

The generated inventory is stored in
[`docs/dependency_audit.md`](docs/dependency_audit.md) and
[`docs/sbom_basic.json`](docs/sbom_basic.json). Third-party software retains its
own license; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Building the Windows application

The release build currently targets the stable v1 application:

```powershell
python -m pip install -r requirements\build.txt
.\scripts\build.ps1
```

The standalone output is expected under `dist\instanashelock.dist`. To build an
installer, install [Inno Setup](https://jrsoftware.org/isinfo.php) and run:

```powershell
iscc packaging\installer.iss
```

Current release artifacts are not code-signed. Code signing is optional for
source publication but should be disclosed with any distributed Windows
binary. Binary distributors must also review and comply with the licenses of
all bundled dependencies, including Qt/PySide6 when applicable. See
[`docs/release_checklist.md`](docs/release_checklist.md).

## Windows data location and migration

- Canonical storage directory: `%LOCALAPPDATA%\Instanashelock`
- Legacy vault directory: `%APPDATA%\Vault`
- A legacy vault is migrated once when the canonical location has no vault.
- The vault, encrypted backup, lock, and temporary write files remain local.
- Uninstalling the application does not delete the vault by default.

Portable encrypted backups are described in
[`docs/encrypted_backups.md`](docs/encrypted_backups.md).

## Roadmap

Current engineering direction is documented in
[`docs/roadmap_practico.md`](docs/roadmap_practico.md) and
[`docs/roadmap_instanashelock_2_0.md`](docs/roadmap_instanashelock_2_0.md).
Roadmap documents express intent, not delivery promises.

## Contributing and maintenance model

Instanashelock is maintainer-led. Bug reports, reproducible technical issues,
and focused suggestions may be considered. Pull requests may be reviewed, but
review or acceptance is not guaranteed and project direction remains with the
maintainer. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

Instanashelock's own source code, documentation, and project-owned visual
assets are distributed under the [MIT License](LICENSE). Third-party
dependencies and tools are not relicensed by this repository.
