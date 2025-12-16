"""
Add indexes on created_at and updated_at for incremental RAG indexing

Revision ID: 009_add_timestamp_indexes
Revises: 008_add_analytics_dashboard_indexes
Create Date: 2025-12-16

Description:
    Добавляет индексы на created_at и updated_at для всех таблиц WB API
    (orders, products, stocks, reviews, sales) для оптимизации инкрементальной
    индексации RAG.

    Также добавляет составные индексы (cabinet_id, created_at/updated_at)
    для максимальной производительности инкрементальных запросов.
"""

from alembic import op


# revision identifiers
revision = '009_add_timestamp_indexes'
down_revision = '008_add_analytics_dashboard_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes on created_at and updated_at."""

    # wb_orders
    op.create_index(
        'idx_wb_orders_created_at',
        'wb_orders',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_orders_updated_at',
        'wb_orders',
        ['updated_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_orders_cabinet_created',
        'wb_orders',
        ['cabinet_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_orders_cabinet_updated',
        'wb_orders',
        ['cabinet_id', 'updated_at'],
        unique=False
    )

    # wb_products
    op.create_index(
        'idx_wb_products_created_at',
        'wb_products',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_products_updated_at',
        'wb_products',
        ['updated_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_products_cabinet_created',
        'wb_products',
        ['cabinet_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_products_cabinet_updated',
        'wb_products',
        ['cabinet_id', 'updated_at'],
        unique=False
    )

    # wb_stocks
    op.create_index(
        'idx_wb_stocks_created_at',
        'wb_stocks',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_stocks_updated_at',
        'wb_stocks',
        ['updated_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_stocks_cabinet_created',
        'wb_stocks',
        ['cabinet_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_stocks_cabinet_updated',
        'wb_stocks',
        ['cabinet_id', 'updated_at'],
        unique=False
    )

    # wb_reviews
    op.create_index(
        'idx_wb_reviews_created_at',
        'wb_reviews',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_reviews_updated_at',
        'wb_reviews',
        ['updated_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_reviews_cabinet_created',
        'wb_reviews',
        ['cabinet_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_reviews_cabinet_updated',
        'wb_reviews',
        ['cabinet_id', 'updated_at'],
        unique=False
    )

    # wb_sales
    op.create_index(
        'idx_wb_sales_created_at',
        'wb_sales',
        ['created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_sales_updated_at',
        'wb_sales',
        ['updated_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_sales_cabinet_created',
        'wb_sales',
        ['cabinet_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'idx_wb_sales_cabinet_updated',
        'wb_sales',
        ['cabinet_id', 'updated_at'],
        unique=False
    )


def downgrade():
    """Remove indexes on created_at and updated_at."""

    # wb_orders
    op.drop_index('idx_wb_orders_cabinet_updated', table_name='wb_orders')
    op.drop_index('idx_wb_orders_cabinet_created', table_name='wb_orders')
    op.drop_index('idx_wb_orders_updated_at', table_name='wb_orders')
    op.drop_index('idx_wb_orders_created_at', table_name='wb_orders')

    # wb_products
    op.drop_index('idx_wb_products_cabinet_updated', table_name='wb_products')
    op.drop_index('idx_wb_products_cabinet_created', table_name='wb_products')
    op.drop_index('idx_wb_products_updated_at', table_name='wb_products')
    op.drop_index('idx_wb_products_created_at', table_name='wb_products')

    # wb_stocks
    op.drop_index('idx_wb_stocks_cabinet_updated', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_cabinet_created', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_updated_at', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_created_at', table_name='wb_stocks')

    # wb_reviews
    op.drop_index('idx_wb_reviews_cabinet_updated', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_cabinet_created', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_updated_at', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_created_at', table_name='wb_reviews')

    # wb_sales
    op.drop_index('idx_wb_sales_cabinet_updated', table_name='wb_sales')
    op.drop_index('idx_wb_sales_cabinet_created', table_name='wb_sales')
    op.drop_index('idx_wb_sales_updated_at', table_name='wb_sales')
    op.drop_index('idx_wb_sales_created_at', table_name='wb_sales')
