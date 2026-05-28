from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.models import Jornada, Marcacao, Terceiro
from app.modules.atividades.repository import AtividadeRepository
from app.modules.jornadas.repository import JornadaRepository
from app.modules.justificativas.repository import JustificativaRepository
from app.modules.marcacoes.repository import MarcacaoRepository

_MES_RE = re.compile(r"^\d{4}-\d{2}$")


def _compute_total_diario_s(marcacoes: list[Marcacao]) -> int | None:
    by_tipo = {m.tipo: m for m in marcacoes}
    required = {"INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"}
    if not required.issubset(set(by_tipo.keys())):
        return None
    if any(m.status == "PENDENTE" for m in marcacoes):
        return None

    def _eff_ts(m: Marcacao) -> int:
        s = m.horario_efetivo or m.horario_registrado
        if s is None:
            return 0
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())

    inicio = _eff_ts(by_tipo["INICIO_JORNADA"])
    saida_alm = _eff_ts(by_tipo["SAIDA_ALMOCO"])
    retorno_alm = _eff_ts(by_tipo["RETORNO_ALMOCO"])
    fim = _eff_ts(by_tipo["FIM_JORNADA"])
    almoco = retorno_alm - saida_alm
    total = (fim - inicio) - almoco
    return total if total > 0 else 0


def _marc_to_dict(m: Marcacao) -> dict[str, Any]:
    return {
        "id": m.id,
        "tipo": m.tipo,
        "horario_registrado": m.horario_registrado,
        "horario_efetivo": m.horario_efetivo,
        "origem": m.origem,
        "status": m.status,
    }


def _jornada_resumo(j: Jornada) -> dict[str, Any]:
    by_tipo = {m.tipo: m for m in j.marcacoes}

    def _h(tipo: str) -> str | None:
        m = by_tipo.get(tipo)
        if m is None:
            return None
        return m.horario_efetivo or m.horario_registrado

    return {
        "id": j.id,
        "data": j.data,
        "status": j.status,
        "total_horas_apuradas_s": j.total_horas_apuradas_s,
        "tem_marcacao_pendente": any(m.status == "PENDENTE" for m in j.marcacoes),
        "horario_inicio": _h("INICIO_JORNADA"),
        "horario_saida_almoco": _h("SAIDA_ALMOCO"),
        "horario_retorno_almoco": _h("RETORNO_ALMOCO"),
        "horario_fim": _h("FIM_JORNADA"),
    }


async def listar_mes(session: AsyncSession, t: Terceiro, mes: str) -> dict[str, Any]:
    if not _MES_RE.match(mes):
        raise DomainError(code="VALIDATION_ERROR", message="Mes invalido", http_status=422)
    repo = JornadaRepository(session)
    rows = await repo.list_for_month(t.id, mes)
    jornadas = [_jornada_resumo(j) for j in rows]
    total = sum((j["total_horas_apuradas_s"] or 0) for j in jornadas)
    return {"mes_referencia": mes, "total_horas_mes_s": total, "jornadas": jornadas}


async def detalhe(session: AsyncSession, t: Terceiro, jornada_id: str) -> dict[str, Any]:
    repo = JornadaRepository(session)
    j = await repo.get_detalhe(jornada_id, t.id)
    if j is None:
        raise DomainError(code="NOT_FOUND", message="Jornada nao encontrada", http_status=404)
    return {
        "id": j.id,
        "data": j.data,
        "status": j.status,
        "total_horas_apuradas_s": j.total_horas_apuradas_s,
        "marcacoes": [_marc_to_dict(m) for m in j.marcacoes],
        "atividade": {
            "id": j.atividade.id,
            "descricao": j.atividade.descricao,
            "registrada_em": j.atividade.registrada_em,
            "atualizado_em": j.atividade.atualizado_em,
        } if j.atividade else None,
        "justificativas": [
            {
                "id": jj.id,
                "motivo": jj.motivo,
                "usuario_responsavel": jj.usuario_responsavel,
                "criada_em": jj.criada_em,
            }
            for jj in j.justificativas
        ],
    }


async def ajustar_jornada(
    session: AsyncSession, t: Terceiro, jornada_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    jrepo = JornadaRepository(session)
    j = await jrepo.get_detalhe(jornada_id, t.id)
    if j is None:
        raise DomainError(code="NOT_FOUND", message="Jornada nao encontrada", http_status=404)
    by_tipo = {m.tipo: m for m in j.marcacoes}
    antes = {
        m.tipo: {"horario_efetivo": m.horario_efetivo, "origem": m.origem}
        for m in j.marcacoes
    }
    for ajuste in payload["marcacoes"]:
        tipo = ajuste["tipo"] if isinstance(ajuste["tipo"], str) else str(ajuste["tipo"])
        horario = ajuste["horario_efetivo"]
        if hasattr(horario, "isoformat"):
            horario = horario.isoformat()
        m = by_tipo.get(tipo)
        if m is None:
            continue
        m.horario_efetivo = horario
        m.origem = "AJUSTE_WEB"
        m.status = "AJUSTADA"
    j.status = "AJUSTADA_MANUALMENTE"
    j.total_horas_apuradas_s = _compute_total_diario_s(list(j.marcacoes))
    depois = {
        m.tipo: {"horario_efetivo": m.horario_efetivo, "origem": m.origem}
        for m in j.marcacoes
    }
    justif_repo = JustificativaRepository(session)
    await justif_repo.create(
        jornada_id=j.id, motivo=payload["motivo"], usuario_responsavel=t.email_contato
    )
    await log_audit(
        session,
        entidade="Jornada",
        entidade_id=j.id,
        autor=t.email_contato,
        antes=antes,
        depois=depois,
        motivo=payload["motivo"],
    )
    await session.commit()
    return await detalhe(session, t, jornada_id)


async def criar_manual(
    session: AsyncSession, t: Terceiro, payload: dict[str, Any]
) -> dict[str, Any]:
    data_val = payload["data"]
    data = data_val.isoformat() if hasattr(data_val, "isoformat") else str(data_val)
    jrepo = JornadaRepository(session)
    existing = await jrepo.get_by_terceiro_and_data(t.id, data)
    if existing is not None:
        raise DomainError(
            code="CONFLICT", message="Ja existe jornada para esta data", http_status=409
        )
    j = Jornada(
        id=str(uuid4()),
        terceiro_id=t.id,
        data=data,
        status="AJUSTADA_MANUALMENTE",
        criada_em=datetime.now(UTC).isoformat(),
    )
    session.add(j)
    await session.flush()
    mrepo = MarcacaoRepository(session)
    for item in payload["marcacoes"]:
        tipo = item["tipo"] if isinstance(item["tipo"], str) else str(item["tipo"])
        horario = item["horario_efetivo"]
        if hasattr(horario, "isoformat"):
            horario = horario.isoformat()
        m = await mrepo.create(
            jornada_id=j.id,
            tipo=tipo,
            horario_registrado=horario,
            horario_efetivo=horario,
            origem="AJUSTE_WEB",
            idempotency_key=str(uuid4()),
        )
        m.status = "AJUSTADA"
    await session.flush()
    # Reload para calcular total
    j_loaded = await jrepo.get_detalhe(j.id, t.id)
    assert j_loaded is not None
    j_loaded.total_horas_apuradas_s = _compute_total_diario_s(list(j_loaded.marcacoes))
    arepo = AtividadeRepository(session)
    await arepo.upsert(j.id, payload["atividade"])
    justif_repo = JustificativaRepository(session)
    await justif_repo.create(
        jornada_id=j.id, motivo=payload["motivo"], usuario_responsavel=t.email_contato
    )
    await log_audit(
        session,
        entidade="Jornada",
        entidade_id=j.id,
        autor=t.email_contato,
        antes=None,
        depois={"data": data, "marcacoes": len(payload["marcacoes"]), "manual": True},
        motivo=payload["motivo"],
    )
    await session.commit()
    return await detalhe(session, t, j.id)
