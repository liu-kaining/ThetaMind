"""Create strategies, ai_reports, and payment_events tables if missing

These tables were defined in models.py but had no corresponding migration,
causing fresh `alembic upgrade head` on an empty database to miss them.

Revision ID: 013_create_missing_core
Revises: 012_drop_daily_anomaly
Create Date: 2026-02-21 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "013_create_missing_core"
down_revision: Union[str, None] = "012_drop_daily_anomaly"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("strategies"):
        op.create_table(
            "strategies",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("legs_json", JSONB(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_strategies_user_id", "strategies", ["user_id"])

    if not _table_exists("ai_reports"):
        op.create_table(
            "ai_reports",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("report_content", sa.Text(), nullable=False),
            sa.Column("model_used", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_ai_reports_user_id", "ai_reports", ["user_id"])

    if not _table_exists("payment_events"):
        op.create_table(
            "payment_events",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("lemon_squeezy_id", sa.String(255), nullable=False, unique=True),
            sa.Column("event_name", sa.String(100), nullable=False),
            sa.Column("payload", JSONB(), nullable=False),
            sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_payment_events_lemon_squeezy_id", "payment_events", ["lemon_squeezy_id"])


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS payment_events"))
    op.execute(sa.text("DROP TABLE IF EXISTS ai_reports"))
    op.execute(sa.text("DROP TABLE IF EXISTS strategies"))
