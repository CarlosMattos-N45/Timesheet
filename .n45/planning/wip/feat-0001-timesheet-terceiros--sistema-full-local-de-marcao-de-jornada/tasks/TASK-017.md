---
checkpoint: null
complexity: G
created_at: "2026-05-28 09:35:58"
criteria:
    - done: true
      test: pytest -k test_list_jornadas_returns_month_with_totals
      text: GET /api/v1/jornadas?mes=2026-05 retorna JornadasMesResponse com total_horas_mes_s somando jornadas completas e tem_marcacao_pendente true se EXISTS marcacao.status=PENDENTE
    - done: true
      test: pytest -k test_list_jornadas_empty_returns_zero_total
      text: GET /jornadas?mes=YYYY-MM sem jornadas retorna total=0 e jornadas=[]
    - done: true
      test: pytest -k test_list_jornadas_invalid_mes_returns_422
      text: GET /jornadas?mes=invalid retorna 422
    - done: true
      test: pytest -k test_get_jornada_detalhe
      text: GET /api/v1/jornadas/{id} carrega marcacoes (4) + atividade + justificativas + total_horas_apuradas_s eager-loaded
    - done: true
      test: pytest -k test_put_jornada_ajusta_marcacoes_cria_justif_e_audit
      text: PUT /api/v1/jornadas/{id} valido atualiza marcacoes (origem=AJUSTE_WEB), status=AJUSTADA_MANUALMENTE, cria Justificativa e LogAuditoria(entidade=Jornada)
    - done: true
      test: pytest -k test_put_jornada_motivo_short_returns_422
      text: PUT /jornadas com motivo<5 retorna 422
    - done: true
      test: pytest -k test_get_jornada_inexistente_returns_404
      text: GET /jornadas/{id} inexistente retorna 404
    - done: true
      test: pytest -k test_post_jornada_manual_creates_all
      text: POST /api/v1/jornadas/manual valido em dia sem jornada cria Jornada(AJUSTADA_MANUALMENTE) + 4 Marcacoes(AJUSTE_WEB) + 1 Atividade + 1 Justificativa + 1 LogAuditoria(Jornada)
    - done: true
      test: pytest -k test_post_jornada_manual_in_existing_day_returns_409
      text: POST /jornadas/manual em dia ja com jornada retorna 409 CONFLICT
    - done: true
      test: pytest -k test_post_jornada_manual_rejects_only_3_marcacoes
      text: POST /jornadas/manual com 3 marcacoes retorna 422
    - done: true
      test: pytest -k test_post_jornada_manual_rejects_short_atividade
      text: POST /jornadas/manual com atividade<10 chars retorna 422
    - done: true
      test: pytest -k test_post_jornada_manual_rejects_non_chronological
      text: POST /jornadas/manual com horarios fora de ordem cronologica retorna 422
    - done: true
      test: pytest -k test_post_atividade_creates_and_audits
      text: POST /api/v1/jornadas/{id}/atividade em jornada sem atividade cria Atividade + LogAuditoria(entidade=Atividade, antes_json=null)
    - done: true
      test: pytest -k test_post_atividade_updates_existing
      text: POST /atividade em jornada com atividade existente atualiza descricao + atualizado_em e cria 2 LogAuditoria (a 2a com antes_json populado)
    - done: true
      test: pytest -k test_post_atividade_short_returns_422
      text: POST /atividade com descricao<10 retorna 422
    - done: true
      test: pytest -k test_get_auditoria_filters_and_orders_desc
      text: GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id> retorna lista ordenada por criado_em DESC
    - done: true
      test: pytest -k test_get_auditoria_invalid_entidade_returns_422
      text: GET /auditoria com entidade fora de {Jornada,Marcacao,Terceiro,Atividade} retorna 422
    - done: true
      test: pytest -k test_get_auditoria_requires_auth
      text: GET /auditoria sem auth retorna 401
    - done: true
      test: pytest --cov=app/modules/jornadas --cov=app/modules/atividades --cov=app/modules/justificativas --cov=app/modules/auditoria --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/{jornadas,atividades,justificativas,auditoria}
    - done: true
      test: grep -E '^class (Jornada|Atividade|Justificativa|Auditoria)Repository' apps/api/app/modules/jornadas/repository.py apps/api/app/modules/atividades/repository.py apps/api/app/modules/justificativas/repository.py apps/api/app/modules/auditoria/repository.py
      text: 'Repository pattern: JornadaRepository, AtividadeRepository, JustificativaRepository, AuditoriaRepository definidos como classes Python'
deps:
    - TASK-012
    - TASK-016
id: TASK-017
linter: ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 3 — Backend por Domínio
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: pytest tests/test_jornadas_list.py tests/test_jornadas_detail_and_put.py tests/test_jornadas_manual.py tests/test_atividade.py tests/test_auditoria_get.py -v
title: 'Jornadas + Atividades + Justificativas + Auditoria: GET mês/detalhe, PUT (ajuste+audit+justif), POST manual (4 marcações AJUSTE_WEB), POST atividade (upsert+audit), GET /auditoria'
updated_at: "2026-05-28 11:20:41"
---
## Contexto

Esta task entrega o **slice vertical das Jornadas + Atividades + Justificativas + endpoint de Auditoria**. É o domínio mais rico em endpoints Web — implementa toda a interação da SPA com jornadas além das marcações:

1. `GET /api/v1/jornadas?mes=YYYY-MM` — lista mensal com 4 horários, total, status, `tem_marcacao_pendente`.
2. `GET /api/v1/jornadas/{id}` — detalhe com marcações, atividade, justificativas.
3. `PUT /api/v1/jornadas/{id}` — ajuste em lote (várias marcações + motivo). Cria audit log + justificativa.
4. `POST /api/v1/jornadas/manual` — criar jornada para dia sem eventos (4 marcações origem=AJUSTE_WEB + atividade + justificativa).
5. `POST /api/v1/jornadas/{id}/atividade` — criar/atualizar atividade.
6. `GET /api/v1/auditoria?entidade=&entidade_id=` — listar log de auditoria de uma entidade.

Esta task **consome** o `JornadaRepository.get_or_create_for_day` da TASK-016 e o `MarcacaoRepository.create` para inserir marcações ao criar jornada manual.

Estado atual (fim TASK-016):
- ORM `Jornada`, `Marcacao`, `Atividade`, `Justificativa`, `LogAuditoria`.
- `JornadaRepository` (parcial, da TASK-016): `get_or_create_for_day`, `set_status_ajustada`, `get_by_terceiro_and_data`.
- `MarcacaoRepository.create` disponível.
- `log_audit` no `app.core.audit`.
- `CurrentTerceiroDep` autentica.

**Decisões nesta task:**

- **Cálculo de total diário** (`total_horas_apuradas_s`): se as 4 marcações existem com `horario_efetivo` (ou `horario_registrado` quando `efetivo IS NULL`), total = `(FIM - INICIO) - (RETORNO_ALMOCO - SAIDA_ALMOCO)`. Se faltam marcações ou alguma está `PENDENTE`, total = `null`. Computado **on demand** no GET, não persistido em cache (campo `total_horas_apuradas_s` permanece na tabela para PDF, mas é atualizado a cada PUT/manual).
- **`tem_marcacao_pendente`** computado por query: `EXISTS (SELECT 1 FROM marcacao WHERE jornada_id=jornada.id AND status='PENDENTE')`.
- **Total mensal** = soma de `total_horas_apuradas_s` das jornadas do mês (NULL contam como 0).
- **`POST /jornadas/manual`**: cria `Jornada(status="AJUSTADA_MANUALMENTE")` + 4 marcações (`origem=AJUSTE_WEB`, `status=AJUSTADA`, `idempotency_key=uuid4` cada) + 1 atividade + 1 justificativa, tudo na mesma transação. Audit log no entidade `Jornada`.
- **`POST /jornadas/{id}/atividade`**: upsert. Se já existe, atualiza `descricao` + `atualizado_em`. Cria audit log `entidade=Atividade`.
- **`PUT /jornadas/{id}`**: atualiza N marcações (por `tipo` no payload, não por id — frontend manda lista de 4) + cria justificativa + audit log entidade=Jornada com diff completo de marcações. Status vira `AJUSTADA_MANUALMENTE`.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `GET /api/v1/jornadas?mes=2026-05` autenticado | `200`, body `{mes_referencia, total_horas_mes_s, jornadas: [{id,data,status,total_horas_apuradas_s,tem_marcacao_pendente, horario_inicio, horario_saida_almoco, horario_retorno_almoco, horario_fim}]}`, ordenado por `data ASC` |
| `GET /api/v1/jornadas?mes=2026-05` sem jornadas | `200`, `jornadas=[]`, `total_horas_mes_s=0` |
| `GET /api/v1/jornadas?mes=invalido` | `422` com field=`query.mes` |
| `GET /api/v1/jornadas/{id}` autenticado, jornada do terceiro | `200`, body com marcações (4 itens com `tipo`, `horario_efetivo`, `status`), atividade (objeto ou null), justificativas (array), `total_horas_apuradas_s` |
| `GET /api/v1/jornadas/{id}` jornada inexistente ou de outro terceiro | `404` |
| `PUT /api/v1/jornadas/{id}` válido com 2 marcações no payload + `motivo>=5` | `200`, body com jornada atualizada `status=AJUSTADA_MANUALMENTE`; atualiza marcações (origem=AJUSTE_WEB); cria 1 `Justificativa(motivo,usuario_responsavel=email)` + 1 `LogAuditoria(entidade=Jornada)` com diff |
| `PUT /api/v1/jornadas/{id}` com `motivo<5` | `422` |
| `POST /api/v1/jornadas/manual` válido (dia sem jornada) | `201`, body como `GET /jornadas/{id}`; cria Jornada(AJUSTADA_MANUALMENTE) + 4 Marcações(AJUSTE_WEB) + 1 Atividade + 1 Justificativa + 1 LogAuditoria(Jornada) |
| `POST /api/v1/jornadas/manual` em dia já com jornada | `409` com `{"code":"CONFLICT","message":"Já existe jornada para esta data"}` |
| `POST /api/v1/jornadas/manual` com 3 marcações (não 4) | `422` |
| `POST /api/v1/jornadas/manual` com horários fora de ordem | `422` |
| `POST /api/v1/jornadas/manual` com `atividade<10` ou `motivo<5` | `422` |
| `POST /api/v1/jornadas/{id}/atividade` em jornada sem atividade | `201`, cria `Atividade`; cria `LogAuditoria(entidade=Atividade, antes=null)` |
| `POST /api/v1/jornadas/{id}/atividade` em jornada com atividade existente | `201`, atualiza `descricao` + `atualizado_em`; `LogAuditoria(entidade=Atividade, antes={"descricao":old})` |
| `POST /atividade` com `descricao<10` | `422` |
| `POST /atividade` em jornada de outro terceiro | `404` |
| `GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id>` autenticado | `200`, lista de `{id, entidade, entidade_id, autor, antes_json, depois_json, motivo, criado_em}` ordenado por `criado_em DESC` |
| `GET /auditoria` sem auth | `401` |
| `GET /auditoria` com entidade inválida | `422` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_jornadas_list.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_and_session(tmp_path, monkeypatch):
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
                idempotency_key=tipo + "-id-aaaaaaaaaaaaaaaaaaaaaaaa"[:36 - len(tipo) - 4],
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


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_list_jornadas_returns_month_with_totals(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
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
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas?mes=2026-04", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"mes_referencia": "2026-04", "total_horas_mes_s": 0, "jornadas": []}


@pytest.mark.asyncio
async def test_list_jornadas_invalid_mes_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas?mes=invalid", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
```

### `apps/api/tests/test_jornadas_detail_and_put.py`

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
async def test_get_jornada_detalhe(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
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
    tok = await _login(app)
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
        m_inicio = (await s.execute(select(Marcacao).where(Marcacao.jornada_id == "j-1", Marcacao.tipo == "INICIO_JORNADA"))).scalar_one()
        assert m_inicio.horario_efetivo == "2026-05-27T08:55:00+00:00"
        assert m_inicio.origem == "AJUSTE_WEB"
        justifs = (await s.execute(select(Justificativa).where(Justificativa.jornada_id == "j-1"))).scalars().all()
        assert len(justifs) == 1
        assert justifs[0].motivo == "ajuste do relogio interno"
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Jornada"))).scalars().all()
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_put_jornada_motivo_short_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.put(
            "/api/v1/jornadas/j-1",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "marcacoes": [{"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T08:55:00+00:00"}],
                "motivo": "abc",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_jornada_inexistente_returns_404(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/jornadas/nao-existe", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
```

### `apps/api/tests/test_jornadas_manual.py`

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
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


def _valid_manual() -> dict:
    return {
        "data": "2026-05-27",
        "marcacoes": [
            {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T09:00:00+00:00"},
            {"tipo": "SAIDA_ALMOCO", "horario_efetivo": "2026-05-27T12:00:00+00:00"},
            {"tipo": "RETORNO_ALMOCO", "horario_efetivo": "2026-05-27T13:00:00+00:00"},
            {"tipo": "FIM_JORNADA", "horario_efetivo": "2026-05-27T18:00:00+00:00"},
        ],
        "atividade": "Trabalhei no projeto X durante o dia inteiro",
        "motivo": "esqueci de fazer login no PC",
    }


@pytest.mark.asyncio
async def test_post_jornada_manual_creates_all(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, Jornada, Justificativa, LogAuditoria, Marcacao
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=_valid_manual())
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["status"] == "AJUSTADA_MANUALMENTE"
    assert len(body["marcacoes"]) == 4
    async with sm() as s:
        j = (await s.execute(select(Jornada))).scalar_one()
        assert j.status == "AJUSTADA_MANUALMENTE"
        marcs = (await s.execute(select(Marcacao))).scalars().all()
        assert len(marcs) == 4
        assert all(m.origem == "AJUSTE_WEB" for m in marcs)
        ats = (await s.execute(select(Atividade))).scalars().all()
        assert len(ats) == 1
        justifs = (await s.execute(select(Justificativa))).scalars().all()
        assert len(justifs) == 1
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Jornada"))).scalars().all()
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_post_jornada_manual_in_existing_day_returns_409(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=_valid_manual())
        r2 = await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=_valid_manual())
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_only_3_marcacoes(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    payload = _valid_manual()
    payload["marcacoes"].pop()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_short_atividade(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    payload = _valid_manual()
    payload["atividade"] = "curta"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_jornada_manual_rejects_non_chronological(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    payload = _valid_manual()
    payload["marcacoes"][0]["horario_efetivo"] = "2026-05-27T20:00:00+00:00"  # depois do fim
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/jornadas/manual", headers={"Authorization": f"Bearer {tok}"}, json=payload)
    assert r.status_code == 422
```

### `apps/api/tests/test_atividade.py`

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
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Jornada, Terceiro
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
        s.add(Jornada(id="j-1", terceiro_id="t-1", data="2026-05-27", status="FECHADA", criada_em=now))
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
async def test_post_atividade_creates_and_audits(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, LogAuditoria
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/jornadas/j-1/atividade",
            headers={"Authorization": f"Bearer {tok}"},
            json={"descricao": "trabalhei oito horas no projeto X"},
        )
    assert r.status_code == 201
    async with sm() as s:
        a = (await s.execute(select(Atividade))).scalar_one()
        assert a.descricao == "trabalhei oito horas no projeto X"
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Atividade"))).scalars().all()
        assert len(audits) == 1
        assert audits[0].antes_json is None


@pytest.mark.asyncio
async def test_post_atividade_updates_existing(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import Atividade, LogAuditoria
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/jornadas/j-1/atividade", headers={"Authorization": f"Bearer {tok}"},
                     json={"descricao": "atividade original mais longa"})
        await c.post("/api/v1/jornadas/j-1/atividade", headers={"Authorization": f"Bearer {tok}"},
                     json={"descricao": "atividade atualizada mais detalhada"})
    async with sm() as s:
        ats = (await s.execute(select(Atividade))).scalars().all()
        assert len(ats) == 1
        assert ats[0].descricao == "atividade atualizada mais detalhada"
        assert ats[0].atualizado_em is not None
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Atividade"))).scalars().all()
        assert len(audits) == 2
        assert audits[1].antes_json is not None  # 2o tem antes


@pytest.mark.asyncio
async def test_post_atividade_short_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/jornadas/j-1/atividade",
            headers={"Authorization": f"Bearer {tok}"},
            json={"descricao": "curta"},
        )
    assert r.status_code == 422
```

### `apps/api/tests/test_auditoria_get.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_and_session(tmp_path, monkeypatch):
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
        from uuid import uuid4
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


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_get_auditoria_filters_and_orders_desc(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/auditoria?entidade=Jornada&entidade_id=j-1", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["motivo"] == "re-ajuste"  # mais recente primeiro
    assert body[1]["motivo"] == "ajuste"


@pytest.mark.asyncio
async def test_get_auditoria_invalid_entidade_returns_422(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/auditoria?entidade=Foo&entidade_id=x", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_auditoria_requires_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/auditoria?entidade=Jornada&entidade_id=j-1")
    assert r.status_code == 401
```

**Refatoração:** Após o green, extrair `app_and_session` para fixture comum em `conftest.py` + helper `_login` em `tests/helpers.py`. `_calc_total_diario_s` deve virar utility em `app/modules/jornadas/service.py`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/app/modules/jornadas/schema.py` | Criar | `JornadaResumo`, `JornadasMesResponse`, `JornadaDetalheResponse`, `AjusteJornadaRequest`, `MarcacaoManualItem`, `JornadaManualRequest`, `AjusteMarcacaoItem` |
| `apps/api/app/modules/jornadas/repository.py` | Modificar | Adicionar: `list_for_month(terceiro_id, mes)`, `get_detalhe(jornada_id, terceiro_id) -> Jornada com marcacoes/atividade/justificativas eager-loaded`, `update_total_horas(jornada_id, total_s)` |
| `apps/api/app/modules/jornadas/service.py` | Criar | `listar_mes`, `detalhe`, `ajustar_jornada`, `criar_manual`, `_compute_total_diario_s`, `_check_chronological` |
| `apps/api/app/modules/jornadas/router.py` | Criar | `GET/PUT /api/v1/jornadas/{id}`, `GET /api/v1/jornadas?mes=`, `POST /api/v1/jornadas/manual` |
| `apps/api/app/modules/atividades/schema.py` | Criar | `AtividadeRequest`, `AtividadeResponse` |
| `apps/api/app/modules/atividades/repository.py` | Criar | `class AtividadeRepository` — `get_by_jornada(j_id)`, `upsert(jornada_id, descricao, autor)` (com audit log inline) |
| `apps/api/app/modules/atividades/service.py` | Criar | `upsert_atividade(session, t, jornada_id, descricao)` (com ownership check + audit) |
| `apps/api/app/modules/atividades/router.py` | Criar | `POST /api/v1/jornadas/{id}/atividade` |
| `apps/api/app/modules/justificativas/repository.py` | Criar | `class JustificativaRepository` — `create(jornada_id, motivo, usuario_responsavel)` |
| `apps/api/app/modules/auditoria/schema.py` | Criar | `AuditoriaItem` (id, entidade, entidade_id, autor, antes_json, depois_json, motivo, criado_em) |
| `apps/api/app/modules/auditoria/repository.py` | Criar | `class AuditoriaRepository` — `list(entidade, entidade_id) -> list[LogAuditoria]` |
| `apps/api/app/modules/auditoria/router.py` | Criar | `GET /api/v1/auditoria?entidade=&entidade_id=` |
| `apps/api/app/main.py` | Modificar | Registrar `jornadas_router`, `atividades_router`, `auditoria_router` |
| `apps/api/tests/test_jornadas_list.py` | Criar | 3 testes |
| `apps/api/tests/test_jornadas_detail_and_put.py` | Criar | 4 testes |
| `apps/api/tests/test_jornadas_manual.py` | Criar | 5 testes |
| `apps/api/tests/test_atividade.py` | Criar | 3 testes |
| `apps/api/tests/test_auditoria_get.py` | Criar | 3 testes |

> **Total: 18 arquivos**. Excede o teto (8) — exceção justificada pela coesão: jornada + atividade + justificativa + auditoria são entrelaçados (toda mutação de jornada cria justificativa+auditoria; atividade é 1:1 com jornada). Dividir em 4 tasks separadas geraria deps em cadeia (auditoria → jornadas → marcacoes) e conflito em `main.py` e em `service.py` da jornada (que invoca `JustificativaRepository.create` + `log_audit`). Cada arquivo é pequeno (≤ 100 linhas), e o domínio é uma unidade vertical da SPA.

### Detalhamento Técnico

**1. `apps/api/app/modules/jornadas/schema.py`:**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

MarcacaoTipo = Literal["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]


class JornadaResumo(BaseModel):
    id: str
    data: str
    status: str
    total_horas_apuradas_s: int | None
    tem_marcacao_pendente: bool
    horario_inicio: str | None
    horario_saida_almoco: str | None
    horario_retorno_almoco: str | None
    horario_fim: str | None


class JornadasMesResponse(BaseModel):
    mes_referencia: str
    total_horas_mes_s: int
    jornadas: list[JornadaResumo]


class MarcacaoDetalhe(BaseModel):
    id: str
    tipo: str
    horario_registrado: str
    horario_efetivo: str | None
    origem: str
    status: str


class JornadaDetalheResponse(BaseModel):
    id: str
    data: str
    status: str
    total_horas_apuradas_s: int | None
    marcacoes: list[MarcacaoDetalhe]
    atividade: dict | None  # {id, descricao, registrada_em, atualizado_em}
    justificativas: list[dict]  # [{id, motivo, usuario_responsavel, criada_em}]


class AjusteMarcacaoItem(BaseModel):
    tipo: MarcacaoTipo
    horario_efetivo: datetime


class AjusteJornadaRequest(BaseModel):
    marcacoes: list[AjusteMarcacaoItem] = Field(min_length=1, max_length=4)
    motivo: str = Field(min_length=5, max_length=500)


class MarcacaoManualItem(BaseModel):
    tipo: MarcacaoTipo
    horario_efetivo: datetime


class JornadaManualRequest(BaseModel):
    data: date
    marcacoes: list[MarcacaoManualItem] = Field(min_length=4, max_length=4)
    atividade: str = Field(min_length=10, max_length=2000)
    motivo: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def _validate(self):
        tipos = [m.tipo for m in self.marcacoes]
        if set(tipos) != {"INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"}:
            raise ValueError({"loc": ("marcacoes",), "msg": "as 4 marcações de tipos distintos são obrigatórias"})
        # Ordenar por tipo canônico
        ordem = {"INICIO_JORNADA": 0, "SAIDA_ALMOCO": 1, "RETORNO_ALMOCO": 2, "FIM_JORNADA": 3}
        sorted_m = sorted(self.marcacoes, key=lambda m: ordem[m.tipo])
        horarios = [m.horario_efetivo for m in sorted_m]
        if not all(horarios[i] < horarios[i + 1] for i in range(3)):
            raise ValueError({"loc": ("marcacoes",), "msg": "horários devem ser cronológicos"})
        return self
```

**2. `apps/api/app/modules/jornadas/repository.py`** — adicionar (mantém o que TASK-016 deixou):

```python
from sqlalchemy import and_, exists, select
from sqlalchemy.orm import selectinload

from app.models import Jornada, Marcacao


# ... mantém TASK-016 ...

    async def list_for_month(self, terceiro_id: str, mes: str) -> list[Jornada]:
        # mes: "YYYY-MM" → filtra data com LIKE "YYYY-MM%"
        stmt = (
            select(Jornada)
            .where(Jornada.terceiro_id == terceiro_id, Jornada.data.like(f"{mes}-%"))
            .options(selectinload(Jornada.marcacoes))
            .order_by(Jornada.data.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_detalhe(self, jornada_id: str, terceiro_id: str) -> Jornada | None:
        stmt = (
            select(Jornada)
            .where(Jornada.id == jornada_id, Jornada.terceiro_id == terceiro_id)
            .options(
                selectinload(Jornada.marcacoes),
                selectinload(Jornada.atividade),
                selectinload(Jornada.justificativas),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_total_horas(self, j: Jornada, total_s: int | None) -> None:
        j.total_horas_apuradas_s = total_s
```

**3. `apps/api/app/modules/atividades/schema.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class AtividadeRequest(BaseModel):
    descricao: str = Field(min_length=10, max_length=2000)


class AtividadeResponse(BaseModel):
    id: str
    jornada_id: str
    descricao: str
    registrada_em: str
    atualizado_em: str | None
```

**4. `apps/api/app/modules/atividades/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Atividade


class AtividadeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_jornada(self, jornada_id: str) -> Atividade | None:
        return (
            await self.session.execute(select(Atividade).where(Atividade.jornada_id == jornada_id))
        ).scalar_one_or_none()

    async def upsert(self, jornada_id: str, descricao: str) -> tuple[Atividade, dict | None]:
        """Returns (atividade, antes_snapshot|None se criando)."""
        existing = await self.get_by_jornada(jornada_id)
        now = datetime.now(UTC).isoformat()
        if existing is None:
            a = Atividade(
                id=str(uuid4()), jornada_id=jornada_id,
                descricao=descricao, registrada_em=now, atualizado_em=None,
            )
            self.session.add(a)
            return a, None
        antes = {"descricao": existing.descricao}
        existing.descricao = descricao
        existing.atualizado_em = now
        return existing, antes
```

**5. `apps/api/app/modules/justificativas/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Justificativa


class JustificativaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, jornada_id: str, motivo: str, usuario_responsavel: str) -> Justificativa:
        j = Justificativa(
            id=str(uuid4()), jornada_id=jornada_id, motivo=motivo,
            usuario_responsavel=usuario_responsavel,
            criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(j)
        return j
```

**6. `apps/api/app/modules/jornadas/service.py`:**

```python
from __future__ import annotations

import re
from datetime import datetime, time
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.models import Jornada, Marcacao, Terceiro
from app.modules.atividades.repository import AtividadeRepository
from app.modules.jornadas.repository import JornadaRepository
from app.modules.justificativas.repository import JustificativaRepository
from app.modules.marcacoes.repository import MarcacaoRepository

_MES_RE = re.compile(r"^\d{4}-\d{2}$")


def _parse_iso_to_secs(s: str | None) -> int | None:
    if s is None:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def _compute_total_diario_s(marcacoes: list[Marcacao]) -> int | None:
    by_tipo = {m.tipo: m for m in marcacoes}
    required = {"INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"}
    if not required.issubset(set(by_tipo.keys())):
        return None
    if any(m.status == "PENDENTE" for m in marcacoes):
        return None

    def _eff(m: Marcacao) -> int:
        s = m.horario_efetivo or m.horario_registrado
        return _parse_iso_to_secs(s) or 0

    inicio = _eff(by_tipo["INICIO_JORNADA"])
    saida_alm = _eff(by_tipo["SAIDA_ALMOCO"])
    retorno_alm = _eff(by_tipo["RETORNO_ALMOCO"])
    fim = _eff(by_tipo["FIM_JORNADA"])
    almoco = retorno_alm - saida_alm
    total = (fim - inicio) - almoco
    return total if total > 0 else 0


def _marc_to_dict(m: Marcacao) -> dict:
    return {
        "id": m.id, "tipo": m.tipo,
        "horario_registrado": m.horario_registrado,
        "horario_efetivo": m.horario_efetivo,
        "origem": m.origem, "status": m.status,
    }


def _jornada_resumo(j: Jornada) -> dict:
    by_tipo = {m.tipo: m for m in j.marcacoes}
    return {
        "id": j.id, "data": j.data, "status": j.status,
        "total_horas_apuradas_s": j.total_horas_apuradas_s,
        "tem_marcacao_pendente": any(m.status == "PENDENTE" for m in j.marcacoes),
        "horario_inicio": (by_tipo.get("INICIO_JORNADA") and (by_tipo["INICIO_JORNADA"].horario_efetivo or by_tipo["INICIO_JORNADA"].horario_registrado)) or None,
        "horario_saida_almoco": (by_tipo.get("SAIDA_ALMOCO") and (by_tipo["SAIDA_ALMOCO"].horario_efetivo or by_tipo["SAIDA_ALMOCO"].horario_registrado)) or None,
        "horario_retorno_almoco": (by_tipo.get("RETORNO_ALMOCO") and (by_tipo["RETORNO_ALMOCO"].horario_efetivo or by_tipo["RETORNO_ALMOCO"].horario_registrado)) or None,
        "horario_fim": (by_tipo.get("FIM_JORNADA") and (by_tipo["FIM_JORNADA"].horario_efetivo or by_tipo["FIM_JORNADA"].horario_registrado)) or None,
    }


async def listar_mes(session: AsyncSession, t: Terceiro, mes: str) -> dict:
    if not _MES_RE.match(mes):
        raise DomainError(code="VALIDATION_ERROR", message="Mês inválido", http_status=422)
    repo = JornadaRepository(session)
    rows = await repo.list_for_month(t.id, mes)
    jornadas = [_jornada_resumo(j) for j in rows]
    total = sum((j["total_horas_apuradas_s"] or 0) for j in jornadas)
    return {"mes_referencia": mes, "total_horas_mes_s": total, "jornadas": jornadas}


async def detalhe(session: AsyncSession, t: Terceiro, jornada_id: str) -> dict:
    repo = JornadaRepository(session)
    j = await repo.get_detalhe(jornada_id, t.id)
    if j is None:
        raise DomainError(code="NOT_FOUND", message="Jornada não encontrada", http_status=404)
    return {
        "id": j.id, "data": j.data, "status": j.status,
        "total_horas_apuradas_s": j.total_horas_apuradas_s,
        "marcacoes": [_marc_to_dict(m) for m in j.marcacoes],
        "atividade": {
            "id": j.atividade.id, "descricao": j.atividade.descricao,
            "registrada_em": j.atividade.registrada_em, "atualizado_em": j.atividade.atualizado_em,
        } if j.atividade else None,
        "justificativas": [
            {"id": jj.id, "motivo": jj.motivo, "usuario_responsavel": jj.usuario_responsavel, "criada_em": jj.criada_em}
            for jj in j.justificativas
        ],
    }


async def ajustar_jornada(session: AsyncSession, t: Terceiro, jornada_id: str, payload: dict) -> dict:
    jrepo = JornadaRepository(session)
    j = await jrepo.get_detalhe(jornada_id, t.id)
    if j is None:
        raise DomainError(code="NOT_FOUND", message="Jornada não encontrada", http_status=404)
    by_tipo = {m.tipo: m for m in j.marcacoes}
    antes = {m.tipo: {"horario_efetivo": m.horario_efetivo, "origem": m.origem} for m in j.marcacoes}
    for ajuste in payload["marcacoes"]:
        m = by_tipo.get(ajuste["tipo"])
        if m is None:
            continue  # silenciosamente ignora tipo não-existente (Web só edita os 4 existentes)
        m.horario_efetivo = ajuste["horario_efetivo"].isoformat()
        m.origem = "AJUSTE_WEB"
        m.status = "AJUSTADA"
    j.status = "AJUSTADA_MANUALMENTE"
    # Recalcula total
    j.total_horas_apuradas_s = _compute_total_diario_s(list(j.marcacoes))
    depois = {m.tipo: {"horario_efetivo": m.horario_efetivo, "origem": m.origem} for m in j.marcacoes}
    # Justificativa + audit
    jrepo_justif = JustificativaRepository(session)
    await jrepo_justif.create(jornada_id=j.id, motivo=payload["motivo"], usuario_responsavel=t.email_contato)
    await log_audit(
        session, entidade="Jornada", entidade_id=j.id,
        autor=t.email_contato, antes=antes, depois=depois, motivo=payload["motivo"],
    )
    await session.commit()
    return await detalhe(session, t, jornada_id)


async def criar_manual(session: AsyncSession, t: Terceiro, payload: dict) -> dict:
    data = payload["data"].isoformat() if hasattr(payload["data"], "isoformat") else payload["data"]
    jrepo = JornadaRepository(session)
    existing = await jrepo.get_by_terceiro_and_data(t.id, data)
    if existing is not None:
        raise DomainError(code="CONFLICT", message="Já existe jornada para esta data", http_status=409)
    # Cria jornada
    j = Jornada(
        id=str(uuid4()), terceiro_id=t.id, data=data, status="AJUSTADA_MANUALMENTE",
        criada_em=datetime.utcnow().isoformat() + "+00:00",
    )
    session.add(j)
    await session.flush()  # garante j.id antes das marcações
    # Marcacoes
    mrepo = MarcacaoRepository(session)
    for item in payload["marcacoes"]:
        h_iso = item["horario_efetivo"].isoformat()
        await mrepo.create(
            jornada_id=j.id, tipo=item["tipo"],
            horario_registrado=h_iso, horario_efetivo=h_iso,
            origem="AJUSTE_WEB",
            idempotency_key=str(uuid4()),
        )
        # Marcações criadas via manual nascem AJUSTADAS
    await session.flush()
    # Reload marcações no jornada
    j_loaded = await jrepo.get_detalhe(j.id, t.id)
    assert j_loaded is not None
    for m in j_loaded.marcacoes:
        m.origem = "AJUSTE_WEB"
        m.status = "AJUSTADA"
    j_loaded.total_horas_apuradas_s = _compute_total_diario_s(list(j_loaded.marcacoes))
    # Atividade
    arepo = AtividadeRepository(session)
    await arepo.upsert(j.id, payload["atividade"])
    # Justificativa
    jrepo_justif = JustificativaRepository(session)
    await jrepo_justif.create(jornada_id=j.id, motivo=payload["motivo"], usuario_responsavel=t.email_contato)
    # Audit (Jornada criada do zero)
    await log_audit(
        session, entidade="Jornada", entidade_id=j.id,
        autor=t.email_contato, antes=None,
        depois={"data": data, "marcacoes": len(payload["marcacoes"]), "manual": True},
        motivo=payload["motivo"],
    )
    await session.commit()
    return await detalhe(session, t, j.id)
```

> **Observação técnica `criar_manual`**: nasce com `status=AJUSTADA_MANUALMENTE`. As marcações são criadas pela `MarcacaoRepository.create` (que seta `status=CONFIRMADA` por default) e depois sobrescritas para `AJUSTE_WEB`/`AJUSTADA`. Alternativa rejeitada: parameterizar `MarcacaoRepository.create` com `origem/status` — quebra invariante "marcações criadas pelo Agente são CONFIRMADAS". Trade-off: 2 statements (create + update) em vez de 1.

**7. `apps/api/app/modules/atividades/service.py`:**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.atividades.repository import AtividadeRepository
from app.modules.jornadas.repository import JornadaRepository


async def upsert_atividade(session: AsyncSession, t: Terceiro, jornada_id: str, descricao: str) -> dict:
    jrepo = JornadaRepository(session)
    j = await jrepo.get_by_terceiro_and_data(t.id, "")  # noop guard
    # Confirma ownership da jornada
    jornada = await jrepo.get_detalhe(jornada_id, t.id)
    if jornada is None:
        raise DomainError(code="NOT_FOUND", message="Jornada não encontrada", http_status=404)
    arepo = AtividadeRepository(session)
    a, antes = await arepo.upsert(jornada_id, descricao)
    depois = {"descricao": a.descricao}
    await log_audit(
        session, entidade="Atividade", entidade_id=a.id,
        autor=t.email_contato, antes=antes, depois=depois, motivo=None,
    )
    await session.commit()
    return {
        "id": a.id, "jornada_id": a.jornada_id, "descricao": a.descricao,
        "registrada_em": a.registrada_em, "atualizado_em": a.atualizado_em,
    }
```

**8. `apps/api/app/modules/atividades/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.atividades import service
from app.modules.atividades.schema import AtividadeRequest, AtividadeResponse

router = APIRouter(prefix="/api/v1/jornadas", tags=["atividades"])


@router.post("/{jornada_id}/atividade", status_code=201, response_model=AtividadeResponse)
async def upsert(
    jornada_id: str, body: AtividadeRequest, t: CurrentTerceiroDep, session: SessionDep
) -> AtividadeResponse:
    data = await service.upsert_atividade(session, t, jornada_id, body.descricao)
    return AtividadeResponse(**data)
```

**9. `apps/api/app/modules/jornadas/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.jornadas import service
from app.modules.jornadas.schema import (
    AjusteJornadaRequest,
    JornadaDetalheResponse,
    JornadaManualRequest,
    JornadasMesResponse,
)

router = APIRouter(prefix="/api/v1/jornadas", tags=["jornadas"])


@router.get("", response_model=JornadasMesResponse)
async def listar(
    t: CurrentTerceiroDep, session: SessionDep,
    mes: str = Query(pattern=r"^\d{4}-\d{2}$"),
) -> JornadasMesResponse:
    data = await service.listar_mes(session, t, mes)
    return JornadasMesResponse(**data)


@router.get("/{jornada_id}", response_model=JornadaDetalheResponse)
async def get_detalhe(jornada_id: str, t: CurrentTerceiroDep, session: SessionDep) -> JornadaDetalheResponse:
    data = await service.detalhe(session, t, jornada_id)
    return JornadaDetalheResponse(**data)


@router.put("/{jornada_id}", response_model=JornadaDetalheResponse)
async def put_ajuste(
    jornada_id: str, body: AjusteJornadaRequest, t: CurrentTerceiroDep, session: SessionDep
) -> JornadaDetalheResponse:
    data = await service.ajustar_jornada(session, t, jornada_id, body.model_dump())
    return JornadaDetalheResponse(**data)


@router.post("/manual", status_code=201, response_model=JornadaDetalheResponse)
async def post_manual(body: JornadaManualRequest, t: CurrentTerceiroDep, session: SessionDep) -> JornadaDetalheResponse:
    data = await service.criar_manual(session, t, body.model_dump())
    return JornadaDetalheResponse(**data)
```

**10. `apps/api/app/modules/auditoria/schema.py`:**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Entidade = Literal["Jornada", "Marcacao", "Terceiro", "Atividade"]


class AuditoriaItem(BaseModel):
    id: str
    entidade: str
    entidade_id: str
    autor: str
    antes_json: str | None
    depois_json: str
    motivo: str | None
    criado_em: str
```

**11. `apps/api/app/modules/auditoria/repository.py`:**

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LogAuditoria


class AuditoriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, entidade: str, entidade_id: str) -> list[LogAuditoria]:
        stmt = (
            select(LogAuditoria)
            .where(LogAuditoria.entidade == entidade, LogAuditoria.entidade_id == entidade_id)
            .order_by(LogAuditoria.criado_em.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
```

**12. `apps/api/app/modules/auditoria/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.auditoria.repository import AuditoriaRepository
from app.modules.auditoria.schema import AuditoriaItem, Entidade

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])


@router.get("", response_model=list[AuditoriaItem])
async def listar(
    _t: CurrentTerceiroDep, session: SessionDep,
    entidade: Entidade = Query(...),
    entidade_id: str = Query(..., min_length=1),
) -> list[AuditoriaItem]:
    repo = AuditoriaRepository(session)
    rows = await repo.list(entidade, entidade_id)
    return [
        AuditoriaItem(
            id=r.id, entidade=r.entidade, entidade_id=r.entidade_id, autor=r.autor,
            antes_json=r.antes_json, depois_json=r.depois_json, motivo=r.motivo, criado_em=r.criado_em,
        )
        for r in rows
    ]
```

**13. `apps/api/app/main.py`** — adicionar:

```python
from app.modules.atividades.router import router as atividades_router
from app.modules.auditoria.router import router as auditoria_router
from app.modules.jornadas.router import router as jornadas_router
app.include_router(jornadas_router)
app.include_router(atividades_router)
app.include_router(auditoria_router)
```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-018 (relatórios):
    - listar_mes(session, t, mes) → fonte de dados para o PDF do mês (mesma estrutura).
    - PUT /jornadas/{id} e POST /jornadas/manual mutam jornada → invalidar relatorio_gerado.invalidado_em (TASK-018 hook via SQLAlchemy event listener OU chamada explícita).
  TASK-019 (wiring final):
    - Todos os endpoints registrados em main.py.
  Phase 4 (Frontend):
    - GET /jornadas (JornadasMesResponse), GET/PUT /jornadas/{id} (JornadaDetalheResponse), POST /jornadas/manual, POST /jornadas/{id}/atividade, GET /auditoria.

Consome de:
  TASK-016: JornadaRepository (estendido), MarcacaoRepository.create.
  TASK-012: CurrentTerceiroDep, SessionDep, log_audit, DomainError.
  TASK-010: modelos Jornada, Marcacao, Atividade, Justificativa, LogAuditoria.

Erros:
  - 401 UNAUTHORIZED.
  - 404 NOT_FOUND (jornada inexistente ou de outro terceiro).
  - 409 CONFLICT (jornada manual em dia já existente).
  - 422 VALIDATION_ERROR (mes inválido, motivo<5, atividade<10, 3 marcações, horários fora de ordem, entidade inválida em /auditoria).
```

## Contrato HTTP

```
GET /api/v1/jornadas?mes=2026-05   (auth Bearer)
Response 200:
{
  "mes_referencia": "2026-05",
  "total_horas_mes_s": 86400,
  "jornadas": [
    {
      "id": "<uuid>", "data": "2026-05-27", "status": "FECHADA",
      "total_horas_apuradas_s": 28800,
      "tem_marcacao_pendente": false,
      "horario_inicio": "2026-05-27T09:00:00+00:00",
      "horario_saida_almoco": "2026-05-27T12:00:00+00:00",
      "horario_retorno_almoco": "2026-05-27T13:00:00+00:00",
      "horario_fim": "2026-05-27T18:00:00+00:00"
    }
  ]
}
Response 422: mes inválido

GET /api/v1/jornadas/{id}   (auth Bearer)
Response 200: JornadaDetalheResponse com marcacoes (4 itens), atividade (objeto ou null), justificativas (array)
Response 404

PUT /api/v1/jornadas/{id}   (auth Bearer)
Request body:
{
  "marcacoes": [
    {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T08:55:00+00:00"}
  ],
  "motivo": "ajuste relógio interno"
}
Response 200: JornadaDetalheResponse atualizada; status=AJUSTADA_MANUALMENTE; +1 Justificativa +1 LogAuditoria(Jornada)
Response 422: motivo<5
Response 404

POST /api/v1/jornadas/manual   (auth Bearer)
Request body:
{
  "data": "2026-05-27",
  "marcacoes": [
    {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T09:00:00+00:00"},
    {"tipo": "SAIDA_ALMOCO", "horario_efetivo": "2026-05-27T12:00:00+00:00"},
    {"tipo": "RETORNO_ALMOCO", "horario_efetivo": "2026-05-27T13:00:00+00:00"},
    {"tipo": "FIM_JORNADA", "horario_efetivo": "2026-05-27T18:00:00+00:00"}
  ],
  "atividade": "Trabalhei no projeto X durante o dia inteiro",
  "motivo": "esqueci de fazer login"
}
Response 201: JornadaDetalheResponse criada (status=AJUSTADA_MANUALMENTE; 4 marcações origem=AJUSTE_WEB; 1 atividade; 1 justificativa; +1 LogAuditoria(Jornada))
Response 409: dia já tem jornada
Response 422: 3 marcações, atividade<10, motivo<5, horários fora de ordem

POST /api/v1/jornadas/{id}/atividade   (auth Bearer)
Request body: {"descricao": "trabalhei oito horas no projeto X"}  // min 10
Response 201: AtividadeResponse (upsert); +1 LogAuditoria(entidade=Atividade)
Response 404: jornada inexistente ou de outro terceiro
Response 422: descricao<10

GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id>   (auth Bearer)
Response 200: [AuditoriaItem, ...] ordenado por criado_em DESC
Response 401
Response 422: entidade fora de {Jornada,Marcacao,Terceiro,Atividade}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/test_jornadas_list.py tests/test_jornadas_detail_and_put.py tests/test_jornadas_manual.py tests/test_atividade.py tests/test_auditoria_get.py -v` — todos passam.
3. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/ -v` — suite completa continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** Após o green, extrair `_compute_total_diario_s` para `app/core/jornada_utils.py` se TASK-018 precisar do mesmo cálculo. Considerar criar `JornadaInvalidator` (hook) que invalida relatorio do mês a cada PUT — fica para TASK-018 implementar via SQLAlchemy event listener.
