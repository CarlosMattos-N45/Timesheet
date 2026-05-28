from __future__ import annotations

from pydantic import BaseModel


class PrivacyStatus(BaseModel):
    accepted: bool
    versao_aviso: str | None
    aceito_em: str | None
