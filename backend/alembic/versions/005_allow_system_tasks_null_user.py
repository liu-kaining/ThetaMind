"""Allow system tasks with null user_id

Revision ID: 005_allow_system_tasks
Revises: 004_add_generated_images_table
Create Date: 2024-12-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_allow_system_tasks'
down_revision = '004_generated_images'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow user_id to be NULL for system tasks."""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col for col in inspector.get_columns('tasks') if col['name'] == 'user_id']
    
    if not columns:
        # tasks table or user_id column doesn't exist, skip
        return
    
    user_id_col = columns[0]
    # Check if column is already nullable
    if user_id_col['nullable']:
        # Already nullable, skip
        return
    
    # Drop the foreign key constraint temporarily (if it exists)
    try:
        op.drop_constraint('tasks_user_id_fkey', 'tasks', type_='foreignkey')
    except Exception:
        # Constraint might not exist or have different name, continue
        pass
    
    # Alter column to allow NULL
    op.alter_column('tasks', 'user_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=True,
                    existing_nullable=False)


def downgrade() -> None:
    """Revert to requiring user_id (not null)."""
    # First, delete any tasks with NULL user_id (system tasks)
    op.execute("DELETE FROM tasks WHERE user_id IS NULL")
    
    # Drop FK constraint
    op.drop_constraint('tasks_user_id_fkey', 'tasks', type_='foreignkey', if_exists=True)
    
    # Alter column to disallow NULL
    op.alter_column('tasks', 'user_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False,
                    existing_nullable=True)
    
    # Re-add foreign key constraint
    op.create_foreign_key('tasks_user_id_fkey', 'tasks', 'users', ['user_id'], ['id'])

