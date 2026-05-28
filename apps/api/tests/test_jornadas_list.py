from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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
        # Jornada completa 2026-05-27 (FECHADA, 8h efetivas)
        s.add(Jornada(id="j-1", terceiro_id="t-1", data="2026-05-27", status="FECHADA",
                       total_horas_apuradas_s=28800, criada_em=now))
        for tipo, h in [
            ("INICIO_JORNADA", "2026-05-27T09:00:00+00:00"),
            ("SAIDA_ALMOCO", "2026-05-27T12:00:00+00:00"),
            ("RETORNO_ALMOCO", "2026-05-27T13:00:00+00:00"),
            ("FIM_JORNADA", "2026-05-27T18:00:00+00:00"),
        ]:
            s.add(Marcacao(
                id=f"m-{tipo}", jornada_id="j-1", tipo=tipo,
                horario_registrado=h, horario_efetivo=h,
                origem="AGENTE_AUTOMATICO", status="CONFIRMADA",
                idempotency_key=(tipo + "-id-aaaaaaaaaaaaaaaaaaaaaaaa")[:36],
                criada_em=now,
            ))
        # Jornada com marcacao pendente 2026-05-28
        s.add(Jornada(id="j-2", terceiro_id="t-1", data="2026-05-28", status="PENDENTE",
                       criada_em=now))
        s.add(Marcacao(
            id="m-pend", jornada_id="j-2", tipo="INICIO_JORNADA",
            horario_registrado="2026-05-28T09:00:00+00:00",
            origem="AGENTE_AUTOMATICO", status="PENDENTE",
            idempotency_key="pend-id-aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            criada_em=now,
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_jornadas_returns_month_with_totals(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas?mes=2026-05", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["mes_referencia"] == "2026-05"
    assert body["total_horas_mes_s"] == 28800  # apenas j-1 conta; j-2 com total=null
    assert len(body["jornadas"]) == 2
    j1 = next(j for j in body["jornadas"] if j["data"] == "2026-05-27")
    assert j1["status"] == "FECHADA"
    assert j1["tem_marcacao_pendente"] is False
    assert j1["total_horas_apuradas_s"] == 28800
    j2 = next(j for j in body["jornadas"] if j["data"] == "2026-05-28")
    assert j2["tem_marcacao_pendente"] is True


@pytest.mark.asyncio
async def test_list_jornadas_empty_returns_zero_total(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas?mes=2026-04", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"mes_referencia": "2026-04", "total_horas_mes_s": 0, "jornadas": []}


@pytest.mark.asyncio
async def test_list_jornadas_invalid_mes_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas?mes=invalid", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
