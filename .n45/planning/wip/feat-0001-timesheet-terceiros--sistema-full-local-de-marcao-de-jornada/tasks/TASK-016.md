---
checkpoint: null
complexity: M
created_at: "2026-05-28 09:31:12"
criteria:
    - done: false
      test: pytest -k test_post_marcacao_creates_marcacao_and_jornada
      text: POST /api/v1/marcacoes em dia sem jornada cria Marcacao+Jornada(status=EM_ANDAMENTO) e retorna MarcacaoResponse 201 com origem=AGENTE_AUTOMATICO status=CONFIRMADA
    - done: false
      test: pytest -k test_post_marcacao_idempotency_returns_same_record
      text: POST com mesma idempotency_key retorna o registro existente (201, mesmo id) — apenas 1 linha em marcacao
    - done: false
      test: pytest -k test_post_marcacao_same_tipo_diff_idem_returns_409
      text: POST com tipo já existente no dia (idempotency_key diferente) retorna 409 code=CONFLICT
    - done: false
      test: pytest -k test_post_marcacao_rejects_ajuste_web_from_agent
      text: POST com origem=AJUSTE_WEB do Agente retorna 422 VALIDATION_ERROR field=body.origem (Literal proibe valor)
    - done: false
      test: pytest -k test_post_marcacao_weekend_blocked_when_not_allowed
      text: POST em sábado/domingo com terceiro.trabalha_fim_de_semana=false retorna 422 code=FIM_DE_SEMANA_NAO_PERMITIDO
    - done: false
      test: pytest -k test_post_marcacao_weekend_allowed_when_flag_true
      text: POST em sábado/domingo com trabalha_fim_de_semana=true retorna 201 normal
    - done: false
      test: pytest -k test_post_marcacao_post_to_ajuste_web_record_returns_409_with_code
      text: 'POST para tipo já AJUSTE_WEB (RN-012 #1) retorna 409 code=AJUSTE_WEB_WINS'
    - done: false
      test: pytest -k test_get_marcacoes_lists_only_authenticated_terceiro
      text: GET /api/v1/marcacoes lista apenas as do terceiro autenticado (ownership via JOIN jornada.terceiro_id)
    - done: false
      test: pytest -k test_put_marcacao_updates_and_audits
      text: PUT /api/v1/marcacoes/{id} válido atualiza marcacao.origem=AJUSTE_WEB status=AJUSTADA, horario_efetivo novo, jornada vira AJUSTADA_MANUALMENTE, +1 LogAuditoria(entidade=Marcacao,motivo)
    - done: false
      test: pytest -k test_put_marcacao_motivo_too_short_returns_422
      text: PUT com motivo<5 chars retorna 422
    - done: false
      test: pytest -k test_put_marcacao_inexistente_returns_404
      text: PUT id inexistente retorna 404 NOT_FOUND
    - done: false
      test: pytest -k test_put_marcacao_de_outro_terceiro_returns_404
      text: PUT marcação de outro terceiro retorna 404 (não vaza existência)
    - done: false
      test: pytest --cov=app/modules/marcacoes --cov=app/modules/jornadas/repository --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/marcacoes e apps/api/app/modules/jornadas/repository.py
    - done: false
      test: grep -E '^class (Marcacao|Jornada)Repository' apps/api/app/modules/marcacoes/repository.py apps/api/app/modules/jornadas/repository.py
      text: 'Repository pattern: MarcacaoRepository e JornadaRepository definidos como classes em repository.py'
deps:
    - TASK-012
    - TASK-013
id: TASK-016
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
tests: pytest tests/test_marcacoes_post.py tests/test_marcacoes_put.py -v
title: 'Marcacoes: POST/GET/PUT com idempotency, auto-criação de jornada, RN-012 (AJUSTE_WEB_WINS), weekend check, audit log no PUT'
updated_at: "2026-05-28 09:31:12"
---
## Contexto

Esta task entrega o **slice vertical do domínio Marcações** — o coração do contrato Agente↔Backend. O Agente .NET envia `POST /api/v1/marcacoes` para cada uma das 4 marcações da jornada do dia (`INICIO_JORNADA`, `SAIDA_ALMOCO`, `RETORNO_ALMOCO`, `FIM_JORNADA`), com `idempotency_key` (UUID v4 = id local no Agente) para tolerar retries do Polly.

Regras críticas (Spec):

- **Auto-criação de jornada**: ao receber a **primeira** marcação de um `data_jornada`, o backend cria `Jornada(id=uuid4, terceiro_id=<sub do JWT>, data, status="EM_ANDAMENTO", criada_em=now)`. Marcações subsequentes do mesmo dia anexam à jornada existente.
- **Idempotência**: `marcacao.idempotency_key UNIQUE`. POST com idempotency_key duplicado retorna o registro existente com status `201` — o Agente trata `201` e `409` igualmente como sucesso (idempotência).
- **Constraint UNIQUE (jornada_id, tipo)**: 1 marcação por tipo por dia. Tentativa de inserir o mesmo tipo retorna `409 CONFLICT` (a menos que `idempotency_key` seja a mesma, daí é idempotente).
- **RN-012 (resolução de conflito)** em `PUT /marcacoes/{id}` vindo da Web:
  1. Se a marcação atual tem `origem="AJUSTE_WEB"`, sempre vence — qualquer write subsequente do Agente para o mesmo (jornada_id, tipo) é descartado com `409 CONFLICT code=AJUSTE_WEB_WINS`.
  2. Senão, last-write-wins por `horario_efetivo` (mais recente vence).
  3. Empate exato em `horario_efetivo` → mantém origem `AGENTE` (incoming descartado).
- **Auditoria**: `PUT /marcacoes/{id}` (Web) cria 1 linha em `log_auditoria` com `entidade="Marcacao"`, `antes_json`/`depois_json`, `autor=<email do terceiro>`, `motivo` (≥5 chars exigido).
- **Origem AJUSTE_WEB nunca vem do Agente**: o `PostMarcacaoRequest` só aceita `origem ∈ {AGENTE_AUTOMATICO, AGENTE_CONFIRMADO}`. `AJUSTE_WEB` é gerado apenas internamente em PUT/POST jornada manual.

Estado atual (fim TASK-013/014/015):
- ORM `Marcacao` (UNIQUE em `idempotency_key` e `(jornada_id, tipo)`), `Jornada` (UNIQUE em `(terceiro_id, data)`), `LogAuditoria`.
- `app.core.deps.CurrentTerceiroDep` autentica e injeta `Terceiro`.
- `app.core.audit.log_audit` para auditoria.
- `app.core.errors.DomainError` para erros padronizados.

Esta task **não** implementa `GET /jornadas`, `PUT /jornadas/{id}`, `POST /jornadas/manual`, `GET /atividade` — esses ficam para a TASK-017 (Jornadas + Atividades + Justificativas). Aqui apenas marcações + a auto-criação de jornada.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `POST /api/v1/marcacoes` autenticado, dia sem jornada, tipo `INICIO_JORNADA`, `horario_registrado="2026-05-27T09:02:00Z"`, `origem="AGENTE_AUTOMATICO"`, `idempotency_key=uuid4` | `201`, body `MarcacaoResponse {id, jornada_id, tipo, horario_registrado, horario_efetivo:null, origem, status:"CONFIRMADA", idempotency_key, criada_em}`; cria `Jornada(status="EM_ANDAMENTO", data="2026-05-27")` |
| `POST /api/v1/marcacoes` 2ª chamada com mesma `idempotency_key` | `201`, retorna o **mesmo** registro existente (idempotente); não cria novo |
| `POST /api/v1/marcacoes` com tipo já existente no dia (idempotency_key diferente) | `409` com `{"code":"CONFLICT","message":"Já existe marcação do tipo X para esta jornada","details":[]}` |
| `POST /api/v1/marcacoes` com `origem="AJUSTE_WEB"` | `422` com `{"code":"VALIDATION_ERROR","details":[{"field":"body.origem","issue":"..."}]}` |
| `POST /api/v1/marcacoes` em sábado/domingo, `terceiro.trabalha_fim_de_semana=false` | `422` com `{"code":"FIM_DE_SEMANA_NAO_PERMITIDO","message":"Terceiro não trabalha em fim de semana","details":[]}` |
| `POST /api/v1/marcacoes` em sábado, `trabalha_fim_de_semana=true` | `201` (normal) |
| `POST /api/v1/marcacoes` sem auth | `401` |
| `GET /api/v1/marcacoes` autenticado | `200`, lista todas as marcações do terceiro autenticado, ordenadas por `criada_em DESC` |
| `GET /api/v1/marcacoes?status=PENDENTE` autenticado | `200`, lista apenas marcações com `status="PENDENTE"` |
| `PUT /api/v1/marcacoes/{id}` autenticado, marcação existe, payload válido | `200`, body atualizado; marcação passa a `origem="AJUSTE_WEB"`, `status="AJUSTADA"`, `horario_efetivo=<novo>`; insere 1 `LogAuditoria(entidade="Marcacao")`; jornada da marcação passa a `status="AJUSTADA_MANUALMENTE"` |
| `PUT /api/v1/marcacoes/{id}` com `motivo` < 5 chars | `422` |
| `PUT /api/v1/marcacoes/{id}` com id inexistente | `404` com `code=NOT_FOUND` |
| `PUT /api/v1/marcacoes/{id}` em marcação de outro terceiro | `404` (não vaza existência) |
| `POST /api/v1/marcacoes` para tipo já `AJUSTE_WEB` (RN-012 #1) | `409` com `code=AJUSTE_WEB_WINS`, body inclui o registro atual servidor; agente descarta tentativa |
| `POST /api/v1/marcacoes` para tipo existente AGENTE_AUTOMATICO com `horario_efetivo` MAIS recente que o atual (RN-012 #2) | NÃO suportado nesta versão — Agente envia POST 1x; conflito tratado retornando 409 acima. **Conflito real entre POSTs simultâneos** = race muito improvável (Agente serial) — fica como tech debt se aparecer |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_marcacoes_post.py`

```python
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
    from app.core import config, db as db_mod
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
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
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


def _payload(*, tipo: str = "INICIO_JORNADA", h: str = "2026-05-27T09:02:00Z",
             origem: str = "AGENTE_AUTOMATICO", idem: str | None = None) -> dict:
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
    from app.models import Jornada, Marcacao
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload())
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
    from app.models import Marcacao
    tok = await _login(app)
    idem = str(uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload(idem=idem))
        r2 = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload(idem=idem))
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
        r1 = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload())
        assert r1.status_code == 201
        r2 = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload())
    assert r2.status_code == 409
    assert r2.json()["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_post_marcacao_rejects_ajuste_web_from_agent(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload(origem="AJUSTE_WEB"))
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
    from app.models import Terceiro
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
async def test_post_marcacao_post_to_ajuste_web_record_returns_409_with_code(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, Marcacao
    # Cria jornada + marcacao com origem=AJUSTE_WEB diretamente
    async with sm() as s:
        s.add(Jornada(id="j-1", terceiro_id="t-1", data="2026-05-27", status="AJUSTADA_MANUALMENTE",
                       criada_em=datetime.now(UTC).isoformat()))
        s.add(Marcacao(
            id="m-existing", jornada_id="j-1", tipo="INICIO_JORNADA",
            horario_registrado="2026-05-27T09:00:00+00:00",
            horario_efetivo="2026-05-27T09:00:00+00:00",
            origem="AJUSTE_WEB", status="AJUSTADA",
            idempotency_key="11111111-1111-1111-1111-111111111111",
            criada_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"}, json=_payload())
    assert r.status_code == 409
    assert r.json()["code"] == "AJUSTE_WEB_WINS"


@pytest.mark.asyncio
async def test_get_marcacoes_lists_only_authenticated_terceiro(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, Marcacao, Terceiro
    from app.core.security import hash_password
    # Adicionar outro terceiro com sua propria jornada
    async with sm() as s:
        s.add(Terceiro(
            id="t-2", nome="Outro", empresa_nome="X", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="outro@x.com",
            senha_hash=hash_password("X" * 8),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        s.add(Jornada(id="j-other", terceiro_id="t-2", data="2026-05-27", status="EM_ANDAMENTO",
                       criada_em=datetime.now(UTC).isoformat()))
        s.add(Marcacao(
            id="m-other", jornada_id="j-other", tipo="INICIO_JORNADA",
            horario_registrado="2026-05-27T09:00:00+00:00",
            origem="AGENTE_AUTOMATICO",
            idempotency_key="22222222-2222-2222-2222-222222222222",
            criada_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/marcacoes", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    # Lista deve ser vazia (terceiro autenticado t-1 ainda não criou marcações)
    assert body == []
```

### `apps/api/tests/test_marcacoes_put.py`

```python
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
        ))
        s.add(Jornada(id="j-1", terceiro_id="t-1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=now))
        s.add(Marcacao(
            id="m-1", jornada_id="j-1", tipo="INICIO_JORNADA",
            horario_registrado="2026-05-27T09:02:00+00:00",
            origem="AGENTE_AUTOMATICO", status="CONFIRMADA",
            idempotency_key="11111111-1111-1111-1111-111111111111",
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
async def test_put_marcacao_updates_and_audits(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Jornada, LogAuditoria, Marcacao
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/marcacoes/m-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={"horario_efetivo": "2026-05-27T09:00:00+00:00", "motivo": "corrigir atraso de relógio"},
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
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Marcacao"))).scalars().all()
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
    from app.models import Jornada, Marcacao, Terceiro
    from app.core.security import hash_password
    async with sm() as s:
        s.add(Terceiro(
            id="t-2", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="outro@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        s.add(Jornada(id="j-other", terceiro_id="t-2", data="2026-05-27", status="EM_ANDAMENTO",
                       criada_em=datetime.now(UTC).isoformat()))
        s.add(Marcacao(
            id="m-other", jornada_id="j-other", tipo="INICIO_JORNADA",
            horario_registrado="2026-05-27T09:00:00+00:00",
            origem="AGENTE_AUTOMATICO", status="CONFIRMADA",
            idempotency_key="22222222-2222-2222-2222-222222222222",
            criada_em=datetime.now(UTC).isoformat(),
        ))
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
```

**Refatoração:** Após o green, considerar extrair `_login` para `tests/helpers.py`. Fixture `app_and_session` repetida pode ir para `conftest.py`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/app/modules/marcacoes/schema.py` | Criar | `PostMarcacaoRequest`, `AjusteMarcacaoRequest`, `MarcacaoResponse` |
| `apps/api/app/modules/marcacoes/repository.py` | Criar | `class MarcacaoRepository` — `get_by_idempotency`, `get_by_id_owned_by`, `list_for_terceiro`, `create`, `ajustar` |
| `apps/api/app/modules/jornadas/repository.py` | Criar | `class JornadaRepository` — `get_or_create_for_day(terceiro_id, data) -> Jornada`, `set_status_ajustada(jornada_id)` |
| `apps/api/app/modules/marcacoes/service.py` | Criar | `criar_marcacao` (com auto-cria jornada + idempotency + RN-012 #1 + weekend check), `listar_marcacoes`, `ajustar_marcacao` |
| `apps/api/app/modules/marcacoes/router.py` | Criar | `POST/GET /api/v1/marcacoes`, `PUT /api/v1/marcacoes/{id}` |
| `apps/api/app/main.py` | Modificar | Registrar `marcacoes_router` |
| `apps/api/tests/test_marcacoes_post.py` | Criar | 8 testes |
| `apps/api/tests/test_marcacoes_put.py` | Criar | 4 testes |

> Total: 8 arquivos. Dentro do orçamento. `JornadaRepository` é introduzido aqui (mínimo necessário) e estendido na TASK-017.

### Detalhamento Técnico

**1. `apps/api/app/modules/marcacoes/schema.py`:**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MarcacaoTipo = Literal["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]
OrigemAgente = Literal["AGENTE_AUTOMATICO", "AGENTE_CONFIRMADO"]
OrigemAny = Literal["AGENTE_AUTOMATICO", "AGENTE_CONFIRMADO", "AJUSTE_WEB"]
StatusMarcacao = Literal["CONFIRMADA", "PENDENTE", "AJUSTADA"]


class PostMarcacaoRequest(BaseModel):
    tipo: MarcacaoTipo
    horario_registrado: datetime  # UTC ISO 8601
    horario_efetivo: datetime | None = None
    origem: OrigemAgente
    idempotency_key: UUID


class AjusteMarcacaoRequest(BaseModel):
    horario_efetivo: datetime
    motivo: str = Field(min_length=5, max_length=500)


class MarcacaoResponse(BaseModel):
    id: str
    jornada_id: str
    tipo: str
    horario_registrado: str
    horario_efetivo: str | None
    origem: str
    status: str
    confirmado_pelo_usuario: bool
    idempotency_key: str
    criada_em: str
```

**2. `apps/api/app/modules/jornadas/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Jornada


class JornadaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_terceiro_and_data(self, terceiro_id: str, data: str) -> Jornada | None:
        return (
            await self.session.execute(
                select(Jornada).where(Jornada.terceiro_id == terceiro_id, Jornada.data == data)
            )
        ).scalar_one_or_none()

    async def get_or_create_for_day(self, terceiro_id: str, data: str) -> Jornada:
        existing = await self.get_by_terceiro_and_data(terceiro_id, data)
        if existing is not None:
            return existing
        j = Jornada(
            id=str(uuid4()), terceiro_id=terceiro_id, data=data,
            status="EM_ANDAMENTO", criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(j)
        return j

    async def set_status_ajustada(self, jornada_id: str) -> None:
        j = (await self.session.execute(select(Jornada).where(Jornada.id == jornada_id))).scalar_one()
        if j.status != "AJUSTADA_MANUALMENTE":
            j.status = "AJUSTADA_MANUALMENTE"
```

**3. `apps/api/app/modules/marcacoes/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Jornada, Marcacao


class MarcacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_idempotency(self, idempotency_key: str) -> Marcacao | None:
        return (
            await self.session.execute(select(Marcacao).where(Marcacao.idempotency_key == idempotency_key))
        ).scalar_one_or_none()

    async def get_in_jornada_by_tipo(self, jornada_id: str, tipo: str) -> Marcacao | None:
        return (
            await self.session.execute(
                select(Marcacao).where(Marcacao.jornada_id == jornada_id, Marcacao.tipo == tipo)
            )
        ).scalar_one_or_none()

    async def get_by_id_owned_by(self, marcacao_id: str, terceiro_id: str) -> Marcacao | None:
        # Join jornada → garante ownership
        row = (
            await self.session.execute(
                select(Marcacao).join(Jornada, Jornada.id == Marcacao.jornada_id)
                .where(Marcacao.id == marcacao_id, Jornada.terceiro_id == terceiro_id)
            )
        ).scalar_one_or_none()
        return row

    async def list_for_terceiro(self, terceiro_id: str, status: str | None) -> list[Marcacao]:
        stmt = (
            select(Marcacao).join(Jornada, Jornada.id == Marcacao.jornada_id)
            .where(Jornada.terceiro_id == terceiro_id)
            .order_by(Marcacao.criada_em.desc())
        )
        if status:
            stmt = stmt.where(Marcacao.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self, *, jornada_id: str, tipo: str, horario_registrado: str,
        horario_efetivo: str | None, origem: str, idempotency_key: str,
    ) -> Marcacao:
        m = Marcacao(
            id=str(uuid4()), jornada_id=jornada_id, tipo=tipo,
            horario_registrado=horario_registrado, horario_efetivo=horario_efetivo,
            origem=origem, status="CONFIRMADA",
            confirmado_pelo_usuario=1 if origem == "AGENTE_CONFIRMADO" else 0,
            idempotency_key=idempotency_key,
            criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(m)
        return m

    @staticmethod
    def snapshot(m: Marcacao) -> dict:
        return {
            "tipo": m.tipo,
            "horario_registrado": m.horario_registrado,
            "horario_efetivo": m.horario_efetivo,
            "origem": m.origem,
            "status": m.status,
        }

    async def ajustar(self, m: Marcacao, horario_efetivo: str) -> None:
        m.horario_efetivo = horario_efetivo
        m.origem = "AJUSTE_WEB"
        m.status = "AJUSTADA"
```

**4. `apps/api/app/modules/marcacoes/service.py`:**

```python
from __future__ import annotations

from datetime import date as dt_date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError, ErrorDetail
from app.models import Marcacao, Terceiro
from app.modules.jornadas.repository import JornadaRepository
from app.modules.marcacoes.repository import MarcacaoRepository


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _to_response(m: Marcacao) -> dict:
    return {
        "id": m.id, "jornada_id": m.jornada_id, "tipo": m.tipo,
        "horario_registrado": m.horario_registrado,
        "horario_efetivo": m.horario_efetivo,
        "origem": m.origem, "status": m.status,
        "confirmado_pelo_usuario": bool(m.confirmado_pelo_usuario),
        "idempotency_key": m.idempotency_key,
        "criada_em": m.criada_em,
    }


async def criar_marcacao(session: AsyncSession, t: Terceiro, payload: dict) -> dict:
    h_reg: datetime = payload["horario_registrado"]
    data_jornada = h_reg.date().isoformat()
    # Weekend check
    if not t.trabalha_fim_de_semana and dt_date.fromisoformat(data_jornada).weekday() >= 5:
        raise DomainError(
            code="FIM_DE_SEMANA_NAO_PERMITIDO",
            message="Terceiro não trabalha em fim de semana",
            http_status=422,
        )

    repo = MarcacaoRepository(session)
    idem = str(payload["idempotency_key"])

    # Idempotency check
    existing = await repo.get_by_idempotency(idem)
    if existing is not None:
        return _to_response(existing)

    # Auto-create jornada
    jrepo = JornadaRepository(session)
    j = await jrepo.get_or_create_for_day(t.id, data_jornada)

    # Conflict resolution (UNIQUE jornada_id+tipo)
    same_tipo = await repo.get_in_jornada_by_tipo(j.id, payload["tipo"])
    if same_tipo is not None:
        # RN-012 #1: AJUSTE_WEB sempre vence
        if same_tipo.origem == "AJUSTE_WEB":
            raise DomainError(
                code="AJUSTE_WEB_WINS",
                message="Marcação foi ajustada via Web — Agente descarta",
                http_status=409,
            )
        # Demais conflitos: 409 CONFLICT genérico
        raise DomainError(
            code="CONFLICT",
            message=f"Já existe marcação do tipo {payload['tipo']} para esta jornada",
            http_status=409,
        )

    m = await repo.create(
        jornada_id=j.id, tipo=payload["tipo"],
        horario_registrado=_iso(h_reg),
        horario_efetivo=_iso(payload["horario_efetivo"]) if payload.get("horario_efetivo") else None,
        origem=payload["origem"],
        idempotency_key=idem,
    )
    await session.commit()
    await session.refresh(m)
    return _to_response(m)


async def listar_marcacoes(session: AsyncSession, t: Terceiro, status: str | None) -> list[dict]:
    repo = MarcacaoRepository(session)
    rows = await repo.list_for_terceiro(t.id, status)
    return [_to_response(m) for m in rows]


async def ajustar_marcacao(
    session: AsyncSession, t: Terceiro, marcacao_id: str, payload: dict
) -> dict:
    repo = MarcacaoRepository(session)
    m = await repo.get_by_id_owned_by(marcacao_id, t.id)
    if m is None:
        raise DomainError(code="NOT_FOUND", message="Marcação não encontrada", http_status=404)
    antes = repo.snapshot(m)
    h_ef: datetime = payload["horario_efetivo"]
    await repo.ajustar(m, _iso(h_ef))
    depois = repo.snapshot(m)
    await log_audit(
        session, entidade="Marcacao", entidade_id=m.id, autor=t.email_contato,
        antes=antes, depois=depois, motivo=payload["motivo"],
    )
    # Atualiza status da jornada
    jrepo = JornadaRepository(session)
    await jrepo.set_status_ajustada(m.jornada_id)
    await session.commit()
    await session.refresh(m)
    return _to_response(m)
```

**5. `apps/api/app/modules/marcacoes/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.marcacoes import service
from app.modules.marcacoes.schema import (
    AjusteMarcacaoRequest,
    MarcacaoResponse,
    PostMarcacaoRequest,
)

router = APIRouter(prefix="/api/v1/marcacoes", tags=["marcacoes"])


@router.post("", status_code=201, response_model=MarcacaoResponse)
async def criar(body: PostMarcacaoRequest, t: CurrentTerceiroDep, session: SessionDep) -> MarcacaoResponse:
    data = await service.criar_marcacao(session, t, body.model_dump())
    return MarcacaoResponse(**data)


@router.get("", response_model=list[MarcacaoResponse])
async def listar(t: CurrentTerceiroDep, session: SessionDep, status: str | None = Query(default=None)) -> list[MarcacaoResponse]:
    rows = await service.listar_marcacoes(session, t, status)
    return [MarcacaoResponse(**r) for r in rows]


@router.put("/{marcacao_id}", response_model=MarcacaoResponse)
async def ajustar(
    marcacao_id: str, body: AjusteMarcacaoRequest, t: CurrentTerceiroDep, session: SessionDep
) -> MarcacaoResponse:
    data = await service.ajustar_marcacao(session, t, marcacao_id, body.model_dump())
    return MarcacaoResponse(**data)
```

**6. `apps/api/app/main.py`** — adicionar:

```python
from app.modules.marcacoes.router import router as marcacoes_router
app.include_router(marcacoes_router)
```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-017 (jornadas + atividades + justificativas + auditoria endpoint):
    - JornadaRepository (get_or_create_for_day, set_status_ajustada, get_by_terceiro_and_data) — TASK-017 estende com queries de listagem/detalhe.
    - MarcacaoRepository — TASK-017 reutiliza para criar 4 marcações em POST /jornadas/manual (com origem=AJUSTE_WEB).
    - Modelo Marcacao + Jornada já alinhados ao schema.
  TASK-018 (relatórios):
    - GET /api/v1/marcacoes serve listagem (consumido por export futuro se necessário, mas relatório usa jornadas/marcacoes diretamente via SQL).
  Phase 5 (Agente .NET):
    - POST /api/v1/marcacoes contrato HTTP estável (idempotency_key UUID v4, origem AGENTE_AUTOMATICO|AGENTE_CONFIRMADO, retorno 201 idempotente, 409 CONFLICT/AJUSTE_WEB_WINS).

Consome de:
  TASK-012: CurrentTerceiroDep, SessionDep, DomainError, log_audit.
  TASK-010: modelos Jornada, Marcacao, LogAuditoria.

Erros:
  - 401 UNAUTHORIZED (deps).
  - 409 CONFLICT (tipo duplicado no dia) e 409 AJUSTE_WEB_WINS (RN-012).
  - 404 NOT_FOUND (marcacao_id inexistente ou de outro terceiro).
  - 422 VALIDATION_ERROR (origem=AJUSTE_WEB no POST, motivo<5, payload inválido).
  - 422 FIM_DE_SEMANA_NAO_PERMITIDO (sábado/domingo sem flag).
```

## Contrato HTTP

```
POST /api/v1/marcacoes   (auth Bearer)
Content-Type: application/json

Request body:
{
  "tipo": "INICIO_JORNADA",                  // enum: INICIO_JORNADA|SAIDA_ALMOCO|RETORNO_ALMOCO|FIM_JORNADA
  "horario_registrado": "2026-05-27T09:02:00Z", // UTC ISO 8601
  "horario_efetivo": null,                   // opcional, ISO 8601
  "origem": "AGENTE_AUTOMATICO",             // enum: AGENTE_AUTOMATICO|AGENTE_CONFIRMADO (AJUSTE_WEB proibido)
  "idempotency_key": "<uuid v4>"             // 36 chars
}

Response 201: MarcacaoResponse (criado ou idempotente)
Response 409: {"code":"CONFLICT","message":"Já existe marcação do tipo X para esta jornada","details":[]}
Response 409: {"code":"AJUSTE_WEB_WINS","message":"Marcação foi ajustada via Web — Agente descarta","details":[]}
Response 422: {"code":"VALIDATION_ERROR",...} (origem=AJUSTE_WEB ou outros campos)
Response 422: {"code":"FIM_DE_SEMANA_NAO_PERMITIDO",...}

GET /api/v1/marcacoes?status=PENDENTE   (auth Bearer)
Response 200: [MarcacaoResponse, ...] (vazio se nada do terceiro autenticado)

PUT /api/v1/marcacoes/{id}   (auth Bearer)
Request body:
{
  "horario_efetivo": "2026-05-27T09:00:00Z",  // ISO 8601
  "motivo": "corrigir atraso de relógio"      // min 5 chars
}
Response 200: MarcacaoResponse com origem=AJUSTE_WEB, status=AJUSTADA; jornada da marcação vira AJUSTADA_MANUALMENTE; +1 LogAuditoria(entidade=Marcacao)
Response 404: {"code":"NOT_FOUND","message":"Marcação não encontrada","details":[]}
Response 422: motivo<5

MarcacaoResponse schema:
{
  "id": "<uuid>",
  "jornada_id": "<uuid>",
  "tipo": "INICIO_JORNADA",
  "horario_registrado": "<iso>",
  "horario_efetivo": "<iso>" | null,
  "origem": "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO" | "AJUSTE_WEB",
  "status": "CONFIRMADA" | "PENDENTE" | "AJUSTADA",
  "confirmado_pelo_usuario": true|false,
  "idempotency_key": "<uuid>",
  "criada_em": "<iso>"
}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/test_marcacoes_post.py tests/test_marcacoes_put.py -v` — todos passam.
3. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/ -v` — suite continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** Após o green, considerar mover `_to_response` para `schema.py` como classmethod. Considerar extrair `_iso` helper para `app/core/datetime_utils.py` se TASK-017 também precisar.
