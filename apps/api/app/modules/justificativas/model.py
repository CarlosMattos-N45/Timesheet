from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.jornadas.model import Jornada


class Justificativa(Base):
    __tablename__ = "justificativa"
    __table_args__ = (
        CheckConstraint("length(motivo) >= 5", name="ck_justif_motivo_len"),
        Index("idx_justificativa_jornada", "jornada_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    jornada_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jornada.id", ondelete="CASCADE"), nullable=False
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    usuario_responsavel: Mapped[str] = mapped_column(Text, nullable=False)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)

    jornada: Mapped[Jornada] = relationship(back_populates="justificativas")
