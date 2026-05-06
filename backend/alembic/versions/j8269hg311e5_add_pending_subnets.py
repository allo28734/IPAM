"""Add pending_subnets table

Revision ID: j8269hg311e5
Revises: i7158gf200d4
Create Date: 2026-05-06 16:28:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'j8269hg311e5'
down_revision = 'i7158gf200d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pending_subnets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cidr', sa.String(length=45), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('gateway', sa.String(length=45), nullable=True),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('ip_version', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column(
            'provider_id', sa.Integer(),
            sa.ForeignKey('integration_providers.id', ondelete='CASCADE',
                          name='fk_pending_subnets_provider_id_integration_providers'),
            nullable=False,
        ),
        sa.Column('vendor', sa.String(length=50), nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_pending_subnets')),
    )
    op.create_index(op.f('ix_pending_subnets_cidr'), 'pending_subnets', ['cidr'], unique=False)
    op.create_index(op.f('ix_pending_subnets_provider_id'), 'pending_subnets', ['provider_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pending_subnets_provider_id'), table_name='pending_subnets')
    op.drop_index(op.f('ix_pending_subnets_cidr'), table_name='pending_subnets')
    op.drop_table('pending_subnets')
