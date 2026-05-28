from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Entidade = Literal["Jornada", "Marcacao", "Terceiro", "Atividade"]


class AuditoriaItem(BaseModel):
    id: str
    entidade: str
    entidade_id: str
    autor: str
    antes_json: str | None
    depois_json: str
    motivo: str | None
    criado_em: str
