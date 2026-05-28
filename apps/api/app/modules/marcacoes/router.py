from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.marcacoes import service
from app.modules.marcacoes.schema import (
    AjusteMarcacaoRequest,
    MarcacaoResponse,
    PostMarcacaoRequest,
)

router = APIRouter(prefix="/api/v1/marcacoes", tags=["marcacoes"])


@router.post("", status_code=201, response_model=MarcacaoResponse)
async def criar(
    body: PostMarcacaoRequest, t: CurrentTerceiroDep, session: SessionDep
) -> MarcacaoResponse:
    data = await service.criar_marcacao(session, t, body.model_dump())
    return MarcacaoResponse(**data)


@router.get("", response_model=list[MarcacaoResponse])
async def listar(
    t: CurrentTerceiroDep,
    session: SessionDep,
    status: str | None = Query(default=None),
) -> list[MarcacaoResponse]:
    rows = await service.listar_marcacoes(session, t, status)
    return [MarcacaoResponse(**r) for r in rows]


@router.put("/{marcacao_id}", response_model=MarcacaoResponse)
async def ajustar(
    marcacao_id: str,
    body: AjusteMarcacaoRequest,
    t: CurrentTerceiroDep,
    session: SessionDep,
) -> MarcacaoResponse:
    data = await service.ajustar_marcacao(session, t, marcacao_id, body.model_dump())
    return MarcacaoResponse(**data)
