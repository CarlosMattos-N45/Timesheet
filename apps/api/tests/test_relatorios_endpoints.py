from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

_FAKE_PDF = b"%PDF-fake"


@pytest.fixture(autouse=True)
def mock_render_pdf(monkeypatch):
    """Mocka render_pdf em todos os testes deste módulo — evita dependência do WeasyPrint/GTK."""
    from app.modules.relatorios import service as svc_mod

    monkeypatch.setattr(svc_mod, "render_pdf", AsyncMock(return_value=_FAKE_PDF))


@pytest_asyncio.fixture
async def app_and_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    monkeypatch.setenv(  # desabilita scheduler nos testes HTTP
        "TIMESHEET_SCHEDULER_ENABLED", "false"
    )
    from app.core import config
    from app.core import db as db_mod
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Jornada, Marcacao, Terceiro

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None

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
                email_destinatario_relatorio="rh@x.com",
            )
        )
        s.add(
            Jornada(
                id="j-1",
                terceiro_id="t-1",
                data="2026-05-27",
                status="FECHADA",
                total_horas_apuradas_s=28800,
                criada_em=now,
            )
        )
        for i, (tipo, h) in enumerate(
            [
                ("INICIO_JORNADA", "2026-05-27T09:00:00+00:00"),
                ("SAIDA_ALMOCO", "2026-05-27T12:00:00+00:00"),
                ("RETORNO_ALMOCO", "2026-05-27T13:00:00+00:00"),
                ("FIM_JORNADA", "2026-05-27T18:00:00+00:00"),
            ]
        ):
            s.add(
                Marcacao(
                    id=f"m-{i}",
                    jornada_id="j-1",
                    tipo=tipo,
                    horario_registrado=h,
                    horario_efetivo=h,
                    origem="AGENTE_AUTOMATICO",
                    status="CONFIRMADA",
                    idempotency_key=f"idem-{i}-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"[:36],
                    criada_em=now,
                )
            )
        await s.commit()
    from app.core import crypto_state

    crypto_state.reset_for_tests()
    crypto_state.configure()
    from app.main import create_app

    yield create_app(), sm
    await engine.dispose()
    crypto_state.reset_for_tests()


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_relatorio_returns_pdf(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get(
            "/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_get_relatorio_meta(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        # Gera primeiro via download
        await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
        r = await c.get(
            "/api/v1/relatorios/2026-05/meta", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 200
    body = r.json()
    assert body["mes_referencia"] == "2026-05"
    assert body["caminho_arquivo"]
    assert body["gerado_em"]
    assert body["invalidado_em"] is None


@pytest.mark.asyncio
async def test_post_enviar_sem_smtp_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 422
    assert r.json()["code"] == "SMTP_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_post_enviar_success_with_mailhog(app_and_session, monkeypatch) -> None:
    """Mocka send_pdf_sync para simular envio SMTP bem-sucedido sem depender do Mailhog."""
    app, sm = app_and_session
    from app.models import HistoricoEnvioRelatorio
    from app.modules.relatorios import service as svc_mod

    monkeypatch.setattr(svc_mod, "send_pdf_sync", lambda **_kwargs: None)
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put(
            "/api/v1/smtp",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "host": "127.0.0.1",
                "port": 1025,
                "username": "anon",
                "password": "anon",
                "use_starttls": False,
                "from_address": "noreply@x.com",
            },
        )
        # gera relatorio
        await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
        r = await c.post(
            "/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "SUCESSO"
    async with sm() as s:
        hist = (await s.execute(select(HistoricoEnvioRelatorio))).scalars().all()
        assert len(hist) == 1
        assert hist[0].status == "SUCESSO"


@pytest.mark.asyncio
async def test_post_enviar_failure_records_historico_falha(app_and_session, monkeypatch) -> None:
    app, sm = app_and_session
    from app.models import HistoricoEnvioRelatorio

    # Mocka SMTP para falhar imediatamente (sem timeout real nem sleeps entre retries)
    monkeypatch.setattr("app.modules.relatorios.smtp_send.time.sleep", lambda _: None)

    def _smtp_fail(*args, **kwargs):
        raise OSError("Connection refused (mock)")

    monkeypatch.setattr("app.modules.relatorios.smtp_send.smtplib.SMTP", _smtp_fail)
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put(
            "/api/v1/smtp",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "host": "127.0.0.2",
                "port": 65530,
                "username": "x",
                "password": "x",
                "use_starttls": False,
                "from_address": "noreply@x.com",
            },
        )
        await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
        r = await c.post(
            "/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 500
    assert r.json()["code"] == "SMTP_SEND_FAILED"
    async with sm() as s:
        hist = (await s.execute(select(HistoricoEnvioRelatorio))).scalars().all()
        assert len(hist) == 1
        assert hist[0].status == "FALHA"
        assert hist[0].erro_mensagem


@pytest.mark.asyncio
async def test_get_historico_orders_desc(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import HistoricoEnvioRelatorio

    async with sm() as s:
        s.add(
            HistoricoEnvioRelatorio(
                id=str(uuid4()),
                mes_referencia="2026-05",
                email_destinatario="rh@x.com",
                status="FALHA",
                erro_mensagem="erro 1",
                enviado_em="2026-05-01T00:00:00+00:00",
            )
        )
        s.add(
            HistoricoEnvioRelatorio(
                id=str(uuid4()),
                mes_referencia="2026-05",
                email_destinatario="rh@x.com",
                status="SUCESSO",
                erro_mensagem=None,
                enviado_em="2026-05-02T00:00:00+00:00",
            )
        )
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get(
            "/api/v1/relatorios/2026-05/historico", headers={"Authorization": f"Bearer {tok}"}
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["status"] == "SUCESSO"  # mais recente primeiro


# ---------------------------------------------------------------------------
# Testes unitários de smtp_send (cobrem SMTP_SSL e caminho de sucesso)
# ---------------------------------------------------------------------------


def test_send_pdf_sync_smtp_ssl_success(monkeypatch) -> None:
    """Cobre o caminho port==465 (SMTP_SSL) com envio bem-sucedido."""
    from unittest.mock import MagicMock

    from app.modules.relatorios.smtp_send import send_pdf_sync  # noqa: PLC0415

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda self: self
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.login = MagicMock()
    mock_smtp.send_message = MagicMock()

    monkeypatch.setattr(
        "app.modules.relatorios.smtp_send.smtplib.SMTP_SSL",
        lambda *a, **kw: mock_smtp,
    )

    send_pdf_sync(
        host="mail.example.com",
        port=465,
        username="user",
        password="pass",
        use_starttls=False,
        from_address="noreply@example.com",
        to_email="dest@example.com",
        pdf_bytes=b"%PDF-fake",
        mes_referencia="2026-05",
    )
    mock_smtp.send_message.assert_called_once()


def test_send_pdf_sync_smtp_plain_success(monkeypatch) -> None:
    """Cobre o caminho SMTP normal (port!=465) com envio bem-sucedido."""
    from unittest.mock import MagicMock

    from app.modules.relatorios.smtp_send import send_pdf_sync  # noqa: PLC0415

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda self: self
    mock_smtp.__exit__ = MagicMock(return_value=False)
    mock_smtp.login = MagicMock()
    mock_smtp.send_message = MagicMock()

    monkeypatch.setattr(
        "app.modules.relatorios.smtp_send.smtplib.SMTP", lambda *a, **kw: mock_smtp
    )

    send_pdf_sync(
        host="mail.example.com",
        port=587,
        username="user",
        password="pass",
        use_starttls=True,
        from_address="noreply@example.com",
        to_email="dest@example.com",
        pdf_bytes=b"%PDF-fake",
        mes_referencia="2026-05",
    )
    mock_smtp.starttls.assert_called_once()
    mock_smtp.send_message.assert_called_once()
