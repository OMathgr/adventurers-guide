"""As migrações do Alembic precisam criar exatamente as tabelas de api/tabelas.py."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from api.db import Base, criar_engine


def test_migracoes_batem_com_as_tabelas(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migrado.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = criar_engine(url)
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
    engine.dispose()
    assert diferencas == [], "Gere uma migração: alembic revision --autogenerate -m '...'"
