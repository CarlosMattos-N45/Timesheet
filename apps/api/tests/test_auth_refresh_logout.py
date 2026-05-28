from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def app_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Terceiro
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="user@example.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_returns_new_pair_and_revokes_old(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        rt_old = login.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt_old})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != rt_old
    async with sm() as s:
        stmt = select(RefreshToken).order_by(RefreshToken.criado_em)
        rows = (await s.execute(stmt)).scalars().all()
        assert rows[0].revogado_em is not None
        assert rows[1].revogado_em is None


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_full_chain(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        rt1 = login.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
        # rota rt2
        await c.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]})
        # Reuso do rt1 (já revogado) — revoga toda a cadeia
        bad = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert bad.status_code == 401
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        assert all(rt.revogado_em is not None for rt in rows)


@pytest.mark.asyncio
async def test_logout_revokes_current_refresh(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        body = login.json()
        r = await c.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {body['access_token']}"},
            json={"refresh_token": body["refresh_token"]},
        )
    assert r.status_code == 204
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        assert all(rt.revogado_em is not None for rt in rows)
