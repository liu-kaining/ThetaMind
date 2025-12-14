"""Add strategy_hash to generated_images

Revision ID: 006_strategy_hash
Revises: 005_allow_system_tasks
Create Date: 2024-12-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_strategy_hash'
down_revision: Union[str, None] = '005_allow_system_tasks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add strategy_hash column to generated_images table
    op.add_column(
        'generated_images',
        sa.Column('strategy_hash', sa.String(64), nullable=True)
    )
    
    # Create index on strategy_hash for fast lookups
    op.create_index(
        'ix_generated_images_strategy_hash',
        'generated_images',
        ['strategy_hash'],
        unique=False
    )
    
    # Create composite index for user_id + strategy_hash (for user-specific lookups)
    op.create_index(
        'ix_generated_images_user_strategy_hash',
        'generated_images',
        ['user_id', 'strategy_hash'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_generated_images_user_strategy_hash', table_name='generated_images')
    op.drop_index('ix_generated_images_strategy_hash', table_name='generated_images')
    
    # Drop column
    op.drop_column('generated_images', 'strategy_hash')

