from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Atividade(Base):
    __tablename__ = "atividade"
    __table_args__ = (
        CheckConstraint("length(descricao) >= 10", name="ck_atividade_desc_len"),
        UniqueConstraint("jornada_id", name="uq_atividade_jornada"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False
    )
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    registrada_em: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str | None] = mapped_column(Text, nullable=True)

    jornada: Mapped[Jornada] = relationship(back_populates="atividade")
