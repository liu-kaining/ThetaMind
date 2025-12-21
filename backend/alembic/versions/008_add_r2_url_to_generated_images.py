"""add r2_url to generated_images

Revision ID: 008_r2_url
Revises: 007_sub_type_img
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_r2_url'
down_revision: Union[str, None] = '007_sub_type_img'
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
    
    columns = [col for col in inspector.get_columns('generated_images')]
    column_names = [col['name'] for col in columns]
    
    # Add r2_url column if it doesn't exist
    if 'r2_url' not in column_names:
        op.add_column(
            'generated_images',
            sa.Column('r2_url', sa.String(512), nullable=True)
        )
    
    # Create index on r2_url if it doesn't exist
    indexes = [idx['name'] for idx in inspector.get_indexes('generated_images')]
    if 'ix_generated_images_r2_url' not in indexes:
        op.create_index(
            'ix_generated_images_r2_url',
            'generated_images',
            ['r2_url'],
            unique=False
        )
    
    # Make base64_data nullable if it's not already nullable
    base64_col = next((col for col in columns if col['name'] == 'base64_data'), None)
    if base64_col and not base64_col['nullable']:
        op.alter_column(
            'generated_images',
            'base64_data',
            existing_type=sa.Text(),
            nullable=True
        )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_generated_images_r2_url', table_name='generated_images')
    
    # Drop r2_url column
    op.drop_column('generated_images', 'r2_url')
    
    # Make base64_data non-nullable again (if needed)
    # Note: This might fail if there are NULL values, so we'll keep it nullable
    # op.alter_column(
    #     'generated_images',
    #     'base64_data',
    #     existing_type=sa.Text(),
    #     nullable=False
    # )

