from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MarcacaoTipo = Literal["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]


class JornadaResumo(BaseModel):
    id: str
    data: str
    status: str
    total_horas_apuradas_s: int | None
    tem_marcacao_pendente: bool
    horario_inicio: str | None
    horario_saida_almoco: str | None
    horario_retorno_almoco: str | None
    horario_fim: str | None


class JornadasMesResponse(BaseModel):
    mes_referencia: str
    total_horas_mes_s: int
    jornadas: list[JornadaResumo]


class MarcacaoDetalhe(BaseModel):
    id: str
    tipo: str
    horario_registrado: str
    horario_efetivo: str | None
    origem: str
    status: str


class JornadaDetalheResponse(BaseModel):
    id: str
    data: str
    status: str
    total_horas_apuradas_s: int | None
    marcacoes: list[MarcacaoDetalhe]
    atividade: dict[str, str | None] | None  # {id, descricao, registrada_em, atualizado_em}
    justificativas: list[dict[str, str]]  # [{id, motivo, usuario_responsavel, criada_em}]


class AjusteMarcacaoItem(BaseModel):
    tipo: MarcacaoTipo
    horario_efetivo: datetime


class AjusteJornadaRequest(BaseModel):
    marcacoes: list[AjusteMarcacaoItem] = Field(min_length=1, max_length=4)
    motivo: str = Field(min_length=5, max_length=500)


class MarcacaoManualItem(BaseModel):
    tipo: MarcacaoTipo
    horario_efetivo: datetime


class JornadaManualRequest(BaseModel):
    data: date
    marcacoes: list[MarcacaoManualItem] = Field(min_length=4, max_length=4)
    atividade: str = Field(min_length=10, max_length=2000)
    motivo: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def _validate(self) -> JornadaManualRequest:
        tipos = [m.tipo for m in self.marcacoes]
        if set(tipos) != {"INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"}:
            msg = "as 4 marcacoes de tipos distintos sao obrigatorias"
            raise ValueError({"loc": ("marcacoes",), "msg": msg})
        # Ordenar por tipo canonico
        ordem = {"INICIO_JORNADA": 0, "SAIDA_ALMOCO": 1, "RETORNO_ALMOCO": 2, "FIM_JORNADA": 3}
        sorted_m = sorted(self.marcacoes, key=lambda m: ordem[m.tipo])
        horarios = [m.horario_efetivo for m in sorted_m]
        if not all(horarios[i] < horarios[i + 1] for i in range(3)):
            raise ValueError({"loc": ("marcacoes",), "msg": "horarios devem ser cronologicos"})
        return self
