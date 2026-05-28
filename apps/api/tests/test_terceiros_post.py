from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata
    from app.core.base import Base
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    from app.main import create_app
    yield create_app()
    await engine.dispose()


def _payload() -> dict:
    return {
        "nome": "Maria Silva",
        "empresa_nome": "ACME LTDA",
        "empresa_cnpj": "00000000000191",  # CNPJ valido
        "horario_inicio_jornada": "09:00:00",
        "horario_saida_almoco": "12:00:00",
        "horario_retorno_almoco": "13:00:00",
        "horario_fim_jornada": "18:00:00",
        "trabalha_fim_de_semana": False,
        "email_contato": "maria@acme.com",
        "email_destinatario_relatorio": "rh@acme.com",
        "senha": "MinhaSenha123!",
        "senha_confirmacao": "MinhaSenha123!",
    }


@pytest.mark.asyncio
async def test_post_terceiros_creates_first_terceiro(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/terceiros", json=_payload())
    assert r.status_code == 201, r.json()
    body = r.json()
    assert "terceiro_id" in body and "criado_em" in body
    assert "access_token" not in body  # endpoint NAO retorna token


@pytest.mark.asyncio
async def test_post_terceiros_second_call_returns_setup_already_done(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.post("/api/v1/terceiros", json=_payload())
        assert r1.status_code == 201
        payload2 = _payload() | {"email_contato": "outra@acme.com"}
        r2 = await c.post("/api/v1/terceiros", json=payload2)
    assert r2.status_code == 403
    assert r2.json() == {
        "code": "SETUP_ALREADY_DONE",
        "message": "Cadastro inicial já realizado",
        "details": [],
    }


@pytest.mark.asyncio
async def test_post_terceiros_rejects_invalid_cnpj(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"empresa_cnpj": "12345678901234"}
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(d["field"].endswith("empresa_cnpj") for d in body["details"])


@pytest.mark.asyncio
async def test_post_terceiros_rejects_non_chronological_horarios(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"horario_inicio_jornada": "14:00:00"}  # depois do almoço
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_post_terceiros_rejects_mismatched_passwords(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"senha_confirmacao": "OutraSenha456!"}
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert any("senha_confirmacao" in d["field"] for d in body["details"])
