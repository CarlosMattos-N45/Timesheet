from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.models import Marcacao, Terceiro
from app.modules.jornadas.repository import JornadaRepository
from app.modules.marcacoes.repository import MarcacaoRepository


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _to_response(m: Marcacao) -> dict[str, Any]:
    return {
        "id": m.id,
        "jornada_id": m.jornada_id,
        "tipo": m.tipo,
        "horario_registrado": m.horario_registrado,
        "horario_efetivo": m.horario_efetivo,
        "origem": m.origem,
        "status": m.status,
        "confirmado_pelo_usuario": bool(m.confirmado_pelo_usuario),
        "idempotency_key": m.idempotency_key,
        "criada_em": m.criada_em,
    }


async def criar_marcacao(
    session: AsyncSession, t: Terceiro, payload: dict[str, Any]
) -> dict[str, Any]:
    h_reg: datetime = payload["horario_registrado"]
    data_jornada = h_reg.date().isoformat()
    # Weekend check
    if not t.trabalha_fim_de_semana and dt_date.fromisoformat(data_jornada).weekday() >= 5:
        raise DomainError(
            code="FIM_DE_SEMANA_NAO_PERMITIDO",
            message="Terceiro não trabalha em fim de semana",
            http_status=422,
        )

    repo = MarcacaoRepository(session)
    idem = str(payload["idempotency_key"])

    # Idempotency check
    existing = await repo.get_by_idempotency(idem)
    if existing is not None:
        return _to_response(existing)

    # Auto-create jornada
    jrepo = JornadaRepository(session)
    j = await jrepo.get_or_create_for_day(t.id, data_jornada)

    # Conflict resolution (UNIQUE jornada_id+tipo)
    same_tipo = await repo.get_in_jornada_by_tipo(j.id, payload["tipo"])
    if same_tipo is not None:
        # RN-012 #1: AJUSTE_WEB sempre vence
        if same_tipo.origem == "AJUSTE_WEB":
            raise DomainError(
                code="AJUSTE_WEB_WINS",
                message="Marcação foi ajustada via Web — Agente descarta",
                http_status=409,
            )
        # Demais conflitos: 409 CONFLICT genérico
        raise DomainError(
            code="CONFLICT",
            message=f"Já existe marcação do tipo {payload['tipo']} para esta jornada",
            http_status=409,
        )

    h_ef = payload.get("horario_efetivo")
    m = await repo.create(
        jornada_id=j.id,
        tipo=payload["tipo"],
        horario_registrado=_iso(h_reg),
        horario_efetivo=_iso(h_ef) if h_ef else None,
        origem=payload["origem"],
        idempotency_key=idem,
    )
    await session.commit()
    await session.refresh(m)
    return _to_response(m)


async def listar_marcacoes(
    session: AsyncSession, t: Terceiro, status: str | None
) -> list[dict[str, Any]]:
    repo = MarcacaoRepository(session)
    rows = await repo.list_for_terceiro(t.id, status)
    return [_to_response(m) for m in rows]


async def ajustar_marcacao(
    session: AsyncSession, t: Terceiro, marcacao_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    repo = MarcacaoRepository(session)
    m = await repo.get_by_id_owned_by(marcacao_id, t.id)
    if m is None:
        raise DomainError(code="NOT_FOUND", message="Marcação não encontrada", http_status=404)
    antes = repo.snapshot(m)
    h_ef: datetime = payload["horario_efetivo"]
    await repo.ajustar(m, _iso(h_ef))
    depois = repo.snapshot(m)
    await log_audit(
        session,
        entidade="Marcacao",
        entidade_id=m.id,
        autor=t.email_contato,
        antes=antes,
        depois=depois,
        motivo=payload["motivo"],
    )
    # Atualiza status da jornada
    jrepo = JornadaRepository(session)
    await jrepo.set_status_ajustada(m.jornada_id)
    await session.commit()
    await session.refresh(m)
    return _to_response(m)
