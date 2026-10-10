"""usuarios e dono dos personagens

Revision ID: 9a3b65539735
Revises: 27a272a09d30
Create Date: 2026-10-10 00:40:28.275845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3b65539735'
down_revision: Union[str, Sequence[str], None] = '27a272a09d30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Personagens criados antes do login não têm dono, e dono_id é obrigatório.
    # Em vez de apagá-los em silêncio, a migração para e explica.
    orfaos = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM personagens")).scalar()
    if orfaos:
        raise RuntimeError(
            f"Há {orfaos} personagem(ns) criado(s) antes do login, sem dono. "
            "Apague-os (DELETE FROM personagens) ou atribua-os a um usuário antes de migrar.")

    op.create_table('usuarios',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('nome', sa.String(length=120), nullable=False),
    sa.Column('senha_hash', sa.String(length=255), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usuarios'))
    )
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_usuarios_email'), ['email'], unique=True)

    with op.batch_alter_table('personagens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dono_id', sa.String(length=36), nullable=False))
        batch_op.create_index(batch_op.f('ix_personagens_dono_id'), ['dono_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_personagens_dono_id_usuarios'), 'usuarios',
                                    ['dono_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    with op.batch_alter_table('personagens', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_personagens_dono_id_usuarios'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_personagens_dono_id'))
        batch_op.drop_column('dono_id')

    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usuarios_email'))

    op.drop_table('usuarios')
