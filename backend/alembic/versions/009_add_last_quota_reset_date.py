"""Add last_quota_reset_date to users

Revision ID: 009_last_quota_reset_date
Revises: 008_r2_url
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009_last_quota_reset_date'
down_revision: Union[str, None] = '008_r2_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add last_quota_reset_date column if it doesn't exist
    if 'last_quota_reset_date' not in columns:
        op.add_column(
            'users',
            sa.Column('last_quota_reset_date', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    # Drop column
    op.drop_column('users', 'last_quota_reset_date')

