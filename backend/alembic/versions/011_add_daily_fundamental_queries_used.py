"""Add daily_fundamental_queries_used to users

Revision ID: 011_fundamental_queries
Revises: 010_add_anomaly_table
Create Date: 2026-02-06 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_fundamental_queries"
down_revision: Union[str, None] = "010_add_anomaly_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("daily_fundamental_queries_used", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "daily_fundamental_queries_used")
