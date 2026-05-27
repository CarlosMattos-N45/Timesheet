"""Cryptographic primitives for at-rest protection.

KEK lifecycle:
- Generated once at install time (32 bytes CSPRNG).
- Protected by DPAPI on Windows (production); plain bytes on disk in dev fallback.
- Never derived from user password (immutable by design).

Subkeys (32 bytes each) are derived via HKDF-Expand(SHA-256) with distinct
``info`` contexts so that compromise of one context does not expose the other:

- ``info=b"db"`` -> SQLCipher PRAGMA key.
- ``info=b"smtp"`` -> AES-GCM key for ``smtp_config.username_enc`` and
  ``smtp_config.password_enc``.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

logger = logging.getLogger(__name__)

KEK_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits, AES-GCM recommended
SUBKEY_SIZE = 32  # 256 bits


def ensure_kek(path: Path) -> bytes:
    """Return the KEK at ``path``, generating + persisting it if absent.

    On Windows uses DPAPI (CryptProtectData) when available.
    On non-Windows, requires ``TIMESHEET_ALLOW_PLAIN_KEK=1`` env var; otherwise
    raises ``RuntimeError`` to prevent accidental plain storage in production.
    """
    path = Path(path)
    if path.exists():
        return _read_kek(path)

    kek = secrets.token_bytes(KEK_SIZE)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_kek(path, kek)
    return kek


def derive_subkey(kek: bytes, info: bytes) -> bytes:
    """HKDF-Expand(SHA-256) of the KEK, namespaced by ``info``."""
    if len(kek) != KEK_SIZE:
        raise ValueError(f"KEK must be {KEK_SIZE} bytes, got {len(kek)}")
    hkdf = HKDFExpand(algorithm=hashes.SHA256(), length=SUBKEY_SIZE, info=info)
    return hkdf.derive(kek)


def aes_gcm_encrypt(subkey: bytes, plaintext: bytes) -> str:
    """Encrypt ``plaintext`` under ``subkey``.

    Returns a base64-urlsafe string (no padding) of ``nonce || ciphertext || tag``.
    """
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(subkey)
    ct_and_tag = aesgcm.encrypt(nonce, plaintext, None)
    return base64.urlsafe_b64encode(nonce + ct_and_tag).decode("ascii").rstrip("=")


def aes_gcm_decrypt(subkey: bytes, encoded: str) -> bytes:
    """Decrypt the base64-urlsafe blob produced by :func:`aes_gcm_encrypt`."""
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    pad = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(encoded + pad)
    if len(raw) < NONCE_SIZE + 16:
        raise ValueError("ciphertext too short")
    nonce, ct_and_tag = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
    aesgcm = AESGCM(subkey)
    return aesgcm.decrypt(nonce, ct_and_tag, None)


def format_db_cipher_key(subkey: bytes) -> str:
    """Hex-encode the SQLCipher key (PRAGMA expects ``x'<hex>'`` form)."""
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    return subkey.hex()


# -------- internals --------


def _read_kek(path: Path) -> bytes:
    blob = path.read_bytes()
    if sys.platform == "win32":
        try:
            return _dpapi_unprotect(blob)
        except RuntimeError:
            # Fallback path for dev on Windows without pywin32 installed.
            if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") == "1":
                logger.warning("PLAIN_KEK_FALLBACK ativo — lendo KEK em claro (dev only)")
                return blob
            raise
    # Non-Windows path
    if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
        raise RuntimeError("DPAPI indisponivel: defina TIMESHEET_ALLOW_PLAIN_KEK=1 apenas em dev")
    return blob


def _write_kek(path: Path, kek: bytes) -> None:
    if sys.platform == "win32":
        try:
            protected = _dpapi_protect(kek)
            path.write_bytes(protected)
            return
        except RuntimeError:
            if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
                raise
            logger.warning("PLAIN_KEK_FALLBACK ativo — escrevendo KEK em claro (dev only)")
            path.write_bytes(kek)
            return
    # Non-Windows path
    if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
        raise RuntimeError("DPAPI ausente: configure TIMESHEET_ALLOW_PLAIN_KEK=1 apenas em dev")
    path.write_bytes(kek)
    _restrict_permissions(path)


def _restrict_permissions(path: Path) -> None:
    if sys.platform == "win32":
        return  # DPAPI ja protegeu
    os.chmod(path, 0o600)


def _dpapi_protect(data: bytes) -> bytes:
    try:
        import win32crypt  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("pywin32 indisponivel") from exc
    result: bytes = win32crypt.CryptProtectData(data, None, None, None, None, 0)
    return result


def _dpapi_unprotect(blob: bytes) -> bytes:
    try:
        import win32crypt
    except ImportError as exc:
        raise RuntimeError("pywin32 indisponivel") from exc
    _desc, plain = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    plain_bytes: bytes = plain
    return plain_bytes
