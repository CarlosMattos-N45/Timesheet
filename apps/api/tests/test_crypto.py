from __future__ import annotations

import base64
import os
import secrets
import stat
import sys
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    derive_subkey,
    ensure_kek,
    format_db_cipher_key,
)


def test_ensure_kek_generates_new_file_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    kek = ensure_kek(path)
    assert len(kek) == 32
    assert path.exists()


def test_ensure_kek_idempotent_when_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    kek1 = ensure_kek(path)
    kek2 = ensure_kek(path)
    assert kek1 == kek2, "ensure_kek deve ser idempotente quando o arquivo existe"


def test_ensure_kek_file_permissions_restricted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform == "win32":
        pytest.skip("Permissoes POSIX nao aplicaveis no Windows")
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    ensure_kek(path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, f"Permissao esperada 0o600, obtida 0o{mode:o}"


def test_ensure_kek_refuses_plain_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform == "win32":
        pytest.skip("Fallback so se aplica fora do Windows")
    monkeypatch.delenv("TIMESHEET_ALLOW_PLAIN_KEK", raising=False)
    with pytest.raises(RuntimeError, match="DPAPI"):
        ensure_kek(tmp_path / "key.kek")


def test_derive_subkey_deterministic_per_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    sub1 = derive_subkey(kek, info=b"db")
    sub2 = derive_subkey(kek, info=b"db")
    assert sub1 == sub2
    assert len(sub1) == 32


def test_derive_subkey_isolated_between_contexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    sub_db = derive_subkey(kek, info=b"db")
    sub_smtp = derive_subkey(kek, info=b"smtp")
    assert sub_db != sub_smtp


def test_aes_gcm_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"smtp")
    plaintext = b"senha-smtp-do-usuario"
    encrypted = aes_gcm_encrypt(subkey, plaintext)
    assert isinstance(encrypted, str) and len(encrypted) > 0
    recovered = aes_gcm_decrypt(subkey, encrypted)
    assert recovered == plaintext


def test_aes_gcm_uses_fresh_nonce_per_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"smtp")
    pt = b"x"
    c1 = aes_gcm_encrypt(subkey, pt)
    c2 = aes_gcm_encrypt(subkey, pt)
    assert c1 != c2, "nonce CSPRNG deve gerar resultados distintos"
    assert aes_gcm_decrypt(subkey, c1) == pt
    assert aes_gcm_decrypt(subkey, c2) == pt


def test_aes_gcm_rejects_wrong_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey_ok = derive_subkey(kek, info=b"smtp")
    subkey_wrong = derive_subkey(kek, info=b"db")
    encrypted = aes_gcm_encrypt(subkey_ok, b"segredo")
    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(subkey_wrong, encrypted)


def test_format_db_cipher_key_is_hex64(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"db")
    hex64 = format_db_cipher_key(subkey)
    assert len(hex64) == 64
    int(hex64, 16)  # raises ValueError se nao for hex valido


def test_derive_subkey_rejects_wrong_kek_size() -> None:
    with pytest.raises(ValueError, match="KEK must be 32 bytes"):
        derive_subkey(b"short", info=b"db")


def test_aes_gcm_encrypt_rejects_wrong_subkey_size() -> None:
    with pytest.raises(ValueError, match="subkey must be 32 bytes"):
        aes_gcm_encrypt(b"short", b"plaintext")


def test_aes_gcm_decrypt_rejects_wrong_subkey_size() -> None:
    with pytest.raises(ValueError, match="subkey must be 32 bytes"):
        aes_gcm_decrypt(b"short", "aGVsbG8=")


def test_aes_gcm_decrypt_rejects_too_short_ciphertext() -> None:
    subkey = secrets.token_bytes(32)
    # base64 de menos de 28 bytes (12 nonce + 16 tag)
    short_blob = base64.urlsafe_b64encode(b"tooshort").decode("ascii").rstrip("=")
    with pytest.raises(ValueError, match="ciphertext too short"):
        aes_gcm_decrypt(subkey, short_blob)


def test_format_db_cipher_key_rejects_wrong_subkey_size() -> None:
    with pytest.raises(ValueError, match="subkey must be 32 bytes"):
        format_db_cipher_key(b"short")


def test_dpapi_protect_raises_runtime_error_when_win32crypt_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cobre a branch ImportError de _dpapi_protect."""
    import sys

    import app.core.crypto as crypto_mod

    # Remove win32crypt do sys.modules para simular ausencia da lib
    monkeypatch.setitem(sys.modules, "win32crypt", None)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="pywin32"):
        crypto_mod._dpapi_protect(b"x" * 32)


def test_dpapi_unprotect_raises_runtime_error_when_win32crypt_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cobre a branch ImportError de _dpapi_unprotect."""
    import sys

    import app.core.crypto as crypto_mod

    monkeypatch.setitem(sys.modules, "win32crypt", None)  # type: ignore[arg-type]
    with pytest.raises((RuntimeError, ImportError)):
        crypto_mod._dpapi_unprotect(b"x" * 32)


def test_posix_read_kek_plain_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobre _read_kek no caminho nao-Windows com TIMESHEET_ALLOW_PLAIN_KEK=1."""
    import app.core.crypto as crypto_mod

    monkeypatch.setattr(crypto_mod.sys, "platform", "linux")
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = secrets.token_bytes(32)
    path = tmp_path / "k.kek"
    path.write_bytes(kek)
    result = crypto_mod._read_kek(path)
    assert result == kek


def test_posix_read_kek_refuses_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobre _read_kek no caminho nao-Windows sem flag."""
    import app.core.crypto as crypto_mod

    monkeypatch.setattr(crypto_mod.sys, "platform", "linux")
    monkeypatch.delenv("TIMESHEET_ALLOW_PLAIN_KEK", raising=False)
    path = tmp_path / "k.kek"
    path.write_bytes(secrets.token_bytes(32))
    with pytest.raises(RuntimeError, match="DPAPI"):
        crypto_mod._read_kek(path)


def test_posix_write_kek_with_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobre _write_kek no caminho nao-Windows com TIMESHEET_ALLOW_PLAIN_KEK=1."""
    import app.core.crypto as crypto_mod

    monkeypatch.setattr(crypto_mod.sys, "platform", "linux")
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = secrets.token_bytes(32)
    path = tmp_path / "k.kek"
    crypto_mod._write_kek(path, kek)
    assert path.read_bytes() == kek


def test_posix_write_kek_refuses_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cobre _write_kek no caminho nao-Windows sem flag."""
    import app.core.crypto as crypto_mod

    monkeypatch.setattr(crypto_mod.sys, "platform", "linux")
    monkeypatch.delenv("TIMESHEET_ALLOW_PLAIN_KEK", raising=False)
    with pytest.raises(RuntimeError, match="DPAPI"):
        crypto_mod._write_kek(tmp_path / "k.kek", secrets.token_bytes(32))
