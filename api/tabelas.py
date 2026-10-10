"""Tabelas do banco (desenho em docs/ARQUITETURA.md).

O personagem é guardado como no motor: a criação e uma linha por subida de
nível. A ficha nunca é salva; é recalculada ao carregar. Equipamento, cofre
e sessão são o estado atual e ficam como JSON na própria linha do personagem.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class PersonagemTabela(Base):
    __tablename__ = "personagens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), default="")
    criacao: Mapped[dict] = mapped_column(JSON)          # motor.Criacao
    equipamento: Mapped[dict] = mapped_column(JSON)      # motor.Equipamento
    cofre: Mapped[list] = mapped_column(JSON)            # ids das cartas no cofre
    sessao: Mapped[dict] = mapped_column(JSON)           # marcas atuais (motor.Sessao)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora,
                                                    onupdate=_agora)

    subidas: Mapped[list["SubidaTabela"]] = relationship(
        back_populates="personagem", order_by="SubidaTabela.nivel",
        cascade="all, delete-orphan", passive_deletes=True)


class SubidaTabela(Base):
    __tablename__ = "subidas_de_nivel"
    __table_args__ = (UniqueConstraint("personagem_id", "nivel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    personagem_id: Mapped[str] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"), index=True)
    nivel: Mapped[int] = mapped_column(Integer)
    dados: Mapped[dict] = mapped_column(JSON)            # motor.SubidaDeNivel

    personagem: Mapped[PersonagemTabela] = relationship(back_populates="subidas")
