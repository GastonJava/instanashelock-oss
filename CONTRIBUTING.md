# Contributing

Instanashelock is a maintainer-led project. Bug reports, reproducible technical
issues, and focused improvement proposals may be considered. Pull requests may
be reviewed, but review or acceptance is not guaranteed.

Project direction and release decisions remain with the maintainer.

## Before opening an issue

- Search existing issues once the public repository exists.
- Reproduce the behavior from the current `main` branch when practical.
- Describe expected and observed behavior clearly.
- Use synthetic vaults, credentials, and fixtures only.
- Do not disclose exploitable security details publicly; follow
  [`SECURITY.md`](SECURITY.md).

## Development setup

On Windows with Python 3.12 and PowerShell:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements\audit.txt
.\scripts\ci.ps1
```

Run v1 with `.\run.ps1` and the v2 work in progress with `.\runv2.ps1`.

## Change expectations

- Preserve vault-format compatibility or document and test migrations.
- Add tests for security-sensitive behavior and failure paths.
- Never place real credentials, vault contents, recovery codes, tokens, keys,
  or personal data in tests, fixtures, screenshots, commits, or issues.
- Use explicit synthetic values that cannot be mistaken for real credentials.
- Keep runtime output free of plaintext secrets and unnecessary logging.
- Run `.\scripts\ci.ps1` and `.\scripts\security_scan.ps1` before proposing a
  change.
- New visual assets require editable sources and documented provenance; see
  [`assets/README.md`](assets/README.md).

Large architectural changes should be discussed before implementation. A
technically correct pull request may still be declined when it does not match
the project's scope, maintenance cost, or direction.
