---
checkpoint: null
complexity: M
created_at: "2026-05-27 15:54:52"
criteria:
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_upgrade_creates_all_11_tables
      text: alembic upgrade head cria todas as 11 tabelas do schema
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_downgrade_to_base_removes_all_domain_tables
      text: alembic downgrade base remove todas as tabelas de dominio
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_terceiro_horario_check_constraint
      text: CHECK de horarios cronologicos em terceiro impede ordem invalida
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_marcacao_idempotency_key_unique
      text: UNIQUE de marcacao.idempotency_key impede duplicata
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_marcacao_jornada_tipo_unique
      text: UNIQUE de marcacao (jornada_id, tipo) impede duplicata
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_jornada_status_check
      text: CHECK de jornada.status rejeita valor fora do enum
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_idempotency_key_length_check
      text: CHECK de marcacao.idempotency_key length=36 rejeita string menor
    - done: false
      test: cd apps/api && pytest tests/test_migration_0001.py -k test_cascade_delete_terceiro
      text: CASCADE delete em terceiro remove jornadas, marcacoes e dependentes
    - done: false
      test: cd apps/api && alembic history
      text: alembic history mostra apenas 0001_initial
    - done: false
      test: grep -E sqlalchemy.*2.0 apps/api/pyproject.toml
      text: sqlalchemy alembic aiosqlite presentes em pyproject.toml
    - done: false
      test: cd apps/api && ruff check .
      text: ruff check sem warnings
    - done: false
      test: cd apps/api && mypy --strict app
      text: mypy --strict app sem erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      test: make smoke
      text: make smoke Phase 1 continua passando
deps:
    - TASK-006
id: TASK-007
linter: cd apps/api && ruff check .
n45_version: 0.2.0
persona: dba
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/api && pytest tests/test_migration_0001.py
title: Alembic setup + migration 0001_initial com as 11 tabelas do schema
updated_at: "2026-05-27 15:54:52"
---
## Contexto

Phase 2 — Dados precisa instalar a infraestrutura de migrações do Backend (Alembic) e materializar o schema completo do domínio em uma migração inicial reversível. Sem isso, nenhum domínio da Phase 3 consegue persistir dados.

Estado atual:
- `apps/api/pyproject.toml` declara FastAPI, uvicorn, pydantic, pydantic-settings, structlog em runtime; pytest, pytest-asyncio, httpx, ruff, mypy em dev. Não inclui SQLAlchemy nem Alembic.
- Não existe pasta `apps/api/alembic/`.
- Não existe schema persistido.
- A TASK-006 (lote-fundação desta fase) cria `data/`, `.env.example` com `TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/timesheet.sqlite`, e o RUNBOOK com a seção `Infraestrutura`. Esta task assume tudo isso pronto.

O schema completo do domínio está descrito na Seção 3 da Spec e é copiado abaixo na íntegra (executor não lê Spec — esta task é auto-suficiente). Todas as 11 tabelas serão criadas na mesma migração `0001_initial`, com seus índices, CHECKs e UNIQUEs preservados. O Agente .NET tem seu próprio banco local e suas próprias migrações via EF Core (tratado em TASK-011) — fora do escopo desta task.

## Comportamento Esperado

| Entrada / Ação                                                              | Saída / Efeito esperado                                                                                                              |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `cd apps/api && alembic upgrade head` (banco vazio)                         | Cria as 11 tabelas, retorna 0; `sqlite3 data/timesheet.sqlite '.tables'` lista as 11 tabelas                                          |
| `cd apps/api && alembic downgrade base` (após upgrade)                      | Remove todas as 11 tabelas, retorna 0; `sqlite3 ... '.tables'` lista apenas `alembic_version`                                         |
| Inserir `terceiro` com `horario_inicio_jornada >= horario_saida_almoco`     | SQLite levanta `IntegrityError` (CHECK violation); registro não persistido                                                           |
| Inserir 2× `terceiro` com mesmo `email_contato`                             | Segundo insert falha com `UNIQUE constraint failed: terceiro.email_contato`                                                          |
| Inserir `marcacao` com `idempotency_key` duplicado                          | Falha com `UNIQUE constraint failed: marcacao.idempotency_key`                                                                       |
| Inserir 2× `marcacao` com mesma `(jornada_id, tipo)`                        | Segundo insert falha com `UNIQUE constraint failed: marcacao.jornada_id, marcacao.tipo`                                              |
| Inserir `jornada.status='INVALIDO'`                                         | Falha com CHECK violation no `status`                                                                                                |
| Inserir `marcacao.idempotency_key` com 35 chars                             | Falha com CHECK violation (`length(idempotency_key) = 36`)                                                                           |
| `PRAGMA foreign_keys = ON; DELETE FROM terceiro WHERE id = X;`              | Cascateia delete em `jornada`, `marcacao`, `atividade`, `justificativa`, `refresh_token` daquele terceiro                            |
| `cd apps/api && alembic check`                                              | Sai 0 — nenhuma divergência pendente entre metadata e migrações                                                                      |
| `cd apps/api && alembic history`                                            | Mostra apenas 1 entrada: revision `0001_initial`                                                                                     |
| `cd apps/api && pytest tests/test_migration_0001.py`                        | Suite passa; cobre upgrade, downgrade idempotente, e cada CHECK/UNIQUE listado acima                                                 |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`apps/api/tests/test_migration_0001.py`):

```python
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    db_path = tmp_path / "test_migration.sqlite"
    sync_url = f"sqlite:///{db_path}"  # Alembic usa driver síncrono; ORM async fica fora desta task
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


def test_upgrade_creates_all_11_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    names = {r[0] for r in rows}
    expected = {
        "alembic_version", "terceiro", "jornada", "marcacao", "atividade",
        "justificativa", "log_auditoria", "historico_envio_relatorio",
        "refresh_token", "relatorio_gerado", "smtp_config", "privacy_acceptance",
    }
    assert expected.issubset(names), f"Faltando: {expected - names}"


def test_downgrade_to_base_removes_all_domain_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    # alembic_version pode permanecer (vazia); demais tabelas removidas
    domain_tables = names - {"alembic_version"}
    assert domain_tables == set(), f"Tabelas remanescentes: {domain_tables}"


def test_terceiro_horario_check_constraint(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO terceiro (id, nome, empresa_nome, empresa_cnpj, "
                "horario_inicio_jornada, horario_saida_almoco, horario_retorno_almoco, "
                "horario_fim_jornada, trabalha_fim_de_semana, email_contato, senha_hash, "
                "criado_em, atualizado_em) VALUES "
                "('00000000-0000-0000-0000-000000000001', 'Maria', 'ACME', "
                "'00000000000191', '12:00:00', '11:00:00', '13:00:00', '18:00:00', "
                "0, 'a@a.com', 'hash', '2026-05-27T12:00:00Z', '2026-05-27T12:00:00Z')"
            )


def test_marcacao_idempotency_key_unique(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m2', 'j1', 'SAIDA_ALMOCO', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
                "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
            )


def test_marcacao_jornada_tipo_unique(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m2', 'j1', 'INICIO_JORNADA', '2026-05-27T12:30:00Z', 'AGENTE_AUTOMATICO', "
                "'22222222-2222-2222-2222-222222222222', '2026-05-27T12:00:00Z')"
            )


def test_jornada_status_check(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro(conn)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO jornada (id, terceiro_id, data, status, criada_em) VALUES "
                "('j1', 't1', '2026-05-27', 'INVALIDO', '2026-05-27T12:00:00Z')"
            )


def test_idempotency_key_length_check(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
                "'curto', '2026-05-27T12:00:00Z')"
            )


def test_cascade_delete_terceiro(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    db_path = alembic_cfg.get_main_option("sqlalchemy.url").replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        conn.execute("DELETE FROM terceiro WHERE id = 't1'")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM jornada").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM marcacao").fetchone()[0] == 0


# Helpers
def _seed_terceiro(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO terceiro (id, nome, empresa_nome, empresa_cnpj, "
        "horario_inicio_jornada, horario_saida_almoco, horario_retorno_almoco, "
        "horario_fim_jornada, trabalha_fim_de_semana, email_contato, senha_hash, "
        "criado_em, atualizado_em) VALUES "
        "('t1', 'Maria', 'ACME', '00000000000191', '09:00:00', '12:00:00', "
        "'13:00:00', '18:00:00', 0, 'a@a.com', 'hash', '2026-05-27T12:00:00Z', '2026-05-27T12:00:00Z')"
    )

def _seed_terceiro_e_jornada(conn: sqlite3.Connection) -> None:
    _seed_terceiro(conn)
    conn.execute(
        "INSERT INTO jornada (id, terceiro_id, data, status, criada_em) VALUES "
        "('j1', 't1', '2026-05-27', 'EM_ANDAMENTO', '2026-05-27T12:00:00Z')"
    )
```

> Os testes acima usam apenas `sqlite3` (stdlib) e `alembic`. Não há dependência circular com SQLAlchemy ORM (que será adicionado pela TASK-010). Isso permite que TASK-007 seja validada de forma isolada.

**Refatoração:** Após o green, garantir que `_seed_terceiro` e `_seed_terceiro_e_jornada` estejam em fixtures ou helpers compartilhados se necessário; nenhuma outra refatoração esperada.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                              | Ação      | Descrição                                                                                                  |
| ---------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------- |
| `apps/api/pyproject.toml`                            | Modificar | Adicionar `sqlalchemy==2.0.*`, `alembic==1.13.*`, `aiosqlite==0.20.*` em `dependencies`                    |
| `apps/api/alembic.ini`                               | Criar     | Config Alembic apontando para `apps/api/alembic/` e lendo `sqlalchemy.url` de env var                      |
| `apps/api/alembic/env.py`                            | Criar     | Env script com modo offline e online (síncrono, usando `sqlite:///` derivado de `TIMESHEET_DB_URL`)         |
| `apps/api/alembic/script.py.mako`                    | Criar     | Template padrão do Alembic (gerar com `alembic init` ou copiar do template oficial)                        |
| `apps/api/alembic/versions/0001_initial.py`          | Criar     | Migração com todas as 11 tabelas + índices + CHECKs + UNIQUEs em `op.create_table` + `op.create_index`     |
| `apps/api/tests/test_migration_0001.py`              | Criar     | Suite descrita acima (8 testes)                                                                            |

### Detalhamento Técnico

**1. Dependências (`apps/api/pyproject.toml`):**

```toml
dependencies = [
  "fastapi==0.115.*",
  "uvicorn[standard]==0.32.*",
  "pydantic==2.9.*",
  "pydantic-settings==2.6.*",
  "structlog==24.4.*",
  "sqlalchemy==2.0.*",
  "alembic==1.13.*",
  "aiosqlite==0.20.*",
]
```

**2. `alembic.ini` (config mínimo):**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`sqlalchemy.url` é vazia — o `env.py` carrega de env var (assim funciona offline em CI sem .env e online em dev/prod). `prepend_sys_path = .` é crítico para o `env.py` importar `app`.

**3. `alembic/env.py`:**

```python
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_sync_url() -> str:
    # Aceita TIMESHEET_DB_URL (formato async) e converte para driver sincrono.
    # Alembic usa driver sincrono para gerar/aplicar migrations.
    raw = os.environ.get("TIMESHEET_DB_URL", "sqlite+aiosqlite:///./data/timesheet.sqlite")
    return raw.replace("sqlite+aiosqlite:", "sqlite:")


# ORM metadata ainda nao existe na TASK-007 (sera adicionada na TASK-010).
# autogenerate fica desativado nesta task; migrations sao escritas manualmente.
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url") or _resolve_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # SQLite friendly
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    if not section.get("sqlalchemy.url"):
        section["sqlalchemy.url"] = _resolve_sync_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # SQLite respects PRAGMA only per-connection; garantir FK on durante migration
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**4. `alembic/script.py.mako`** — template padrão do alembic 1.13. Conteúdo idêntico ao gerado por `alembic init alembic` (manter compatível com versões maiores). Não é arquivo de lógica — copiar do template oficial.

**5. `alembic/versions/0001_initial.py`** — migração completa com TODAS as 11 tabelas:

```python
"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27 18:50:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "terceiro",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("empresa_nome", sa.Text(), nullable=False),
        sa.Column("empresa_cnpj", sa.Text(), nullable=False),
        sa.Column("horario_inicio_jornada", sa.Text(), nullable=False),
        sa.Column("horario_saida_almoco", sa.Text(), nullable=False),
        sa.Column("horario_retorno_almoco", sa.Text(), nullable=False),
        sa.Column("horario_fim_jornada", sa.Text(), nullable=False),
        sa.Column("trabalha_fim_de_semana", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("email_contato", sa.Text(), nullable=False),
        sa.Column("email_destinatario_relatorio", sa.Text(), nullable=True),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(nome) BETWEEN 1 AND 120", name="ck_terceiro_nome_len"),
        sa.CheckConstraint("length(empresa_nome) BETWEEN 1 AND 150", name="ck_terceiro_empresa_len"),
        sa.CheckConstraint("length(empresa_cnpj) = 14", name="ck_terceiro_cnpj_len"),
        sa.CheckConstraint("length(email_contato) <= 254", name="ck_terceiro_email_len"),
        sa.CheckConstraint(
            "horario_inicio_jornada < horario_saida_almoco "
            "AND horario_saida_almoco < horario_retorno_almoco "
            "AND horario_retorno_almoco < horario_fim_jornada",
            name="ck_terceiro_horarios_crono",
        ),
        sa.UniqueConstraint("email_contato", name="uq_terceiro_email"),
    )

    op.create_table(
        "jornada",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("terceiro_id", sa.Text(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_horas_apuradas_s", sa.Integer(), nullable=True),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.Column("fechada_em", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE')",
            name="ck_jornada_status",
        ),
        sa.ForeignKeyConstraint(
            ["terceiro_id"], ["terceiro.id"], ondelete="CASCADE", name="fk_jornada_terceiro"
        ),
        sa.UniqueConstraint("terceiro_id", "data", name="uq_jornada_terceiro_data"),
    )
    op.create_index("idx_jornada_terceiro_data", "jornada", ["terceiro_id", "data"])

    op.create_table(
        "marcacao",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("horario_registrado", sa.Text(), nullable=False),
        sa.Column("horario_efetivo", sa.Text(), nullable=True),
        sa.Column("origem", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'CONFIRMADA'")),
        sa.Column("confirmado_pelo_usuario", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')",
            name="ck_marcacao_tipo",
        ),
        sa.CheckConstraint(
            "origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB')",
            name="ck_marcacao_origem",
        ),
        sa.CheckConstraint(
            "status IN ('CONFIRMADA','PENDENTE','AJUSTADA')",
            name="ck_marcacao_status",
        ),
        sa.CheckConstraint("length(idempotency_key) = 36", name="ck_marcacao_idem_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key", name="uq_marcacao_idem"),
        sa.UniqueConstraint("jornada_id", "tipo", name="uq_marcacao_jornada_tipo"),
    )
    op.create_index("idx_marcacao_jornada", "marcacao", ["jornada_id"])

    op.create_table(
        "atividade",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("registrada_em", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=True),
        sa.CheckConstraint("length(descricao) >= 10", name="ck_atividade_desc_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("jornada_id", name="uq_atividade_jornada"),
    )

    op.create_table(
        "justificativa",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("usuario_responsavel", sa.Text(), nullable=False),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(motivo) >= 5", name="ck_justif_motivo_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_justificativa_jornada", "justificativa", ["jornada_id"])

    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("entidade", sa.Text(), nullable=False),
        sa.Column("entidade_id", sa.Text(), nullable=False),
        sa.Column("autor", sa.Text(), nullable=False),
        sa.Column("antes_json", sa.Text(), nullable=True),
        sa.Column("depois_json", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.Column("expira_em", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "entidade IN ('Jornada','Marcacao','Terceiro','Atividade')",
            name="ck_audit_entidade",
        ),
    )
    op.create_index("idx_audit_entidade", "log_auditoria", ["entidade", "entidade_id"])
    op.create_index("idx_audit_criado_em", "log_auditoria", ["criado_em"])

    op.create_table(
        "historico_envio_relatorio",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("mes_referencia", sa.Text(), nullable=False),
        sa.Column("email_destinatario", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("enviado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(mes_referencia) = 7", name="ck_hist_mes_len"),
        sa.CheckConstraint("status IN ('SUCESSO','FALHA')", name="ck_hist_status"),
    )
    op.create_index("idx_hist_envio_mes", "historico_envio_relatorio", ["mes_referencia"])

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("terceiro_id", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expira_em", sa.Text(), nullable=False),
        sa.Column("revogado_em", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["terceiro_id"], ["terceiro.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_refresh_token_hash", "refresh_token", ["token_hash"])
    op.create_index("idx_refresh_token_exp", "refresh_token", ["expira_em"])

    op.create_table(
        "relatorio_gerado",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("mes_referencia", sa.Text(), nullable=False),
        sa.Column("caminho_arquivo", sa.Text(), nullable=False),
        sa.Column("gerado_em", sa.Text(), nullable=False),
        sa.Column("invalidado_em", sa.Text(), nullable=True),
        sa.CheckConstraint("length(mes_referencia) = 7", name="ck_relat_mes_len"),
        sa.UniqueConstraint("mes_referencia", name="uq_relat_mes"),
    )

    op.create_table(
        "smtp_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username_enc", sa.Text(), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
        sa.Column("use_starttls", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("from_address", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_smtp_singleton"),
    )

    op.create_table(
        "privacy_acceptance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aceito_em", sa.Text(), nullable=False),
        sa.Column("versao_aviso", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_priv_singleton"),
    )


def downgrade() -> None:
    op.drop_table("privacy_acceptance")
    op.drop_table("smtp_config")
    op.drop_table("relatorio_gerado")
    op.drop_index("idx_refresh_token_exp", table_name="refresh_token")
    op.drop_index("idx_refresh_token_hash", table_name="refresh_token")
    op.drop_table("refresh_token")
    op.drop_index("idx_hist_envio_mes", table_name="historico_envio_relatorio")
    op.drop_table("historico_envio_relatorio")
    op.drop_index("idx_audit_criado_em", table_name="log_auditoria")
    op.drop_index("idx_audit_entidade", table_name="log_auditoria")
    op.drop_table("log_auditoria")
    op.drop_index("idx_justificativa_jornada", table_name="justificativa")
    op.drop_table("justificativa")
    op.drop_table("atividade")
    op.drop_index("idx_marcacao_jornada", table_name="marcacao")
    op.drop_table("marcacao")
    op.drop_index("idx_jornada_terceiro_data", table_name="jornada")
    op.drop_table("jornada")
    op.drop_table("terceiro")
```

Notas:
- Tabelas singleton (`smtp_config`, `privacy_acceptance`) usam `id` Integer com CHECK `id = 1`.
- `render_as_batch=True` no env.py é necessário para SQLite (constraints alteradas via batch ops em migrations futuras); aqui não é usado mas fica preparado.
- A migration **não usa** ORM `Base.metadata` (que será criado na TASK-010). Toda a criação é via `op.create_table` direto.
- A ordem de `drop_table` no downgrade é o reverso da ordem de criação (dependentes primeiro).
- Os nomes de constraints/índices são fixos via `name=` para reprodutibilidade entre SQLite e potencial migração futura.

## Contratos com camadas adjacentes

```
Produz para:
  - TASK-010 (ORM models): schema persistido com nomes de colunas em pt-BR e tipos SQLite. ORM models devem refletir exatamente as colunas, tipos, NOT NULL e defaults.
  - TASK-008 (SQLAlchemy session): cliente assume que o schema ja foi aplicado (alembic upgrade head) antes de abrir sessao em runtime.

Consome de:
  - TASK-006: TIMESHEET_DB_URL (sqlite+aiosqlite:///./data/timesheet.sqlite) presente em .env.example; pasta data/ via make data-dir.
```

Nenhum contrato HTTP é tocado nesta task.

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"` (ou `pip install sqlalchemy alembic aiosqlite` no venv ativo) — runtime deps disponíveis.
2. `cd apps/api && pytest tests/test_migration_0001.py -v` — 8 testes passam.
3. `cd apps/api && ruff check .` — sem warnings.
4. `cd apps/api && mypy --strict app` — sem regressão (alembic não é coberto por mypy strict, apenas `app/`).
5. Smoke manual: `cd apps/api && TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/timesheet.sqlite alembic upgrade head && alembic downgrade base && alembic upgrade head` — ciclo idempotente.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.
