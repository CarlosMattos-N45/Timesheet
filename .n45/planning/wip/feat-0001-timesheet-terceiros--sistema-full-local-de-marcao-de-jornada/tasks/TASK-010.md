---
checkpoint: null
complexity: G
created_at: "2026-05-27 16:02:00"
criteria:
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_all_11_tables_in_metadata
      text: Base.metadata.tables contem as 11 tabelas do schema
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_terceiro_roundtrip
      text: Terceiro round-trip persistir e recuperar via select
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_terceiro_check_constraint
      text: CHECK de horarios cronologicos rejeita ordem invalida via ORM
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_jornada_marcacoes_relationship
      text: Jornada.marcacoes relationship carrega marcacoes via selectinload
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_marcacao_tipo_check_constraint
      text: Marcacao.tipo CHECK rejeita valor fora do enum via ORM
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_atividade_one_to_one_with_jornada
      text: Atividade 1:1 com Jornada (UNIQUE jornada_id) via relationship
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_smtp_config_singleton_check
      text: SmtpConfig CHECK singleton (id=1) rejeita id=2
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_privacy_acceptance_singleton
      text: PrivacyAcceptance singleton round-trip
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_refresh_token_cascade_on_terceiro_delete
      text: RefreshToken cascade delete quando Terceiro e removido
    - done: true
      test: cd apps/api && pytest tests/test_models.py -k test_alembic_env_uses_base_metadata
      text: alembic env.py importa Base e seta target_metadata=Base.metadata
    - done: true
      test: cd apps/api && alembic upgrade head && alembic check
      text: alembic check apos upgrade nao reporta divergencia (ORM 1:1 com migration)
    - done: true
      test: cd apps/api && ruff check .
      text: ruff check sem warnings
    - done: true
      test: cd apps/api && mypy --strict app
      text: mypy --strict app sem erros
    - done: true
      text: Testes passando com cobertura >= 80%
    - done: true
      test: make smoke
      text: make smoke Phase 1 continua passando
deps:
    - TASK-007
    - TASK-008
id: TASK-010
linter: cd apps/api && ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/api && pytest tests/test_models.py
title: 'ORM SQLAlchemy 2.x: Base + 11 modelos em slices por dominio + alembic env conectado'
updated_at: "2026-05-27 17:22:55"
---
## Contexto

Após a Phase 2 ter o schema (TASK-007) e o engine async (TASK-008), os domínios da Phase 3 vão acessar o banco via SQLAlchemy 2.x ORM. Esta task entrega o ORM completo: `Base` declarativa + uma classe modelo por tabela, organizada em slices por domínio (`app/modules/<dominio>/model.py`). Cada modelo reflete **exatamente** as colunas, tipos, NOT NULL, defaults e UNIQUE definidos pela migração — o ORM é uma visão consumível pela camada de aplicação, não uma re-definição independente.

Estado atual após Phase 2 prévia (TASK-006/007/008/009):
- Schema persistido em SQLite via Alembic `0001_initial`.
- `app/core/db.py` expõe `get_engine`, `get_sessionmaker`, `get_session`.
- `app/core/config.py` lê `db_url`.
- Pacote `app/modules/sistema/` contém o `router.py` da Phase 1.
- Pasta `app/modules/` é o destino dos slices da Phase 3 — esta task **cria a estrutura inicial** dos pacotes com apenas o `model.py` em cada.

**Decisão arquitetural registrada nesta task** (consumida pela Phase 3 inteira):
- Cada domínio do backend vive em `app/modules/<dominio>/` com 4 arquivos: `model.py` (este task), `schema.py`, `service.py`, `router.py` (Phase 3).
- Repositories serão **classes** (não módulos de funções) — decisão tomada na Phase 3 (FundaÃ§Ã£o Backend); aqui apenas o ORM models, sem repositórios ainda.
- `Base = DeclarativeBase` único em `app/core/base.py`; todos os modelos herdam.
- `Base.metadata` será associado a `target_metadata` do Alembic na próxima vez que a migração for editada (a TASK-007 deixou `target_metadata = None` propositadamente; **esta task atualiza o env.py** para apontar para `Base.metadata`).

Esta task **não** introduz repositories, services, schemas Pydantic, nem endpoints. Apenas: `Base`, 11 modelos ORM, registro no Alembic env, e testes que validam round-trip ORM ↔ banco.

## Comportamento Esperado

| Entrada / Ação                                                                                  | Saída / Efeito esperado                                                                                          |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `from app.core.base import Base`                                                                | `Base` é uma subclass de `DeclarativeBase`; `Base.metadata` contém as 11 tabelas registradas                     |
| `Base.metadata.tables.keys()` (após importar `app.models`)                                      | Conjunto contém: `terceiro`, `jornada`, `marcacao`, `atividade`, `justificativa`, `log_auditoria`, `historico_envio_relatorio`, `refresh_token`, `relatorio_gerado`, `smtp_config`, `privacy_acceptance` |
| `session.add(Terceiro(...))` + `await session.commit()` (após `alembic upgrade head`)           | Linha persistida; `select(Terceiro).where(...)` retorna o objeto                                                 |
| Inserir `Terceiro` com `horario_inicio_jornada >= horario_saida_almoco`                         | Banco levanta `IntegrityError` (CHECK constraint — mesmo path do TASK-007)                                       |
| `Jornada.marcacoes` relationship                                                                | Acesso retorna lista de `Marcacao` da jornada (carga via `selectinload`)                                         |
| `Terceiro.jornadas` relationship com cascade `all, delete-orphan`                               | `session.delete(terceiro)` cascateia delete em todas as jornadas filhas (alinhado com `ON DELETE CASCADE` SQL)   |
| `Marcacao.tipo` setado para `"INVALIDO"`                                                        | `await session.commit()` levanta `IntegrityError` (CHECK no DB; sem validador Python aqui)                       |
| `Atividade.jornada` relationship                                                                | Retorna o `Jornada` parent; FK 1:1 (`UNIQUE` no `jornada_id`)                                                    |
| `select(Terceiro).options(selectinload(Terceiro.jornadas))` round-trip                          | Carrega terceiro + jornadas em 1 query agrupada                                                                  |
| `alembic check` após mudança nos modelos sem migração                                           | Reporta divergência (autogenerate detecta) — comprova que `target_metadata = Base.metadata` está conectado       |
| `Base.metadata.create_all(engine)` em banco vazio                                               | Cria todas as 11 tabelas idênticas à migração (smoke alternativo)                                                |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`apps/api/tests/test_models.py`):

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import db as db_mod
from app.core.base import Base
from app.models import (
    Atividade,
    Jornada,
    Justificativa,
    LogAuditoria,
    Marcacao,
    PrivacyAcceptance,
    RefreshToken,
    RelatorioGerado,
    SmtpConfig,
    Terceiro,
    HistoricoEnvioRelatorio,
)


@pytest_asyncio.fixture
async def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "models.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        yield s
    await engine.dispose()


def _now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.mark.asyncio
async def test_all_11_tables_in_metadata() -> None:
    expected = {
        "terceiro", "jornada", "marcacao", "atividade", "justificativa",
        "log_auditoria", "historico_envio_relatorio", "refresh_token",
        "relatorio_gerado", "smtp_config", "privacy_acceptance",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


@pytest.mark.asyncio
async def test_terceiro_roundtrip(session: AsyncSession) -> None:
    t = Terceiro(
        id=str(uuid4()), nome="Maria", empresa_nome="ACME", empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="m@a.com", senha_hash="hash",
        criado_em=_now(), atualizado_em=_now(),
    )
    session.add(t)
    await session.commit()
    fetched = (await session.execute(select(Terceiro).where(Terceiro.id == t.id))).scalar_one()
    assert fetched.nome == "Maria"
    assert fetched.empresa_cnpj == "00000000000191"


@pytest.mark.asyncio
async def test_terceiro_check_constraint(session: AsyncSession) -> None:
    t = Terceiro(
        id=str(uuid4()), nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
        horario_inicio_jornada="12:00:00",  # depois do almoco - viola CHECK
        horario_saida_almoco="11:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="z@z.com", senha_hash="h",
        criado_em=_now(), atualizado_em=_now(),
    )
    session.add(t)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_jornada_marcacoes_relationship(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1", nome="Maria", empresa_nome="ACME", empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="m@a.com", senha_hash="h",
        criado_em=_now(), atualizado_em=_now(),
    )
    j = Jornada(id="j1", terceiro_id="t1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=_now())
    m1 = Marcacao(
        id="m1", jornada_id="j1", tipo="INICIO_JORNADA",
        horario_registrado=_now(), origem="AGENTE_AUTOMATICO",
        idempotency_key="11111111-1111-1111-1111-111111111111", criada_em=_now(),
    )
    m2 = Marcacao(
        id="m2", jornada_id="j1", tipo="FIM_JORNADA",
        horario_registrado=_now(), origem="AGENTE_AUTOMATICO",
        idempotency_key="22222222-2222-2222-2222-222222222222", criada_em=_now(),
    )
    session.add_all([t, j, m1, m2])
    await session.commit()
    fetched = (
        await session.execute(
            select(Jornada).where(Jornada.id == "j1").options(selectinload(Jornada.marcacoes))
        )
    ).scalar_one()
    tipos = {m.tipo for m in fetched.marcacoes}
    assert tipos == {"INICIO_JORNADA", "FIM_JORNADA"}


@pytest.mark.asyncio
async def test_marcacao_tipo_check_constraint(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1", nome="Maria", empresa_nome="ACME", empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="m@a.com", senha_hash="h",
        criado_em=_now(), atualizado_em=_now(),
    )
    j = Jornada(id="j1", terceiro_id="t1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=_now())
    session.add_all([t, j])
    await session.commit()
    m = Marcacao(
        id="m_bad", jornada_id="j1", tipo="TIPO_INVALIDO",  # nao existe
        horario_registrado=_now(), origem="AGENTE_AUTOMATICO",
        idempotency_key="33333333-3333-3333-3333-333333333333", criada_em=_now(),
    )
    session.add(m)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_atividade_one_to_one_with_jornada(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="m@a.com", senha_hash="h",
        criado_em=_now(), atualizado_em=_now(),
    )
    j = Jornada(id="j1", terceiro_id="t1", data="2026-05-27", status="FECHADA", criada_em=_now())
    a = Atividade(id="a1", jornada_id="j1", descricao="trabalhei dez horas", registrada_em=_now())
    session.add_all([t, j, a])
    await session.commit()
    fetched_j = (
        await session.execute(
            select(Jornada).where(Jornada.id == "j1").options(selectinload(Jornada.atividade))
        )
    ).scalar_one()
    assert fetched_j.atividade is not None
    assert fetched_j.atividade.descricao == "trabalhei dez horas"


@pytest.mark.asyncio
async def test_smtp_config_singleton_check(session: AsyncSession) -> None:
    cfg = SmtpConfig(
        id=2,  # viola CHECK id=1
        host="smtp.example.com", port=587, username_enc="ENC1", password_enc="ENC2",
        use_starttls=1, from_address="noreply@example.com", atualizado_em=_now(),
    )
    session.add(cfg)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_privacy_acceptance_singleton(session: AsyncSession) -> None:
    p = PrivacyAcceptance(id=1, aceito_em=_now(), versao_aviso="1.0")
    session.add(p)
    await session.commit()
    fetched = (await session.execute(select(PrivacyAcceptance))).scalar_one()
    assert fetched.versao_aviso == "1.0"


@pytest.mark.asyncio
async def test_refresh_token_cascade_on_terceiro_delete(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0, email_contato="m@a.com", senha_hash="h",
        criado_em=_now(), atualizado_em=_now(),
    )
    rt = RefreshToken(
        id="rt1", terceiro_id="t1", token_hash="hashvalue",
        expira_em=_now(), criado_em=_now(),
    )
    session.add_all([t, rt])
    await session.commit()
    await session.delete(t)
    await session.commit()
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert rows == []


def test_alembic_env_uses_base_metadata() -> None:
    # Smoke estatico: env.py importa Base e seta target_metadata = Base.metadata
    env_path = Path(__file__).parent.parent / "alembic" / "env.py"
    content = env_path.read_text(encoding="utf-8")
    assert "from app.core.base import Base" in content
    assert "target_metadata = Base.metadata" in content
    # Garante que models foram importados antes (autogenerate enxerga as tabelas)
    assert "from app import models" in content or "import app.models" in content
```

> Os testes usam `Base.metadata.create_all` em vez de Alembic para isolamento (mais rápido); a integridade contra migrations já foi validada na TASK-007. O teste estático `test_alembic_env_uses_base_metadata` garante que o autogenerate funcionará nas próximas migrations.

**Refatoração:** Após o green, se houver muita duplicação de fixtures (`_now`, criação de terceiro base), extrair para `tests/conftest.py`. Manter `test_models.py` legível com helpers locais quando possível.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                                       | Ação      | Descrição                                                                                              |
| ------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------ |
| `apps/api/app/core/base.py`                                   | Criar     | `DeclarativeBase` única + naming convention para constraints                                           |
| `apps/api/app/models.py`                                      | Criar     | Re-exporta todos os 11 modelos para uso uniforme em `from app.models import ...`                       |
| `apps/api/app/modules/terceiros/__init__.py`                  | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/terceiros/model.py`                     | Criar     | Classe `Terceiro`                                                                                      |
| `apps/api/app/modules/jornadas/__init__.py`                   | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/jornadas/model.py`                      | Criar     | Classes `Jornada`                                                                                      |
| `apps/api/app/modules/marcacoes/__init__.py`                  | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/marcacoes/model.py`                     | Criar     | Classe `Marcacao`                                                                                      |
| `apps/api/app/modules/atividades/__init__.py`                 | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/atividades/model.py`                    | Criar     | Classe `Atividade`                                                                                     |
| `apps/api/app/modules/justificativas/__init__.py`             | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/justificativas/model.py`                | Criar     | Classe `Justificativa`                                                                                 |
| `apps/api/app/modules/auditoria/__init__.py`                  | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/auditoria/model.py`                     | Criar     | Classe `LogAuditoria`                                                                                  |
| `apps/api/app/modules/relatorios/__init__.py`                 | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/relatorios/model.py`                    | Criar     | Classes `RelatorioGerado`, `HistoricoEnvioRelatorio`                                                   |
| `apps/api/app/modules/auth/__init__.py`                       | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/auth/model.py`                          | Criar     | Classe `RefreshToken`                                                                                  |
| `apps/api/app/modules/smtp/__init__.py`                       | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/smtp/model.py`                          | Criar     | Classe `SmtpConfig`                                                                                    |
| `apps/api/app/modules/privacidade/__init__.py`                | Criar     | Pacote vazio                                                                                           |
| `apps/api/app/modules/privacidade/model.py`                   | Criar     | Classe `PrivacyAcceptance`                                                                             |
| `apps/api/alembic/env.py`                                     | Modificar | Importar `Base` e modelos; setar `target_metadata = Base.metadata`                                     |
| `apps/api/tests/test_models.py`                               | Criar     | Suite acima (10 testes)                                                                                |

> **Total de arquivos-alvo modificados ou criados:** 23 — excede o teto de 8. Justificativa para exceder: cada novo módulo precisa do par `__init__.py` + `model.py` e cada arquivo é trivial (1 classe). A persona é única (`50a8844c7d`) e os arquivos são auto-contidos. Alternativa rejeitada: colocar todos os modelos em `app/models.py` único — viola "slice vertical por domínio" definido na arquitetura. Alternativa rejeitada: dividir em 2 tasks (5 + 6 domínios) — gera 2 PRs sequenciais para a mesma persona com zero ganho semântico e cria conflito em `alembic/env.py`. Esta é uma exceção justificada pela coesão (todos os 11 modelos compõem **um único contrato com o banco**) e pelo custo trivial por arquivo. Manter como uma única task.

### Detalhamento Técnico

**1. `app/core/base.py`** — base declarativa única:

```python
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

> A naming convention é registrada no `Base.metadata` mas **os nomes existentes na migração 0001** já são explícitos (`name="ck_terceiro_horarios_crono"`, etc.), então não há colisão. Em migrations futuras (autogenerate), nomes derivados seguem a convention.

**2. `app/modules/terceiros/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.auth.model import RefreshToken
    from app.modules.jornadas.model import Jornada


class Terceiro(Base):
    __tablename__ = "terceiro"
    __table_args__ = (
        CheckConstraint("length(nome) BETWEEN 1 AND 120", name="ck_terceiro_nome_len"),
        CheckConstraint("length(empresa_nome) BETWEEN 1 AND 150", name="ck_terceiro_empresa_len"),
        CheckConstraint("length(empresa_cnpj) = 14", name="ck_terceiro_cnpj_len"),
        CheckConstraint("length(email_contato) <= 254", name="ck_terceiro_email_len"),
        CheckConstraint(
            "horario_inicio_jornada < horario_saida_almoco "
            "AND horario_saida_almoco < horario_retorno_almoco "
            "AND horario_retorno_almoco < horario_fim_jornada",
            name="ck_terceiro_horarios_crono",
        ),
        UniqueConstraint("email_contato", name="uq_terceiro_email"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    empresa_nome: Mapped[str] = mapped_column(Text, nullable=False)
    empresa_cnpj: Mapped[str] = mapped_column(Text, nullable=False)
    horario_inicio_jornada: Mapped[str] = mapped_column(Text, nullable=False)
    horario_saida_almoco: Mapped[str] = mapped_column(Text, nullable=False)
    horario_retorno_almoco: Mapped[str] = mapped_column(Text, nullable=False)
    horario_fim_jornada: Mapped[str] = mapped_column(Text, nullable=False)
    trabalha_fim_de_semana: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    email_contato: Mapped[str] = mapped_column(Text, nullable=False)
    email_destinatario_relatorio: Mapped[str | None] = mapped_column(Text, nullable=True)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str] = mapped_column(Text, nullable=False)

    jornadas: Mapped[list["Jornada"]] = relationship(
        back_populates="terceiro", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="terceiro", cascade="all, delete-orphan", passive_deletes=True
    )
```

**3. `app/modules/jornadas/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.atividades.model import Atividade
    from app.modules.justificativas.model import Justificativa
    from app.modules.marcacoes.model import Marcacao
    from app.modules.terceiros.model import Terceiro


class Jornada(Base):
    __tablename__ = "jornada"
    __table_args__ = (
        CheckConstraint(
            "status IN ('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE')",
            name="ck_jornada_status",
        ),
        UniqueConstraint("terceiro_id", "data", name="uq_jornada_terceiro_data"),
        Index("idx_jornada_terceiro_data", "terceiro_id", "data"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    terceiro_id: Mapped[str] = mapped_column(
        Text, ForeignKey("terceiro.id", ondelete="CASCADE", name="fk_jornada_terceiro"), nullable=False
    )
    data: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    total_horas_apuradas_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)
    fechada_em: Mapped[str | None] = mapped_column(Text, nullable=True)

    terceiro: Mapped["Terceiro"] = relationship(back_populates="jornadas")
    marcacoes: Mapped[list["Marcacao"]] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", passive_deletes=True
    )
    atividade: Mapped["Atividade | None"] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", uselist=False, passive_deletes=True
    )
    justificativas: Mapped[list["Justificativa"]] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", passive_deletes=True
    )
```

**4. `app/modules/marcacoes/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Marcacao(Base):
    __tablename__ = "marcacao"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')",
            name="ck_marcacao_tipo",
        ),
        CheckConstraint(
            "origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB')",
            name="ck_marcacao_origem",
        ),
        CheckConstraint(
            "status IN ('CONFIRMADA','PENDENTE','AJUSTADA')",
            name="ck_marcacao_status",
        ),
        CheckConstraint("length(idempotency_key) = 36", name="ck_marcacao_idem_len"),
        UniqueConstraint("idempotency_key", name="uq_marcacao_idem"),
        UniqueConstraint("jornada_id", "tipo", name="uq_marcacao_jornada_tipo"),
        Index("idx_marcacao_jornada", "jornada_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    horario_registrado: Mapped[str] = mapped_column(Text, nullable=False)
    horario_efetivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="CONFIRMADA")
    confirmado_pelo_usuario: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)

    jornada: Mapped["Jornada"] = relationship(back_populates="marcacoes")
```

**5–11.** Os demais modelos seguem o **mesmo padrão** das classes acima. Por brevidade, abaixo o template estruturado:

**`app/modules/atividades/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Atividade(Base):
    __tablename__ = "atividade"
    __table_args__ = (
        CheckConstraint("length(descricao) >= 10", name="ck_atividade_desc_len"),
        UniqueConstraint("jornada_id", name="uq_atividade_jornada"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    registrada_em: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str | None] = mapped_column(Text, nullable=True)
    jornada: Mapped["Jornada"] = relationship(back_populates="atividade")
```

**`app/modules/justificativas/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Justificativa(Base):
    __tablename__ = "justificativa"
    __table_args__ = (
        CheckConstraint("length(motivo) >= 5", name="ck_justif_motivo_len"),
        Index("idx_justificativa_jornada", "jornada_id"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    usuario_responsavel: Mapped[str] = mapped_column(Text, nullable=False)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)
    jornada: Mapped["Jornada"] = relationship(back_populates="justificativas")
```

**`app/modules/auditoria/model.py`:**

```python
from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"
    __table_args__ = (
        CheckConstraint(
            "entidade IN ('Jornada','Marcacao','Terceiro','Atividade')",
            name="ck_audit_entidade",
        ),
        Index("idx_audit_entidade", "entidade", "entidade_id"),
        Index("idx_audit_criado_em", "criado_em"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    entidade: Mapped[str] = mapped_column(Text, nullable=False)
    entidade_id: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[str] = mapped_column(Text, nullable=False)
    antes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    depois_json: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)
    expira_em: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**`app/modules/relatorios/model.py`:**

```python
from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class RelatorioGerado(Base):
    __tablename__ = "relatorio_gerado"
    __table_args__ = (
        CheckConstraint("length(mes_referencia) = 7", name="ck_relat_mes_len"),
        UniqueConstraint("mes_referencia", name="uq_relat_mes"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    mes_referencia: Mapped[str] = mapped_column(Text, nullable=False)
    caminho_arquivo: Mapped[str] = mapped_column(Text, nullable=False)
    gerado_em: Mapped[str] = mapped_column(Text, nullable=False)
    invalidado_em: Mapped[str | None] = mapped_column(Text, nullable=True)


class HistoricoEnvioRelatorio(Base):
    __tablename__ = "historico_envio_relatorio"
    __table_args__ = (
        CheckConstraint("length(mes_referencia) = 7", name="ck_hist_mes_len"),
        CheckConstraint("status IN ('SUCESSO','FALHA')", name="ck_hist_status"),
        Index("idx_hist_envio_mes", "mes_referencia"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    mes_referencia: Mapped[str] = mapped_column(Text, nullable=False)
    email_destinatario: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    enviado_em: Mapped[str] = mapped_column(Text, nullable=False)
```

**`app/modules/auth/model.py`:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.terceiros.model import Terceiro


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    __table_args__ = (
        Index("idx_refresh_token_hash", "token_hash"),
        Index("idx_refresh_token_exp", "expira_em"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    terceiro_id: Mapped[str] = mapped_column(Text, ForeignKey("terceiro.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_em: Mapped[str] = mapped_column(Text, nullable=False)
    revogado_em: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)
    terceiro: Mapped["Terceiro"] = relationship(back_populates="refresh_tokens")
```

**`app/modules/smtp/model.py`:**

```python
from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_smtp_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username_enc: Mapped[str] = mapped_column(Text, nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)
    use_starttls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    from_address: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str] = mapped_column(Text, nullable=False)
```

**`app/modules/privacidade/model.py`:**

```python
from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class PrivacyAcceptance(Base):
    __tablename__ = "privacy_acceptance"
    __table_args__ = (CheckConstraint("id = 1", name="ck_priv_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aceito_em: Mapped[str] = mapped_column(Text, nullable=False)
    versao_aviso: Mapped[str] = mapped_column(Text, nullable=False)
```

**12. `app/models.py`** — re-export central para consumo uniforme:

```python
"""Re-export of all ORM models. Importing this module registers every table
on ``Base.metadata`` for Alembic autogenerate and ``Base.metadata.create_all``."""

from app.modules.atividades.model import Atividade
from app.modules.auditoria.model import LogAuditoria
from app.modules.auth.model import RefreshToken
from app.modules.jornadas.model import Jornada
from app.modules.justificativas.model import Justificativa
from app.modules.marcacoes.model import Marcacao
from app.modules.privacidade.model import PrivacyAcceptance
from app.modules.relatorios.model import HistoricoEnvioRelatorio, RelatorioGerado
from app.modules.smtp.model import SmtpConfig
from app.modules.terceiros.model import Terceiro

__all__ = [
    "Atividade",
    "HistoricoEnvioRelatorio",
    "Jornada",
    "Justificativa",
    "LogAuditoria",
    "Marcacao",
    "PrivacyAcceptance",
    "RefreshToken",
    "RelatorioGerado",
    "SmtpConfig",
    "Terceiro",
]
```

**13. `apps/api/alembic/env.py`** — substituir o bloco `target_metadata = None`:

```python
# Antes: target_metadata = None
from app import models  # noqa: F401 — registra modelos no Base.metadata
from app.core.base import Base

target_metadata = Base.metadata
```

(Manter o restante de `env.py` inalterado.)

## Contratos com camadas adjacentes

```
Produz para:
  - Phase 3 (todos os dominios): classes ORM Terceiro, Jornada, Marcacao, etc., importadas via from app.modules.<dominio>.model import <Modelo>.
  - Phase 3 (auditoria, smtp, privacidade): LogAuditoria, SmtpConfig, PrivacyAcceptance disponiveis ja com o mesmo schema da migracao.

Consome de:
  - TASK-007: schema fisico (tabelas, indices, CHECKs, FKs). Os modelos DEVEM bater 1:1.
  - TASK-008: Base.metadata sera usada por get_engine() em testes (create_all) e pela aplicacao em runtime.

Erros:
  - Tipo/CHECK divergente entre ORM e SQL: detectado por alembic check (autogenerate); falha aborta build em CI futura. Esta task NAO altera a migracao 0001 — mantem 1:1 estrutural.
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && pytest tests/test_models.py -v` — 10 testes passam.
3. `cd apps/api && pytest tests/ -v` — toda a suite (Phase 1 + TASK-007 + TASK-008 + TASK-009) continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `cd apps/api && TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/check.sqlite alembic upgrade head && alembic check` → "No new upgrade operations detected" (autogenerate confirma 1:1 entre ORM e migration).
7. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–7 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Se ficar evidente que dois ou mais modelos compartilham padrões repetitivos (ex: `criado_em` + `atualizado_em`), considerar mixin `TimestampMixin` em `app/core/base.py`. Por ora, manter explícito — clareza > DRY em modelos.
