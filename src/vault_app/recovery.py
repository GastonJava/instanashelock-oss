"""
Recovery key generation, encoding, parsing, and derivation.

A recovery key is 20 random bytes (160 bits) encoded as 10 groups of 4
characters from an unambiguous charset (no 0/O, 1/I/L).  All 10 groups
together form a single secret.
"""

from __future__ import annotations

import re
import secrets

from vault_app.constants import (
    RECOVERY_CODE_GROUPS,
    RECOVERY_GROUP_LEN,
    RECOVERY_CHARSET,
    RECOVERY_RAW_BYTES,
    KDF_ARGON2ID,
    SALT_SIZE,
    KEY_SIZE,
)


def generate_recovery_secret() -> tuple[str, bytes]:
    """Generate a new recovery secret.

    Returns ``(display_codes, raw_bytes)`` where *display_codes* is the
    human-readable string like ``AXKF-9M2R-BNPL-...`` and *raw_bytes*
    is the underlying secret used for key derivation.
    """
    raw = secrets.token_bytes(RECOVERY_RAW_BYTES)
    display = _encode(raw)
    return display, raw


def _encode(raw: bytes) -> str:
    """Encode raw bytes into groups of charset characters."""
    num = int.from_bytes(raw, "big")
    base = len(RECOVERY_CHARSET)
    total_chars = RECOVERY_CODE_GROUPS * RECOVERY_GROUP_LEN

    chars: list[str] = []
    for _ in range(total_chars):
        num, rem = divmod(num, base)
        chars.append(RECOVERY_CHARSET[rem])
    chars.reverse()

    groups = [
        "".join(chars[i: i + RECOVERY_GROUP_LEN])
        for i in range(0, total_chars, RECOVERY_GROUP_LEN)
    ]
    return "-".join(groups)


def parse_recovery_input(user_input: str) -> bytes:
    """Normalise and decode user-typed recovery codes back to raw bytes.

    Accepts codes with or without dashes, any casing, with extra whitespace.
    Raises ``ValueError`` if the input cannot be decoded.
    """
    cleaned = user_input.upper().replace("-", "").replace(" ", "").strip()
    expected_len = RECOVERY_CODE_GROUPS * RECOVERY_GROUP_LEN
    if len(cleaned) != expected_len:
        raise ValueError(
            f"Se esperan {expected_len} caracteres ({RECOVERY_CODE_GROUPS} grupos "
            f"de {RECOVERY_GROUP_LEN}), se recibieron {len(cleaned)}."
        )

    base = len(RECOVERY_CHARSET)
    num = 0
    for ch in cleaned:
        idx = RECOVERY_CHARSET.find(ch)
        if idx < 0:
            raise ValueError(f"Caracter invalido en codigo de recuperacion: '{ch}'")
        num = num * base + idx

    return num.to_bytes(RECOVERY_RAW_BYTES, "big")


def derive_recovery_key(raw_secret: bytes, salt: bytes) -> bytes:
    """Derive a 256-bit wrapping key from the raw recovery secret via Argon2id."""
    from vault_app.crypto import derive_key
    return derive_key(
        raw_secret.hex(),
        salt,
        kdf_id=KDF_ARGON2ID,
    )
