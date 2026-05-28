from __future__ import annotations

from app.core.security import hash_password, verify_password


def test_hash_and_verify_password_roundtrip() -> None:
    h = hash_password("MinhaSenha123!")
    assert h != "MinhaSenha123!"
    assert verify_password(h, "MinhaSenha123!") is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    h = hash_password("MinhaSenha123!")
    assert verify_password(h, "outraSenha") is False


def test_hash_password_uses_argon2id() -> None:
    h = hash_password("x")
    assert h.startswith("$argon2id$")
