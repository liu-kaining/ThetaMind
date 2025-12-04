"""Add StockSymbol table for symbol search

Revision ID: 002_stock_symbols
Revises: 001_superuser_config
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_stock_symbols'
down_revision: Union[str, None] = '001_superuser_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create stock_symbols table
    op.create_table(
        'stock_symbols',
        sa.Column('symbol', sa.String(20), primary_key=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('market', sa.String(10), nullable=False, server_default='US'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for fast search
    op.create_index('ix_stock_symbols_name', 'stock_symbols', ['name'])
    op.create_index('ix_stock_symbols_market_active', 'stock_symbols', ['market', 'is_active'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_stock_symbols_market_active', table_name='stock_symbols')
    op.drop_index('ix_stock_symbols_name', table_name='stock_symbols')
    
    # Drop table
    op.drop_table('stock_symbols')

