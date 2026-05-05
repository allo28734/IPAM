"""Add discovery fields

Revision ID: f4825dc977a1
Revises: e145ae9795ae
Create Date: 2026-05-05 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4825dc977a1'
down_revision: Union[str, None] = 'e145ae9795ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ip_addresses', sa.Column('mac_address', sa.String(length=17), nullable=True))
    op.add_column('ip_addresses', sa.Column('vendor', sa.String(length=255), nullable=True))
    op.add_column('ip_addresses', sa.Column('os_guess', sa.String(length=255), nullable=True))
    op.add_column('ip_addresses', sa.Column('device_type', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('ip_addresses', 'device_type')
    op.drop_column('ip_addresses', 'os_guess')
    op.drop_column('ip_addresses', 'vendor')
    op.drop_column('ip_addresses', 'mac_address')
