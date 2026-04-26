"""fix alerts table columns

Revision ID: a3a0b2e768bb
Revises: 6b4d8279c5fb
Create Date: 2026-04-25 23:49:48.007682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3a0b2e768bb'
down_revision: Union[str, None] = '6b4d8279c5fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('alerts', 'sent_at', new_column_name='triggered_at')
    op.add_column('alerts', sa.Column('is_resolved', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('alerts', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('alerts', 'resolved_at')
    op.drop_column('alerts', 'is_resolved')
    op.alter_column('alerts', 'triggered_at', new_column_name='sent_at')
