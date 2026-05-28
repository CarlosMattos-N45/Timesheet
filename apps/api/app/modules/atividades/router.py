from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.atividades import service
from app.modules.atividades.schema import AtividadeRequest, AtividadeResponse

router = APIRouter(prefix="/api/v1/jornadas", tags=["atividades"])


@router.post("/{jornada_id}/atividade", status_code=201, response_model=AtividadeResponse)
async def upsert(
    jornada_id: str,
    body: AtividadeRequest,
    t: CurrentTerceiroDep,
    session: SessionDep,
) -> AtividadeResponse:
    data = await service.upsert_atividade(session, t, jornada_id, body.descricao)
    return AtividadeResponse(**data)
