from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, event, pool

from alembic import context
from app import models  # noqa: F401 — registra modelos no Base.metadata
from app.core.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _resolve_sync_url() -> str:
    # Aceita TIMESHEET_DB_URL (formato async) e converte para driver sincrono.
    # Alembic usa driver sincrono para gerar/aplicar migrations.
    raw = os.environ.get("TIMESHEET_DB_URL", "sqlite+aiosqlite:///./data/timesheet.sqlite")
    return raw.replace("sqlite+aiosqlite:", "sqlite:")


target_metadata = Base.metadata


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

    @event.listens_for(connectable, "connect")
    def set_sqlite_pragma(dbapi_conn: object, _: object) -> None:
        # Ativar FK enforcement por conexao (SQLite ignora FKs por padrao)
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with connectable.connect() as connection:
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
