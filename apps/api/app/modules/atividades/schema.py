from __future__ import annotations

from pydantic import BaseModel, Field


class AtividadeRequest(BaseModel):
    descricao: str = Field(min_length=10, max_length=2000)


class AtividadeResponse(BaseModel):
    id: str
    jornada_id: str
    descricao: str
    registrada_em: str
    atualizado_em: str | None
