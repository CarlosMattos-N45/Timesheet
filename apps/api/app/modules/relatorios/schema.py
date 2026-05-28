from __future__ import annotations

from pydantic import BaseModel, EmailStr


class RelatorioMesResponse(BaseModel):
    mes_referencia: str
    caminho_arquivo: str
    gerado_em: str
    invalidado_em: str | None


class HistoricoEnvioItem(BaseModel):
    id: str
    mes_referencia: str
    email_destinatario: str
    status: str
    erro_mensagem: str | None
    enviado_em: str


class EnviarRelatorioRequest(BaseModel):
    email: EmailStr | None = None


class EnviarResponse(BaseModel):
    status: str
    historico_id: str
