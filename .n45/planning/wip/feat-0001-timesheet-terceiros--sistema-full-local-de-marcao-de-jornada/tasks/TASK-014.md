---
checkpoint: null
complexity: P
created_at: "2026-05-28 09:25:36"
criteria:
    - done: false
      test: pytest -k test_get_privacidade_returns_false_when_empty
      text: GET /api/v1/privacidade autenticado com banco vazio retorna {accepted:false, versao_aviso:null, aceito_em:null}
    - done: false
      test: pytest -k test_post_aceitar_inserts_row
      text: POST /api/v1/privacidade/aceitar autenticado insere PrivacyAcceptance(id=1, versao_aviso=1.0, aceito_em=now) e retorna 204
    - done: false
      test: pytest -k test_get_privacidade_returns_true_after_aceite
      text: GET /privacidade apos aceite retorna accepted=true com versao 1.0 e aceito_em populado
    - done: false
      test: pytest -k test_post_aceitar_is_idempotent
      text: POST /aceitar chamado 2 vezes mantem apenas 1 linha em privacy_acceptance (idempotente, singleton id=1)
    - done: false
      test: pytest -k test_get_privacidade_returns_false_for_old_version
      text: GET /privacidade com aceite em versao antiga (0.9) retorna accepted=false e versao_aviso=0.9 (frontend re-exibe modal)
    - done: false
      test: pytest -k test_post_aceitar_updates_old_version_inplace
      text: POST /aceitar com aceite antigo atualiza versao_aviso para 1.0 e aceito_em para now inplace (singleton mantem id=1)
    - done: false
      test: pytest -k test_endpoints_require_auth
      text: Ambos endpoints exigem auth Bearer (sem header retorna 401 com code=UNAUTHORIZED)
    - done: false
      test: pytest --cov=app/modules/privacidade --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/privacidade
    - done: false
      test: grep -E '^class PrivacyRepository' apps/api/app/modules/privacidade/repository.py
      text: 'Repository pattern: PrivacyRepository definido como classe em repository.py'
deps:
    - TASK-012
    - TASK-013
id: TASK-014
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
tests: pytest tests/test_privacidade.py -v
title: 'Privacidade: GET /api/v1/privacidade + POST /aceitar (singleton, versão atual 1.0, idempotente, upsert em versão antiga)'
updated_at: "2026-05-28 09:25:36"
---
## Contexto

Esta task entrega o **slice vertical do domínio Privacidade** — gerenciamento do aviso de privacidade one-time exigido por LGPD (RF-012). O domínio é singleton: a tabela `privacy_acceptance` tem `id=1` (CHECK constraint) e armazena `aceito_em` + `versao_aviso` (ex: `"1.0"` — permite re-exibição futura quando o texto muda).

Estado atual (fim TASK-012 + TASK-013):
- ORM `PrivacyAcceptance` em `app/modules/privacidade/model.py` com CHECK `id=1`.
- `app.core.deps.CurrentTerceiroDep` exige Bearer; rota `/privacidade` precisa ser autenticada **e também** ser navegável antes do aceite — porém, o aceite é por instalação, não por terceiro, então só faz sentido autenticado (a Web só chega aqui após login).
- Sem service/router para privacidade ainda.

Decisão arquitetural: privacidade é singleton da instalação (não por terceiro). `GET /api/v1/privacidade` retorna `{accepted: bool, versao_aviso: str | null, aceito_em: str | null}` para o frontend decidir mostrar/esconder o modal. `POST /api/v1/privacidade/aceitar` cria a linha (upsert se `versao_aviso` mudar — futura re-exibição). Versão atual = `"1.0"` (constante em `app/modules/privacidade/service.py`).

Esta task segue o padrão repository decidido na TASK-013: classe `PrivacyRepository` em `repository.py`.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `GET /api/v1/privacidade` autenticado, banco sem aceite | `200`, body `{"accepted": false, "versao_aviso": null, "aceito_em": null}` |
| `GET /api/v1/privacidade` autenticado, com aceite na versão atual | `200`, body `{"accepted": true, "versao_aviso": "1.0", "aceito_em": "<iso-utc>"}` |
| `GET /api/v1/privacidade` autenticado, aceite com versão antiga ("0.9") | `200`, body `{"accepted": false, "versao_aviso": "0.9", "aceito_em": "<iso-utc>"}` — frontend re-exibe modal |
| `GET /api/v1/privacidade` sem auth | `401` com `code=UNAUTHORIZED` |
| `POST /api/v1/privacidade/aceitar` autenticado, banco sem aceite | `204`; insere `PrivacyAcceptance(id=1, aceito_em=now, versao_aviso="1.0")` |
| `POST /api/v1/privacidade/aceitar` autenticado, aceite versão antiga existente | `204`; atualiza `aceito_em=now`, `versao_aviso="1.0"` (UPDATE inplace) |
| `POST /api/v1/privacidade/aceitar` autenticado, aceite versão atual já existente | `204` (idempotente; nada muda) |
| `POST /api/v1/privacidade/aceitar` sem auth | `401` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_privacidade.py`

```python
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


@pytest.mark.asyncio
async def test_get_privacidade_returns_false_when_empty(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == {"accepted": False, "versao_aviso": None, "aceito_em": None}


@pytest.mark.asyncio
async def test_post_aceitar_inserts_row(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 204
    async with sm() as s:
        row = (await s.execute(select(PrivacyAcceptance))).scalar_one()
        assert row.id == 1
        assert row.versao_aviso == "1.0"
        assert row.aceito_em


@pytest.mark.asyncio
async def test_get_privacidade_returns_true_after_aceite(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["versao_aviso"] == "1.0"
    assert body["aceito_em"]


@pytest.mark.asyncio
async def test_post_aceitar_is_idempotent(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    async with sm() as s:
        rows = (await s.execute(select(PrivacyAcceptance))).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_privacidade_returns_false_for_old_version(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    async with sm() as s:
        s.add(PrivacyAcceptance(id=1, aceito_em=datetime.now(UTC).isoformat(), versao_aviso="0.9"))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is False  # versao antiga != versao atual
    assert body["versao_aviso"] == "0.9"


@pytest.mark.asyncio
async def test_post_aceitar_updates_old_version_inplace(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import PrivacyAcceptance
    async with sm() as s:
        s.add(PrivacyAcceptance(id=1, aceito_em="2025-01-01T00:00:00+00:00", versao_aviso="0.9"))
        await s.commit()
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.post("/api/v1/privacidade/aceitar", headers={"Authorization": f"Bearer {tok}"})
    async with sm() as s:
        row = (await s.execute(select(PrivacyAcceptance))).scalar_one()
        assert row.versao_aviso == "1.0"
        assert row.aceito_em != "2025-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_endpoints_require_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.get("/api/v1/privacidade")
        r2 = await c.post("/api/v1/privacidade/aceitar")
    assert r1.status_code == 401
    assert r2.status_code == 401
```

**Refatoração:** Após o green, considerar mover `VERSAO_AVISO_ATUAL` para `app/core/config.py` se outras partes do sistema (frontend bundle, PDF) precisarem da mesma constante.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/app/modules/privacidade/schema.py` | Criar | `PrivacyStatus` (response) |
| `apps/api/app/modules/privacidade/repository.py` | Criar | `class PrivacyRepository` — `get_or_none`, `upsert(versao)` |
| `apps/api/app/modules/privacidade/service.py` | Criar | `get_status`, `aceitar(autor)`; constante `VERSAO_AVISO_ATUAL = "1.0"` |
| `apps/api/app/modules/privacidade/router.py` | Criar | `GET /api/v1/privacidade`, `POST /api/v1/privacidade/aceitar` |
| `apps/api/app/main.py` | Modificar | Registrar `privacidade_router` |
| `apps/api/tests/test_privacidade.py` | Criar | 7 testes |

> Total: 6 arquivos. Dentro do orçamento.

### Detalhamento Técnico

**1. `apps/api/app/modules/privacidade/schema.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel


class PrivacyStatus(BaseModel):
    accepted: bool
    versao_aviso: str | None
    aceito_em: str | None
```

**2. `apps/api/app/modules/privacidade/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PrivacyAcceptance


class PrivacyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_none(self) -> PrivacyAcceptance | None:
        return (
            await self.session.execute(select(PrivacyAcceptance).where(PrivacyAcceptance.id == 1))
        ).scalar_one_or_none()

    async def upsert(self, versao: str) -> PrivacyAcceptance:
        existing = await self.get_or_none()
        now = datetime.now(UTC).isoformat()
        if existing is None:
            row = PrivacyAcceptance(id=1, aceito_em=now, versao_aviso=versao)
            self.session.add(row)
            return row
        existing.aceito_em = now
        existing.versao_aviso = versao
        return existing
```

**3. `apps/api/app/modules/privacidade/service.py`:**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.privacidade.repository import PrivacyRepository

VERSAO_AVISO_ATUAL = "1.0"


async def get_status(session: AsyncSession) -> dict:
    repo = PrivacyRepository(session)
    row = await repo.get_or_none()
    if row is None:
        return {"accepted": False, "versao_aviso": None, "aceito_em": None}
    return {
        "accepted": row.versao_aviso == VERSAO_AVISO_ATUAL,
        "versao_aviso": row.versao_aviso,
        "aceito_em": row.aceito_em,
    }


async def aceitar(session: AsyncSession) -> None:
    repo = PrivacyRepository(session)
    existing = await repo.get_or_none()
    if existing is not None and existing.versao_aviso == VERSAO_AVISO_ATUAL:
        return  # idempotente
    await repo.upsert(VERSAO_AVISO_ATUAL)
    await session.commit()
```

**4. `apps/api/app/modules/privacidade/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.privacidade import service
from app.modules.privacidade.schema import PrivacyStatus

router = APIRouter(prefix="/api/v1/privacidade", tags=["privacidade"])


@router.get("", response_model=PrivacyStatus)
async def get_status(_t: CurrentTerceiroDep, session: SessionDep) -> PrivacyStatus:
    data = await service.get_status(session)
    return PrivacyStatus(**data)


@router.post("/aceitar", status_code=status.HTTP_204_NO_CONTENT)
async def aceitar(_t: CurrentTerceiroDep, session: SessionDep) -> None:
    await service.aceitar(session)
```

**5. `apps/api/app/main.py`** — adicionar:

```python
from app.modules.privacidade.router import router as privacidade_router
app.include_router(privacidade_router)
```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-019 (wiring final):
    - GET /api/v1/privacidade e POST /api/v1/privacidade/aceitar registrados em main.py — testes de wiring confirmam.
  Phase 4 (Frontend):
    - GET retorna {accepted, versao_aviso, aceito_em} para o guard de rota /privacidade.

Consome de:
  TASK-012:
    - SessionDep, CurrentTerceiroDep (mesmo padrão de todas as rotas autenticadas).
    - DomainError indireto (deps de TASK-012 levantam 401).
  TASK-010:
    - Modelo PrivacyAcceptance.

Erros:
  - UNAUTHORIZED → 401 quando sem Bearer.
```

## Contrato HTTP

```
GET /api/v1/privacidade   (auth Bearer)
Response 200: {"accepted": false|true, "versao_aviso": "1.0"|null, "aceito_em": "<iso>"|null}
Response 401: {"code":"UNAUTHORIZED",...}

POST /api/v1/privacidade/aceitar   (auth Bearer)
Response 204: vazio; cria/atualiza PrivacyAcceptance(id=1, versao_aviso="1.0", aceito_em=now)
Response 401: {"code":"UNAUTHORIZED",...}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && pytest tests/test_privacidade.py -v` — 7 testes passam.
3. `cd apps/api && pytest tests/ -v` — toda suite continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** Nenhuma além da indicada no green (constante para `app/core/config.py` se necessário).
