from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.auth.model import RefreshToken
    from app.modules.jornadas.model import Jornada


class Terceiro(Base):
    __tablename__ = "terceiro"
    __table_args__ = (
        CheckConstraint("length(nome) BETWEEN 1 AND 120", name="ck_terceiro_nome_len"),
        CheckConstraint("length(empresa_nome) BETWEEN 1 AND 150", name="ck_terceiro_empresa_len"),
        CheckConstraint("length(empresa_cnpj) = 14", name="ck_terceiro_cnpj_len"),
        CheckConstraint("length(email_contato) <= 254", name="ck_terceiro_email_len"),
        CheckConstraint(
            "horario_inicio_jornada < horario_saida_almoco "
            "AND horario_saida_almoco < horario_retorno_almoco "
            "AND horario_retorno_almoco < horario_fim_jornada",
            name="ck_terceiro_horarios_crono",
        ),
        UniqueConstraint("email_contato", name="uq_terceiro_email"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    empresa_nome: Mapped[str] = mapped_column(Text, nullable=False)
    empresa_cnpj: Mapped[str] = mapped_column(Text, nullable=False)
    horario_inicio_jornada: Mapped[str] = mapped_column(Text, nullable=False)
    horario_saida_almoco: Mapped[str] = mapped_column(Text, nullable=False)
    horario_retorno_almoco: Mapped[str] = mapped_column(Text, nullable=False)
    horario_fim_jornada: Mapped[str] = mapped_column(Text, nullable=False)
    trabalha_fim_de_semana: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    email_contato: Mapped[str] = mapped_column(Text, nullable=False)
    email_destinatario_relatorio: Mapped[str | None] = mapped_column(Text, nullable=True)
    senha_hash: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str] = mapped_column(Text, nullable=False)

    jornadas: Mapped[list[Jornada]] = relationship(
        back_populates="terceiro", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="terceiro", cascade="all, delete-orphan", passive_deletes=True
    )
