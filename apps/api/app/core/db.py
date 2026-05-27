from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import config as _config

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazy singleton engine. Aceita reset em teste via `_engine = None`."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _config.settings.db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        _attach_pragmas(_engine)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Use: session = Depends(get_session)."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session


def _attach_pragmas(engine: AsyncEngine) -> None:
    """Registra listener no engine sincrono subjacente. Roda em toda nova conexao."""
    sync_engine = engine.sync_engine
    cipher_key = _config.settings.db_cipher_key

    @event.listens_for(sync_engine, "connect")
    def _on_connect(dbapi_conn: Any, _record: Any) -> None:  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        try:
            # PRAGMA key DEVE ser o primeiro statement em uma conexao SQLCipher.
            # No dialeto aiosqlite com sqlite plano, o PRAGMA e' simplesmente ignorado
            # (banco nao cifrado retorna 0 rows). Em SQLCipher, ativa a chave.
            if cipher_key:
                cursor.execute(f"PRAGMA key = \"x'{cipher_key}'\"")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA busy_timeout = 5000")
        finally:
            cursor.close()


async def dispose_engine() -> None:
    """Chamado no shutdown da aplicacao."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
