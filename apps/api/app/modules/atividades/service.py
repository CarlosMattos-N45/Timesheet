from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.atividades.repository import AtividadeRepository
from app.modules.jornadas.repository import JornadaRepository


async def upsert_atividade(
    session: AsyncSession, t: Terceiro, jornada_id: str, descricao: str
) -> dict[str, Any]:
    jrepo = JornadaRepository(session)
    jornada = await jrepo.get_detalhe(jornada_id, t.id)
    if jornada is None:
        raise DomainError(code="NOT_FOUND", message="Jornada nao encontrada", http_status=404)
    arepo = AtividadeRepository(session)
    a, antes = await arepo.upsert(jornada_id, descricao)
    depois = {"descricao": a.descricao}
    await log_audit(
        session,
        entidade="Atividade",
        entidade_id=a.id,
        autor=t.email_contato,
        antes=antes,
        depois=depois,
        motivo=None,
    )
    await session.commit()
    return {
        "id": a.id,
        "jornada_id": a.jornada_id,
        "descricao": a.descricao,
        "registrada_em": a.registrada_em,
        "atualizado_em": a.atualizado_em,
    }
