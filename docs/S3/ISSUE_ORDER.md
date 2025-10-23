

Заказы

Order ID: 2452 ✓
WB Order ID: 96932207636229823973
NM ID (товар): 317313124 ✓
Название: Юбки ✓
Бренд: SLAVALOOK BRAND ✓
Артикул: slavalookbrand_shorts_skirt_vinous
Размер: L ✓
Штрихкод: 2042583874119 ✓
Статус: active ✓
💰 Финансовые данные:
Цена заказа: 3000.0₽ ✓
СПП %: 27.0% ✓
Цена для покупателя: 571.0₽ ✓
Комиссия: 20.0%
Скидка: 74.0%
🏢 Логистика:
Склад от: Рязань (Тюшевское) ✓
Склад к: Кемеровская область ✓
Дата заказа: 2025-10-23 04:56:41+00:00 ✓

⭐ Рейтинг и отзывы:
Средний рейтинг: 4.69 (из WBReview) vs 0.0 (в логе)
Всего отзывов: 26 ✓
Распределение рейтингов:
5 звезд: 21 отзыв
4 звезды: 3 отзыва
3 звезды: 1 отзыв
2 звезды: 1 отзыв

📦 Остатки по размерам:
L: 2 шт. ✓
XL: 18 шт.
M: 0 шт.

📈 Продажи за периоды:
За 7 дней: 4 продажи
За 14 дней: 4 продажи
За 30 дней: 4 продажи

🔍 Статистика по заказам:
Всего заказов: 38
Активные: 21 заказ
Отмененные: 17 заказов

ИСТОЧНИКИ

## 📋 **Источники данных для получения подробной информации о заказе**

### 🗄️ **Основные таблицы базы данных:**

#### 1. **`WBOrder`** - основная таблица заказов
```sql
-- Основные поля заказа
SELECT id, order_id, nm_id, status, name, brand, article, size, 
       barcode, total_price, spp_percent, customer_price, 
       logistics_amount, warehouse_from, warehouse_to, 
       order_date, created_at, updated_at, cabinet_id
FROM wb_orders 
WHERE nm_id = 317313124;
```

#### 2. **`WBReview`** - отзывы и рейтинги
```sql
-- Статистика по отзывам
SELECT 
    AVG(rating) as avg_rating,
    COUNT(*) as total_reviews,
    rating,
    COUNT(*) as rating_count
FROM wb_reviews 
WHERE nm_id = 317313124
GROUP BY rating
ORDER BY rating;
```

#### 3. **`WBStock`** - остатки товаров
```sql
-- Остатки по размерам и складам
SELECT size, warehouse_name, quantity, updated_at
FROM wb_stocks 
WHERE nm_id = 317313124
ORDER BY size, warehouse_name;
```

#### 4. **`WBSales`** - продажи за периоды
```sql
-- Продажи за периоды
SELECT 
    COUNT(*) as sales_7_days
FROM wb_sales 
WHERE nm_id = 317313124 
  AND sale_date >= NOW() - INTERVAL '7 days';
```

### 🐍 **Python код для получения данных:**

#### **1. Подключение к базе данных:**
```python
import sys
sys.path.append('/app')
from app.core.database import get_db
from app.features.wb_api.models import WBOrder, WBProduct, WBStock, WBReview, WBSales
from sqlalchemy.orm import Session
from sqlalchemy import func

db = next(get_db())
```

#### **2. Получение основного заказа:**
```python
# Поиск заказа по ID
order = db.query(WBOrder).filter(WBOrder.id == 2452).first()

# Поиск заказа по NM ID
orders = db.query(WBOrder).filter(WBOrder.nm_id == 317313124).all()
```

#### **3. Получение рейтинга и отзывов:**
```python
# Статистика по отзывам
reviews_stats = db.query(
    func.avg(WBReview.rating).label('avg_rating'),
    func.count(WBReview.id).label('total_reviews')
).filter(WBReview.nm_id == 317313124).first()

# Все отзывы с группировкой по рейтингам
reviews = db.query(WBReview).filter(WBReview.nm_id == 317313124).all()
```

#### **4. Получение остатков:**
```python
# Остатки по размерам
stocks = db.query(WBStock).filter(WBStock.nm_id == 317313124).all()

# Группировка по размерам
stock_by_size = {}
for stock in stocks:
    size = stock.size or 'Без размера'
    if size not in stock_by_size:
        stock_by_size[size] = 0
    stock_by_size[size] += stock.quantity or 0
```

#### **5. Получение продаж за периоды:**
```python
from datetime import datetime, timedelta

# Продажи за 7 дней
seven_days_ago = datetime.utcnow() - timedelta(days=7)
sales_7_days = db.query(WBSales).filter(
    WBSales.nm_id == 317313124,
    WBSales.sale_date >= seven_days_ago
).count()
```

### 🐳 **Docker команды для выполнения:**

#### **1. Выполнение Python скрипта в контейнере:**
```bash
docker exec $(docker ps -q --filter "name=server") python -c "
# Ваш Python код здесь
"
```

#### **2. Прямое подключение к PostgreSQL:**
```bash
# Подключение к базе данных
docker exec -it $(docker ps -q --filter "name=server") psql -U postgres -d wb_assist

# Выполнение SQL запросов
SELECT * FROM wb_orders WHERE nm_id = 317313124;
```

### 📊 **Структура данных для форматирования:**

#### **Основные поля заказа:**
```python
order_data = {
    "id": order.id,
    "order_id": order.order_id,
    "nm_id": order.nm_id,
    "status": order.status,
    "name": order.name,
    "brand": order.brand,
    "article": order.article,
    "size": order.size,
    "barcode": order.barcode,
    "total_price": order.total_price,
    "spp_percent": order.spp_percent,
    "customer_price": order.customer_price,
    "logistics_amount": order.logistics_amount,
    "warehouse_from": order.warehouse_from,
    "warehouse_to": order.warehouse_to,
    "order_date": order.order_date.isoformat() if order.order_date else None
}
```

#### **Дополнительные данные:**
```python
# Рейтинг и отзывы
rating_data = {
    "avg_rating": reviews_stats.avg_rating,
    "total_reviews": reviews_stats.total_reviews
}

# Остатки
stocks_data = {
    size: quantity for size, quantity in stock_by_size.items()
}

# Продажи
sales_data = {
    "sales_7_days": sales_7_days,
    "sales_14_days": sales_14_days,
    "sales_30_days": sales_30_days
}
```

### 🔧 **Полезные SQL запросы:**

#### **1. Полная информация о заказе:**
```sql
SELECT 
    o.*,
    p.rating as product_rating,
    p.reviews_count as product_reviews_count
FROM wb_orders o
LEFT JOIN wb_products p ON o.nm_id = p.nm_id
WHERE o.id = 2452;
```

#### **2. Статистика по товару:**
```sql
SELECT 
    o.nm_id,
    COUNT(o.id) as total_orders,
    COUNT(CASE WHEN o.status = 'active' THEN 1 END) as active_orders,
    COUNT(CASE WHEN o.status = 'canceled' THEN 1 END) as canceled_orders,
    AVG(r.rating) as avg_rating,
    COUNT(r.id) as total_reviews
FROM wb_orders o
LEFT JOIN wb_reviews r ON o.nm_id = r.nm_id
WHERE o.nm_id = 317313124
GROUP BY o.nm_id;
```

### 📝 **Итоговый шаблон для получения данных:**

```python
def get_order_detailed_info(order_id: int):
    db = next(get_db())
    
    # 1. Основной заказ
    order = db.query(WBOrder).filter(WBOrder.id == order_id).first()
    
    # 2. Рейтинг и отзывы
    reviews_stats = db.query(
        func.avg(WBReview.rating).label('avg_rating'),
        func.count(WBReview.id).label('total_reviews')
    ).filter(WBReview.nm_id == order.nm_id).first()
    
    # 3. Остатки
    stocks = db.query(WBStock).filter(WBStock.nm_id == order.nm_id).all()
    
    # 4. Продажи
    sales_7_days = db.query(WBSales).filter(
        WBSales.nm_id == order.nm_id,
        WBSales.sale_date >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    return {
        "order": order,
        "rating": reviews_stats.avg_rating,
        "reviews_count": reviews_stats.total_reviews,
        "stocks": stocks,
        "sales_7_days": sales_7_days
    }
```

Эти источники и методы позволят вам получать полную информацию о заказах для форматирования сообщений пользователям! 🎯