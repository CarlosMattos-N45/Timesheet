from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.auditoria.repository import AuditoriaRepository
from app.modules.auditoria.schema import AuditoriaItem, Entidade

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

EntidadeQuery = Annotated[Entidade, Query()]
EntidadeIdQuery = Annotated[str, Query(min_length=1)]


@router.get("", response_model=list[AuditoriaItem])
async def listar(
    _t: CurrentTerceiroDep,
    session: SessionDep,
    entidade: EntidadeQuery,
    entidade_id: EntidadeIdQuery,
) -> list[AuditoriaItem]:
    repo = AuditoriaRepository(session)
    rows = await repo.list(entidade, entidade_id)
    return [
        AuditoriaItem(
            id=r.id,
            entidade=r.entidade,
            entidade_id=r.entidade_id,
            autor=r.autor,
            antes_json=r.antes_json,
            depois_json=r.depois_json,
            motivo=r.motivo,
            criado_em=r.criado_em,
        )
        for r in rows
    ]
