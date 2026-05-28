from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
    from app.models import Terceiro  # noqa: PLC0415

    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
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
                criado_em=datetime.now(UTC).isoformat(),
                atualizado_em=datetime.now(UTC).isoformat(),
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


def _payload(
    *,
    tipo: str = "INICIO_JORNADA",
    h: str = "2026-05-27T09:02:00Z",
    origem: str = "AGENTE_AUTOMATICO",
    idem: str | None = None,
) -> dict:
    return {
        "tipo": tipo,
        "horario_registrado": h,
        "horario_efetivo": None,
        "origem": origem,
        "idempotency_key": idem or str(uuid4()),
    }


@pytest.mark.asyncio
async def test_post_marcacao_creates_marcacao_and_jornada(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, Marcacao  # noqa: PLC0415

    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(),
        )
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["tipo"] == "INICIO_JORNADA"
    assert body["origem"] == "AGENTE_AUTOMATICO"
    assert body["status"] == "CONFIRMADA"
    assert body["jornada_id"]
    async with sm() as s:
        jornadas = (await s.execute(select(Jornada))).scalars().all()
        marcacoes = (await s.execute(select(Marcacao))).scalars().all()
        assert len(jornadas) == 1
        assert jornadas[0].data == "2026-05-27"
        assert jornadas[0].status == "EM_ANDAMENTO"
        assert len(marcacoes) == 1


@pytest.mark.asyncio
async def test_post_marcacao_idempotency_returns_same_record(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Marcacao  # noqa: PLC0415

    tok = await _login(app)
    idem = str(uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(idem=idem),
        )
        r2 = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(idem=idem),
        )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    async with sm() as s:
        rows = (await s.execute(select(Marcacao))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_post_marcacao_same_tipo_diff_idem_returns_409(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(),
        )
        assert r1.status_code == 201
        r2 = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(),
        )
    assert r2.status_code == 409
    assert r2.json()["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_post_marcacao_rejects_ajuste_web_from_agent(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(origem="AJUSTE_WEB"),
        )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"
    assert any("origem" in d["field"] for d in r.json()["details"])


@pytest.mark.asyncio
async def test_post_marcacao_weekend_blocked_when_not_allowed(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    # 2026-05-30 é sábado
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(h="2026-05-30T09:02:00Z"),
        )
    assert r.status_code == 422
    assert r.json()["code"] == "FIM_DE_SEMANA_NAO_PERMITIDO"


@pytest.mark.asyncio
async def test_post_marcacao_weekend_allowed_when_flag_true(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Terceiro  # noqa: PLC0415

    async with sm() as s:
        t = (await s.execute(select(Terceiro))).scalar_one()
        t.trabalha_fim_de_semana = 1
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(h="2026-05-30T09:02:00Z"),
        )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_post_marcacao_post_to_ajuste_web_record_returns_409_with_code(
    app_and_session,
) -> None:
    app, sm = app_and_session
    from app.models import Jornada, Marcacao  # noqa: PLC0415

    # Cria jornada + marcacao com origem=AJUSTE_WEB diretamente
    async with sm() as s:
        s.add(
            Jornada(
                id="j-1",
                terceiro_id="t-1",
                data="2026-05-27",
                status="AJUSTADA_MANUALMENTE",
                criada_em=datetime.now(UTC).isoformat(),
            )
        )
        s.add(
            Marcacao(
                id="m-existing",
                jornada_id="j-1",
                tipo="INICIO_JORNADA",
                horario_registrado="2026-05-27T09:00:00+00:00",
                horario_efetivo="2026-05-27T09:00:00+00:00",
                origem="AJUSTE_WEB",
                status="AJUSTADA",
                idempotency_key="11111111-1111-1111-1111-111111111111",
                criada_em=datetime.now(UTC).isoformat(),
            )
        )
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/marcacoes",
            headers={"Authorization": f"Bearer {tok}"},
            json=_payload(),
        )
    assert r.status_code == 409
    assert r.json()["code"] == "AJUSTE_WEB_WINS"


@pytest.mark.asyncio
async def test_get_marcacoes_lists_only_authenticated_terceiro(app_and_session) -> None:
    app, sm = app_and_session
    from app.core.security import hash_password  # noqa: PLC0415
    from app.models import Jornada, Marcacao, Terceiro  # noqa: PLC0415

    # Adicionar outro terceiro com sua propria jornada
    async with sm() as s:
        s.add(
            Terceiro(
                id="t-2",
                nome="Outro",
                empresa_nome="X",
                empresa_cnpj="00000000000191",
                horario_inicio_jornada="09:00:00",
                horario_saida_almoco="12:00:00",
                horario_retorno_almoco="13:00:00",
                horario_fim_jornada="18:00:00",
                trabalha_fim_de_semana=0,
                email_contato="outro@x.com",
                senha_hash=hash_password("X" * 8),
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
                idempotency_key="22222222-2222-2222-2222-222222222222",
                criada_em=datetime.now(UTC).isoformat(),
            )
        )
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    # Lista deve ser vazia (terceiro autenticado t-1 ainda não criou marcações)
    assert body == []
