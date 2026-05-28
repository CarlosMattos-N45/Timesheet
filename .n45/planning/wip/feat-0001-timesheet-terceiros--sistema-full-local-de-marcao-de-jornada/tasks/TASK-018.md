---
checkpoint: null
complexity: G
created_at: "2026-05-28 09:40:13"
criteria:
    - done: false
      test: pytest -k test_gerar_pdf_cria_arquivo_e_relatorio_gerado
      text: gerar_pdf gera bytes PDF (inicia com %PDF) e persiste RelatorioGerado(mes_referencia, caminho_arquivo, gerado_em, invalidado_em=null)
    - done: false
      test: pytest -k test_gerar_pdf_sem_jornadas_levanta_no_data
      text: gerar_pdf de mês sem jornadas levanta DomainError code=NO_DATA http_status=422
    - done: false
      test: pytest -k test_invalidacao_seta_invalidado_em_ao_mutar_jornada
      text: Mutação em Jornada/Marcacao/Atividade do mês X dispara after_flush listener e seta relatorio_gerado(mes=X).invalidado_em
    - done: false
      test: pytest -k test_get_relatorio_returns_pdf
      text: GET /api/v1/relatorios/{mes} retorna FileResponse application/pdf com body iniciando em %PDF (gera on-demand se ausente ou invalidado)
    - done: false
      test: pytest -k test_get_relatorio_meta
      text: GET /relatorios/{mes}/meta retorna {mes_referencia,caminho_arquivo,gerado_em,invalidado_em} apos geração
    - done: false
      test: pytest -k test_post_enviar_sem_smtp_returns_422
      text: POST /relatorios/{mes}/enviar sem SmtpConfig retorna 422 code=SMTP_NOT_CONFIGURED
    - done: false
      test: pytest -k test_post_enviar_success_with_mailhog
      text: POST /relatorios/{mes}/enviar com SMTP configurado (Mailhog) retorna 202 status=SUCESSO e cria HistoricoEnvioRelatorio(SUCESSO) (ou skip se Mailhog ausente)
    - done: false
      test: pytest -k test_post_enviar_failure_records_historico_falha
      text: POST /relatorios/{mes}/enviar com host inalcancavel retorna 500 code=SMTP_SEND_FAILED e cria HistoricoEnvioRelatorio(FALHA, erro_mensagem)
    - done: false
      test: pytest -k test_get_historico_orders_desc
      text: GET /relatorios/{mes}/historico retorna lista ordenada enviado_em DESC
    - done: false
      test: pytest -k test_scheduler_jobs_registered_when_enabled
      text: build_scheduler com TIMESHEET_SCHEDULER_ENABLED=true registra jobs relatorios_mensal (cron dia 1 00:00 BRT) e relatorios_purge (cron domingo 02:00)
    - done: false
      test: pytest -k test_scheduler_disabled_when_flag_false
      text: build_scheduler com TIMESHEET_SCHEDULER_ENABLED=false NAO registra jobs
    - done: false
      test: pytest -k test_purge_remove_arquivos_e_relatorios_antigos
      text: purge_old_pdfs remove RelatorioGerado com gerado_em > 24 meses + arquivo físico; preserva recentes
    - done: false
      test: pytest --cov=app/modules/relatorios --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/relatorios
    - done: false
      test: grep -E 'wait_for.*timeout=120|smtp_timeout' apps/api/app/modules/relatorios/pdf.py apps/api/app/modules/relatorios/smtp_send.py
      text: WeasyPrint chamado via asyncio.wait_for(timeout=120) e SMTP via timeout=30 (settings.smtp_timeout)
    - done: false
      test: grep -E '^class (Relatorio|HistoricoEnvio)Repository' apps/api/app/modules/relatorios/repository.py
      text: 'Repository pattern: RelatorioRepository e HistoricoEnvioRepository definidos como classes'
deps:
    - TASK-012
    - TASK-015
    - TASK-017
id: TASK-018
linter: ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 3 — Backend por Domínio
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: pytest tests/test_relatorios_pdf.py tests/test_relatorios_endpoints.py tests/test_scheduler.py -v
title: 'Relatorios + APScheduler + PDF WeasyPrint + SMTP send: GET/POST endpoints, cron mensal/purge, invalidação via after_flush, retry 3x backoff'
updated_at: "2026-05-28 09:40:13"
---
## Contexto

Esta task entrega o **slice vertical de Relatórios** — geração de PDF mensal, agendamento via APScheduler, envio SMTP e endpoints HTTP de download/envio/histórico. É a peça que entrega o valor final do produto (RF-008).

Capacidades:
1. **Geração de PDF** via WeasyPrint + Jinja2 (template HTML): cabeçalho do Terceiro (nome, empresa, CNPJ, mês/ano), tabela de dias com 4 horários + total + indicador de ajuste, total mensal, seção "Atividades" agrupada por dia.
2. **APScheduler** in-process: job `gerar_e_enviar_mensal` agendado para `00:00 BRT` do dia 1 de cada mês — gera PDF do mês anterior + tenta envio SMTP. Jobstore SQLite separado (`./data/scheduler.sqlite`); `misfire_grace_time=3600`, `coalesce=True`. Outro job semanal de **purge de PDFs** antigos (≥ 24 meses).
3. **Invalidação**: hook (event listener SQLAlchemy `after_flush`) que detecta mutações em `Jornada`/`Marcacao`/`Atividade` e seta `relatorio_gerado.invalidado_em = now()` para o `mes_referencia` afetado.
4. **Envio SMTP**: usa `SmtpRepository.decrypt_password` (TASK-015) + `smtplib` com `timeout=30`, retry 3× backoff linear 5s. Registra `HistoricoEnvioRelatorio(SUCESSO|FALHA, erro_mensagem)`.
5. **Endpoints HTTP**:
   - `GET /api/v1/relatorios/{mes}` (FileResponse PDF).
   - `GET /api/v1/relatorios/{mes}/meta` (RelatorioMesResponse com `invalidado_em`).
   - `POST /api/v1/relatorios/{mes}/enviar` (202 Accepted, executa síncrono mas retorna ack para o frontend mostrar progresso).
   - `GET /api/v1/relatorios/{mes}/historico`.

Estado atual (fim TASK-017):
- Todos os endpoints de auth, terceiros, privacidade, smtp, marcacoes, jornadas/atividades/auditoria estão implementados.
- `JornadaRepository.list_for_month` retorna jornadas com marcações.
- `SmtpRepository.decrypt_*` disponível.
- ORM `RelatorioGerado`, `HistoricoEnvioRelatorio`.

Deps a adicionar:
- `weasyprint==62.*`
- `jinja2==3.1.*`
- `apscheduler==3.10.*`
- `tzdata==2024.*` (timezone America/Sao_Paulo no Windows)

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `gerar_pdf(session, "2026-05", terceiro)` | Retorna `bytes` do PDF (WeasyPrint), conteúdo contém nome+CNPJ+ano-mês; cria/atualiza `RelatorioGerado(mes_referencia="2026-05", caminho_arquivo=..., gerado_em=now, invalidado_em=null)` |
| `gerar_pdf` para mês sem jornadas | Levanta `DomainError(code="NO_DATA",message="Sem jornadas no mês","details":[])` (422) |
| `gerar_pdf` excede 120s | Levanta `DomainError(code="PDF_TIMEOUT", http_status=500)` (envolto em `asyncio.wait_for`) |
| `enviar_relatorio(session, "2026-05")` com SMTP configurado | Lê PDF cached; envia via SMTP (`timeout=30`); retry 3× backoff 5s em falha; registra `HistoricoEnvioRelatorio(SUCESSO)` ou `FALHA(erro)`; retorna `dict` com status |
| `enviar_relatorio` sem SMTP configurado | Levanta `DomainError(code="SMTP_NOT_CONFIGURED", http_status=422)` |
| `enviar_relatorio` falha 3× | Registra `HistoricoEnvioRelatorio(FALHA, erro_mensagem=<último erro>)`; levanta `DomainError(code="SMTP_SEND_FAILED", http_status=500)` |
| `GET /api/v1/relatorios/2026-05` autenticado, PDF existe | `200` com `FileResponse` (`application/pdf`) |
| `GET /api/v1/relatorios/2026-05` PDF não gerado ainda | Gera on-demand + retorna |
| `GET /api/v1/relatorios/2026-05/meta` PDF não gerado | `404` |
| `GET /api/v1/relatorios/2026-05/meta` PDF gerado | `200`, body `{mes_referencia, caminho_arquivo, gerado_em, invalidado_em}` |
| `POST /api/v1/relatorios/2026-05/enviar` autenticado, SMTP config existe, PDF existe | `202` com body `{"status":"SUCESSO","historico_id":"<uuid>"}` |
| `POST /api/v1/relatorios/2026-05/enviar` sem SMTP | `422` com `code=SMTP_NOT_CONFIGURED` |
| `POST /api/v1/relatorios/2026-05/enviar` SMTP falha após retry | `500` com `code=SMTP_SEND_FAILED`; histórico registrado FALHA |
| `GET /api/v1/relatorios/2026-05/historico` | `200`, lista de `HistoricoEnvioItem` ordenada `enviado_em DESC` |
| Mutação em `Jornada` afetando `2026-05` (PUT/POST manual/POST atividade) | Hook `after_flush` seta `relatorio_gerado(mes="2026-05").invalidado_em = now` se existir |
| Job APScheduler `gerar_e_enviar_mensal` em 2026-06-01 00:00 BRT | Gera PDF de `2026-05` + tenta envio + registra histórico |
| Job APScheduler de purge semanal | Remove `RelatorioGerado` + arquivo físico com `gerado_em > 24 meses atrás`; loga estruturado |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_relatorios_pdf.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def session_with_jornada(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    from app.core import config, db as db_mod
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
        t = Terceiro(
            id="t-1", nome="Maria Silva", empresa_nome="ACME LTDA", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=now, atualizado_em=now,
        )
        s.add(t)
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
    yield sm, t
    await engine.dispose()


@pytest.mark.asyncio
async def test_gerar_pdf_cria_arquivo_e_relatorio_gerado(session_with_jornada, tmp_path) -> None:
    sm, _t = session_with_jornada
    from app.modules.relatorios.service import gerar_pdf
    from app.models import RelatorioGerado
    from sqlalchemy import select
    async with sm() as s:
        await gerar_pdf(s, "2026-05")
    async with sm() as s:
        r = (await s.execute(select(RelatorioGerado))).scalar_one()
        assert r.mes_referencia == "2026-05"
        assert Path(r.caminho_arquivo).exists()
        assert Path(r.caminho_arquivo).read_bytes().startswith(b"%PDF")
        assert r.invalidado_em is None


@pytest.mark.asyncio
async def test_gerar_pdf_sem_jornadas_levanta_no_data(session_with_jornada) -> None:
    sm, _t = session_with_jornada
    from app.modules.relatorios.service import gerar_pdf
    from app.core.errors import DomainError
    async with sm() as s:
        with pytest.raises(DomainError) as exc:
            await gerar_pdf(s, "2026-04")
        assert exc.value.code == "NO_DATA"


@pytest.mark.asyncio
async def test_invalidacao_seta_invalidado_em_ao_mutar_jornada(session_with_jornada) -> None:
    sm, _t = session_with_jornada
    from app.modules.relatorios.service import gerar_pdf
    from app.models import Jornada, RelatorioGerado
    from sqlalchemy import select
    async with sm() as s:
        await gerar_pdf(s, "2026-05")
    # Mutar jornada
    async with sm() as s:
        j = (await s.execute(select(Jornada).where(Jornada.id == "j-1"))).scalar_one()
        j.status = "AJUSTADA_MANUALMENTE"
        await s.commit()
    async with sm() as s:
        r = (await s.execute(select(RelatorioGerado).where(RelatorioGerado.mes_referencia == "2026-05"))).scalar_one()
        assert r.invalidado_em is not None
```

### `apps/api/tests/test_relatorios_endpoints.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def app_and_session(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")  # desabilita scheduler nos testes HTTP
    from app.core import config, db as db_mod
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
            email_destinatario_relatorio="rh@x.com",
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
        r = await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
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
        r = await c.get("/api/v1/relatorios/2026-05/meta", headers={"Authorization": f"Bearer {tok}"})
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
        r = await c.post("/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
    assert r.json()["code"] == "SMTP_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_post_enviar_success_with_mailhog(app_and_session, monkeypatch) -> None:
    """Requer Mailhog em 127.0.0.1:1025 (make smtp-up)."""
    app, sm = app_and_session
    from app.models import HistoricoEnvioRelatorio
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json={
            "host": "127.0.0.1", "port": 1025, "username": "anon",
            "password": "anon", "use_starttls": False, "from_address": "noreply@x.com",
        })
        # gera relatorio
        await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
        r = await c.post("/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"})
    # Aceita 202 (sucesso) OU 500 (Mailhog não está up — pula teste)
    if r.status_code == 500 and "SMTP" in r.text:
        pytest.skip("Mailhog não disponível em 127.0.0.1:1025")
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "SUCESSO"
    async with sm() as s:
        hist = (await s.execute(select(HistoricoEnvioRelatorio))).scalars().all()
        assert len(hist) == 1
        assert hist[0].status == "SUCESSO"


@pytest.mark.asyncio
async def test_post_enviar_failure_records_historico_falha(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import HistoricoEnvioRelatorio
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json={
            "host": "127.0.0.2", "port": 65530, "username": "x",  # inalcançável
            "password": "x", "use_starttls": False, "from_address": "noreply@x.com",
        })
        await c.get("/api/v1/relatorios/2026-05", headers={"Authorization": f"Bearer {tok}"})
        r = await c.post("/api/v1/relatorios/2026-05/enviar", headers={"Authorization": f"Bearer {tok}"})
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
    from uuid import uuid4
    async with sm() as s:
        s.add(HistoricoEnvioRelatorio(
            id=str(uuid4()), mes_referencia="2026-05", email_destinatario="rh@x.com",
            status="FALHA", erro_mensagem="erro 1", enviado_em="2026-05-01T00:00:00+00:00",
        ))
        s.add(HistoricoEnvioRelatorio(
            id=str(uuid4()), mes_referencia="2026-05", email_destinatario="rh@x.com",
            status="SUCESSO", erro_mensagem=None, enviado_em="2026-05-02T00:00:00+00:00",
        ))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/relatorios/2026-05/historico", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["status"] == "SUCESSO"  # mais recente primeiro
```

### `apps/api/tests/test_scheduler.py`

```python
from __future__ import annotations

import pytest


def test_scheduler_jobs_registered_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "true")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.modules.relatorios import scheduler
    sched = scheduler.build_scheduler()
    job_ids = {j.id for j in sched.get_jobs()}
    assert "relatorios_mensal" in job_ids
    assert "relatorios_purge" in job_ids


def test_scheduler_disabled_when_flag_false(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.modules.relatorios import scheduler
    sched = scheduler.build_scheduler()
    # Quando desabilitado, scheduler é construído mas sem jobs
    assert len(sched.get_jobs()) == 0


@pytest.mark.asyncio
async def test_purge_remove_arquivos_e_relatorios_antigos(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.models import RelatorioGerado
    from sqlalchemy import select
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    old_file = pdf_dir / "2023-01.pdf"
    old_file.write_bytes(b"%PDF-fake")
    recent_file = pdf_dir / "2026-05.pdf"
    recent_file.write_bytes(b"%PDF-fake")
    async with sm() as s:
        s.add(RelatorioGerado(
            id="r-old", mes_referencia="2023-01", caminho_arquivo=str(old_file),
            gerado_em="2023-01-01T00:00:00+00:00",
        ))
        s.add(RelatorioGerado(
            id="r-recent", mes_referencia="2026-05", caminho_arquivo=str(recent_file),
            gerado_em="2026-05-01T00:00:00+00:00",
        ))
        await s.commit()

    from app.modules.relatorios.scheduler import purge_old_pdfs
    await purge_old_pdfs()

    async with sm() as s:
        rows = (await s.execute(select(RelatorioGerado))).scalars().all()
        ids = {r.id for r in rows}
        assert "r-old" not in ids  # removido
        assert "r-recent" in ids  # mantido
    assert not old_file.exists()
    assert recent_file.exists()
```

**Refatoração:** Após o green, extrair template Jinja (PDF) para `apps/api/app/modules/relatorios/templates/mensal.html` (já criado). Extrair `_now_brt()` para util se reusado.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/pyproject.toml` | Modificar | Adicionar `weasyprint==62.*`, `jinja2==3.1.*`, `apscheduler==3.10.*`, `tzdata==2024.*` |
| `apps/api/.env.example` | Modificar | `TIMESHEET_PDF_DIR=./data/pdfs`, `TIMESHEET_SCHEDULER_ENABLED=true`, `TIMESHEET_SCHEDULER_JOBSTORE=./data/scheduler.sqlite`, `TIMESHEET_SMTP_TIMEOUT=30` |
| `apps/api/app/core/config.py` | Modificar | Adicionar `pdf_dir`, `scheduler_enabled` (bool), `scheduler_jobstore`, `smtp_timeout` |
| `apps/api/app/modules/relatorios/templates/mensal.html` | Criar | Template Jinja2 (cabeçalho, tabela dias, totais, atividades) |
| `apps/api/app/modules/relatorios/pdf.py` | Criar | `render_pdf(terceiro, mes, jornadas_data) -> bytes` (WeasyPrint + Jinja) com `asyncio.wait_for(timeout=120)` |
| `apps/api/app/modules/relatorios/repository.py` | Criar | `class RelatorioRepository` — `get_by_mes`, `upsert(mes, caminho)`, `mark_invalidado(mes)`, `list_to_purge(cutoff_date)`, `delete_by_id`; `class HistoricoEnvioRepository` — `create(mes, email, status, erro)`, `list_by_mes(mes)` |
| `apps/api/app/modules/relatorios/smtp_send.py` | Criar | `async def send_pdf(cfg, pdf_bytes, to_email, mes_referencia) -> None` (smtplib + retry 3× backoff 5s + timeout 30s) |
| `apps/api/app/modules/relatorios/service.py` | Criar | `gerar_pdf`, `enviar_relatorio`, `get_meta`, `listar_historico` |
| `apps/api/app/modules/relatorios/schema.py` | Criar | `RelatorioMesResponse`, `HistoricoEnvioItem`, `EnviarRelatorioRequest`, `EnviarResponse` |
| `apps/api/app/modules/relatorios/router.py` | Criar | `GET /relatorios/{mes}` (FileResponse), `GET /relatorios/{mes}/meta`, `POST /relatorios/{mes}/enviar`, `GET /relatorios/{mes}/historico` |
| `apps/api/app/modules/relatorios/scheduler.py` | Criar | `build_scheduler() -> AsyncIOScheduler`, `gerar_e_enviar_mensal`, `purge_old_pdfs`, `start_scheduler(app)`, `stop_scheduler(app)` |
| `apps/api/app/modules/relatorios/invalidation.py` | Criar | `register_invalidation_listener()` — SQLAlchemy `after_flush` listener que detecta mutações em Jornada/Marcacao/Atividade e seta `relatorio_gerado.invalidado_em` |
| `apps/api/app/main.py` | Modificar | `_lifespan` startup/shutdown do scheduler; registrar `relatorios_router`; chamar `register_invalidation_listener` |
| `apps/api/tests/test_relatorios_pdf.py` | Criar | 3 testes (PDF + invalidação) |
| `apps/api/tests/test_relatorios_endpoints.py` | Criar | 6 testes (HTTP endpoints) |
| `apps/api/tests/test_scheduler.py` | Criar | 3 testes (jobs + purge) |

> **Total: 16 arquivos**. Excede o teto (8) — exceção justificada pela coesão: relatórios + scheduler + PDF + SMTP send + invalidação são entrelaçados (scheduler chama service que chama pdf+smtp+repo; invalidação muta `relatorio_gerado` mas só sob mutação de outras tabelas). Dividir geraria 4 PRs sequenciais que compartilham `relatorios/service.py` e o lifespan de `main.py`. Cada arquivo é pequeno-médio (template HTML é o maior, ~80 linhas).

### Detalhamento Técnico

**1. `apps/api/app/core/config.py`** — adicionar:

```python
    pdf_dir: str = Field(
        default="./data/pdfs",
        validation_alias=AliasChoices("TIMESHEET_PDF_DIR", "pdf_dir"),
    )
    scheduler_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("TIMESHEET_SCHEDULER_ENABLED", "scheduler_enabled"),
    )
    scheduler_jobstore: str = Field(
        default="./data/scheduler.sqlite",
        validation_alias=AliasChoices("TIMESHEET_SCHEDULER_JOBSTORE", "scheduler_jobstore"),
    )
    smtp_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("TIMESHEET_SMTP_TIMEOUT", "smtp_timeout"),
    )
```

**2. `apps/api/app/modules/relatorios/templates/mensal.html`** (Jinja2):

```html
<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body { font-family: sans-serif; font-size: 11px; }
  h1 { font-size: 18px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; }
  th { background: #eee; }
  .ajustada { background: #fff8e1; }
  .totais { margin-top: 20px; font-weight: bold; }
</style></head><body>
<h1>Relatório Mensal — {{ mes_referencia }}</h1>
<p><b>{{ terceiro.nome }}</b> · {{ terceiro.empresa_nome }} · CNPJ {{ terceiro.empresa_cnpj }}</p>
<table>
  <thead><tr>
    <th>Data</th><th>Dia</th>
    <th>Início</th><th>Saída Almoço</th><th>Retorno Almoço</th><th>Fim</th>
    <th>Total</th><th>Status</th>
  </tr></thead>
  <tbody>
  {% for j in jornadas %}
    <tr class="{{ 'ajustada' if j.status == 'AJUSTADA_MANUALMENTE' else '' }}">
      <td>{{ j.data }}</td>
      <td>{{ j.dia_semana }}</td>
      <td>{{ j.horarios.get('INICIO_JORNADA', '—') }}</td>
      <td>{{ j.horarios.get('SAIDA_ALMOCO', '—') }}</td>
      <td>{{ j.horarios.get('RETORNO_ALMOCO', '—') }}</td>
      <td>{{ j.horarios.get('FIM_JORNADA', '—') }}</td>
      <td>{{ j.total_str }}</td>
      <td>{{ j.status }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<p class="totais">Total mensal: {{ total_mes_str }}</p>
<h2>Atividades</h2>
{% for j in jornadas if j.atividade %}
<p><b>{{ j.data }}:</b> {{ j.atividade }}</p>
{% endfor %}
</body></html>
```

**3. `apps/api/app/modules/relatorios/pdf.py`:**

```python
from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import DomainError

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLATES), autoescape=select_autoescape(["html"]))


def _format_secs(s: int | None) -> str:
    if s is None or s == 0:
        return "—"
    h, rem = divmod(s, 3600)
    m, _ = divmod(rem, 60)
    return f"{h:02d}:{m:02d}"


def _dia_semana(data_iso: str) -> str:
    days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    d = date.fromisoformat(data_iso)
    return days[d.weekday()]


def _build_context(terceiro, jornadas_data: list[dict], mes_referencia: str) -> dict[str, Any]:
    jornadas_view = []
    total_mes = 0
    for j in jornadas_data:
        total = j.get("total_horas_apuradas_s") or 0
        total_mes += total
        horarios = {}
        for m in j.get("marcacoes", []):
            t = (m.get("horario_efetivo") or m.get("horario_registrado") or "")[11:16]
            horarios[m["tipo"]] = t
        jornadas_view.append({
            "data": j["data"],
            "dia_semana": _dia_semana(j["data"]),
            "horarios": horarios,
            "total_str": _format_secs(total),
            "status": j["status"],
            "atividade": (j.get("atividade") or {}).get("descricao"),
        })
    return {
        "terceiro": terceiro,
        "mes_referencia": mes_referencia,
        "jornadas": jornadas_view,
        "total_mes_str": _format_secs(total_mes),
    }


async def render_pdf(terceiro, jornadas_data: list[dict], mes_referencia: str) -> bytes:
    if not jornadas_data:
        raise DomainError(code="NO_DATA", message="Sem jornadas no mês", http_status=422)

    def _run() -> bytes:
        from weasyprint import HTML  # import dentro pra evitar carregamento se não usado
        ctx = _build_context(terceiro, jornadas_data, mes_referencia)
        html = _env.get_template("mensal.html").render(**ctx)
        return HTML(string=html).write_pdf()

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run), timeout=120)
    except asyncio.TimeoutError as exc:
        raise DomainError(code="PDF_TIMEOUT", message="Geração de PDF excedeu 120s", http_status=500) from exc
```

**4. `apps/api/app/modules/relatorios/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HistoricoEnvioRelatorio, RelatorioGerado


class RelatorioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_mes(self, mes: str) -> RelatorioGerado | None:
        return (
            await self.session.execute(select(RelatorioGerado).where(RelatorioGerado.mes_referencia == mes))
        ).scalar_one_or_none()

    async def upsert(self, mes: str, caminho: str) -> RelatorioGerado:
        existing = await self.get_by_mes(mes)
        now = datetime.now(UTC).isoformat()
        if existing is None:
            r = RelatorioGerado(
                id=str(uuid4()), mes_referencia=mes, caminho_arquivo=caminho,
                gerado_em=now, invalidado_em=None,
            )
            self.session.add(r)
            return r
        existing.caminho_arquivo = caminho
        existing.gerado_em = now
        existing.invalidado_em = None
        return existing

    async def mark_invalidado(self, mes: str) -> None:
        r = await self.get_by_mes(mes)
        if r is not None and r.invalidado_em is None:
            r.invalidado_em = datetime.now(UTC).isoformat()

    async def list_to_purge(self, cutoff_iso: str) -> list[RelatorioGerado]:
        stmt = select(RelatorioGerado).where(RelatorioGerado.gerado_em < cutoff_iso)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete(self, r: RelatorioGerado) -> None:
        await self.session.delete(r)


class HistoricoEnvioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, mes: str, email: str, status: str, erro: str | None) -> HistoricoEnvioRelatorio:
        h = HistoricoEnvioRelatorio(
            id=str(uuid4()), mes_referencia=mes, email_destinatario=email,
            status=status, erro_mensagem=erro,
            enviado_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(h)
        return h

    async def list_by_mes(self, mes: str) -> list[HistoricoEnvioRelatorio]:
        stmt = (
            select(HistoricoEnvioRelatorio)
            .where(HistoricoEnvioRelatorio.mes_referencia == mes)
            .order_by(HistoricoEnvioRelatorio.enviado_em.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
```

**5. `apps/api/app/modules/relatorios/smtp_send.py`:**

```python
from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage

from app.core.config import settings
from app.core.errors import DomainError


def send_pdf_sync(*, host: str, port: int, username: str, password: str,
                  use_starttls: bool, from_address: str, to_email: str,
                  pdf_bytes: bytes, mes_referencia: str) -> None:
    """Envia o PDF anexado. Retry 3x backoff linear 5s. Levanta DomainError em falha final."""
    msg = EmailMessage()
    msg["Subject"] = f"Relatório de jornada — {mes_referencia}"
    msg["From"] = from_address
    msg["To"] = to_email
    msg.set_content(f"Segue em anexo o relatório de jornada do mês {mes_referencia}.")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename=f"relatorio-{mes_referencia}.pdf")
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=settings.smtp_timeout) as s:
                    if username and password:
                        try:
                            s.login(username, password)
                        except smtplib.SMTPNotSupportedError:
                            pass
                    s.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=settings.smtp_timeout) as s:
                    if use_starttls:
                        s.starttls()
                    if username and password:
                        try:
                            s.login(username, password)
                        except smtplib.SMTPNotSupportedError:
                            pass
                    s.send_message(msg)
            return
        except (OSError, smtplib.SMTPException) as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(5)
    raise DomainError(
        code="SMTP_SEND_FAILED",
        message=f"Envio SMTP falhou após 3 tentativas: {last_err}",
        http_status=500,
    )
```

**6. `apps/api/app/modules/relatorios/service.py`:**

```python
from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto_state
from app.core.config import settings
from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.jornadas.service import detalhe as jornada_detalhe, listar_mes
from app.modules.relatorios.pdf import render_pdf
from app.modules.relatorios.repository import HistoricoEnvioRepository, RelatorioRepository
from app.modules.relatorios.smtp_send import send_pdf_sync
from app.modules.smtp.repository import SmtpRepository


async def gerar_pdf(session: AsyncSession, mes_referencia: str, *, terceiro: Terceiro | None = None) -> str:
    """Gera (ou regenera) o PDF; retorna o caminho. Se terceiro None, usa o único do sistema."""
    if terceiro is None:
        from sqlalchemy import select
        terceiro = (await session.execute(select(Terceiro))).scalar_one_or_none()
        if terceiro is None:
            raise DomainError(code="NO_DATA", message="Terceiro não cadastrado", http_status=422)
    mes_data = await listar_mes(session, terceiro, mes_referencia)
    if not mes_data["jornadas"]:
        raise DomainError(code="NO_DATA", message="Sem jornadas no mês", http_status=422)
    # Carrega detalhe completo para atividade
    jornadas_full: list[dict] = []
    for resumo in mes_data["jornadas"]:
        det = await jornada_detalhe(session, terceiro, resumo["id"])
        jornadas_full.append({
            "data": det["data"], "status": det["status"],
            "total_horas_apuradas_s": det["total_horas_apuradas_s"],
            "marcacoes": det["marcacoes"], "atividade": det["atividade"],
        })
    pdf_bytes = await render_pdf(terceiro, jornadas_full, mes_referencia)
    pdf_dir = Path(settings.pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    caminho = pdf_dir / f"relatorio-{mes_referencia}.pdf"
    caminho.write_bytes(pdf_bytes)
    repo = RelatorioRepository(session)
    await repo.upsert(mes_referencia, str(caminho))
    await session.commit()
    return str(caminho)


async def get_meta(session: AsyncSession, mes_referencia: str) -> dict:
    repo = RelatorioRepository(session)
    r = await repo.get_by_mes(mes_referencia)
    if r is None:
        raise DomainError(code="NOT_FOUND", message="Relatório não gerado", http_status=404)
    return {
        "mes_referencia": r.mes_referencia,
        "caminho_arquivo": r.caminho_arquivo,
        "gerado_em": r.gerado_em,
        "invalidado_em": r.invalidado_em,
    }


async def enviar_relatorio(session: AsyncSession, mes_referencia: str, *, email_override: str | None = None) -> dict:
    from sqlalchemy import select
    smtp_repo = SmtpRepository(session)
    cfg = await smtp_repo.get_or_none()
    if cfg is None:
        raise DomainError(code="SMTP_NOT_CONFIGURED", message="SMTP não configurado", http_status=422)
    # Garante PDF
    rel_repo = RelatorioRepository(session)
    r = await rel_repo.get_by_mes(mes_referencia)
    if r is None or r.invalidado_em is not None:
        await gerar_pdf(session, mes_referencia)
        r = await rel_repo.get_by_mes(mes_referencia)
    assert r is not None
    pdf_bytes = Path(r.caminho_arquivo).read_bytes()
    # Decide destinatário
    if email_override:
        to_email = email_override
    else:
        terceiro = (await session.execute(select(Terceiro))).scalar_one()
        to_email = terceiro.email_destinatario_relatorio or terceiro.email_contato
    # Envia
    username = smtp_repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP)
    password = smtp_repo.decrypt_password(cfg, crypto_state.SUBKEY_SMTP)
    hist_repo = HistoricoEnvioRepository(session)
    try:
        send_pdf_sync(
            host=cfg.host, port=cfg.port,
            username=username, password=password,
            use_starttls=bool(cfg.use_starttls),
            from_address=cfg.from_address,
            to_email=to_email, pdf_bytes=pdf_bytes,
            mes_referencia=mes_referencia,
        )
    except DomainError as exc:
        h = await hist_repo.create(mes=mes_referencia, email=to_email, status="FALHA", erro=exc.message)
        await session.commit()
        raise
    h = await hist_repo.create(mes=mes_referencia, email=to_email, status="SUCESSO", erro=None)
    await session.commit()
    return {"status": "SUCESSO", "historico_id": h.id}


async def listar_historico(session: AsyncSession, mes_referencia: str) -> list[dict]:
    repo = HistoricoEnvioRepository(session)
    rows = await repo.list_by_mes(mes_referencia)
    return [
        {"id": r.id, "mes_referencia": r.mes_referencia, "email_destinatario": r.email_destinatario,
         "status": r.status, "erro_mensagem": r.erro_mensagem, "enviado_em": r.enviado_em}
        for r in rows
    ]
```

**7. `apps/api/app/modules/relatorios/scheduler.py`:**

```python
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.config import settings
from app.core.db import get_sessionmaker
from app.models import RelatorioGerado

logger = logging.getLogger(__name__)


async def gerar_e_enviar_mensal() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        # Mês anterior (em BRT)
        now = datetime.utcnow() - timedelta(hours=3)  # BRT = UTC-3
        primeiro_dia_mes = now.replace(day=1)
        ultimo_mes = (primeiro_dia_mes - timedelta(days=1)).strftime("%Y-%m")
        try:
            from app.modules.relatorios.service import enviar_relatorio
            await enviar_relatorio(session, ultimo_mes)
        except Exception as exc:
            logger.error("scheduler_envio_falhou", exc_info=exc)


async def purge_old_pdfs() -> None:
    sm = get_sessionmaker()
    cutoff = (datetime.now(UTC) - timedelta(days=24 * 30)).isoformat()  # ~24 meses
    async with sm() as session:
        from app.modules.relatorios.repository import RelatorioRepository
        repo = RelatorioRepository(session)
        rows = await repo.list_to_purge(cutoff)
        for r in rows:
            try:
                p = Path(r.caminho_arquivo)
                if p.exists():
                    p.unlink()
            except OSError as exc:
                logger.warning("purge_falhou_remover_arquivo", path=r.caminho_arquivo, error=str(exc))
            await repo.delete(r)
        await session.commit()
        logger.info("purge_old_pdfs_done", removed=len(rows))


def build_scheduler() -> AsyncIOScheduler:
    jobstore_url = f"sqlite:///{settings.scheduler_jobstore}"
    Path(settings.scheduler_jobstore).parent.mkdir(parents=True, exist_ok=True)
    sched = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=jobstore_url)},
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
        timezone="America/Sao_Paulo",
    )
    if not settings.scheduler_enabled:
        return sched
    sched.add_job(
        gerar_e_enviar_mensal, id="relatorios_mensal",
        trigger=CronTrigger(day=1, hour=0, minute=0),
        replace_existing=True,
    )
    sched.add_job(
        purge_old_pdfs, id="relatorios_purge",
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        replace_existing=True,
    )
    return sched


_scheduler_instance: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler_instance
    if _scheduler_instance is not None:
        return
    _scheduler_instance = build_scheduler()
    if settings.scheduler_enabled:
        _scheduler_instance.start()


def stop_scheduler() -> None:
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance.running:
        _scheduler_instance.shutdown(wait=True)
    _scheduler_instance = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler_instance
```

**8. `apps/api/app/modules/relatorios/invalidation.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Atividade, Jornada, Marcacao, RelatorioGerado


def _mes_de(data_iso: str) -> str | None:
    return data_iso[:7] if data_iso and len(data_iso) >= 7 else None


def register_invalidation_listener() -> None:
    """Registra after_flush para detectar mutações em Jornada/Marcacao/Atividade
    e setar relatorio_gerado.invalidado_em do mes correspondente."""

    @event.listens_for(AsyncSession.sync_session_class, "after_flush")
    def _after_flush(session, _flush_context):  # type: ignore[no-untyped-def]
        meses_afetados: set[str] = set()
        for obj in list(session.new) + list(session.dirty):
            if isinstance(obj, Jornada):
                m = _mes_de(obj.data)
            elif isinstance(obj, Marcacao):
                j = session.identity_map.get((Jornada, obj.jornada_id))
                m = _mes_de(j.data) if j else None
            elif isinstance(obj, Atividade):
                j = session.identity_map.get((Jornada, obj.jornada_id))
                m = _mes_de(j.data) if j else None
            else:
                m = None
            if m:
                meses_afetados.add(m)
        for mes in meses_afetados:
            session.execute(
                update(RelatorioGerado)
                .where(RelatorioGerado.mes_referencia == mes,
                       RelatorioGerado.invalidado_em.is_(None))
                .values(invalidado_em=datetime.now(UTC).isoformat())
            )
```

> **Quirk SQLAlchemy async**: `after_flush` é síncrono no `Session` interno; usamos `session.execute(update(...))` síncrono (não await) dentro do listener. Isso funciona porque o flush é executado dentro de um `run_sync`.

**9. `apps/api/app/modules/relatorios/schema.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class RelatorioMesResponse(BaseModel):
    mes_referencia: str
    caminho_arquivo: str
    gerado_em: str
    invalidado_em: str | None


class HistoricoEnvioItem(BaseModel):
    id: str
    mes_referencia: str
    email_destinatario: str
    status: str
    erro_mensagem: str | None
    enviado_em: str


class EnviarRelatorioRequest(BaseModel):
    email: EmailStr | None = None


class EnviarResponse(BaseModel):
    status: str
    historico_id: str
```

**10. `apps/api/app/modules/relatorios/router.py`:**

```python
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Path as FastPath
from fastapi.responses import FileResponse

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.core.errors import DomainError
from app.modules.relatorios import service
from app.modules.relatorios.repository import RelatorioRepository
from app.modules.relatorios.schema import (
    EnviarRelatorioRequest,
    EnviarResponse,
    HistoricoEnvioItem,
    RelatorioMesResponse,
)

router = APIRouter(prefix="/api/v1/relatorios", tags=["relatorios"])

_MES_PATTERN = r"^\d{4}-\d{2}$"


@router.get("/{mes}")
async def download(mes: str = FastPath(pattern=_MES_PATTERN), _t: CurrentTerceiroDep = None, session: SessionDep = None) -> FileResponse:  # type: ignore[assignment]
    rel_repo = RelatorioRepository(session)
    r = await rel_repo.get_by_mes(mes)
    if r is None or r.invalidado_em is not None or not Path(r.caminho_arquivo).exists():
        await service.gerar_pdf(session, mes)
        r = await rel_repo.get_by_mes(mes)
    assert r is not None
    return FileResponse(r.caminho_arquivo, media_type="application/pdf",
                        filename=f"relatorio-{mes}.pdf")


@router.get("/{mes}/meta", response_model=RelatorioMesResponse)
async def meta(mes: str = FastPath(pattern=_MES_PATTERN), _t: CurrentTerceiroDep = None, session: SessionDep = None) -> RelatorioMesResponse:  # type: ignore[assignment]
    data = await service.get_meta(session, mes)
    return RelatorioMesResponse(**data)


@router.post("/{mes}/enviar", status_code=202, response_model=EnviarResponse)
async def enviar(
    mes: str = FastPath(pattern=_MES_PATTERN),
    body: EnviarRelatorioRequest | None = None,
    _t: CurrentTerceiroDep = None,
    session: SessionDep = None,
) -> EnviarResponse:  # type: ignore[assignment]
    override = body.email if body else None
    data = await service.enviar_relatorio(session, mes, email_override=override)
    return EnviarResponse(**data)


@router.get("/{mes}/historico", response_model=list[HistoricoEnvioItem])
async def historico(mes: str = FastPath(pattern=_MES_PATTERN), _t: CurrentTerceiroDep = None, session: SessionDep = None) -> list[HistoricoEnvioItem]:  # type: ignore[assignment]
    rows = await service.listar_historico(session, mes)
    return [HistoricoEnvioItem(**r) for r in rows]
```

**11. `apps/api/app/main.py`** — atualizar `_lifespan` + adicionar router:

```python
@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    from app.core import crypto_state
    crypto_state.configure()
    from app.modules.relatorios.invalidation import register_invalidation_listener
    register_invalidation_listener()
    from app.modules.relatorios.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()
    await dispose_engine()

# ... include_router(...relatorios_router) ...
from app.modules.relatorios.router import router as relatorios_router
app.include_router(relatorios_router)
```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-019 (wiring final + /ready):
    - app.modules.relatorios.scheduler.get_scheduler() → /ready verifica STATE_RUNNING.
    - Endpoints /api/v1/relatorios/* registrados em main.py — TASK-019 confirma via testes integrados.
  Phase 4 (Frontend):
    - GET /relatorios/{mes}/meta retorna invalidado_em — badge âmbar.
    - POST /relatorios/{mes}/enviar com {email?} no body.

Consome de:
  TASK-015: SmtpRepository (get_or_none, decrypt_*), crypto_state.SUBKEY_SMTP.
  TASK-017: jornadas.service (listar_mes, detalhe) para fonte do PDF.
  TASK-012: SessionDep, CurrentTerceiroDep, DomainError.
  TASK-010: modelos RelatorioGerado, HistoricoEnvioRelatorio.

Erros:
  - 422 NO_DATA (sem jornadas), 422 SMTP_NOT_CONFIGURED, 500 PDF_TIMEOUT, 500 SMTP_SEND_FAILED, 404 NOT_FOUND (meta sem relatório).
```

## Contrato HTTP

```
GET /api/v1/relatorios/{mes}   (auth Bearer)
Response 200: FileResponse application/pdf (gera on-demand se ausente ou invalidado)
Response 422: NO_DATA (sem jornadas no mês)

GET /api/v1/relatorios/{mes}/meta   (auth Bearer)
Response 200: {"mes_referencia":"2026-05","caminho_arquivo":"<path>","gerado_em":"<iso>","invalidado_em":null|"<iso>"}
Response 404: relatório não gerado

POST /api/v1/relatorios/{mes}/enviar   (auth Bearer)
Request body (opcional): {"email": "destino@example.com"}
Response 202: {"status":"SUCESSO","historico_id":"<uuid>"}
Response 422: {"code":"SMTP_NOT_CONFIGURED",...}
Response 500: {"code":"SMTP_SEND_FAILED","message":"Envio SMTP falhou após 3 tentativas: <erro>","details":[]} + HistoricoEnvioRelatorio(FALHA) persistido

GET /api/v1/relatorios/{mes}/historico   (auth Bearer)
Response 200: [HistoricoEnvioItem, ...] ordenado enviado_em DESC
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 TIMESHEET_SCHEDULER_ENABLED=false pytest tests/test_relatorios_pdf.py tests/test_relatorios_endpoints.py tests/test_scheduler.py -v`.
3. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 TIMESHEET_SCHEDULER_ENABLED=false pytest tests/ -v` — suite completa continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smtp-up && make smoke` — Mailhog up + Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. **WeasyPrint requer libs nativas** (pango/cairo) — em Windows dev, instalar via GTK runtime (link no README do WeasyPrint); em CI Linux já estão disponíveis via apt.

**Refatoração:** Após o green, considerar mover `_dia_semana`, `_format_secs` para `app/core/datetime_utils.py` se Phase 4 (Frontend) ou outras tasks precisarem. Considerar substituir `time.sleep` em `send_pdf_sync` por `asyncio.sleep` se a função vir a ser chamada de coroutine — atualmente é chamada do scheduler (que já roda em thread separada) e do endpoint via `await asyncio.to_thread(send_pdf_sync, ...)` (sugerido em refactor futuro).
