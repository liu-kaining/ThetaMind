"""Add subscription_type and daily_image_usage to users

Revision ID: 007_subscription_type_image_usage
Revises: 006_strategy_hash
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_sub_type_img'
down_revision: Union[str, None] = '006_strategy_hash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add subscription_type column if it doesn't exist
    if 'subscription_type' not in columns:
        op.add_column(
            'users',
            sa.Column('subscription_type', sa.String(20), nullable=True)
        )
    
    # Add daily_image_usage column if it doesn't exist
    if 'daily_image_usage' not in columns:
        op.add_column(
            'users',
            sa.Column('daily_image_usage', sa.Integer(), nullable=False, server_default='0')
        )
    
    # Create index on subscription_type if it doesn't exist
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'ix_users_subscription_type' not in indexes:
        op.create_index(
            'ix_users_subscription_type',
            'users',
            ['subscription_type'],
            unique=False
        )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_users_subscription_type', table_name='users')
    
    # Drop columns
    op.drop_column('users', 'daily_image_usage')
    op.drop_column('users', 'subscription_type')

