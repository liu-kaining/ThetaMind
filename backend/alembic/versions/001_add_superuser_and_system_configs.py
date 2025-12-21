"""Add is_superuser to users and system_configs table

Revision ID: 001_superuser_config
Revises: 
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '001_superuser_config'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Create users table if it doesn't exist (first migration)
    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('email', sa.String(255), nullable=False, unique=True),
            sa.Column('google_sub', sa.String(255), nullable=False, unique=True),
            sa.Column('is_pro', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('subscription_id', sa.String(255), nullable=True),
            sa.Column('subscription_type', sa.String(20), nullable=True),
            sa.Column('plan_expiry_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('daily_ai_usage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('daily_image_usage', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_quota_reset_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)
    else:
        # Table exists, check if is_superuser column exists
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'is_superuser' not in columns:
            op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create system_configs table if it doesn't exist
    if 'system_configs' not in tables:
        op.create_table(
            'system_configs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('key', sa.String(255), nullable=False, unique=True),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('description', sa.String(500), nullable=True),
            sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        )
        op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)


def downgrade() -> None:
    # Drop system_configs table
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_table('system_configs')
    
    # Remove is_superuser column from users table
    op.drop_column('users', 'is_superuser')

