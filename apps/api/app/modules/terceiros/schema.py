from __future__ import annotations

from datetime import time
from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator
from stdnum.br import cnpj as cnpj_validator  # type: ignore[import-untyped]


class CreateTerceiroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    empresa_nome: str = Field(min_length=1, max_length=150)
    empresa_cnpj: str = Field(min_length=14, max_length=14)
    horario_inicio_jornada: time
    horario_saida_almoco: time
    horario_retorno_almoco: time
    horario_fim_jornada: time
    trabalha_fim_de_semana: bool = False
    email_contato: EmailStr
    email_destinatario_relatorio: EmailStr | None = None
    senha: str = Field(min_length=8, max_length=128)
    senha_confirmacao: str

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not cnpj_validator.is_valid(self.empresa_cnpj):
            raise ValueError(  # noqa: TRY004
                {"loc": ("empresa_cnpj",), "msg": "CNPJ inválido (dígito verificador incorreto)"}
            )
        if not (
            self.horario_inicio_jornada < self.horario_saida_almoco
            < self.horario_retorno_almoco < self.horario_fim_jornada
        ):
            raise ValueError({"loc": (), "msg": "horários devem ser cronológicos"})
        if self.senha != self.senha_confirmacao:
            raise ValueError({"loc": ("senha_confirmacao",), "msg": "Senhas não coincidem"})
        return self


class CreateTerceiroResponse(BaseModel):
    terceiro_id: str
    criado_em: str


class TerceiroResponse(BaseModel):
    id: str
    nome: str
    empresa_nome: str
    empresa_cnpj: str
    horario_inicio_jornada: str
    horario_saida_almoco: str
    horario_retorno_almoco: str
    horario_fim_jornada: str
    trabalha_fim_de_semana: bool
    email_contato: str
    email_destinatario_relatorio: str | None
    criado_em: str
    atualizado_em: str


class UpdateTerceiroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    empresa_nome: str = Field(min_length=1, max_length=150)
    empresa_cnpj: str = Field(min_length=14, max_length=14)
    horario_inicio_jornada: time
    horario_saida_almoco: time
    horario_retorno_almoco: time
    horario_fim_jornada: time
    trabalha_fim_de_semana: bool = False
    email_contato: EmailStr
    email_destinatario_relatorio: EmailStr | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not cnpj_validator.is_valid(self.empresa_cnpj):
            raise ValueError(  # noqa: TRY004
                {"loc": ("empresa_cnpj",), "msg": "CNPJ inválido (dígito verificador incorreto)"}
            )
        if not (
            self.horario_inicio_jornada < self.horario_saida_almoco
            < self.horario_retorno_almoco < self.horario_fim_jornada
        ):
            raise ValueError({"loc": (), "msg": "horários devem ser cronológicos"})
        return self


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=128)
