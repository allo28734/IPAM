"""Add enable_network_discovery to system_settings

Revision ID: h6047fe199c3
Revises: g5936ed088b2
Create Date: 2026-05-05 20:42:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h6047fe199c3'
down_revision = 'g5936ed088b2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add enable_network_discovery column with default True
    op.add_column('system_settings', sa.Column('enable_network_discovery', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('system_settings', 'enable_network_discovery')
