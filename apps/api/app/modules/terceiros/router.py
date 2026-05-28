from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.models import Terceiro as TerceiroModel
from app.modules.terceiros import service
from app.modules.terceiros.schema import (
    ChangePasswordRequest,
    CreateTerceiroRequest,
    CreateTerceiroResponse,
    TerceiroResponse,
    UpdateTerceiroRequest,
)

router = APIRouter(prefix="/api/v1/terceiros", tags=["terceiros"])


def _to_response(t: TerceiroModel) -> TerceiroResponse:
    return TerceiroResponse(
        id=t.id,
        nome=t.nome,
        empresa_nome=t.empresa_nome,
        empresa_cnpj=t.empresa_cnpj,
        horario_inicio_jornada=t.horario_inicio_jornada,
        horario_saida_almoco=t.horario_saida_almoco,
        horario_retorno_almoco=t.horario_retorno_almoco,
        horario_fim_jornada=t.horario_fim_jornada,
        trabalha_fim_de_semana=bool(t.trabalha_fim_de_semana),
        email_contato=t.email_contato,
        email_destinatario_relatorio=t.email_destinatario_relatorio,
        criado_em=t.criado_em,
        atualizado_em=t.atualizado_em,
    )


@router.post("", status_code=201, response_model=CreateTerceiroResponse)
async def create(body: CreateTerceiroRequest, session: SessionDep) -> CreateTerceiroResponse:
    t = await service.create_terceiro(session, body.model_dump())
    return CreateTerceiroResponse(terceiro_id=t.id, criado_em=t.criado_em)


@router.get("/me", response_model=TerceiroResponse)
async def get_me(t: CurrentTerceiroDep) -> TerceiroResponse:
    return _to_response(t)


@router.put("/me", response_model=TerceiroResponse)
async def put_me(
    body: UpdateTerceiroRequest, t: CurrentTerceiroDep, session: SessionDep
) -> TerceiroResponse:
    updated = await service.update_me(session, t, body.model_dump(), autor=t.email_contato)
    return _to_response(updated)


@router.put("/me/senha", status_code=status.HTTP_204_NO_CONTENT)
async def put_me_senha(
    body: ChangePasswordRequest, t: CurrentTerceiroDep, session: SessionDep
) -> None:
    await service.change_password(session, t, body.senha_atual, body.nova_senha)
