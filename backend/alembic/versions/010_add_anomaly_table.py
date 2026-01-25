"""Add anomalies table

Revision ID: 010_add_anomaly_table
Revises: 009_last_quota_reset_date
Create Date: 2026-01-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '010_add_anomaly_table'
down_revision: Union[str, None] = '009_last_quota_reset_date'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create anomalies table for anomaly detection tracking."""
    op.create_table(
        'anomalies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('anomaly_type', sa.String(50), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('details', JSONB, nullable=False),
        sa.Column('ai_insight', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_anomalies_symbol', 'anomalies', ['symbol'])
    op.create_index('ix_anomalies_anomaly_type', 'anomalies', ['anomaly_type'])
    op.create_index('ix_anomalies_detected_at', 'anomalies', ['detected_at'])
    op.create_index('ix_anomalies_symbol_detected', 'anomalies', ['symbol', 'detected_at'])
    op.create_index('ix_anomalies_type_detected', 'anomalies', ['anomaly_type', 'detected_at'])


def downgrade() -> None:
    """Drop anomalies table."""
    op.drop_index('ix_anomalies_type_detected', table_name='anomalies')
    op.drop_index('ix_anomalies_symbol_detected', table_name='anomalies')
    op.drop_index('ix_anomalies_detected_at', table_name='anomalies')
    op.drop_index('ix_anomalies_anomaly_type', table_name='anomalies')
    op.drop_index('ix_anomalies_symbol', table_name='anomalies')
    op.drop_table('anomalies')
