from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.recovery import parse_recovery_input
from vault_app_v2.services.auth_service import CreateVaultService, CreateVaultSuccess, UnlockService, UnlockSuccess
from vault_app.storage import decrypt_with_recovery, load_vault


def test_create_vault_service_creates_strict_vault_that_unlocks(tmp_path):
    vault_file = tmp_path / "strict.vault"
    service = CreateVaultService(path=str(vault_file))

    result = service.create_vault("correct horse battery staple", recovery_enabled=False)

    assert isinstance(result, CreateVaultSuccess)
    assert result.recovery_enabled is False
    assert result.recovery_codes == ""
    assert vault_file.exists()

    unlock = UnlockService(path=str(vault_file)).unlock("correct horse battery staple")
    assert isinstance(unlock, UnlockSuccess)
    assert unlock.data == {"entries": []}
    assert unlock.header.has_recovery is False


def test_create_vault_service_creates_recovery_vault_with_codes(tmp_path):
    vault_file = tmp_path / "recovery.vault"
    service = CreateVaultService(path=str(vault_file))

    result = service.create_vault("correct horse battery staple", recovery_enabled=True)

    assert isinstance(result, CreateVaultSuccess)
    assert result.recovery_enabled is True
    assert len(result.recovery_codes.split("-")) == 10

    header, encrypted_blob, _fingerprint = load_vault(str(vault_file))
    recovery_raw = parse_recovery_input(result.recovery_codes)
    recovered_header, _vmk, data = decrypt_with_recovery(
        str(vault_file),
        header,
        encrypted_blob,
        recovery_raw,
    )

    assert recovered_header.has_recovery is True
    assert data == {"entries": []}
