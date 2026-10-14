"""versao para gravacao simultanea (personagens, mesas, sessoes, encontros, lojas)

Revision ID: 7c1d5e2a9b40
Revises: 20cba93777f4
Create Date: 2026-10-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1d5e2a9b40'
down_revision: Union[str, Sequence[str], None] = '20cba93777f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ALTER TABLE simples (sem "batch"): no SQLite, recriar estas tabelas apagaria em
# cascata o que depende delas (ver docs/ARQUITETURA.md, "Migrações no SQLite").
TABELAS = ('mesas', 'sessoes', 'encontros', 'lojas', 'personagens')


def upgrade() -> None:
    """Upgrade schema."""
    for tabela in TABELAS:
        op.add_column(tabela, sa.Column('versao', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    for tabela in TABELAS:
        op.drop_column(tabela, 'versao')   # SQLite 3.35+ tem DROP COLUMN direto
