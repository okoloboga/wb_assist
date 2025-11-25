"""add_analytics_dashboard_indexes

Revision ID: 008
Revises: 007
Create Date: 2025-11-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Установка расширения pg_trgm для полнотекстового поиска
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # WBStock индексы
    op.create_index(
        'idx_wb_stock_cabinet_warehouse_size',
        'wb_stocks',
        ['cabinet_id', 'warehouse_name', 'size'],
        postgresql_where=sa.text('quantity > 0')
    )
    
    op.execute('''
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wb_stock_name_trgm 
        ON wb_stocks USING gin(name gin_trgm_ops)
    ''')
    
    op.execute('''
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wb_stock_article_trgm 
        ON wb_stocks USING gin(article gin_trgm_ops)
    ''')
    
    op.create_index(
        'idx_wb_stock_nm_id_cabinet',
        'wb_stocks',
        ['nm_id', 'cabinet_id'],
        postgresql_where=sa.text('quantity > 0')
    )
    
    op.create_index(
        'idx_wb_stock_quantity',
        'wb_stocks',
        ['cabinet_id', 'quantity'],
        postgresql_where=sa.text('quantity > 0')
    )
    
    # WBProduct индексы
    op.create_index(
        'idx_wb_product_nm_id_cabinet',
        'wb_products',
        ['nm_id', 'cabinet_id']
    )
    
    op.execute('''
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wb_product_name_trgm 
        ON wb_products USING gin(name gin_trgm_ops)
    ''')
    
    op.execute('''
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wb_product_vendor_code_trgm 
        ON wb_products USING gin(vendor_code gin_trgm_ops)
    ''')
    
    # WBOrder индексы
    op.create_index(
        'idx_wb_order_cabinet_date_status',
        'wb_orders',
        ['cabinet_id', sa.text('order_date DESC'), 'status']
    )
    
    op.create_index(
        'idx_wb_order_nm_id_cabinet_date',
        'wb_orders',
        ['nm_id', 'cabinet_id', sa.text('order_date DESC')],
        postgresql_where=sa.text("status != 'canceled'")
    )
    
    op.create_index(
        'idx_wb_order_active',
        'wb_orders',
        ['cabinet_id', sa.text('order_date DESC')],
        postgresql_where=sa.text("status != 'canceled'")
    )
    
    op.create_index(
        'idx_wb_order_canceled_updated',
        'wb_orders',
        ['cabinet_id', sa.text('updated_at DESC')],
        postgresql_where=sa.text("status = 'canceled'")
    )
    
    # WBSales индексы
    op.create_index(
        'idx_wb_sales_cabinet_date_type',
        'wb_sales',
        ['cabinet_id', sa.text('sale_date DESC'), 'type'],
        postgresql_where=sa.text('is_cancel = false OR is_cancel IS NULL')
    )
    
    op.create_index(
        'idx_wb_sales_nm_id_cabinet_date',
        'wb_sales',
        ['nm_id', 'cabinet_id', sa.text('sale_date DESC')],
        postgresql_where=sa.text('is_cancel = false OR is_cancel IS NULL')
    )
    
    op.create_index(
        'idx_wb_sales_buyouts',
        'wb_sales',
        ['cabinet_id', sa.text('sale_date DESC')],
        postgresql_where=sa.text("type = 'buyout' AND (is_cancel = false OR is_cancel IS NULL)")
    )
    
    op.create_index(
        'idx_wb_sales_returns',
        'wb_sales',
        ['cabinet_id', sa.text('sale_date DESC')],
        postgresql_where=sa.text("type = 'return' AND (is_cancel = false OR is_cancel IS NULL)")
    )
    
    # WBReview индексы
    op.create_index(
        'idx_wb_review_cabinet_date',
        'wb_reviews',
        ['cabinet_id', sa.text('created_date DESC')]
    )
    
    op.create_index(
        'idx_wb_review_cabinet_rating',
        'wb_reviews',
        ['cabinet_id', 'rating'],
        postgresql_where=sa.text('rating IS NOT NULL')
    )
    
    op.create_index(
        'idx_wb_review_nm_id_cabinet',
        'wb_reviews',
        ['nm_id', 'cabinet_id', 'rating'],
        postgresql_where=sa.text('rating IS NOT NULL')
    )


def downgrade():
    # Удаление индексов в обратном порядке
    op.drop_index('idx_wb_review_nm_id_cabinet', table_name='wb_reviews')
    op.drop_index('idx_wb_review_cabinet_rating', table_name='wb_reviews')
    op.drop_index('idx_wb_review_cabinet_date', table_name='wb_reviews')
    
    op.drop_index('idx_wb_sales_returns', table_name='wb_sales')
    op.drop_index('idx_wb_sales_buyouts', table_name='wb_sales')
    op.drop_index('idx_wb_sales_nm_id_cabinet_date', table_name='wb_sales')
    op.drop_index('idx_wb_sales_cabinet_date_type', table_name='wb_sales')
    
    op.drop_index('idx_wb_order_canceled_updated', table_name='wb_orders')
    op.drop_index('idx_wb_order_active', table_name='wb_orders')
    op.drop_index('idx_wb_order_nm_id_cabinet_date', table_name='wb_orders')
    op.drop_index('idx_wb_order_cabinet_date_status', table_name='wb_orders')
    
    op.drop_index('idx_wb_product_vendor_code_trgm', table_name='wb_products')
    op.drop_index('idx_wb_product_name_trgm', table_name='wb_products')
    op.drop_index('idx_wb_product_nm_id_cabinet', table_name='wb_products')
    
    op.drop_index('idx_wb_stock_quantity', table_name='wb_stocks')
    op.drop_index('idx_wb_stock_nm_id_cabinet', table_name='wb_stocks')
    op.drop_index('idx_wb_stock_article_trgm', table_name='wb_stocks')
    op.drop_index('idx_wb_stock_name_trgm', table_name='wb_stocks')
    op.drop_index('idx_wb_stock_cabinet_warehouse_size', table_name='wb_stocks')
