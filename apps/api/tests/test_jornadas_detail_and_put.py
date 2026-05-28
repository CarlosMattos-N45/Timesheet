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
    from app.models import Jornada, Marcacao, Terceiro
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
        s.add(Jornada(id="j-1", terceiro_id="t-1", data="2026-05-27", status="FECHADA",
                       total_horas_apuradas_s=28800, criada_em=now))
        for i, (tipo, h) in enumerate([
            ("INICIO_JORNADA", "2026-05-27T09:00:00+00:00"),
            ("SAIDA_ALMOCO", "2026-05-27T12:00:00+00:00"),
            ("RETORNO_ALMOCO", "2026-05-27T13:00:00+00:00"),
            ("FIM_JORNADA", "2026-05-27T18:00:00+00:00"),
        ]):
            s.add(Marcacao(
                id=f"m-{i}", jornada_id="j-1", tipo=tipo,
                horario_registrado=h, horario_efetivo=h,
                origem="AGENTE_AUTOMATICO", status="CONFIRMADA",
                idempotency_key=f"idem-{i}-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"[:36],
                criada_em=now,
            ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_jornada_detalhe(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas/j-1", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["id"] == "j-1"
    assert body["status"] == "FECHADA"
    assert len(body["marcacoes"]) == 4
    assert body["total_horas_apuradas_s"] == 28800


@pytest.mark.asyncio
async def test_put_jornada_ajusta_marcacoes_cria_justif_e_audit(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, Justificativa, LogAuditoria, Marcacao
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/jornadas/j-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "marcacoes": [
                    {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T08:55:00+00:00"},
                    {"tipo": "FIM_JORNADA", "horario_efetivo": "2026-05-27T18:05:00+00:00"},
                ],
                "motivo": "ajuste do relogio interno",
            },
        )
    assert r.status_code == 200, r.json()
    async with sm() as s:
        j = (await s.execute(select(Jornada).where(Jornada.id == "j-1"))).scalar_one()
        assert j.status == "AJUSTADA_MANUALMENTE"
        stmt_m = select(Marcacao).where(
            Marcacao.jornada_id == "j-1", Marcacao.tipo == "INICIO_JORNADA"
        )
        m_inicio = (await s.execute(stmt_m)).scalar_one()
        assert m_inicio.horario_efetivo == "2026-05-27T08:55:00+00:00"
        assert m_inicio.origem == "AJUSTE_WEB"
        stmt_j = select(Justificativa).where(Justificativa.jornada_id == "j-1")
        justifs = (await s.execute(stmt_j)).scalars().all()
        assert len(justifs) == 1
        assert justifs[0].motivo == "ajuste do relogio interno"
        stmt_a = select(LogAuditoria).where(LogAuditoria.entidade == "Jornada")
        audits = (await s.execute(stmt_a)).scalars().all()
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_put_jornada_motivo_short_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/jornadas/j-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "marcacoes": [
                    {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T08:55:00+00:00"},
                ],
                "motivo": "abc",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_jornada_inexistente_returns_404(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas/nao-existe", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
