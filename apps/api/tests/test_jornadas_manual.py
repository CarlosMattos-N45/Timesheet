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
    from app.models import Terceiro
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
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


def _valid_manual() -> dict:
    return {
        "data": "2026-05-27",
        "marcacoes": [
            {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T09:00:00+00:00"},
            {"tipo": "SAIDA_ALMOCO", "horario_efetivo": "2026-05-27T12:00:00+00:00"},
            {"tipo": "RETORNO_ALMOCO", "horario_efetivo": "2026-05-27T13:00:00+00:00"},
            {"tipo": "FIM_JORNADA", "horario_efetivo": "2026-05-27T18:00:00+00:00"},
        ],
        "atividade": "Trabalhei no projeto X durante o dia inteiro",
        "motivo": "esqueci de fazer login no PC",
    }


@pytest.mark.asyncio
async def test_post_jornada_manual_creates_all(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, Jornada, Justificativa, LogAuditoria, Marcacao
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers=auth, json=_valid_manual())
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["status"] == "AJUSTADA_MANUALMENTE"
    assert len(body["marcacoes"]) == 4
    async with sm() as s:
        j = (await s.execute(select(Jornada))).scalar_one()
        assert j.status == "AJUSTADA_MANUALMENTE"
        marcs = (await s.execute(select(Marcacao))).scalars().all()
        assert len(marcs) == 4
        assert all(m.origem == "AJUSTE_WEB" for m in marcs)
        ats = (await s.execute(select(Atividade))).scalars().all()
        assert len(ats) == 1
        justifs = (await s.execute(select(Justificativa))).scalars().all()
        assert len(justifs) == 1
        stmt_a = select(LogAuditoria).where(LogAuditoria.entidade == "Jornada")
        audits = (await s.execute(stmt_a)).scalars().all()
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_post_jornada_manual_in_existing_day_returns_409(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/jornadas/manual", headers=auth, json=_valid_manual())
        r2 = await c.post("/api/v1/jornadas/manual", headers=auth, json=_valid_manual())
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_only_3_marcacoes(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    payload = _valid_manual()
    payload["marcacoes"].pop()
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers=auth, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_short_atividade(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    payload = _valid_manual()
    payload["atividade"] = "curta"
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers=auth, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_non_chronological(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    payload = _valid_manual()
    payload["marcacoes"][0]["horario_efetivo"] = "2026-05-27T20:00:00+00:00"  # depois do fim
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers=auth, json=payload)
    assert r.status_code == 422
