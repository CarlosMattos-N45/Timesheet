from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.helpers import login_with_app


@pytest_asyncio.fixture
async def app_and_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Jornada, Terceiro
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    now = datetime.now(UTC).isoformat()
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=now, atualizado_em=now,
        ))
        s.add(Jornada(
            id="j-1", terceiro_id="t-1", data="2026-05-27", status="FECHADA", criada_em=now
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_post_atividade_creates_and_audits(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, LogAuditoria
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/jornadas/j-1/atividade",
            headers={"Authorization": f"Bearer {tok}"},
            json={"descricao": "trabalhei oito horas no projeto X"},
        )
    assert r.status_code == 201
    async with sm() as s:
        a = (await s.execute(select(Atividade))).scalar_one()
        assert a.descricao == "trabalhei oito horas no projeto X"
        stmt = select(LogAuditoria).where(LogAuditoria.entidade == "Atividade")
        audits = (await s.execute(stmt)).scalars().all()
        assert len(audits) == 1
        assert audits[0].antes_json is None


@pytest.mark.asyncio
async def test_post_atividade_updates_existing(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, LogAuditoria
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/jornadas/j-1/atividade", headers={"Authorization": f"Bearer {tok}"},
                     json={"descricao": "atividade original mais longa"})
        await c.post("/api/v1/jornadas/j-1/atividade", headers={"Authorization": f"Bearer {tok}"},
                     json={"descricao": "atividade atualizada mais detalhada"})
    async with sm() as s:
        ats = (await s.execute(select(Atividade))).scalars().all()
        assert len(ats) == 1
        assert ats[0].descricao == "atividade atualizada mais detalhada"
        assert ats[0].atualizado_em is not None
        stmt = select(LogAuditoria).where(LogAuditoria.entidade == "Atividade")
        audits = (await s.execute(stmt)).scalars().all()
        assert len(audits) == 2
        assert audits[1].antes_json is not None  # 2o tem antes


@pytest.mark.asyncio
async def test_post_atividade_short_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/jornadas/j-1/atividade",
            headers={"Authorization": f"Bearer {tok}"},
            json={"descricao": "curta"},
        )
    assert r.status_code == 422
