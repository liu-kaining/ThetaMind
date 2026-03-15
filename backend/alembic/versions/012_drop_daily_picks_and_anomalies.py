"""Drop daily_picks and anomalies tables

Revision ID: 012_drop_daily_anomaly
Revises: 011_fundamental_queries
Create Date: 2026-02-21 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "012_drop_daily_anomaly"
down_revision: Union[str, None] = "011_fundamental_queries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("daily_picks")
    op.drop_table("anomalies")


def downgrade() -> None:
    op.create_table(
        "daily_picks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("content_json", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_daily_picks_date", "daily_picks", ["date"], unique=True)

    op.create_table(
        "anomalies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("ai_insight", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_anomalies_symbol_detected", "anomalies", ["symbol", "detected_at"])
    op.create_index("ix_anomalies_type_detected", "anomalies", ["anomaly_type", "detected_at"])
