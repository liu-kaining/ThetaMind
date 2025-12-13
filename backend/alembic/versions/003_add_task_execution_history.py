"""Add execution history and details to tasks

Revision ID: 003_task_execution_history
Revises: 002_add_stock_symbols
Create Date: 2025-12-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '003_task_execution_history'
down_revision: Union[str, None] = '002_stock_symbols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tasks')]
    
    # Add execution_history column
    if 'execution_history' not in columns:
        op.add_column('tasks', sa.Column('execution_history', postgresql.JSONB, nullable=True))
    else:
        print("Column 'execution_history' already exists in 'tasks' table, skipping...")
    
    # Add prompt_used column
    if 'prompt_used' not in columns:
        op.add_column('tasks', sa.Column('prompt_used', sa.Text, nullable=True))
    else:
        print("Column 'prompt_used' already exists in 'tasks' table, skipping...")
    
    # Add model_used column
    if 'model_used' not in columns:
        op.add_column('tasks', sa.Column('model_used', sa.String(100), nullable=True))
    else:
        print("Column 'model_used' already exists in 'tasks' table, skipping...")
    
    # Add started_at column
    if 'started_at' not in columns:
        op.add_column('tasks', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    else:
        print("Column 'started_at' already exists in 'tasks' table, skipping...")
    
    # Add retry_count column
    if 'retry_count' not in columns:
        op.add_column('tasks', sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'))
    else:
        print("Column 'retry_count' already exists in 'tasks' table, skipping...")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tasks')]
    
    if 'retry_count' in columns:
        op.drop_column('tasks', 'retry_count')
    if 'started_at' in columns:
        op.drop_column('tasks', 'started_at')
    if 'model_used' in columns:
        op.drop_column('tasks', 'model_used')
    if 'prompt_used' in columns:
        op.drop_column('tasks', 'prompt_used')
    if 'execution_history' in columns:
        op.drop_column('tasks', 'execution_history')

