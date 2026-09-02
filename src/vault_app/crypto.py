"""
Cryptographic primitives: key derivation, vault encryption / decryption.

All randomness goes through ``secrets`` (CSPRNG).
"""

from __future__ import annotations

import json
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from vault_app.constants import (
    KEY_SIZE,
    NONCE_SIZE,
    KDF_PBKDF2_SHA256,
    KDF_ARGON2ID,
    PBKDF2_ITERATIONS,
    ARGON2_MEMORY_COST,
    ARGON2_TIME_COST,
    ARGON2_PARALLELISM,
)


def derive_key(
    password: str,
    salt: bytes,
    kdf_id: int,
    *,
    iterations: int = PBKDF2_ITERATIONS,
    argon2_params: dict | None = None,
) -> bytes:
    """Derive a 256-bit key from *password* + *salt* using the KDF indicated by *kdf_id*."""

    if kdf_id == KDF_PBKDF2_SHA256:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password.encode("utf-8"))

    if kdf_id == KDF_ARGON2ID:
        from argon2.low_level import hash_secret_raw, Type  # type: ignore[import-untyped]

        params = argon2_params or {
            "memory_cost": ARGON2_MEMORY_COST,
            "time_cost": ARGON2_TIME_COST,
            "parallelism": ARGON2_PARALLELISM,
        }
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=params["time_cost"],
            memory_cost=params["memory_cost"],
            parallelism=params["parallelism"],
            hash_len=KEY_SIZE,
            type=Type.ID,
        )

    raise ValueError(f"KDF desconocida: {kdf_id}")


def generate_vmk() -> bytes:
    """Generate a random 256-bit Vault Master Key."""
    return secrets.token_bytes(KEY_SIZE)


def wrap_vmk(vmk: bytes, wrapping_key: bytes) -> bytes:
    """Encrypt *vmk* with *wrapping_key* using AES-256-GCM.  Returns ``nonce || ciphertext``."""
    nonce = secrets.token_bytes(NONCE_SIZE)
    ct = AESGCM(wrapping_key).encrypt(nonce, vmk, None)
    return nonce + ct


def unwrap_vmk(wrapped: bytes, wrapping_key: bytes) -> bytes:
    """Decrypt a wrapped VMK.  Raises ``InvalidTag`` on wrong key."""
    nonce = wrapped[:NONCE_SIZE]
    ct = wrapped[NONCE_SIZE:]
    return AESGCM(wrapping_key).decrypt(nonce, ct, None)


def encrypt_vault(data: dict, key: bytes, aad: bytes | None = None) -> bytes:
    """Serialise *data* as JSON, encrypt with AES-256-GCM.  Returns ``nonce || ciphertext``."""
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return nonce + ciphertext


def decrypt_vault(blob: bytes, key: bytes, aad: bytes | None = None) -> dict:
    """Decrypt *blob* (``nonce || ciphertext``) and return the parsed JSON dict.

    Raises ``InvalidTag`` on wrong key / tampered data.
    Raises ``json.JSONDecodeError`` on corrupt plaintext.
    """
    min_len = NONCE_SIZE + 16  # at least nonce + GCM tag
    if len(blob) < min_len:
        raise ValueError("Blob cifrado demasiado corto para ser válido.")
    nonce = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    return json.loads(plaintext.decode("utf-8"))
