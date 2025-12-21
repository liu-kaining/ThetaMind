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
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'generated_images' not in tables:
        # Table doesn't exist yet, skip
        return
    
    columns = [col['name'] for col in inspector.get_columns('generated_images')]
    
    # Add strategy_hash column if it doesn't exist
    if 'strategy_hash' not in columns:
        op.add_column(
            'generated_images',
            sa.Column('strategy_hash', sa.String(64), nullable=True)
        )
    
    # Create indexes if they don't exist
    indexes = [idx['name'] for idx in inspector.get_indexes('generated_images')]
    
    if 'ix_generated_images_strategy_hash' not in indexes:
        op.create_index(
            'ix_generated_images_strategy_hash',
            'generated_images',
            ['strategy_hash'],
            unique=False
        )
    
    if 'ix_generated_images_user_strategy_hash' not in indexes:
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

