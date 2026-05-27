from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Marcacao(Base):
    __tablename__ = "marcacao"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')",
            name="ck_marcacao_tipo",
        ),
        CheckConstraint(
            "origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB')",
            name="ck_marcacao_origem",
        ),
        CheckConstraint(
            "status IN ('CONFIRMADA','PENDENTE','AJUSTADA')",
            name="ck_marcacao_status",
        ),
        CheckConstraint("length(idempotency_key) = 36", name="ck_marcacao_idem_len"),
        UniqueConstraint("idempotency_key", name="uq_marcacao_idem"),
        UniqueConstraint("jornada_id", "tipo", name="uq_marcacao_jornada_tipo"),
        Index("idx_marcacao_jornada", "jornada_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    horario_registrado: Mapped[str] = mapped_column(Text, nullable=False)
    horario_efetivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="CONFIRMADA")
    confirmado_pelo_usuario: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)

    jornada: Mapped[Jornada] = relationship(back_populates="marcacoes")
