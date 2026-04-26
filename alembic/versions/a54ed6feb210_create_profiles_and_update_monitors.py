"""create profiles and update monitors

Revision ID: a54ed6feb210
Revises: 
Create Date: 2026-04-25 23:42:36.661404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a54ed6feb210'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create profiles table
    op.create_table('profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('plan', sa.String(), nullable=True),
    sa.Column('telegram_chat_id', sa.String(), nullable=True),
    sa.Column('alert_email', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # 2. Drop old tables with CASCADE
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    
    # 3. Handle monitors table
    # Drop existing constraints and columns to avoid type mismatch issues
    op.execute("DROP TABLE IF EXISTS pings CASCADE")
    op.execute("DROP TABLE IF EXISTS alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS monitors CASCADE")

    # 4. Re-create monitors table
    op.create_table('monitors',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('interval_seconds', sa.Integer(), nullable=False),
    sa.Column('grace_seconds', sa.Integer(), nullable=True),
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('last_ping_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug'),
    sa.UniqueConstraint('token')
    )

    # 5. Re-create alerts table
    op.create_table('alerts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('monitor_id', sa.UUID(), nullable=False),
    sa.Column('channel', sa.String(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['monitor_id'], ['monitors.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # 6. Re-create pings table
    op.create_table('pings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('monitor_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('ip_address', sa.String(), nullable=True),
    sa.Column('user_agent', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['monitor_id'], ['monitors.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('pings')
    op.drop_table('alerts')
    op.drop_table('monitors')
    op.drop_table('profiles')
