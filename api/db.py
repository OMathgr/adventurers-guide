"""Conexão com o banco.

A URL vem da variável de ambiente DATABASE_URL. Sem ela, usa um arquivo
SQLite local; para PostgreSQL, basta algo como
postgresql+psycopg://usuario:senha@servidor/adventurers (e instalar o driver).
"""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

URL_PADRAO = "sqlite:///./adventurers.db"


class Base(DeclarativeBase):
    pass


def criar_engine(url: str | None = None, **opcoes):
    url = url or os.environ.get("DATABASE_URL", URL_PADRAO)
    if url.startswith("sqlite"):
        opcoes.setdefault("connect_args", {"check_same_thread": False})
    engine = create_engine(url, **opcoes)
    if url.startswith("sqlite"):
        # SQLite só respeita ON DELETE CASCADE com foreign_keys ligado
        @event.listens_for(engine, "connect")
        def _ligar_chaves_estrangeiras(conexao, _):
            conexao.execute("PRAGMA foreign_keys=ON")
    return engine


engine = criar_engine()
FabricaDeSessao = sessionmaker(bind=engine, expire_on_commit=False)


def sessao_do_banco() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão (transação) por requisição."""
    with FabricaDeSessao() as sessao:
        yield sessao
