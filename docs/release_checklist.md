# Release Readiness Checklist

This checklist separates source-publication readiness from distribution of a
Windows executable or installer. An unsigned binary is not a blocker for
publishing source, but its unsigned status must be disclosed.

No public release has been created from this repository.

## Current version alignment

| Component | Version | State |
| --- | --- | --- |
| v1 Python package | `1.0.0` | Aligned with packaging configuration |
| Nuitka Windows metadata | `1.0.0.0` | Aligned |
| Inno Setup application/installer | `1.0.0` | Aligned |
| v2 Python package | `2.0.0a0` | Explicit work-in-progress version |

## Source-publication checks

- [x] OSI-approved project license included
- [x] Third-party dependencies retain their own licenses
- [x] Project-owned visual assets are covered by the project license
- [x] Public README and security limitations are documented
- [x] Pre-OSS history is clearly distinguished from public OSS history
- [x] Tests, compilation, dependency audit, and secret scanning are scripted
- [x] GitHub Actions workflow is configured without signing or repository secrets
- [x] Run the workflow on the private GitHub remote
- [x] Complete a fresh-clone audit from that private remote

## Source release (`v1.0.0`) checks

- [ ] Decide that the current source snapshot is the intended `v1.0.0` content
- [ ] Update `CHANGELOG.md` from `Unreleased` to the release date
- [ ] Re-run the complete validation suite from a fresh clone
- [ ] Create and verify the `v1.0.0` tag only after the private-remote gate passes
- [ ] Prepare truthful release notes with security limitations

## Windows binary checks

- [ ] Build v1 from a clean OSS checkout with `requirements\build.txt`
- [ ] Inspect the Nuitka output and generated compilation/license report
- [ ] Inventory every bundled third-party library and include required notices
- [ ] Confirm whether Qt/PySide6 is present; if present, satisfy its LGPL, GPL,
      or commercial-license obligations
- [ ] Launch and exercise the standalone executable in an isolated data directory
- [ ] Compile the Inno Setup installer from the same verified output
- [ ] Test install, launch, upgrade behavior, and uninstall on a clean Windows environment
- [ ] Publish checksums for any distributed artifacts
- [ ] State prominently when executable and installer are unsigned
- [ ] Optionally sign executable and installer with a key stored outside the repository

## Pre-OSS evidence

Private development previously produced and smoke-tested a local Nuitka build
and Inno Setup installer. That record is preserved in
[`release_smoke_test_note.md`](release_smoke_test_note.md) and
[`v1_closeout.md`](v1_closeout.md). It is historical engineering evidence, not
proof that a future artifact built from the OSS repository has passed the same
checks.
