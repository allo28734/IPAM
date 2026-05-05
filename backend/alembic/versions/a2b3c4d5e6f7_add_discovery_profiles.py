"""Add discovery profiles

Revision ID: a2b3c4d5e6f7
Revises: f4825dc977a1
Create Date: 2026-05-05 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f4825dc977a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discovery_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('auth_protocol', sa.String(length=50), nullable=True),
        sa.Column('auth_password', sa.String(length=500), nullable=True),
        sa.Column('priv_protocol', sa.String(length=50), nullable=True),
        sa.Column('priv_password', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_discovery_profiles_name'), 'discovery_profiles', ['name'], unique=True)
    
    op.add_column('subnets', sa.Column('discovery_profile_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_subnets_discovery_profile_id'), 'subnets', ['discovery_profile_id'], unique=False)
    # The foreign key name is required for SQLite and Postgres, we just use a basic one
    op.create_foreign_key('fk_subnets_discovery_profile_id', 'subnets', 'discovery_profiles', ['discovery_profile_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_subnets_discovery_profile_id', 'subnets', type_='foreignkey')
    op.drop_index(op.f('ix_subnets_discovery_profile_id'), table_name='subnets')
    op.drop_column('subnets', 'discovery_profile_id')
    
    op.drop_index(op.f('ix_discovery_profiles_name'), table_name='discovery_profiles')
    op.drop_table('discovery_profiles')
