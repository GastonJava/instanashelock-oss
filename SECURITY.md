# Security Policy

Instanashelock stores sensitive data locally. Security reports must use
synthetic data and should be handled privately whenever they contain
exploitable details.

## Supported versions

No public versioned release has been published from this repository yet.
Security fixes currently target the latest commit on `main`:

| Code line | Status |
| --- | --- |
| v1 application and shared vault core on `main` | Supported |
| v2 PySide6/QML work in progress on `main` | Development code; reports accepted |
| Historical pre-OSS builds and snapshots | Unsupported |

This table will be replaced with explicit version ranges after public releases
exist.

## Private reporting channel

GitHub private vulnerability reporting is enabled for this repository. Use
**Security → Report a vulnerability** to submit exploitable details privately.
Do not disclose an
exploitable vulnerability in a public issue, discussion, pull request, commit
message, or social-media post.

If private vulnerability reporting is temporarily unavailable, do not post
technical details publicly. A public issue may request that the maintainer open
a private channel, but that issue must contain no exploit, secret, real vault,
or sensitive diagnostic information. No email address is designated by this
repository.

## What to include

A useful report contains only the information needed to reproduce and assess
the issue:

- affected release or commit;
- Windows and Python versions, where relevant;
- minimal reproduction steps using synthetic data;
- expected and observed behavior;
- security impact and realistic attack prerequisites;
- a proposed remediation, if available.

Never attach a real vault, master password, recovery code, encryption key,
access token, private key, credential, memory dump, or log containing personal
data. Create a minimal synthetic fixture instead.

## Disclosure and response expectations

Please allow the maintainer time to reproduce and remediate an issue before
public disclosure. This is a maintainer-led project without a guaranteed
response-time or remediation SLA. Receipt, acceptance, a fix, or a particular
release date cannot be promised.

## Security boundary

The project does not claim protection from a compromised operating system,
administrator-level access, malware, kernel compromise, debugger access, or
physical access to an unlocked machine. Secret cleanup in CPython is
best-effort and cannot guarantee complete erasure from RAM. See
[`docs/memory_limits.md`](docs/memory_limits.md).

## Repository hygiene

Keep vaults, backups, signing material, credentials, logs, dumps, generated
release artifacts, and local configuration out of Git. Run
`.\scripts\security_scan.ps1` before publishing history or preparing a release.
