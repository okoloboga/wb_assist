# Database Indexes Recommendations

## Обзор

Рекомендации по индексам для оптимизации производительности запросов аналитического дашборда.

## Критические индексы

### 1. WBStock (Остатки)

**Текущие запросы:**
- Фильтрация по `cabinet_id`, `warehouse_name`, `size`
- Поиск по `name`, `article`
- Сортировка по `quantity`

**Рекомендуемые индексы:**

```sql
-- Основной индекс для фильтрации
CREATE INDEX idx_wb_stock_cabinet_warehouse_size 
ON wb_stocks(cabinet_id, warehouse_name, size) 
WHERE quantity > 0;

-- Индекс для поиска по названию
CREATE INDEX idx_wb_stock_name_trgm 
ON wb_stocks USING gin(name gin_trgm_ops);

-- Индекс для поиска по артикулу
CREATE INDEX idx_wb_stock_article_trgm 
ON wb_stocks USING gin(article gin_trgm_ops);

-- Индекс для группировки по nm_id
CREATE INDEX idx_wb_stock_nm_id_cabinet 
ON wb_stocks(nm_id, cabinet_id) 
WHERE quantity > 0;

-- Индекс для быстрого подсчета остатков
CREATE INDEX idx_wb_stock_quantity 
ON wb_stocks(cabinet_id, quantity) 
WHERE quantity > 0;
```

### 2. WBProduct (Товары)

**Текущие запросы:**
- JOIN с WBStock по `nm_id` и `cabinet_id`
- Поиск по `name`, `vendor_code`

**Рекомендуемые индексы:**

```sql
-- Основной индекс для JOIN
CREATE INDEX idx_wb_product_nm_id_cabinet 
ON wb_products(nm_id, cabinet_id);

-- Индекс для поиска по названию
CREATE INDEX idx_wb_product_name_trgm 
ON wb_products USING gin(name gin_trgm_ops);

-- Индекс для поиска по артикулу
CREATE INDEX idx_wb_product_vendor_code_trgm 
ON wb_products USING gin(vendor_code gin_trgm_ops);
```

### 3. WBOrder (Заказы)

**Текущие запросы:**
- Фильтрация по `cabinet_id`, `order_date`, `status`
- Группировка по `nm_id`
- Сортировка по `order_date DESC`

**Рекомендуемые индексы:**

```sql
-- Основной индекс для аналитики
CREATE INDEX idx_wb_order_cabinet_date_status 
ON wb_orders(cabinet_id, order_date DESC, status);

-- Индекс для группировки по товарам
CREATE INDEX idx_wb_order_nm_id_cabinet_date 
ON wb_orders(nm_id, cabinet_id, order_date DESC) 
WHERE status != 'canceled';

-- Индекс для подсчета активных заказов
CREATE INDEX idx_wb_order_active 
ON wb_orders(cabinet_id, order_date DESC) 
WHERE status != 'canceled';

-- Индекс для отмененных заказов (по дате обновления)
CREATE INDEX idx_wb_order_canceled_updated 
ON wb_orders(cabinet_id, updated_at DESC) 
WHERE status = 'canceled';
```

### 4. WBSales (Продажи)

**Текущие запросы:**
- Фильтрация по `cabinet_id`, `sale_date`, `type`
- Группировка по `nm_id`
- Подсчет выкупов и возвратов

**Рекомендуемые индексы:**

```sql
-- Основной индекс для аналитики
CREATE INDEX idx_wb_sales_cabinet_date_type 
ON wb_sales(cabinet_id, sale_date DESC, type) 
WHERE is_cancel = false OR is_cancel IS NULL;

-- Индекс для группировки по товарам
CREATE INDEX idx_wb_sales_nm_id_cabinet_date 
ON wb_sales(nm_id, cabinet_id, sale_date DESC) 
WHERE is_cancel = false OR is_cancel IS NULL;

-- Индекс для подсчета выкупов
CREATE INDEX idx_wb_sales_buyouts 
ON wb_sales(cabinet_id, sale_date DESC) 
WHERE type = 'buyout' AND (is_cancel = false OR is_cancel IS NULL);

-- Индекс для подсчета возвратов
CREATE INDEX idx_wb_sales_returns 
ON wb_sales(cabinet_id, sale_date DESC) 
WHERE type = 'return' AND (is_cancel = false OR is_cancel IS NULL);
```

### 5. WBReview (Отзывы)

**Текущие запросы:**
- Фильтрация по `cabinet_id`, `nm_id`, `rating`
- Сортировка по `created_date DESC`

**Рекомендуемые индексы:**

```sql
-- Основной индекс для отзывов
CREATE INDEX idx_wb_review_cabinet_date 
ON wb_reviews(cabinet_id, created_date DESC);

-- Индекс для фильтрации по рейтингу
CREATE INDEX idx_wb_review_cabinet_rating 
ON wb_reviews(cabinet_id, rating) 
WHERE rating IS NOT NULL;

-- Индекс для группировки по товарам
CREATE INDEX idx_wb_review_nm_id_cabinet 
ON wb_reviews(nm_id, cabinet_id, rating) 
WHERE rating IS NOT NULL;
```

## Расширение PostgreSQL для полнотекстового поиска

Для эффективного поиска по текстовым полям необходимо установить расширение `pg_trgm`:

```sql
-- Установка расширения
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Проверка установки
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

## Миграция для создания индексов

Создайте файл миграции Alembic:

```bash
alembic revision -m "add_analytics_dashboard_indexes"
```

**Содержимое миграции:**

```python
"""add_analytics_dashboard_indexes

Revision ID: xxxxx
Revises: xxxxx
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxxx'
down_revision = 'xxxxx'
branch_labels = None
depends_on = None


def upgrade():
    # Установка расширения pg_trgm
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # WBStock индексы
    op.create_index(
        'idx_wb_stock_cabinet_warehouse_size',
        'wb_stocks',
        ['cabinet_id', 'warehouse_name', 'size'],
        postgresql_where=sa.text('quantity > 0')
    )
    
    op.execute('''
        CREATE INDEX idx_wb_stock_name_trgm 
        ON wb_stocks USING gin(name gin_trgm_ops)
    ''')
    
    op.execute('''
        CREATE INDEX idx_wb_stock_article_trgm 
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
        CREATE INDEX idx_wb_product_name_trgm 
        ON wb_products USING gin(name gin_trgm_ops)
    ''')
    
    op.execute('''
        CREATE INDEX idx_wb_product_vendor_code_trgm 
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
```

## Анализ производительности

### Проверка использования индексов

```sql
-- Проверка использования индекса для запроса остатков
EXPLAIN ANALYZE
SELECT * FROM wb_stocks 
WHERE cabinet_id = 1 
  AND warehouse_name = 'Коледино' 
  AND quantity > 0
ORDER BY nm_id;

-- Проверка использования индекса для поиска
EXPLAIN ANALYZE
SELECT * FROM wb_stocks 
WHERE cabinet_id = 1 
  AND name ILIKE '%футболка%';

-- Проверка использования индекса для аналитики заказов
EXPLAIN ANALYZE
SELECT nm_id, COUNT(*), SUM(total_price)
FROM wb_orders
WHERE cabinet_id = 1
  AND order_date >= '2025-10-26'
  AND order_date < '2025-11-26'
  AND status != 'canceled'
GROUP BY nm_id
ORDER BY COUNT(*) DESC
LIMIT 10;
```

### Мониторинг неиспользуемых индексов

```sql
-- Проверка неиспользуемых индексов
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE 'pg_toast%'
ORDER BY schemaname, tablename;
```

## Ожидаемые улучшения

- **Запросы остатков**: ускорение в 5-10 раз
- **Поиск по тексту**: ускорение в 10-20 раз
- **Аналитика заказов**: ускорение в 3-5 раз
- **Группировка по товарам**: ускорение в 5-10 раз

## Рекомендации по обслуживанию

1. **Регулярная очистка:**
   ```sql
   VACUUM ANALYZE wb_stocks;
   VACUUM ANALYZE wb_orders;
   VACUUM ANALYZE wb_sales;
   ```

2. **Обновление статистики:**
   ```sql
   ANALYZE wb_stocks;
   ANALYZE wb_orders;
   ANALYZE wb_sales;
   ```

3. **Мониторинг размера индексов:**
   ```sql
   SELECT 
       tablename,
       indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) as index_size
   FROM pg_stat_user_indexes
   WHERE schemaname = 'public'
   ORDER BY pg_relation_size(indexrelid) DESC;
   ```

## Changelog

### 2025-11-25 - Initial recommendations
- Добавлены индексы для WBStock, WBProduct, WBOrder, WBSales, WBReview
- Добавлена поддержка полнотекстового поиска через pg_trgm
- Создана миграция Alembic для применения индексов
