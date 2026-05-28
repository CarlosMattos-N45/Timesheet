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
            trabalha_fim_de_semana=0, email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_privacidade_returns_false_when_empty(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"accepted": False, "versao_aviso": None, "aceito_em": None}


@pytest.mark.asyncio
async def test_post_aceitar_inserts_row(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 204
    async with sm() as s:
        row = (await s.execute(select(PrivacyAcceptance))).scalar_one()
        assert row.id == 1
        assert row.versao_aviso == "1.0"
        assert row.aceito_em


@pytest.mark.asyncio
async def test_get_privacidade_returns_true_after_aceite(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["versao_aviso"] == "1.0"
    assert body["aceito_em"]


@pytest.mark.asyncio
async def test_post_aceitar_is_idempotent(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    async with sm() as s:
        rows = (await s.execute(select(PrivacyAcceptance))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_privacidade_returns_false_for_old_version(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    async with sm() as s:
        s.add(PrivacyAcceptance(id=1, aceito_em=datetime.now(UTC).isoformat(), versao_aviso="0.9"))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is False  # versao antiga != versao atual
    assert body["versao_aviso"] == "0.9"


@pytest.mark.asyncio
async def test_post_aceitar_updates_old_version_inplace(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    async with sm() as s:
        s.add(PrivacyAcceptance(id=1, aceito_em="2025-01-01T00:00:00+00:00", versao_aviso="0.9"))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    async with sm() as s:
        row = (await s.execute(select(PrivacyAcceptance))).scalar_one()
        assert row.versao_aviso == "1.0"
        assert row.aceito_em != "2025-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_endpoints_require_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.get("/api/v1/privacidade")
        r2 = await c.post("/api/v1/privacidade/aceitar")
    assert r1.status_code == 401
    assert r2.status_code == 401
