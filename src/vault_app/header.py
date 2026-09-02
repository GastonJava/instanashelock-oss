"""
Vault binary header: build, parse, and validate.

Three formats coexist for migration purposes:

* **v1** (legacy): ``[4 magic][1 ver=1][1 kdf][4 iter LE][1 salt_len][salt]``
* **v2**: ``[4 magic][1 ver=2][1 kdf][2 params_len LE][params][1 salt_len][salt]``
* **v3** (current): v2 KDF block + wrapped VMK + optional recovery blob
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from vault_app.constants import (
    NONCE_SIZE,
    VAULT_MAGIC,
    VAULT_VERSION,
    VAULT_VERSION_2,
    VAULT_VERSION_LEGACY,
    V1_HEADER_FIXED,
    V2_HEADER_FIXED,
    V3_HEADER_FIXED,
    KDF_PBKDF2_SHA256,
    KDF_ARGON2ID,
    PBKDF2_ITERATIONS,
    ARGON2_MEMORY_COST,
    ARGON2_TIME_COST,
    ARGON2_PARALLELISM,
    SUPPORTED_VERSIONS,
    SUPPORTED_KDFS,
    PBKDF2_ITER_MIN,
    PBKDF2_ITER_MAX,
    ARGON2_MEM_MIN,
    ARGON2_MEM_MAX,
    ARGON2_TIME_MIN,
    ARGON2_TIME_MAX,
    ARGON2_PAR_MIN,
    ARGON2_PAR_MAX,
    SALT_LEN_MIN,
    SALT_LEN_MAX,
    SALT_SIZE,
)
from vault_app.errors import VaultFormatError


WRAPPED_KEY_LEN_MIN = NONCE_SIZE + 16
WRAPPED_KEY_LEN_MAX = 512


@dataclass(slots=True)
class VaultHeader:
    """Parsed representation of the vault file header."""

    version: int
    kdf_id: int
    salt: bytes                  # password-derivation salt (salt_pw in v3)

    # PBKDF2
    iterations: int = PBKDF2_ITERATIONS

    # Argon2id
    argon2_memory_cost: int = ARGON2_MEMORY_COST
    argon2_time_cost: int = ARGON2_TIME_COST
    argon2_parallelism: int = ARGON2_PARALLELISM

    # v3: wrapped VMK (password path)
    enc_vmk_pw: bytes = b""

    # v3: recovery
    has_recovery: bool = False
    salt_rec: bytes = b""
    enc_vmk_rec: bytes = b""

    @property
    def argon2_params(self) -> dict:
        return {
            "memory_cost": self.argon2_memory_cost,
            "time_cost": self.argon2_time_cost,
            "parallelism": self.argon2_parallelism,
        }

    def serialise(self) -> bytes:
        """Build the binary header for writing to disk."""
        if self.version == VAULT_VERSION_LEGACY:
            return _build_v1(self)
        if self.version == VAULT_VERSION_2:
            return _build_v2(self)
        return _build_v3(self)


# ── KDF params helpers ──────────────────────────────────────────────────────


def _pack_kdf_params(h: VaultHeader) -> bytes:
    if h.kdf_id == KDF_PBKDF2_SHA256:
        return struct.pack("<I", h.iterations)
    if h.kdf_id == KDF_ARGON2ID:
        return struct.pack("<III", h.argon2_memory_cost, h.argon2_time_cost, h.argon2_parallelism)
    raise VaultFormatError(f"KDF desconocida al serializar: {h.kdf_id}")


def _unpack_kdf_params(kdf_id: int, raw: bytes) -> dict:
    """Returns dict with iterations / argon2 fields."""
    result: dict = {}
    if kdf_id == KDF_PBKDF2_SHA256:
        if len(raw) < 4:
            raise VaultFormatError("Params PBKDF2 truncados.")
        result["iterations"] = struct.unpack_from("<I", raw, 0)[0]
        _validate_pbkdf2_iterations(result["iterations"])
    elif kdf_id == KDF_ARGON2ID:
        if len(raw) < 12:
            raise VaultFormatError("Params Argon2id truncados.")
        m, t, p = struct.unpack_from("<III", raw, 0)
        _validate_argon2_params(m, t, p)
        result["argon2_memory_cost"] = m
        result["argon2_time_cost"] = t
        result["argon2_parallelism"] = p
    return result


# ── Builders ────────────────────────────────────────────────────────────────


def _build_v1(h: VaultHeader) -> bytes:
    return (
        VAULT_MAGIC
        + struct.pack("<B", VAULT_VERSION_LEGACY)
        + struct.pack("<B", h.kdf_id)
        + struct.pack("<I", h.iterations)
        + struct.pack("<B", len(h.salt))
        + h.salt
    )


def _build_v2(h: VaultHeader) -> bytes:
    kdf_params = _pack_kdf_params(h)
    return (
        VAULT_MAGIC
        + struct.pack("<B", VAULT_VERSION_2)
        + struct.pack("<B", h.kdf_id)
        + struct.pack("<H", len(kdf_params))
        + kdf_params
        + struct.pack("<B", len(h.salt))
        + h.salt
    )


def _build_v3(h: VaultHeader) -> bytes:
    kdf_params = _pack_kdf_params(h)
    parts = bytearray()
    parts += VAULT_MAGIC
    parts += struct.pack("<B", VAULT_VERSION)
    parts += struct.pack("<B", h.kdf_id)
    parts += struct.pack("<H", len(kdf_params))
    parts += kdf_params
    parts += struct.pack("<B", len(h.salt))
    parts += h.salt
    parts += struct.pack("<H", len(h.enc_vmk_pw))
    parts += h.enc_vmk_pw
    parts += struct.pack("<B", 1 if h.has_recovery else 0)
    if h.has_recovery:
        parts += struct.pack("<B", len(h.salt_rec))
        parts += h.salt_rec
        parts += struct.pack("<H", len(h.enc_vmk_rec))
        parts += h.enc_vmk_rec
    return bytes(parts)


# ── Parser ──────────────────────────────────────────────────────────────────


def parse_header(raw: bytes) -> tuple[VaultHeader, bytes]:
    """Parse the binary header and return ``(header, encrypted_blob)``.

    Raises ``VaultFormatError`` on any format / validation failure.
    """
    if len(raw) < len(VAULT_MAGIC) + 1:
        raise VaultFormatError("Archivo demasiado corto para contener un header valido.")
    if raw[: len(VAULT_MAGIC)] != VAULT_MAGIC:
        raise VaultFormatError("El archivo no es un vault valido (magic incorrecto).")

    version = struct.unpack_from("<B", raw, 4)[0]
    if version not in SUPPORTED_VERSIONS:
        raise VaultFormatError(f"Version de vault no soportada: {version}")

    if version == VAULT_VERSION_LEGACY:
        return _parse_v1(raw)
    if version == VAULT_VERSION_2:
        return _parse_v2(raw)
    return _parse_v3(raw)


def _parse_v1(raw: bytes) -> tuple[VaultHeader, bytes]:
    if len(raw) < V1_HEADER_FIXED + 1:
        raise VaultFormatError("Header v1 truncado.")

    off = 4
    version = struct.unpack_from("<B", raw, off)[0]; off += 1
    kdf_id = struct.unpack_from("<B", raw, off)[0]; off += 1
    iterations = struct.unpack_from("<I", raw, off)[0]; off += 4
    salt_len = struct.unpack_from("<B", raw, off)[0]; off += 1

    _validate_kdf_id(kdf_id)
    _validate_pbkdf2_iterations(iterations)
    _validate_salt_len(salt_len)

    if len(raw) < off + salt_len:
        raise VaultFormatError("Header v1 truncado: salt incompleto.")

    salt = raw[off: off + salt_len]; off += salt_len
    encrypted_blob = raw[off:]
    _validate_encrypted_blob_present(encrypted_blob)
    return VaultHeader(version=version, kdf_id=kdf_id, salt=salt, iterations=iterations), encrypted_blob


def _parse_v2(raw: bytes) -> tuple[VaultHeader, bytes]:
    if len(raw) < V2_HEADER_FIXED + 1:
        raise VaultFormatError("Header v2 truncado.")

    off = 4
    version = struct.unpack_from("<B", raw, off)[0]; off += 1
    kdf_id = struct.unpack_from("<B", raw, off)[0]; off += 1
    kdf_params_len = struct.unpack_from("<H", raw, off)[0]; off += 2

    _validate_kdf_id(kdf_id)
    if len(raw) < off + kdf_params_len + 1:
        raise VaultFormatError("Header v2 truncado: params incompletos.")

    kdf_fields = _unpack_kdf_params(kdf_id, raw[off: off + kdf_params_len]); off += kdf_params_len

    salt_len = struct.unpack_from("<B", raw, off)[0]; off += 1
    _validate_salt_len(salt_len)
    if len(raw) < off + salt_len:
        raise VaultFormatError("Header v2 truncado: salt incompleto.")

    salt = raw[off: off + salt_len]; off += salt_len

    encrypted_blob = raw[off:]
    _validate_encrypted_blob_present(encrypted_blob)

    return (
        VaultHeader(
            version=version, kdf_id=kdf_id, salt=salt,
            iterations=kdf_fields.get("iterations", PBKDF2_ITERATIONS),
            argon2_memory_cost=kdf_fields.get("argon2_memory_cost", ARGON2_MEMORY_COST),
            argon2_time_cost=kdf_fields.get("argon2_time_cost", ARGON2_TIME_COST),
            argon2_parallelism=kdf_fields.get("argon2_parallelism", ARGON2_PARALLELISM),
        ),
        encrypted_blob,
    )


def _parse_v3(raw: bytes) -> tuple[VaultHeader, bytes]:
    if len(raw) < V3_HEADER_FIXED + 1:
        raise VaultFormatError("Header v3 truncado.")

    off = 4
    version = struct.unpack_from("<B", raw, off)[0]; off += 1
    kdf_id = struct.unpack_from("<B", raw, off)[0]; off += 1
    kdf_params_len = struct.unpack_from("<H", raw, off)[0]; off += 2

    _validate_kdf_id(kdf_id)
    if len(raw) < off + kdf_params_len:
        raise VaultFormatError("Header v3 truncado: params incompletos.")

    kdf_fields = _unpack_kdf_params(kdf_id, raw[off: off + kdf_params_len]); off += kdf_params_len

    # salt_pw
    if len(raw) < off + 1:
        raise VaultFormatError("Header v3 truncado: falta salt_pw_len.")
    salt_pw_len = struct.unpack_from("<B", raw, off)[0]; off += 1
    _validate_salt_len(salt_pw_len)
    if len(raw) < off + salt_pw_len:
        raise VaultFormatError("Header v3 truncado: salt_pw incompleto.")
    salt_pw = raw[off: off + salt_pw_len]; off += salt_pw_len

    # enc_vmk_pw
    if len(raw) < off + 2:
        raise VaultFormatError("Header v3 truncado: falta enc_vmk_pw_len.")
    enc_vmk_pw_len = struct.unpack_from("<H", raw, off)[0]; off += 2
    _validate_wrapped_key_len("enc_vmk_pw", enc_vmk_pw_len)
    if len(raw) < off + enc_vmk_pw_len:
        raise VaultFormatError("Header v3 truncado: enc_vmk_pw incompleto.")
    enc_vmk_pw = raw[off: off + enc_vmk_pw_len]; off += enc_vmk_pw_len

    # has_recovery
    if len(raw) < off + 1:
        raise VaultFormatError("Header v3 truncado: falta has_recovery.")
    has_recovery_raw = struct.unpack_from("<B", raw, off)[0]; off += 1
    _validate_flag_byte("has_recovery", has_recovery_raw)
    has_recovery = has_recovery_raw == 1

    salt_rec = b""
    enc_vmk_rec = b""

    if has_recovery:
        if len(raw) < off + 1:
            raise VaultFormatError("Header v3 truncado: falta salt_rec_len.")
        salt_rec_len = struct.unpack_from("<B", raw, off)[0]; off += 1
        _validate_salt_len(salt_rec_len)
        if len(raw) < off + salt_rec_len:
            raise VaultFormatError("Header v3 truncado: salt_rec incompleto.")
        salt_rec = raw[off: off + salt_rec_len]; off += salt_rec_len

        if len(raw) < off + 2:
            raise VaultFormatError("Header v3 truncado: falta enc_vmk_rec_len.")
        enc_vmk_rec_len = struct.unpack_from("<H", raw, off)[0]; off += 2
        _validate_wrapped_key_len("enc_vmk_rec", enc_vmk_rec_len)
        if len(raw) < off + enc_vmk_rec_len:
            raise VaultFormatError("Header v3 truncado: enc_vmk_rec incompleto.")
        enc_vmk_rec = raw[off: off + enc_vmk_rec_len]; off += enc_vmk_rec_len

    encrypted_blob = raw[off:]
    _validate_encrypted_blob_present(encrypted_blob)

    return (
        VaultHeader(
            version=version, kdf_id=kdf_id, salt=salt_pw,
            iterations=kdf_fields.get("iterations", PBKDF2_ITERATIONS),
            argon2_memory_cost=kdf_fields.get("argon2_memory_cost", ARGON2_MEMORY_COST),
            argon2_time_cost=kdf_fields.get("argon2_time_cost", ARGON2_TIME_COST),
            argon2_parallelism=kdf_fields.get("argon2_parallelism", ARGON2_PARALLELISM),
            enc_vmk_pw=enc_vmk_pw,
            has_recovery=has_recovery,
            salt_rec=salt_rec,
            enc_vmk_rec=enc_vmk_rec,
        ),
        encrypted_blob,
    )


# ── Validation helpers ──────────────────────────────────────────────────────


def _validate_kdf_id(kdf_id: int) -> None:
    if kdf_id not in SUPPORTED_KDFS:
        raise VaultFormatError(f"KDF desconocida: {kdf_id}")


def _validate_pbkdf2_iterations(n: int) -> None:
    if not (PBKDF2_ITER_MIN <= n <= PBKDF2_ITER_MAX):
        raise VaultFormatError(
            f"Iteraciones PBKDF2 fuera de rango ({PBKDF2_ITER_MIN}-{PBKDF2_ITER_MAX}): {n}"
        )


def _validate_argon2_params(mem: int, time: int, par: int) -> None:
    if not (ARGON2_MEM_MIN <= mem <= ARGON2_MEM_MAX):
        raise VaultFormatError(f"Argon2id memory_cost fuera de rango: {mem}")
    if not (ARGON2_TIME_MIN <= time <= ARGON2_TIME_MAX):
        raise VaultFormatError(f"Argon2id time_cost fuera de rango: {time}")
    if not (ARGON2_PAR_MIN <= par <= ARGON2_PAR_MAX):
        raise VaultFormatError(f"Argon2id parallelism fuera de rango: {par}")


def _validate_salt_len(n: int) -> None:
    if not (SALT_LEN_MIN <= n <= SALT_LEN_MAX):
        raise VaultFormatError(f"Salt length fuera de rango ({SALT_LEN_MIN}-{SALT_LEN_MAX}): {n}")


def _validate_wrapped_key_len(name: str, n: int) -> None:
    if not (WRAPPED_KEY_LEN_MIN <= n <= WRAPPED_KEY_LEN_MAX):
        raise VaultFormatError(
            f"{name} fuera de rango ({WRAPPED_KEY_LEN_MIN}-{WRAPPED_KEY_LEN_MAX}): {n}"
        )


def _validate_flag_byte(name: str, value: int) -> None:
    if value not in (0, 1):
        raise VaultFormatError(f"{name} invalido: {value}")


def _validate_encrypted_blob_present(encrypted_blob: bytes) -> None:
    if not encrypted_blob:
        raise VaultFormatError("El vault no contiene payload cifrado.")


# ── Convenience ─────────────────────────────────────────────────────────────


def default_header(salt: bytes) -> VaultHeader:
    """Return a new v2 header with Argon2id defaults and the given *salt*.

    .. deprecated:: Use :func:`default_v3_header` for new vaults.
    """
    return VaultHeader(
        version=VAULT_VERSION_2,
        kdf_id=KDF_ARGON2ID,
        salt=salt,
        argon2_memory_cost=ARGON2_MEMORY_COST,
        argon2_time_cost=ARGON2_TIME_COST,
        argon2_parallelism=ARGON2_PARALLELISM,
    )


def default_v3_header(
    salt_pw: bytes,
    enc_vmk_pw: bytes,
    *,
    has_recovery: bool = False,
    salt_rec: bytes = b"",
    enc_vmk_rec: bytes = b"",
) -> VaultHeader:
    """Return a new v3 header with Argon2id defaults, wrapped VMK, and optional recovery."""
    return VaultHeader(
        version=VAULT_VERSION,
        kdf_id=KDF_ARGON2ID,
        salt=salt_pw,
        argon2_memory_cost=ARGON2_MEMORY_COST,
        argon2_time_cost=ARGON2_TIME_COST,
        argon2_parallelism=ARGON2_PARALLELISM,
        enc_vmk_pw=enc_vmk_pw,
        has_recovery=has_recovery,
        salt_rec=salt_rec,
        enc_vmk_rec=enc_vmk_rec,
    )
