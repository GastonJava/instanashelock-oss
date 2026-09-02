"""
Cryptographic and application constants.

Centralises every tunable so that no magic numbers leak into other modules.
"""

# ── Product identity ─────────────────────────────────────────────────────────

APP_NAME = "Instanashelock"
APP_TITLE = "instanashelock"
APP_DIR_NAME = "Instanashelock"
APP_BRAND_LEAD = "Insta"
APP_BRAND_TAIL = "nashelock"
PORTABLE_BACKUP_EXTENSION = ".instanashelock-backup"

# ── Cryptographic defaults ──────────────────────────────────────────────────

SALT_SIZE = 32          # bytes
NONCE_SIZE = 12         # bytes  (GCM standard)
KEY_SIZE = 32           # bytes  → AES-256

# KDF identifiers stored in the vault header
KDF_PBKDF2_SHA256 = 1
KDF_ARGON2ID = 2

# PBKDF2 defaults (kept for v1 migration and fallback)
PBKDF2_ITERATIONS = 600_000

# Argon2id defaults
ARGON2_MEMORY_COST = 65_536   # 64 MiB
ARGON2_TIME_COST = 3
ARGON2_PARALLELISM = 4

# ── Vault file format ───────────────────────────────────────────────────────

VAULT_MAGIC = b"VLT!"
VAULT_VERSION_LEGACY = 1       # v1.1 format  (PBKDF2, no AAD)
VAULT_VERSION_2 = 2            # v2.0 format  (Argon2id default, AAD, no VMK)
VAULT_VERSION = 3              # v3.0 format  (VMK + optional recovery keys)

# v1 header: [4 magic][1 ver][1 kdf][4 iter LE][1 salt_len][salt]
V1_HEADER_FIXED = 4 + 1 + 1 + 4 + 1   # 11 bytes before salt

# v2 header: [4 magic][1 ver][1 kdf][2 kdf_params_len LE][params][1 salt_len][salt]
V2_HEADER_FIXED = 4 + 1 + 1 + 2       # 8 bytes before kdf_params

# v3 header: [4 magic][1 ver][1 kdf][2 kdf_params_len][params]
#             [1 salt_pw_len][salt_pw][2 enc_vmk_pw_len][enc_vmk_pw]
#             [1 has_recovery][if 1: 1 salt_rec_len, salt_rec, 2 enc_vmk_rec_len, enc_vmk_rec]
V3_HEADER_FIXED = 4 + 1 + 1 + 2       # 8 bytes before kdf_params (same start as v2)

# ── Recovery keys ──────────────────────────────────────────────────────────

RECOVERY_CODE_GROUPS = 10
RECOVERY_GROUP_LEN = 4
RECOVERY_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 31 chars, no 0/O/1/I/L
RECOVERY_RAW_BYTES = 20   # 160 bits of entropy

# ── Validation ranges ───────────────────────────────────────────────────────

SUPPORTED_VERSIONS = {VAULT_VERSION_LEGACY, VAULT_VERSION_2, VAULT_VERSION}
SUPPORTED_KDFS = {KDF_PBKDF2_SHA256, KDF_ARGON2ID}

PBKDF2_ITER_MIN = 100_000
PBKDF2_ITER_MAX = 10_000_000

ARGON2_MEM_MIN = 16_384
ARGON2_MEM_MAX = 4_194_304
ARGON2_TIME_MIN = 1
ARGON2_TIME_MAX = 20
ARGON2_PAR_MIN = 1
ARGON2_PAR_MAX = 16

SALT_LEN_MIN = 16
SALT_LEN_MAX = 64

# ── UI timing ──────────────────────────────────────────────────────────────

CLIPBOARD_CLEAR_MS = 30_000    # 30 s
REVEAL_CLEAR_MS = 20_000       # 20 s
AUTO_LOCK_MS = 300_000         # 5 min inactivity
