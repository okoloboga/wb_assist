-- Установка расширения pg_trgm для полнотекстового поиска
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- WBStock индексы
CREATE INDEX IF NOT EXISTS idx_wb_stock_cabinet_warehouse_size 
ON wb_stocks(cabinet_id, warehouse_name, size) 
WHERE quantity > 0;

CREATE INDEX IF NOT EXISTS idx_wb_stock_name_trgm 
ON wb_stocks USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_wb_stock_article_trgm 
ON wb_stocks USING gin(article gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_wb_stock_nm_id_cabinet 
ON wb_stocks(nm_id, cabinet_id) 
WHERE quantity > 0;

CREATE INDEX IF NOT EXISTS idx_wb_stock_quantity 
ON wb_stocks(cabinet_id, quantity) 
WHERE quantity > 0;

-- WBProduct индексы
CREATE INDEX IF NOT EXISTS idx_wb_product_nm_id_cabinet 
ON wb_products(nm_id, cabinet_id);

CREATE INDEX IF NOT EXISTS idx_wb_product_name_trgm 
ON wb_products USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_wb_product_vendor_code_trgm 
ON wb_products USING gin(vendor_code gin_trgm_ops);

-- WBOrder индексы
CREATE INDEX IF NOT EXISTS idx_wb_order_cabinet_date_status 
ON wb_orders(cabinet_id, order_date DESC, status);

CREATE INDEX IF NOT EXISTS idx_wb_order_nm_id_cabinet_date 
ON wb_orders(nm_id, cabinet_id, order_date DESC) 
WHERE status != 'canceled';

CREATE INDEX IF NOT EXISTS idx_wb_order_active 
ON wb_orders(cabinet_id, order_date DESC) 
WHERE status != 'canceled';

CREATE INDEX IF NOT EXISTS idx_wb_order_canceled_updated 
ON wb_orders(cabinet_id, updated_at DESC) 
WHERE status = 'canceled';

-- WBSales индексы
CREATE INDEX IF NOT EXISTS idx_wb_sales_cabinet_date_type 
ON wb_sales(cabinet_id, sale_date DESC, type) 
WHERE is_cancel = false OR is_cancel IS NULL;

CREATE INDEX IF NOT EXISTS idx_wb_sales_nm_id_cabinet_date 
ON wb_sales(nm_id, cabinet_id, sale_date DESC) 
WHERE is_cancel = false OR is_cancel IS NULL;

CREATE INDEX IF NOT EXISTS idx_wb_sales_buyouts 
ON wb_sales(cabinet_id, sale_date DESC) 
WHERE type = 'buyout' AND (is_cancel = false OR is_cancel IS NULL);

CREATE INDEX IF NOT EXISTS idx_wb_sales_returns 
ON wb_sales(cabinet_id, sale_date DESC) 
WHERE type = 'return' AND (is_cancel = false OR is_cancel IS NULL);

-- WBReview индексы
CREATE INDEX IF NOT EXISTS idx_wb_review_cabinet_date 
ON wb_reviews(cabinet_id, created_date DESC);

CREATE INDEX IF NOT EXISTS idx_wb_review_cabinet_rating 
ON wb_reviews(cabinet_id, rating) 
WHERE rating IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_wb_review_nm_id_cabinet 
ON wb_reviews(nm_id, cabinet_id, rating) 
WHERE rating IS NOT NULL;
