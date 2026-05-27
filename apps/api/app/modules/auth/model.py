from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.modules.terceiros.model import Terceiro


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    __table_args__ = (
        Index("idx_refresh_token_hash", "token_hash"),
        Index("idx_refresh_token_exp", "expira_em"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    terceiro_id: Mapped[str] = mapped_column(
        Text, ForeignKey("terceiro.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expira_em: Mapped[str] = mapped_column(Text, nullable=False)
    revogado_em: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[str] = mapped_column(Text, nullable=False)

    terceiro: Mapped[Terceiro] = relationship(back_populates="refresh_tokens")
