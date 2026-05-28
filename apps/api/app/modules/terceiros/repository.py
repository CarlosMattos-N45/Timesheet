from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.core.security import (
    hash_password,
    revoke_token_chain,
    verify_password,
)
from app.models import Terceiro


class TerceiroRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count(self) -> int:
        n = (await self.session.execute(select(func.count()).select_from(Terceiro))).scalar_one()
        return int(n)

    async def get_by_id(self, terceiro_id: str) -> Terceiro | None:
        return (
            await self.session.execute(select(Terceiro).where(Terceiro.id == terceiro_id))
        ).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Terceiro | None:
        return (
            await self.session.execute(select(Terceiro).where(Terceiro.email_contato == email))
        ).scalar_one_or_none()

    async def create(self, payload: dict[str, Any]) -> Terceiro:
        now = datetime.now(UTC).isoformat()
        t = Terceiro(
            id=str(uuid4()),
            nome=payload["nome"],
            empresa_nome=payload["empresa_nome"],
            empresa_cnpj=payload["empresa_cnpj"],
            horario_inicio_jornada=payload["horario_inicio_jornada"].isoformat(),
            horario_saida_almoco=payload["horario_saida_almoco"].isoformat(),
            horario_retorno_almoco=payload["horario_retorno_almoco"].isoformat(),
            horario_fim_jornada=payload["horario_fim_jornada"].isoformat(),
            trabalha_fim_de_semana=1 if payload["trabalha_fim_de_semana"] else 0,
            email_contato=payload["email_contato"],
            email_destinatario_relatorio=payload.get("email_destinatario_relatorio"),
            senha_hash=hash_password(payload["senha"]),
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(t)
        return t

    @staticmethod
    def _snapshot(t: Terceiro) -> dict[str, Any]:
        return {
            "nome": t.nome,
            "empresa_nome": t.empresa_nome,
            "empresa_cnpj": t.empresa_cnpj,
            "horario_inicio_jornada": t.horario_inicio_jornada,
            "horario_saida_almoco": t.horario_saida_almoco,
            "horario_retorno_almoco": t.horario_retorno_almoco,
            "horario_fim_jornada": t.horario_fim_jornada,
            "trabalha_fim_de_semana": t.trabalha_fim_de_semana,
            "email_contato": t.email_contato,
            "email_destinatario_relatorio": t.email_destinatario_relatorio,
        }

    async def update(self, t: Terceiro, payload: dict[str, Any], autor: str) -> Terceiro:
        antes = self._snapshot(t)
        t.nome = payload["nome"]
        t.empresa_nome = payload["empresa_nome"]
        t.empresa_cnpj = payload["empresa_cnpj"]
        t.horario_inicio_jornada = payload["horario_inicio_jornada"].isoformat()
        t.horario_saida_almoco = payload["horario_saida_almoco"].isoformat()
        t.horario_retorno_almoco = payload["horario_retorno_almoco"].isoformat()
        t.horario_fim_jornada = payload["horario_fim_jornada"].isoformat()
        t.trabalha_fim_de_semana = 1 if payload["trabalha_fim_de_semana"] else 0
        t.email_contato = payload["email_contato"]
        t.email_destinatario_relatorio = payload.get("email_destinatario_relatorio")
        t.atualizado_em = datetime.now(UTC).isoformat()
        await log_audit(
            self.session,
            entidade="Terceiro",
            entidade_id=t.id,
            autor=autor,
            antes=antes,
            depois=self._snapshot(t),
            motivo=None,
        )
        return t

    async def change_password(self, t: Terceiro, senha_atual: str, nova_senha: str) -> None:
        if not verify_password(t.senha_hash, senha_atual):
            raise DomainError(code="UNAUTHORIZED", message="Senha atual incorreta", http_status=401)
        t.senha_hash = hash_password(nova_senha)
        t.atualizado_em = datetime.now(UTC).isoformat()
        await revoke_token_chain(t.id, self.session)
