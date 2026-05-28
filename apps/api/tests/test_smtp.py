from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.helpers import login_with_app


@pytest_asyncio.fixture
async def app_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    from app.core import config  # noqa: PLC0415
    from app.core import db as db_mod  # noqa: PLC0415

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

    app = create_app()
    # Força inicialização do crypto_state (configurado em lifespan)
    from app.core import crypto_state  # noqa: PLC0415

    crypto_state.reset_for_tests()
    crypto_state.configure()
    yield app, sm
    await engine.dispose()


async def _login(app) -> str:
    return await login_with_app(app)


def _valid_payload() -> dict:
    return {
        "host": "127.0.0.1",
        "port": 1025,
        "username": "user@example.com",
        "password": "smtp-secret-pwd",
        "use_starttls": False,
        "from_address": "noreply@example.com",
    }


@pytest.mark.asyncio
async def test_get_smtp_returns_404_when_empty(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_put_smtp_creates_and_get_returns_without_password(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.put("/api/v1/smtp", headers=auth, json=_valid_payload())
        assert r1.status_code == 200
        body = r1.json()
        assert body["host"] == "127.0.0.1"
        assert body["port"] == 1025
        assert body["username"] == "user@example.com"  # descriptografado
        assert body["from_address"] == "noreply@example.com"
        assert (
            "password" not in body
            and "password_enc" not in body
            and "username_enc" not in body
        )

        r2 = await c.get("/api/v1/smtp", headers=auth)
        assert r2.status_code == 200
        assert r2.json()["username"] == "user@example.com"


@pytest.mark.asyncio
async def test_username_and_password_are_encrypted_on_disk(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import SmtpConfig  # noqa: PLC0415

    tok = await _login(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers=auth, json=_valid_payload())
    async with sm() as s:
        cfg = (await s.execute(select(SmtpConfig))).scalar_one()
        # Texto claro NUNCA aparece na coluna enc
        assert cfg.username_enc != "user@example.com"
        assert "user@example.com" not in cfg.username_enc
        assert cfg.password_enc != "smtp-secret-pwd"
        assert "smtp-secret-pwd" not in cfg.password_enc
        # Decifragem funciona
        from app.core import crypto, crypto_state  # noqa: PLC0415

        assert (
            crypto.aes_gcm_decrypt(crypto_state.SUBKEY_SMTP, cfg.username_enc)
            == b"user@example.com"
        )
        assert (
            crypto.aes_gcm_decrypt(crypto_state.SUBKEY_SMTP, cfg.password_enc)
            == b"smtp-secret-pwd"
        )


@pytest.mark.asyncio
async def test_put_smtp_updates_existing(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers=auth, json=_valid_payload())
        new = _valid_payload() | {"host": "novo.example.com", "port": 465, "use_starttls": True}
        r = await c.put("/api/v1/smtp", headers=auth, json=new)
    assert r.status_code == 200
    body = r.json()
    assert body["host"] == "novo.example.com"
    assert body["port"] == 465
    assert body["use_starttls"] is True


@pytest.mark.asyncio
async def test_put_smtp_rejects_invalid_port(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"port": 0}
        r = await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=bad)
    assert r.status_code == 422
    assert any("port" in d["field"] for d in r.json()["details"])


@pytest.mark.asyncio
async def test_put_smtp_rejects_invalid_email_from(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"from_address": "not-email"}
        r = await c.put(
            "/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=bad
        )
    assert r.status_code == 422
    assert any("from_address" in d["field"] for d in r.json()["details"])


@pytest.mark.asyncio
async def test_post_smtp_test_without_config_returns_422_smtp_not_configured(
    app_and_session,
) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/smtp/test", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
    assert r.json()["code"] == "SMTP_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_post_smtp_test_unreachable_host_returns_400(
    app_and_session, monkeypatch
) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    auth = {"Authorization": f"Bearer {tok}"}
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"host": "127.0.0.2", "port": 65530}  # porta improvável
        await c.put("/api/v1/smtp", headers=auth, json=bad)
        r = await c.post("/api/v1/smtp/test", headers=auth)
    assert r.status_code == 400
    assert r.json()["code"] == "SMTP_TEST_FAILED"


@pytest.mark.asyncio
async def test_endpoints_require_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.get("/api/v1/smtp")
        r2 = await c.put("/api/v1/smtp", json=_valid_payload())
        r3 = await c.post("/api/v1/smtp/test")
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
