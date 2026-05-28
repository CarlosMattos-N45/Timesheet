from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LogAuditoria

_ALLOWED: set[str] = {"Jornada", "Marcacao", "Terceiro", "Atividade"}


async def log_audit(
    session: AsyncSession,
    *,
    entidade: str,
    entidade_id: str,
    autor: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any],
    motivo: str | None,
) -> None:
    """Insere uma linha em log_auditoria. NÃO commita — caller é responsável."""
    if entidade not in _ALLOWED:
        raise ValueError(f"entidade inválida: {entidade}")
    row = LogAuditoria(
        id=str(uuid4()),
        entidade=entidade,
        entidade_id=entidade_id,
        autor=autor,
        antes_json=(
            json.dumps(antes, ensure_ascii=False, sort_keys=True) if antes is not None else None
        ),
        depois_json=json.dumps(depois, ensure_ascii=False, sort_keys=True),
        motivo=motivo,
        criado_em=datetime.now(UTC).isoformat(),
        expira_em=None,
    )
    session.add(row)
