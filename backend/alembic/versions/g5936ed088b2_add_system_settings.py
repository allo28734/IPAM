"""add system settings

Revision ID: g5936ed088b2
Revises: f4825dc977a1
Create Date: 2026-05-05 16:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g5936ed088b2'
down_revision: Union[str, None] = 'f4825dc977a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('base_domain', sa.String(), nullable=True),
    sa.Column('sso_client_id', sa.String(), nullable=True),
    sa.Column('sso_client_secret', sa.String(), nullable=True),
    sa.Column('sso_discovery_url', sa.String(), nullable=True),
    sa.Column('sso_admin_group', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_settings_id'), table_name='system_settings')
    op.drop_table('system_settings')
