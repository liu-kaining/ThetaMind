"""Add is_superuser to users and system_configs table

Revision ID: 001_superuser_config
Revises: 
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_superuser_config'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_superuser column to users table
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create system_configs table
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    )
    op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)


def downgrade() -> None:
    # Drop system_configs table
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_table('system_configs')
    
    # Remove is_superuser column from users table
    op.drop_column('users', 'is_superuser')

