"""npcs: dono e visibilidade

Cada NPC passa a ter dono (quem criou) e visibilidade (privado, mestres ou
todos). Os que já existiam ficam com quem criou a mesa como dono e
visibilidade "mestres" (como antes); os que estavam revelados, "todos".

Revision ID: 9aef996c7f88
Revises: 45a719f76e56
Create Date: 2026-10-16 00:33:58.462177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9aef996c7f88'
down_revision: Union[str, Sequence[str], None] = '45a719f76e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # add_column direto (sem batch: recriar a tabela no SQLite apagaria em cascata)
    op.add_column('npcs', sa.Column('dono_id', sa.String(length=36), nullable=True))
    op.add_column('npcs', sa.Column('visibilidade', sa.String(length=10), server_default='mestres', nullable=False))
    op.create_index(op.f('ix_npcs_dono_id'), 'npcs', ['dono_id'], unique=False)
    op.execute("UPDATE npcs SET dono_id = (SELECT criador_id FROM mesas WHERE mesas.id = npcs.mesa_id)")
    op.execute("UPDATE npcs SET visibilidade = 'todos' WHERE revelado")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_npcs_dono_id'), table_name='npcs')
    with op.batch_alter_table('npcs', schema=None) as batch_op:
        batch_op.drop_column('visibilidade')
        batch_op.drop_column('dono_id')
