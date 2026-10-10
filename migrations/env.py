"""Migrações do banco (Alembic).

A URL vem da mesma configuração da API (DATABASE_URL, ou o SQLite local).
Gerar uma migração depois de mudar api/tabelas.py:
    alembic revision --autogenerate -m "descrição"
Aplicar:
    alembic upgrade head
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

import api.tabelas  # noqa: F401  (registra as tabelas no metadata)
from api.db import Base, criar_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar (alembic upgrade head --sql)."""
    context.configure(
        url=str(criar_engine().url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = criar_engine(poolclass=pool.NullPool)
    with engine.connect() as connection:
        # render_as_batch: o SQLite não altera colunas no lugar; o Alembic
        # recria a tabela. No PostgreSQL isso não faz diferença.
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
