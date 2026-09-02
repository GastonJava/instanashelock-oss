# V2 Architecture

Technical source of truth for the first `Instanashelock 2.0` implementation slice.

This document exists to keep `v1` and `v2` parallel inside the same repo without mixing UI stacks accidentally.

## Goals

- keep `v1` stable and runnable
- introduce `v2` as a separate app package
- reuse shared core/storage/crypto logic
- forbid `v2` from importing Tkinter UI code
- extract shared orchestration gradually through `vault_app.services.*`

## Package Boundaries

### `v1`

`src/vault_app`

Rules:

- `vault_app.ui.*` is `v1`-only
- Tkinter windows, dialogs, and view glue stay here
- `v1` remains the default runnable app

### Shared Core

Still inside `src/vault_app` for now:

- `vault_app.constants`
- `vault_app.crypto`
- `vault_app.storage`
- `vault_app.header`
- `vault_app.recovery`
- `vault_app.security`
- `vault_app.errors`
- `vault_app.app_lifecycle`

These modules are allowed for both `v1` and `v2`.

### Shared App Services

`src/vault_app/services`

Rules:

- UI-agnostic only
- no Tkinter imports
- no QML imports
- return typed outcomes, not widgets or toolkit-specific dialogs

Current extracted service:

- `unlock_service`

The Tkinter v1 unlock window currently consumes this service. The v2
controller does **not** yet import it: v2 currently has parallel unlock and
create-vault orchestration in
`vault_app_v2.services.auth_service`. Both implementations call the same
established core storage, crypto, header, recovery, and rate-limit helpers.

This distinction is important: the security-sensitive primitives are shared,
but all higher-level authentication orchestration has not yet been
consolidated.

### `v2`

`src/vault_app_v2`

Rules:

- `vault_app_v2.*` is `v2`-only
- uses `PySide6 + Qt Quick / QML`
- imports shared core modules directly
- may consume `vault_app.services.*` after behavior is consolidated
- must never import `vault_app.ui.*`

## Import Rules

Allowed:

- `vault_app.ui.* -> vault_app.services.*`
- `vault_app_v2.* -> vault_app.services.*`
- both apps -> shared core modules

Not allowed:

- `vault_app_v2.* -> vault_app.ui.*`
- `vault_app.services.* -> vault_app.ui.*`
- `vault_app.services.* -> vault_app_v2.*`

The dependency direction should always point inward toward shared logic, never sideways between UI stacks.

## Current Authentication Service Boundary

v1 uses `vault_app.services.unlock_service.UnlockService` for password unlock.
v2 currently uses the services in `vault_app_v2.services.auth_service`:

- `UnlockService` performs real vault detection, parsing, rate limiting, and
  password unlock through the shared core;
- `CreateVaultService` creates a real v3 vault and can enable recovery-code
  generation through shared storage/recovery operations.

The two unlock services currently overlap. Consolidating that orchestration is
a maintainability improvement, not a cryptographic migration.

Not yet connected in v2:

- recovery-code unlock;
- encrypted-backup restore;
- destructive local reset;
- post-unlock entry persistence and conflict handling;
- Windows Hello.

## V2 Controller Pattern

`QML -> QObject controller -> v2 auth service -> shared core`

For the first slice:

- QML screen: `UnlockScreen.qml`
- controller: `UnlockController`
- services: v2 `UnlockService` and `CreateVaultService`

Controller rules:

- translate typed service results into UI state
- expose bindable properties for QML
- emit route changes and one-off animation signals
- avoid embedding vault crypto or storage logic in QML

## Navigation Model

The root `v2` window uses `ApplicationWindow + StackView` from day one.

Current routes:

- `unlock`
- `forgot`
- `create`
- `recoveryCodes`
- `recoveryUnlock`
- `corrupt`
- `unlocked`

Password unlock and vault creation are connected to real backend behavior.
Recovery-code display after creation is also real. The recovery-unlock screen
is visual only, the backup/reset choices announce future backend work, the
corrupt-vault route is a placeholder, and `unlocked` resolves to
`UnlockedPlaceholderScreen.qml` rather than the main vault application.

## Current Implementation Status

| Area | Status | Evidence |
| --- | --- | --- |
| QML bootstrap, theme, and reusable controls | Done | `app.py`, `App.qml`, `qml/components/`, `qml/theme/` |
| Password unlock | Done for the current slice | `UnlockController.submitPassword`, v2 `UnlockService` |
| Create vault | Done for the current slice | `UnlockController.createVault`, `CreateVaultService` |
| Recovery-code generation during creation | Done | `CreateVaultService`, `RecoveryCodesScreen.qml` |
| Recovery-code unlock | In progress | Screen exists; action states that backend is pending |
| Backup restore and local reset | Planned | Options exist in `ForgotPasswordScreen.qml`; backend is pending |
| Corrupt-vault recovery | Planned | `CorruptVaultPlaceholderScreen.qml` |
| Main post-unlock vault UI | Next major slice | `UnlockedPlaceholderScreen.qml` |
| Entry list/search/CRUD and conflict-safe save | Planned | Not present in `vault_app_v2` |

## Runner Separation

`v1`:

- `run`
- `scripts/dev.ps1`

`v2`:

- `runv2`
- `scripts/run_dev_v2.ps1`

No `v2` packaging work is part of this slice.

## Implementation Rule for This Ticket

Before adding more `v2` screens, keep following the same pattern:

1. extract shared orchestration into `vault_app.services.*`
2. keep UI-specific behavior inside each frontend
3. wire one vertical slice end-to-end
4. leave unfinished adjacent states as explicit placeholders
