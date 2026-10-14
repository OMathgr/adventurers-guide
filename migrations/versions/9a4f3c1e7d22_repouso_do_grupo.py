"""repouso do grupo (aberto pelo mestre, escolhido pelos jogadores)

Revision ID: 9a4f3c1e7d22
Revises: 7c1d5e2a9b40
Create Date: 2026-10-14 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a4f3c1e7d22'
down_revision: Union[str, Sequence[str], None] = '7c1d5e2a9b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('repousos',
    sa.Column('versao', sa.Integer(), server_default='1', nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('mesa_id', sa.String(length=36), nullable=False),
    sa.Column('sessao_id', sa.String(length=36), nullable=False),
    sa.Column('tipo', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('participantes', sa.JSON(), nullable=False),
    sa.Column('escolhas', sa.JSON(), nullable=False),
    sa.Column('resultado', sa.JSON(), nullable=True),
    sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['mesa_id'], ['mesas.id'], name=op.f('fk_repousos_mesa_id_mesas'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sessao_id'], ['sessoes.id'], name=op.f('fk_repousos_sessao_id_sessoes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_repousos'))
    )
    op.create_index(op.f('ix_repousos_mesa_id'), 'repousos', ['mesa_id'], unique=False)
    op.create_index(op.f('ix_repousos_sessao_id'), 'repousos', ['sessao_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_repousos_sessao_id'), table_name='repousos')
    op.drop_index(op.f('ix_repousos_mesa_id'), table_name='repousos')
    op.drop_table('repousos')
