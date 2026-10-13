"""Tabelas do banco (desenho em docs/ARQUITETURA.md).

O personagem é guardado como no motor: a criação e uma linha por subida de
nível. A ficha nunca é salva; é recalculada ao carregar. Equipamento, cofre
e sessão são o estado atual e ficam como JSON na própria linha do personagem.
"""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class UsuarioTabela(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)   # sempre minúsculo
    nome: Mapped[str] = mapped_column(String(120))
    senha_hash: Mapped[str] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    personagens: Mapped[list["PersonagemTabela"]] = relationship(
        back_populates="dono", cascade="all, delete-orphan", passive_deletes=True)


class MesaTabela(Base):
    __tablename__ = "mesas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    criador_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    codigo_convite: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    # o que TODOS os mestres podem fazer (o criador pode tudo): {"ver_fichas": true, ...}
    permissoes_mestres: Mapped[dict] = mapped_column(JSON)
    # nível máximo dos personagens da mesa: mesa nova começa no 1; as que já
    # existiam ficaram no 10 (a migração não trava ninguém)
    nivel_maximo: Mapped[int] = mapped_column(Integer, default=1, server_default="10")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    membros: Mapped[list["MembroTabela"]] = relationship(
        back_populates="mesa", cascade="all, delete-orphan", passive_deletes=True)
    personagens: Mapped[list["PersonagemTabela"]] = relationship(back_populates="mesa")


class MembroTabela(Base):
    __tablename__ = "membros_mesa"

    mesa_id: Mapped[str] = mapped_column(ForeignKey("mesas.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"),
                                            primary_key=True, index=True)
    papel: Mapped[str] = mapped_column(String(16))   # "jogador" ou "mestre"
    entrou_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    mesa: Mapped[MesaTabela] = relationship(back_populates="membros")
    usuario: Mapped[UsuarioTabela] = relationship()


class InimigoTabela(Base):
    """Inimigo da mesa: criado do zero ou copiado de um adversário do SRD.
    Privado dos mestres. `dados` é um motor.Adversario."""

    __tablename__ = "inimigos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mesa_id: Mapped[str] = mapped_column(ForeignKey("mesas.id", ondelete="CASCADE"), index=True)
    dados: Mapped[dict] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, onupdate=_agora)


class NpcTabela(Base):
    """NPC da mesa: ficha simples, com ficha de combate opcional (motor.Adversario)."""

    __tablename__ = "npcs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mesa_id: Mapped[str] = mapped_column(ForeignKey("mesas.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(4000), default="")
    motivacoes: Mapped[str] = mapped_column(String(2000), default="")
    notas: Mapped[str] = mapped_column(String(8000), default="")
    ficha_combate: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    foto: Mapped[str | None] = mapped_column(String(36), nullable=True)   # id em `imagens`
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, onupdate=_agora)


class SessaoTabela(Base):
    """Sessão de jogo planejada e conduzida por UM mestre (o responsável, quem
    criou). Os outros mestres só veem se ele compartilhar. Tem o próprio Medo
    e os encontros que podem (ou não) acontecer."""

    __tablename__ = "sessoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mesa_id: Mapped[str] = mapped_column(ForeignKey("mesas.id", ondelete="CASCADE"), index=True)
    responsavel_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    titulo: Mapped[str] = mapped_column(String(120))
    data: Mapped[date | None] = mapped_column(Date, nullable=True)
    resumo: Mapped[str] = mapped_column(String(4000), default="")     # objetivos, o que deve acontecer
    notas: Mapped[str] = mapped_column(String(8000), default="")      # anotações privadas do mestre
    status: Mapped[str] = mapped_column(String(16), default="planejada")   # planejada, em_andamento, encerrada
    medo: Mapped[int] = mapped_column(Integer, default=0)             # Pontos de Medo desta sessão (0 a 12)
    compartilhada_com: Mapped[list] = mapped_column(JSON, default=list)   # ids de mestres que podem ver
    npcs: Mapped[list] = mapped_column(JSON, default=list)            # NPCs da mesa que devem aparecer
    inimigos: Mapped[list] = mapped_column(JSON, default=list)        # inimigos da mesa que devem aparecer
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, onupdate=_agora)

    responsavel: Mapped[UsuarioTabela] = relationship()


class EncontroTabela(Base):
    """Encontro de uma sessão: cópias de adversários com as marcas de cada
    uma. `combatentes` é uma lista de motor.encontro.Combatente. Não há ordem:
    um encontro pode nunca acontecer, conforme o caminho dos jogadores."""

    __tablename__ = "encontros"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mesa_id: Mapped[str] = mapped_column(ForeignKey("mesas.id", ondelete="CASCADE"), index=True)
    sessao_id: Mapped[str] = mapped_column(ForeignKey("sessoes.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    combatentes: Mapped[list] = mapped_column(JSON)
    # escolhas do Guia de Batalha (motor.guia_batalha.OpcoesDoGuia); None: padrão da mesa
    guia: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, onupdate=_agora)


class PersonagemTabela(Base):
    __tablename__ = "personagens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dono_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    # uma mesa por vez; apagar a mesa só desvincula o personagem
    mesa_id: Mapped[str | None] = mapped_column(ForeignKey("mesas.id", ondelete="SET NULL"),
                                                index=True, nullable=True)
    nome: Mapped[str] = mapped_column(String(120), default="")
    criacao: Mapped[dict] = mapped_column(JSON)          # motor.Criacao
    equipamento: Mapped[dict] = mapped_column(JSON)      # motor.Equipamento
    cofre: Mapped[list] = mapped_column(JSON)            # ids das cartas no cofre
    sessao: Mapped[dict] = mapped_column(JSON)           # marcas atuais (motor.Sessao)
    # níveis planejados (motor.SubidaDeNivel), vindos de uma cópia para mesa de nível menor
    plano: Mapped[list] = mapped_column(JSON, default=list, server_default="[]")
    foto: Mapped[str | None] = mapped_column(String(36), nullable=True)   # id em `imagens`
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora,
                                                    onupdate=_agora)

    dono: Mapped[UsuarioTabela] = relationship(back_populates="personagens")
    mesa: Mapped[MesaTabela | None] = relationship(back_populates="personagens")
    subidas: Mapped[list["SubidaTabela"]] = relationship(
        back_populates="personagem", order_by="SubidaTabela.nivel",
        cascade="all, delete-orphan", passive_deletes=True)


class ImagemTabela(Base):
    """Foto enviada (personagem, NPC ou inimigo). Fica no banco para funcionar
    igual no SQLite e no PostgreSQL, sem pasta de arquivos para configurar."""

    __tablename__ = "imagens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dono_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(32))          # image/jpeg, image/png, image/webp
    dados: Mapped[bytes] = mapped_column(LargeBinary)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)


class SubidaTabela(Base):
    __tablename__ = "subidas_de_nivel"
    __table_args__ = (UniqueConstraint("personagem_id", "nivel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    personagem_id: Mapped[str] = mapped_column(
        ForeignKey("personagens.id", ondelete="CASCADE"), index=True)
    nivel: Mapped[int] = mapped_column(Integer)
    dados: Mapped[dict] = mapped_column(JSON)            # motor.SubidaDeNivel

    personagem: Mapped[PersonagemTabela] = relationship(back_populates="subidas")
