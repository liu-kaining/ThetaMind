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
    # Add subscription_type column to users table (monthly/yearly)
    op.add_column(
        'users',
        sa.Column('subscription_type', sa.String(20), nullable=True)
    )
    
    # Add daily_image_usage column to users table
    op.add_column(
        'users',
        sa.Column('daily_image_usage', sa.Integer(), nullable=False, server_default='0')
    )
    
    # Create index on subscription_type for fast lookups
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

