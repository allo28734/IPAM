"""add ipv6 support

Revision ID: e145ae9795ae
Revises: ba66eac6973b
Create Date: 2026-04-30 16:13:40.787724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e145ae9795ae'
down_revision: Union[str, Sequence[str], None] = 'ba66eac6973b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add ip_version to subnets and alter columns
    with op.batch_alter_table('subnets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ip_version', sa.Integer(), nullable=False, server_default='4'))
        batch_op.alter_column('cidr', type_=sa.String(length=45), existing_type=sa.String(length=18))
        batch_op.alter_column('gateway', type_=sa.String(length=45), existing_type=sa.String(length=15))

    # Add ip_version to ip_addresses and alter address column
    with op.batch_alter_table('ip_addresses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ip_version', sa.Integer(), nullable=False, server_default='4'))
        batch_op.alter_column('address', type_=sa.String(length=45), existing_type=sa.String(length=15))


def downgrade() -> None:
    """Downgrade schema."""
    # Revert ip_addresses
    with op.batch_alter_table('ip_addresses', schema=None) as batch_op:
        batch_op.alter_column('address', type_=sa.String(length=15), existing_type=sa.String(length=45))
        batch_op.drop_column('ip_version')

    # Revert subnets
    with op.batch_alter_table('subnets', schema=None) as batch_op:
        batch_op.alter_column('gateway', type_=sa.String(length=15), existing_type=sa.String(length=45))
        batch_op.alter_column('cidr', type_=sa.String(length=18), existing_type=sa.String(length=45))
        batch_op.drop_column('ip_version')
