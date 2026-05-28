from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import DomainError
from app.models import RefreshToken

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return bool(_pwd_context.verify(password, hashed))
    except Exception:
        return False


def _sign(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(claims: dict[str, Any], ttl_seconds: int | None = None) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(
        seconds=ttl_seconds if ttl_seconds is not None else settings.access_token_ttl_seconds
    )
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        "type": "access",
    }
    return _sign(payload)


async def create_refresh_token(claims: dict[str, Any], session: AsyncSession) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        "type": "refresh",
    }
    token = _sign(payload)
    rt = RefreshToken(
        id=str(uuid4()),
        terceiro_id=claims["sub"],
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expira_em=exp.isoformat(),
        criado_em=now.isoformat(),
    )
    session.add(rt)
    return token


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise DomainError(
            code="UNAUTHORIZED", message="Token inválido ou expirado", http_status=401
        ) from exc


async def rotate_refresh_token(token: str, session: AsyncSession) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise DomainError(code="UNAUTHORIZED", message="Tipo de token inválido", http_status=401)
    sub = payload["sub"]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    rt = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if rt is None:
        raise DomainError(
            code="UNAUTHORIZED", message="Refresh token não reconhecido", http_status=401
        )
    if rt.revogado_em is not None:
        await revoke_token_chain(sub, session)
        raise DomainError(
            code="UNAUTHORIZED",
            message="Reuso de refresh token detectado — sessão revogada",
            http_status=401,
        )
    rt.revogado_em = datetime.now(UTC).isoformat()
    new_access = create_access_token({"sub": sub})
    new_refresh = await create_refresh_token({"sub": sub}, session)
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "expires_in": settings.access_token_ttl_seconds,
    }


async def revoke_token_chain(terceiro_id: str, session: AsyncSession) -> None:
    now_iso = datetime.now(UTC).isoformat()
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.terceiro_id == terceiro_id, RefreshToken.revogado_em.is_(None))
        .values(revogado_em=now_iso)
    )
