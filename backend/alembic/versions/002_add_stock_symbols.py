"""Add StockSymbol table for symbol search

Revision ID: 002_stock_symbols
Revises: 001_superuser_config
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '002_stock_symbols'
down_revision: Union[str, None] = '001_superuser_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if stock_symbols table already exists before creating
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'stock_symbols' not in tables:
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
    else:
        print("Table 'stock_symbols' already exists, skipping...")
        # Check and create indexes if they don't exist
        indexes = [idx['name'] for idx in inspector.get_indexes('stock_symbols')]
        if 'ix_stock_symbols_name' not in indexes:
            op.create_index('ix_stock_symbols_name', 'stock_symbols', ['name'])
        if 'ix_stock_symbols_market_active' not in indexes:
            op.create_index('ix_stock_symbols_market_active', 'stock_symbols', ['market', 'is_active'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_stock_symbols_market_active', table_name='stock_symbols')
    op.drop_index('ix_stock_symbols_name', table_name='stock_symbols')
    
    # Drop table
    op.drop_table('stock_symbols')

