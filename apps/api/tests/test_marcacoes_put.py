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
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    from app.core import config  # noqa: PLC0415
    from app.core import db as db_mod

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base  # noqa: PLC0415
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models import Jornada, Marcacao, Terceiro  # noqa: PLC0415

    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    now = datetime.now(UTC).isoformat()
    async with sm() as s:
        s.add(
            Terceiro(
                id="t-1",
                nome="X",
                empresa_nome="Y",
                empresa_cnpj="00000000000191",
                horario_inicio_jornada="09:00:00",
                horario_saida_almoco="12:00:00",
                horario_retorno_almoco="13:00:00",
                horario_fim_jornada="18:00:00",
                trabalha_fim_de_semana=0,
                email_contato="u@x.com",
                senha_hash=hash_password("Senha123!"),
                criado_em=now,
                atualizado_em=now,
            )
        )
        s.add(
            Jornada(
                id="j-1", terceiro_id="t-1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=now
            )
        )
        s.add(
            Marcacao(
                id="m-1",
                jornada_id="j-1",
                tipo="INICIO_JORNADA",
                horario_registrado="2026-05-27T09:02:00+00:00",
                origem="AGENTE_AUTOMATICO",
                status="CONFIRMADA",
                idempotency_key="11111111-1111-1111-1111-111111111111",
                criada_em=now,
            )
        )
        await s.commit()
    from app.main import create_app  # noqa: PLC0415

    yield create_app(), sm
    await engine.dispose()


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_put_marcacao_updates_and_audits(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, LogAuditoria, Marcacao  # noqa: PLC0415

    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/marcacoes/m-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "horario_efetivo": "2026-05-27T09:00:00+00:00",
                "motivo": "corrigir atraso de relógio",
            },
        )
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["origem"] == "AJUSTE_WEB"
    assert body["status"] == "AJUSTADA"
    assert body["horario_efetivo"] == "2026-05-27T09:00:00+00:00"
    async with sm() as s:
        m = (await s.execute(select(Marcacao).where(Marcacao.id == "m-1"))).scalar_one()
        assert m.origem == "AJUSTE_WEB"
        j = (await s.execute(select(Jornada).where(Jornada.id == "j-1"))).scalar_one()
        assert j.status == "AJUSTADA_MANUALMENTE"
        audits = (
            await s.execute(
                select(LogAuditoria).where(LogAuditoria.entidade == "Marcacao")
            )
        ).scalars().all()
        assert len(audits) == 1
        assert audits[0].motivo == "corrigir atraso de relógio"


@pytest.mark.asyncio
async def test_put_marcacao_motivo_too_short_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/marcacoes/m-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={"horario_efetivo": "2026-05-27T09:00:00+00:00", "motivo": "abc"},
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_marcacao_inexistente_returns_404(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/marcacoes/nao-existe",
            headers={"Authorization": f"Bearer {tok}"},
            json={"horario_efetivo": "2026-05-27T09:00:00+00:00", "motivo": "qualquer coisa"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_marcacao_de_outro_terceiro_returns_404(app_and_session) -> None:
    app, sm = app_and_session
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models import Jornada, Marcacao, Terceiro  # noqa: PLC0415

    async with sm() as s:
        s.add(
            Terceiro(
                id="t-2",
                nome="X",
                empresa_nome="Y",
                empresa_cnpj="00000000000191",
                horario_inicio_jornada="09:00:00",
                horario_saida_almoco="12:00:00",
                horario_retorno_almoco="13:00:00",
                horario_fim_jornada="18:00:00",
                trabalha_fim_de_semana=0,
                email_contato="outro@x.com",
                senha_hash=hash_password("Senha123!"),
                criado_em=datetime.now(UTC).isoformat(),
                atualizado_em=datetime.now(UTC).isoformat(),
            )
        )
        s.add(
            Jornada(
                id="j-other",
                terceiro_id="t-2",
                data="2026-05-27",
                status="EM_ANDAMENTO",
                criada_em=datetime.now(UTC).isoformat(),
            )
        )
        s.add(
            Marcacao(
                id="m-other",
                jornada_id="j-other",
                tipo="INICIO_JORNADA",
                horario_registrado="2026-05-27T09:00:00+00:00",
                origem="AGENTE_AUTOMATICO",
                status="CONFIRMADA",
                idempotency_key="22222222-2222-2222-2222-222222222222",
                criada_em=datetime.now(UTC).isoformat(),
            )
        )
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/marcacoes/m-other",
            headers={"Authorization": f"Bearer {tok}"},
            json={"horario_efetivo": "2026-05-27T09:00:00+00:00", "motivo": "tentando hackear"},
        )
    assert r.status_code == 404
