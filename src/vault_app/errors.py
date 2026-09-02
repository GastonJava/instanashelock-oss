"""
Typed exceptions used across vault parsing and storage flows.
"""

from __future__ import annotations


class VaultError(Exception):
    """Base class for vault-specific failures."""


class VaultFormatError(VaultError, ValueError):
    """The vault file exists but its format is invalid or unsupported."""


class VaultStorageError(VaultError, OSError):
    """The vault could not be read or written reliably on disk."""


class VaultBusyError(VaultStorageError):
    """Another process already holds the vault write lock."""


class VaultBackupError(VaultStorageError):
    """A backup copy could not be created before replacing the vault."""


class VaultConflictError(VaultStorageError):
    """The vault changed on disk since this instance loaded it."""
