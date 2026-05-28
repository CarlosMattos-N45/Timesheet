from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

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
    from app.models import LogAuditoria, Terceiro
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
        s.add(LogAuditoria(
            id=str(uuid4()), entidade="Jornada", entidade_id="j-1",
            autor="u@x.com", antes_json=None, depois_json='{"a":1}',
            motivo="ajuste", criado_em=now,
        ))
        s.add(LogAuditoria(
            id=str(uuid4()), entidade="Jornada", entidade_id="j-1",
            autor="u@x.com", antes_json='{"a":1}', depois_json='{"a":2}',
            motivo="re-ajuste", criado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_auditoria_filters_and_orders_desc(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get(
            "/api/v1/auditoria?entidade=Jornada&entidade_id=j-1",
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["motivo"] == "re-ajuste"  # mais recente primeiro
    assert body[1]["motivo"] == "ajuste"


@pytest.mark.asyncio
async def test_get_auditoria_invalid_entidade_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await login_with_app(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get(
            "/api/v1/auditoria?entidade=Foo&entidade_id=x",
            headers={"Authorization": f"Bearer {tok}"},
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_auditoria_requires_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/auditoria?entidade=Jornada&entidade_id=j-1")
    assert r.status_code == 401
