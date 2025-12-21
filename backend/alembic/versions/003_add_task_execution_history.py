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
    tables = inspector.get_table_names()
    
    # Create tasks table if it doesn't exist
    if 'tasks' not in tables:
        op.create_table(
            'tasks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('task_type', sa.String(50), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
            sa.Column('result_ref', sa.String(255), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('task_metadata', postgresql.JSONB, nullable=True),
            # Execution details (included in initial creation)
            sa.Column('execution_history', postgresql.JSONB, nullable=True),
            sa.Column('prompt_used', sa.Text(), nullable=True),
            sa.Column('model_used', sa.String(100), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        )
        op.create_index(op.f('ix_tasks_user_id'), 'tasks', ['user_id'], unique=False)
        op.create_index(op.f('ix_tasks_task_type'), 'tasks', ['task_type'], unique=False)
        op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
        op.create_index(op.f('ix_tasks_user_status'), 'tasks', ['user_id', 'status'], unique=False)
        op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'], unique=False)
    else:
        # Table exists, add missing columns
        columns = [col['name'] for col in inspector.get_columns('tasks')]
        
        if 'execution_history' not in columns:
            op.add_column('tasks', sa.Column('execution_history', postgresql.JSONB, nullable=True))
        if 'prompt_used' not in columns:
            op.add_column('tasks', sa.Column('prompt_used', sa.Text(), nullable=True))
        if 'model_used' not in columns:
            op.add_column('tasks', sa.Column('model_used', sa.String(100), nullable=True))
        if 'started_at' not in columns:
            op.add_column('tasks', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        if 'retry_count' not in columns:
            op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))


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

