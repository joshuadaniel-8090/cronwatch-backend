"""rename pings created_at to received_at

Revision ID: 6b4d8279c5fb
Revises: a54ed6feb210
Create Date: 2026-04-25 23:46:10.976373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b4d8279c5fb'
down_revision: Union[str, None] = 'a54ed6feb210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('pings', 'created_at', new_column_name='received_at')


def downgrade() -> None:
    op.alter_column('pings', 'received_at', new_column_name='created_at')
