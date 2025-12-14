"""add_generated_images_table

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_generated_images'
down_revision: Union[str, None] = '003_task_execution_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create generated_images table
    op.create_table(
        'generated_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('base64_data', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index(op.f('ix_generated_images_user_id'), 'generated_images', ['user_id'], unique=False)
    op.create_index(op.f('ix_generated_images_task_id'), 'generated_images', ['task_id'], unique=False)
    op.create_index(op.f('ix_generated_images_created_at'), 'generated_images', ['created_at'], unique=False)
    op.create_index(op.f('ix_generated_images_user_created'), 'generated_images', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_generated_images_user_created'), table_name='generated_images')
    op.drop_index(op.f('ix_generated_images_created_at'), table_name='generated_images')
    op.drop_index(op.f('ix_generated_images_task_id'), table_name='generated_images')
    op.drop_index(op.f('ix_generated_images_user_id'), table_name='generated_images')
    
    # Drop table
    op.drop_table('generated_images')

