from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"
    __table_args__ = (
        CheckConstraint(
            "entidade IN ('Jornada','Marcacao','Terceiro','Atividade')",
            name="ck_audit_entidade",
        ),
        Index("idx_audit_entidade", "entidade", "entidade_id"),
        Index("idx_audit_criado_em", "criado_em"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    entidade: Mapped[str] = mapped_column(Text, nullable=False)
    entidade_id: Mapped[str] = mapped_column(Text, nullable=False)
    autor: Mapped[str] = mapped_column(Text, nullable=False)
    antes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    depois_json: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)
    expira_em: Mapped[str | None] = mapped_column(Text, nullable=True)
