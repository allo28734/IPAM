"""Add integration_providers table and source_integration_id FK

Revision ID: i7158gf200d4
Revises: h6047fe199c3
Create Date: 2026-05-06 15:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'i7158gf200d4'
down_revision = 'h6047fe199c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create integration_providers table
    op.create_table(
        'integration_providers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('vendor', sa.String(length=50), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('api_key_encrypted', sa.String(length=1000), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('password_encrypted', sa.String(length=1000), nullable=True),
        sa.Column('extra_config', sa.JSON(), nullable=True),
        sa.Column('auto_create_subnets', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(length=50), nullable=False, server_default='never'),
        sa.Column('last_sync_error', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_integration_providers')),
        sa.UniqueConstraint('name', name=op.f('uq_integration_providers_name')),
    )
    op.create_index(op.f('ix_integration_providers_name'), 'integration_providers', ['name'], unique=False)
    op.create_index(op.f('ix_integration_providers_vendor'), 'integration_providers', ['vendor'], unique=False)

    # Add source_integration_id FK to ip_addresses
    op.add_column(
        'ip_addresses',
        sa.Column(
            'source_integration_id',
            sa.Integer(),
            sa.ForeignKey('integration_providers.id', ondelete='SET NULL', name='fk_ip_addresses_source_integration_id_integration_providers'),
            nullable=True,
        )
    )
    op.create_index(
        op.f('ix_ip_addresses_source_integration_id'),
        'ip_addresses', ['source_integration_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_ip_addresses_source_integration_id'), table_name='ip_addresses')
    op.drop_column('ip_addresses', 'source_integration_id')
    op.drop_index(op.f('ix_integration_providers_vendor'), table_name='integration_providers')
    op.drop_index(op.f('ix_integration_providers_name'), table_name='integration_providers')
    op.drop_table('integration_providers')
