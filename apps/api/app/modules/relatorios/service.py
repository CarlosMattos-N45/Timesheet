from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto_state
from app.core.config import settings
from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.jornadas.service import detalhe as jornada_detalhe
from app.modules.jornadas.service import listar_mes
from app.modules.relatorios.invalidation import register_invalidation_listener
from app.modules.relatorios.pdf import render_pdf
from app.modules.relatorios.repository import HistoricoEnvioRepository, RelatorioRepository
from app.modules.relatorios.smtp_send import send_pdf_sync
from app.modules.smtp.repository import SmtpRepository

# Registra o listener de invalidação ao importar o módulo (idempotente)
register_invalidation_listener()


async def gerar_pdf(
    session: AsyncSession,
    mes_referencia: str,
    *,
    terceiro: Terceiro | None = None,
) -> str:
    """Gera (ou regenera) o PDF; persiste RelatorioGerado; retorna o caminho."""
    if terceiro is None:
        terceiro = (await session.execute(select(Terceiro))).scalar_one_or_none()
        if terceiro is None:
            raise DomainError(code="NO_DATA", message="Terceiro não cadastrado", http_status=422)
    mes_data = await listar_mes(session, terceiro, mes_referencia)
    if not mes_data["jornadas"]:
        raise DomainError(code="NO_DATA", message="Sem jornadas no mês", http_status=422)
    # Carrega detalhe completo para marcações e atividade
    jornadas_full: list[dict[str, Any]] = []
    for resumo in mes_data["jornadas"]:
        det = await jornada_detalhe(session, terceiro, resumo["id"])
        jornadas_full.append(
            {
                "data": det["data"],
                "status": det["status"],
                "total_horas_apuradas_s": det["total_horas_apuradas_s"],
                "marcacoes": det["marcacoes"],
                "atividade": det["atividade"],
            }
        )
    pdf_bytes = await render_pdf(terceiro, jornadas_full, mes_referencia)
    pdf_dir = Path(settings.pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    caminho = pdf_dir / f"relatorio-{mes_referencia}.pdf"
    caminho.write_bytes(pdf_bytes)
    repo = RelatorioRepository(session)
    await repo.upsert(mes_referencia, str(caminho))
    await session.commit()
    return str(caminho)


async def get_meta(session: AsyncSession, mes_referencia: str) -> dict[str, Any]:
    repo = RelatorioRepository(session)
    r = await repo.get_by_mes(mes_referencia)
    if r is None:
        raise DomainError(code="NOT_FOUND", message="Relatório não gerado", http_status=404)
    return {
        "mes_referencia": r.mes_referencia,
        "caminho_arquivo": r.caminho_arquivo,
        "gerado_em": r.gerado_em,
        "invalidado_em": r.invalidado_em,
    }


async def enviar_relatorio(
    session: AsyncSession,
    mes_referencia: str,
    *,
    email_override: str | None = None,
) -> dict[str, Any]:
    smtp_repo = SmtpRepository(session)
    cfg = await smtp_repo.get_or_none()
    if cfg is None:
        raise DomainError(
            code="SMTP_NOT_CONFIGURED", message="SMTP não configurado", http_status=422
        )
    # Garante PDF válido
    rel_repo = RelatorioRepository(session)
    r = await rel_repo.get_by_mes(mes_referencia)
    if r is None or r.invalidado_em is not None:
        await gerar_pdf(session, mes_referencia)
        r = await rel_repo.get_by_mes(mes_referencia)
    assert r is not None
    pdf_bytes = Path(r.caminho_arquivo).read_bytes()
    # Decide destinatário
    if email_override:
        to_email = email_override
    else:
        terceiro = (await session.execute(select(Terceiro))).scalar_one()
        to_email = terceiro.email_destinatario_relatorio or terceiro.email_contato
    username = smtp_repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP)
    password = smtp_repo.decrypt_password(cfg, crypto_state.SUBKEY_SMTP)
    hist_repo = HistoricoEnvioRepository(session)
    try:
        send_pdf_sync(
            host=cfg.host,
            port=cfg.port,
            username=username,
            password=password,
            use_starttls=bool(cfg.use_starttls),
            from_address=cfg.from_address,
            to_email=to_email,
            pdf_bytes=pdf_bytes,
            mes_referencia=mes_referencia,
        )
    except DomainError as exc:
        await hist_repo.create(
            mes=mes_referencia, email=to_email, status="FALHA", erro=exc.message
        )
        await session.commit()
        raise
    h = await hist_repo.create(mes=mes_referencia, email=to_email, status="SUCESSO", erro=None)
    await session.commit()
    return {"status": "SUCESSO", "historico_id": h.id}


async def listar_historico(
    session: AsyncSession, mes_referencia: str
) -> list[dict[str, Any]]:
    repo = HistoricoEnvioRepository(session)
    rows = await repo.list_by_mes(mes_referencia)
    return [
        {
            "id": r.id,
            "mes_referencia": r.mes_referencia,
            "email_destinatario": r.email_destinatario,
            "status": r.status,
            "erro_mensagem": r.erro_mensagem,
            "enviado_em": r.enviado_em,
        }
        for r in rows
    ]
