from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.atividades.model import Atividade
    from app.modules.justificativas.model import Justificativa
    from app.modules.marcacoes.model import Marcacao
    from app.modules.terceiros.model import Terceiro


class Jornada(Base):
    __tablename__ = "jornada"
    __table_args__ = (
        CheckConstraint(
            "status IN ('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE')",
            name="ck_jornada_status",
        ),
        UniqueConstraint("terceiro_id", "data", name="uq_jornada_terceiro_data"),
        Index("idx_jornada_terceiro_data", "terceiro_id", "data"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    terceiro_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("terceiro.id", ondelete="CASCADE", name="fk_jornada_terceiro"),
        nullable=False,
    )
    data: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    total_horas_apuradas_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criada_em: Mapped[str] = mapped_column(Text, nullable=False)
    fechada_em: Mapped[str | None] = mapped_column(Text, nullable=True)

    terceiro: Mapped[Terceiro] = relationship(back_populates="jornadas")
    marcacoes: Mapped[list[Marcacao]] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", passive_deletes=True
    )
    atividade: Mapped[Atividade | None] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", uselist=False, passive_deletes=True
    )
    justificativas: Mapped[list[Justificativa]] = relationship(
        back_populates="jornada", cascade="all, delete-orphan", passive_deletes=True
    )
