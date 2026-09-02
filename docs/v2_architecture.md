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

First extracted service:

- `unlock_service`

### `v2`

`src/vault_app_v2`

Rules:

- `vault_app_v2.*` is `v2`-only
- uses `PySide6 + Qt Quick / QML`
- may import shared core modules and `vault_app.services.*`
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

## Unlock Service Contract

`vault_app.services.unlock_service.UnlockService`

Responsibilities:

- detect whether a vault exists
- parse the vault container safely
- attempt password unlock
- own rate-limit / cooldown state for the existing-vault unlock path
- return typed results for:
  - `VaultReady`
  - `MissingVault`
  - `CorruptVault`
  - `UnlockWrongPassword`
  - `LockedOut`
  - `UnlockSuccess`

Non-goals for this first slice:

- create-vault orchestration
- recovery-code orchestration
- local reset orchestration
- backup restore orchestration
- Windows Hello

## V2 Controller Pattern

`QML -> QObject controller -> service layer -> shared core`

For the first slice:

- QML screen: `UnlockScreen.qml`
- controller: `UnlockController`
- service: `UnlockService`

Controller rules:

- translate typed service results into UI state
- expose bindable properties for QML
- emit route changes and one-off animation signals
- avoid embedding vault crypto or storage logic in QML

## Navigation Model

The root `v2` window uses `ApplicationWindow + StackView` from day one.

First routes:

- `unlock`
- `forgot`
- `missing`
- `corrupt`
- `unlocked`

Only `unlock` is connected to real backend behavior in this slice.

The others are honest placeholders so adjacent states can be tested without pretending the full auth system already exists.

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
