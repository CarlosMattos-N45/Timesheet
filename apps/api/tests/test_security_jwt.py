from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import db as db_mod
from app.core.base import Base
from app.core.errors import DomainError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    rotate_refresh_token,
)
from app.models import RefreshToken, Terceiro


@pytest_asyncio.fixture
async def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "test-secret-key-min-32-chars-abcdef")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        t = Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="x@y.com", senha_hash="h",
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        )
        s.add(t)
        await s.commit()
        yield s
    await engine.dispose()


def test_create_access_token_contains_required_claims() -> None:
    tok = create_access_token({"sub": "t-1"})
    payload = decode_token(tok)
    assert payload["sub"] == "t-1"
    assert payload["type"] == "access"
    assert "exp" in payload and "iat" in payload and "jti" in payload


def test_decode_expired_token_raises() -> None:
    tok = create_access_token({"sub": "t-1"}, ttl_seconds=-1)
    with pytest.raises(DomainError) as exc:
        decode_token(tok)
    assert exc.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_create_refresh_token_persists_in_db(session: AsyncSession) -> None:
    jwt = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert len(rows) == 1
    assert rows[0].revogado_em is None
    assert rows[0].token_hash == hashlib.sha256(jwt.encode()).hexdigest()


@pytest.mark.asyncio
async def test_rotate_refresh_token_revokes_old_and_issues_new(session: AsyncSession) -> None:
    old = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    pair = await rotate_refresh_token(old, session)
    await session.commit()
    assert "access_token" in pair and "refresh_token" in pair
    assert pair["expires_in"] == 900
    assert pair["refresh_token"] != old
    rows = (
        await session.execute(select(RefreshToken).order_by(RefreshToken.criado_em))
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].revogado_em is not None
    assert rows[1].revogado_em is None


@pytest.mark.asyncio
async def test_reuse_of_revoked_token_revokes_full_chain(session: AsyncSession) -> None:
    r1 = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    pair = await rotate_refresh_token(r1, session)  # r1 revogado, r2 ativo
    await session.commit()
    r2 = pair["refresh_token"]
    await rotate_refresh_token(r2, session)  # r2 revogado, r3 ativo
    await session.commit()
    with pytest.raises(DomainError) as exc:
        await rotate_refresh_token(r1, session)
    await session.commit()
    assert exc.value.code == "UNAUTHORIZED"
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert all(rt.revogado_em is not None for rt in rows)
