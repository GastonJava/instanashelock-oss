"""Additional parser hardening coverage: truncations and basic fuzzing."""

from __future__ import annotations

import os
import random
import secrets
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vault_app.constants import (
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
    KDF_ARGON2ID,
    KDF_PBKDF2_SHA256,
    PBKDF2_ITERATIONS,
    SALT_SIZE,
    VAULT_MAGIC,
    VAULT_VERSION,
    VAULT_VERSION_2,
    VAULT_VERSION_LEGACY,
)
from vault_app.crypto import generate_vmk, wrap_vmk
from vault_app.errors import VaultFormatError
from vault_app.header import default_v3_header, parse_header


def _valid_v1_raw() -> bytes:
    salt = secrets.token_bytes(SALT_SIZE)
    return (
        VAULT_MAGIC
        + struct.pack("<B", VAULT_VERSION_LEGACY)
        + struct.pack("<B", KDF_PBKDF2_SHA256)
        + struct.pack("<I", PBKDF2_ITERATIONS)
        + struct.pack("<B", len(salt))
        + salt
        + b"payload-v1"
    )


def _valid_v2_raw() -> bytes:
    salt = secrets.token_bytes(SALT_SIZE)
    kdf_params = struct.pack(
        "<III",
        ARGON2_MEMORY_COST,
        ARGON2_TIME_COST,
        ARGON2_PARALLELISM,
    )
    return (
        VAULT_MAGIC
        + struct.pack("<B", VAULT_VERSION_2)
        + struct.pack("<B", KDF_ARGON2ID)
        + struct.pack("<H", len(kdf_params))
        + kdf_params
        + struct.pack("<B", len(salt))
        + salt
        + b"payload-v2"
    )


def _valid_v3_raw(*, recovery: bool) -> tuple[bytes, int]:
    salt_pw = secrets.token_bytes(SALT_SIZE)
    enc_vmk_pw = wrap_vmk(generate_vmk(), secrets.token_bytes(32))
    kwargs = {"salt_pw": salt_pw, "enc_vmk_pw": enc_vmk_pw}
    if recovery:
        kwargs.update(
            has_recovery=True,
            salt_rec=secrets.token_bytes(SALT_SIZE),
            enc_vmk_rec=wrap_vmk(generate_vmk(), secrets.token_bytes(32)),
        )
    header = default_v3_header(**kwargs)
    raw = header.serialise() + b"payload-v3"
    return raw, len(header.serialise())


def _assert_parse_or_format_error(raw: bytes) -> None:
    try:
        header, blob = parse_header(raw)
    except VaultFormatError:
        return

    assert isinstance(header.version, int)
    assert isinstance(blob, bytes)
    assert blob


def test_v1_all_header_truncations_fail_cleanly() -> None:
    raw = _valid_v1_raw()
    header, blob = parse_header(raw)
    header_len = len(raw) - len(blob)

    for length in range(header_len + 1):
        truncated = raw[:length]
        with pytest.raises(VaultFormatError):
            parse_header(truncated)


def test_v2_all_header_truncations_fail_cleanly() -> None:
    raw = _valid_v2_raw()
    header, blob = parse_header(raw)
    header_len = len(raw) - len(blob)

    for length in range(header_len + 1):
        truncated = raw[:length]
        with pytest.raises(VaultFormatError):
            parse_header(truncated)


@pytest.mark.parametrize("recovery", [False, True])
def test_v3_all_header_truncations_fail_cleanly(recovery: bool) -> None:
    raw, header_len = _valid_v3_raw(recovery=recovery)
    for length in range(header_len + 1):
        truncated = raw[:length]
        with pytest.raises(VaultFormatError):
            parse_header(truncated)


def test_v3_single_byte_header_mutations_never_crash_parser() -> None:
    raw, header_len = _valid_v3_raw(recovery=True)

    for offset in range(len(VAULT_MAGIC), header_len):
        mutated = bytearray(raw)
        mutated[offset] = (mutated[offset] + 1) % 256
        _assert_parse_or_format_error(bytes(mutated))


def test_basic_fuzzing_random_v3_header_mutations_fail_cleanly() -> None:
    rng = random.Random(20260401)
    raw, header_len = _valid_v3_raw(recovery=True)

    for _ in range(250):
        candidate = bytearray(raw)
        mutation_count = rng.randint(1, 3)
        for _ in range(mutation_count):
            offset = rng.randrange(len(VAULT_MAGIC), header_len)
            candidate[offset] = rng.randrange(256)

        if rng.random() < 0.35:
            cut = rng.randrange(0, len(candidate))
            candidate = candidate[:cut]

        _assert_parse_or_format_error(bytes(candidate))


def test_basic_fuzzing_random_v1_v2_mutations_fail_cleanly() -> None:
    rng = random.Random(20260402)

    for raw in (_valid_v1_raw(), _valid_v2_raw()):
        for _ in range(150):
            candidate = bytearray(raw)
            mutation_count = rng.randint(1, 2)
            for _ in range(mutation_count):
                offset = rng.randrange(len(candidate))
                candidate[offset] = rng.randrange(256)

            if rng.random() < 0.25:
                cut = rng.randrange(0, len(candidate))
                candidate = candidate[:cut]

            _assert_parse_or_format_error(bytes(candidate))
