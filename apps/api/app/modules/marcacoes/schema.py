from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MarcacaoTipo = Literal["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]
OrigemAgente = Literal["AGENTE_AUTOMATICO", "AGENTE_CONFIRMADO"]
OrigemAny = Literal["AGENTE_AUTOMATICO", "AGENTE_CONFIRMADO", "AJUSTE_WEB"]
StatusMarcacao = Literal["CONFIRMADA", "PENDENTE", "AJUSTADA"]


class PostMarcacaoRequest(BaseModel):
    tipo: MarcacaoTipo
    horario_registrado: datetime  # UTC ISO 8601
    horario_efetivo: datetime | None = None
    origem: OrigemAgente
    idempotency_key: UUID


class AjusteMarcacaoRequest(BaseModel):
    horario_efetivo: datetime
    motivo: str = Field(min_length=5, max_length=500)


class MarcacaoResponse(BaseModel):
    id: str
    jornada_id: str
    tipo: str
    horario_registrado: str
    horario_efetivo: str | None
    origem: str
    status: str
    confirmado_pelo_usuario: bool
    idempotency_key: str
    criada_em: str
