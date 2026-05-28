from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.models import Atividade, Jornada, Marcacao, RelatorioGerado

_listener_registered = False


def _mes_de(data_iso: str) -> str | None:
    return data_iso[:7] if data_iso and len(data_iso) >= 7 else None


def register_invalidation_listener() -> None:
    """Registra after_flush para detectar mutações em Jornada/Marcacao/Atividade
    e setar relatorio_gerado.invalidado_em do mes correspondente. Idempotente."""
    global _listener_registered
    if _listener_registered:
        return
    _listener_registered = True

    @event.listens_for(Session, "after_flush")
    def _after_flush(session: Session, _flush_context: Any) -> None:
        meses_afetados: set[str] = set()
        for obj in list(session.new) + list(session.dirty):
            if isinstance(obj, Jornada):
                m = _mes_de(obj.data)
            elif isinstance(obj, Marcacao):
                # Tenta buscar a jornada pelo identity_map
                j = session.identity_map.get((Jornada, (obj.jornada_id,)))  # type: ignore[arg-type]
                m = None if j is None else _mes_de(j.data)
            elif isinstance(obj, Atividade):
                j = session.identity_map.get((Jornada, (obj.jornada_id,)))  # type: ignore[arg-type]
                m = _mes_de(j.data) if j else None
            else:
                m = None
            if m:
                meses_afetados.add(m)
        for mes in meses_afetados:
            session.execute(
                update(RelatorioGerado)
                .where(
                    RelatorioGerado.mes_referencia == mes,
                    RelatorioGerado.invalidado_em.is_(None),
                )
                .values(invalidado_em=datetime.now(UTC).isoformat())
            )
