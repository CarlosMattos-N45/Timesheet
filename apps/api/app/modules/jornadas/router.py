from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.jornadas import service
from app.modules.jornadas.schema import (
    AjusteJornadaRequest,
    JornadaDetalheResponse,
    JornadaManualRequest,
    JornadasMesResponse,
)

router = APIRouter(prefix="/api/v1/jornadas", tags=["jornadas"])


@router.get("", response_model=JornadasMesResponse)
async def listar(
    t: CurrentTerceiroDep,
    session: SessionDep,
    mes: str = Query(pattern=r"^\d{4}-\d{2}$"),
) -> JornadasMesResponse:
    data = await service.listar_mes(session, t, mes)
    return JornadasMesResponse(**data)


@router.post("/manual", status_code=201, response_model=JornadaDetalheResponse)
async def post_manual(
    body: JornadaManualRequest, t: CurrentTerceiroDep, session: SessionDep
) -> JornadaDetalheResponse:
    data = await service.criar_manual(session, t, body.model_dump())
    return JornadaDetalheResponse(**data)


@router.get("/{jornada_id}", response_model=JornadaDetalheResponse)
async def get_detalhe(
    jornada_id: str, t: CurrentTerceiroDep, session: SessionDep
) -> JornadaDetalheResponse:
    data = await service.detalhe(session, t, jornada_id)
    return JornadaDetalheResponse(**data)


@router.put("/{jornada_id}", response_model=JornadaDetalheResponse)
async def put_ajuste(
    jornada_id: str,
    body: AjusteJornadaRequest,
    t: CurrentTerceiroDep,
    session: SessionDep,
) -> JornadaDetalheResponse:
    data = await service.ajustar_jornada(session, t, jornada_id, body.model_dump())
    return JornadaDetalheResponse(**data)
