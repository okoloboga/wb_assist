# 📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ЗАКАЗЕ - ТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ

## 🎯 Обзор

Этот документ описывает полный процесс получения и отображения детальной информации о заказе в Telegram боте WB Assist.

---

## 📊 ПРИМЕР ОТОБРАЖЕНИЯ

```
Заказ ID: 2207 от 23.10.2025 13:00

🆔 225287280 / slavabrand_dress_white_belt / (M)
🎹 2041472975210

💰 Финансы:
Цена заказа: 8,100.0₽
СПП %: 23.0%
Цена для покупателя: 1,626.0₽
Скидка: 74.0%

🚛 Казань -> Нижегородская область

📈 Выкупы за периоды:
7 | 14 | 30 дней:
19 | 25 | 32

🔍 Статистика по заказам:
Всего: 140 заказов
Активные: 85
Отмененные: 55
Выкупы: 32
Возвраты: 7

⭐ Рейтинг и отзывы:
Средний рейтинг: 4.63
Всего отзывов: 351

5⭐ - 84.4%
4⭐ - 5.8%
3⭐ - 3.9%
2⭐ - 1.9%
1⭐ - 3.9%

📦 Остатки по размерам:
L: 91 шт.
M: 86 шт.
S: 46 шт.
XL: 0 шт.
```

---

## 🔄 ПРОЦЕСС ПОЛУЧЕНИЯ ДАННЫХ

### 1️⃣ **Инициализация запроса (Telegram Bot)**

**Файл:** `bot/handlers/orders.py`  
**Функция:** `show_order_details(callback: CallbackQuery)`  
**Строки:** 151-215

#### Входные данные:
- **Callback data:** `order_details_{order_id}` (например, `order_details_2207`)
- **User ID:** `callback.from_user.id` (Telegram ID пользователя)

#### Процесс:
1. Парсим `order_id` из callback data (строка 155)
2. Вызываем API клиент: `bot_api_client.get_order_details(order_id, user_id)` (строка 160)

---

### 2️⃣ **HTTP запрос к серверу (Bot API Client)**

**Файл:** `bot/api/client.py`  
**Функция:** `get_order_details(order_id: int, user_id: int)`  
**Строки:** 351-354

#### HTTP запрос:
```http
GET /api/v1/bot/orders/{order_id}?telegram_id={user_id}
Headers:
  X-API-SECRET-KEY: {API_SECRET_KEY}
  Content-Type: application/json
```

**Пример:** `GET /api/v1/bot/orders/2207?telegram_id=5101525651`

#### Retry логика:
- **Максимум попыток:** 3
- **Timeout:** 30 секунд
- **Exponential backoff:** 1s → 2s → 4s

---

### 3️⃣ **Обработка запроса на сервере (Bot API Service)**

**Файл:** `server/app/features/bot_api/routes.py`  
**Endpoint:** `GET /api/v1/bot/orders/{order_id}`  
**Функция:** `get_order_detail(order_id, telegram_id, db)`

#### Процесс:
1. Получаем пользователя по `telegram_id` из таблицы `users`
2. Вызываем сервис: `BotAPIService.get_order_detail(order_id, user.id, db)`

---

### 4️⃣ **Сбор данных о заказе (Bot API Service)**

**Файл:** `server/app/features/bot_api/service.py`  
**Функция:** `get_order_detail(order_id: int, user_id: int, db: Session)`  
**Строки:** 247-429

#### 📊 **ИСПОЛЬЗУЕМЫЕ ТАБЛИЦЫ БД:**

| Таблица | Назначение | Поля |
|---------|-----------|------|
| **users** | Связь Telegram → Cabinet | `id`, `telegram_id` |
| **cabinet_users** | Связь User → Cabinet | `user_id`, `cabinet_id` |
| **wb_cabinets** | WB кабинеты | `id`, `api_key`, `name` |
| **wb_orders** | Заказы WB | `id`, `order_id`, `nm_id`, `name`, `article`, `size`, `barcode`, `total_price`, `spp_percent`, `customer_price`, `discount_percent`, `warehouse_from`, `warehouse_to`, `order_date`, `status` |
| **wb_products** | Товары WB | `nm_id`, `rating`, `image_url` |
| **wb_stocks** | Остатки товаров | `nm_id`, `size`, `quantity`, `warehouse_name` |
| **wb_reviews** | Отзывы | `nm_id`, `rating`, `created_at` |
| **wb_sales** | Продажи и возвраты | `nm_id`, `type` ('buyout'/'return'), `sale_date`, `is_cancel` |

---

#### 📝 **ДЕТАЛЬНЫЙ ПРОЦЕСС СБОРА ДАННЫХ:**

##### **Шаг 1: Получение основного заказа**
**Строки:** 260-272  
**Запрос:**
```sql
SELECT * FROM wb_orders 
WHERE id = {order_id} 
  AND cabinet_id = {cabinet.id}
```

**Получаемые данные:**
- Order ID (внутренний)
- WB Order ID
- NM ID товара
- Название товара
- Артикул, размер, штрихкод
- Цены (total_price, spp_percent, customer_price, discount_percent)
- Склады (warehouse_from, warehouse_to)
- Дата заказа, статус

---

##### **Шаг 2: Получение информации о товаре**
**Строки:** 274-280  
**Запрос:**
```sql
SELECT * FROM wb_products 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {order.nm_id}
```

**Получаемые данные:**
- Рейтинг товара (`rating`)
- URL изображения (`image_url`)

---

##### **Шаг 3: Получение остатков товара по размерам**
**Строки:** 282-299  
**Запрос:**
```sql
SELECT * FROM wb_stocks 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {order.nm_id}
```

**Обработка:**
```python
# Суммируем остатки по всем складам для одного размера
stocks_dict = {}
for stock in stocks:
    size = stock.size or "ONE SIZE"
    quantity = stock.quantity or 0
    if size in stocks_dict:
        stocks_dict[size] += quantity  # Суммирование!
    else:
        stocks_dict[size] = quantity
```

**Результат:** `{"L": 91, "M": 86, "S": 46, "XL": 0}`

---

##### **Шаг 4: Получение количества отзывов**
**Строки:** 301-307  
**Запрос:**
```sql
SELECT COUNT(*) FROM wb_reviews 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {order.nm_id}
```

**Результат:** `reviews_count = 351`

---

##### **Шаг 5: Получение статистики продаж**
**Функция:** `_get_product_statistics(cabinet_id, nm_id)`  
**Строки:** 1527-1582

**5.1 Выкупы за периоды (7/14/30 дней):**
```sql
SELECT * FROM wb_sales 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {nm_id}
  AND sale_date >= {start_date}
  AND type = 'buyout'
  AND is_cancel = False
```

**Периоды:**
- `7_days`: последние 7 дней
- `14_days`: последние 14 дней
- `30_days`: последние 30 дней

**Результат:** `{"7_days": 19, "14_days": 25, "30_days": 32}`

---

##### **Шаг 6: Получение статистики по заказам**
**Строки:** 316-342

**6.1 Статистика заказов (активные/отмененные):**
```sql
SELECT 
    COUNT(id) as total_orders,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_orders,
    COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_orders
FROM wb_orders 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {nm_id}
```

**6.2 Статистика продаж (выкупы/возвраты):**
```sql
SELECT 
    COUNT(CASE WHEN type = 'buyout' THEN 1 END) as buyout_count,
    COUNT(CASE WHEN type = 'return' THEN 1 END) as return_count
FROM wb_sales 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {nm_id}
  AND is_cancel = False
```

**Результат:**
```python
{
    "total_orders": 140,
    "active_orders": 85,
    "canceled_orders": 55,
    "buyout_orders": 32,
    "return_orders": 7
}
```

---

##### **Шаг 7: Получение распределения рейтингов**
**Строки:** 344-353

**Запрос:**
```sql
SELECT 
    rating,
    COUNT(id) as count
FROM wb_reviews 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {nm_id}
  AND rating IS NOT NULL
GROUP BY rating
```

**Результат:** `{5: 290, 4: 30, 3: 10, 2: 5, 1: 16}`

**Расчет процентов (в форматтере):**
```python
pct_5 = (290 / 351) * 100 = 84.4%
pct_4 = (30 / 351) * 100 = 5.8%
pct_3 = (10 / 351) * 100 = 3.9%
pct_2 = (5 / 351) * 100 = 1.9%
pct_1 = (16 / 351) * 100 = 3.9%
```

---

##### **Шаг 8: Получение среднего рейтинга**
**Строки:** 346-353

**Запрос:**
```sql
SELECT AVG(rating) FROM wb_reviews 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id = {nm_id}
  AND rating IS NOT NULL
```

**Результат:** `avg_rating = 4.63`

---

#### 📦 **ФОРМИРОВАНИЕ ИТОГОВОГО ОБЪЕКТА ДАННЫХ**

**Строки:** 360-420

```python
order_data = {
    # Основная информация о заказе
    "id": 2207,
    "order_id": "5669701717467158671",  # WB ID
    "nm_id": 225287280,
    "article": "slavabrand_dress_white_belt",
    "size": "M",
    "barcode": "2041472975210",
    "status": "active",
    
    # Название и бренд
    "product_name": "Платья",
    "brand": "SLAVABRAND",
    
    # Даты
    "date": "2025-10-23T13:00:00+00:00",
    "order_date": "2025-10-23T13:00:00+00:00",
    
    # Финансы
    "total_price": 8100.0,
    "spp_percent": 23.0,
    "customer_price": 1626.0,
    "discount_percent": 74.0,
    
    # Склады
    "warehouse_from": "Казань",
    "warehouse_to": "Нижегородская область",
    
    # Изображение товара
    "image_url": "https://basket-xx.wbbasket.ru/.../1.webp",
    
    # Рейтинг и отзывы
    "rating": 4.7,  # Из wb_products
    "avg_rating": 4.63,  # Средний из отзывов
    "reviews_count": 351,
    "rating_distribution": {5: 290, 4: 30, 3: 10, 2: 5, 1: 16},
    
    # Выкупы за периоды
    "sales_periods": {
        "7_days": 19,
        "14_days": 25,
        "30_days": 32
    },
    
    # Статистика заказов
    "orders_stats": {
        "total_orders": 140,
        "active_orders": 85,
        "canceled_orders": 55,
        "buyout_orders": 32,
        "return_orders": 7
    },
    
    # Остатки по размерам (суммированные по всем складам)
    "stocks": {
        "L": 91,
        "M": 86,
        "S": 46,
        "XL": 0
    }
}
```

---

### 5️⃣ **Форматирование сообщения (Bot API Formatter)**

**Файл:** `server/app/features/bot_api/formatter.py`  
**Функция:** `format_order_detail(data: Dict[str, Any])`  
**Строки:** 458-606

#### Процесс форматирования:

**1. Заголовок:**
```python
# Определение типа заказа по статусу
status_map = {
    "active": "Заказ",
    "buyout": "Выкуп", 
    "canceled": "Отмена",
    "return": "Возврат"
}

# Форматирование даты: "23.10.2025 13:00"
date_part = "2025-10-23"
time_part = "13:00"
year, month, day = date_part.split('-')
formatted_datetime = f"{day}.{month}.{year} {time_part}"

# Результат: "Заказ ID: 2207 от 23.10.2025 13:00"
```

**2. Идентификаторы товара:**
```python
# 🆔 {nm_id} / {article} / ({size})
# 🎹 {barcode}

# Результат:
# 🆔 225287280 / slavabrand_dress_white_belt / (M)
# 🎹 2041472975210
```

**3. Финансовая информация:**
```python
# Использование f-string с форматированием чисел
total_price = 8100.0
spp_percent = 23.0
customer_price = 1626.0
discount_percent = 74.0

# Результат:
# Цена заказа: 8,100.0₽
# СПП %: 23.0%
# Цена для покупателя: 1,626.0₽
# Скидка: 74.0%
```

**4. Выкупы за периоды:**
```python
sales_7 = sales_periods.get('7_days', 0)   # 19
sales_14 = sales_periods.get('14_days', 0)  # 25
sales_30 = sales_periods.get('30_days', 0)  # 32

# Результат:
# 📈 Выкупы за периоды:
# 7 | 14 | 30 дней:
# 19 | 25 | 32
```

**5. Статистика заказов:**
```python
# Результат:
# 🔍 Статистика по заказам:
# Всего: 140 заказов
# Активные: 85
# Отмененные: 55
# Выкупы: 32
# Возвраты: 7
```

**6. Распределение рейтингов (в процентах):**
```python
stars_5 = 290
pct_5 = (290 / 351) * 100 = 84.4%

# Результат:
# 5⭐ - 84.4%
# 4⭐ - 5.8%
# 3⭐ - 3.9%
# 2⭐ - 1.9%
# 1⭐ - 3.9%
```

**7. Остатки по размерам:**
```python
# Сортировка по размерам
sorted_stocks = sorted(stocks.keys())

# Результат:
# 📦 Остатки по размерам:
# L: 91 шт.
# M: 86 шт.
# S: 46 шт.
# XL: 0 шт.
```

---

### 6️⃣ **Отправка ответа клиенту**

**Файл:** `server/app/features/bot_api/service.py`  
**Строки:** 415-422

```python
return {
    "success": True,
    "data": order_data,
    "telegram_text": formatted_text  # Готовое сообщение
}
```

**HTTP Response:**
```json
{
  "success": true,
  "data": {...},
  "telegram_text": "Заказ ID: 2207 от 23.10.2025 13:00\n\n🆔 225287280...",
  "order": {
    "id": 2207,
    "nm_id": 225287280,
    "image_url": "https://..."
  }
}
```

---

### 7️⃣ **Отображение в Telegram**

**Файл:** `bot/handlers/orders.py`  
**Строки:** 186-207

#### Логика отображения:

**Если есть изображение товара:**
```python
await callback.message.answer_photo(
    photo=image_url,
    caption=response.telegram_text,
    reply_markup=keyboard
)
```

**Если нет изображения:**
```python
await callback.message.edit_text(
    response.telegram_text,
    reply_markup=keyboard
)
```

**Клавиатура:**
```python
InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(
        text="🔙 К списку заказов",
        callback_data="orders"
    )]
])
```

---

## 🗄️ СХЕМА БАЗЫ ДАННЫХ

### Связи таблиц:

```
users (telegram_id)
  ↓
cabinet_users (user_id, cabinet_id)
  ↓
wb_cabinets (id, api_key)
  ↓
  ├─→ wb_orders (cabinet_id, nm_id)
  ├─→ wb_products (cabinet_id, nm_id)
  ├─→ wb_stocks (cabinet_id, nm_id)
  ├─→ wb_reviews (cabinet_id, nm_id)
  └─→ wb_sales (cabinet_id, nm_id)
```

### Индексы для оптимизации:

**wb_orders:**
- `idx_order_id` на `order_id`
- `idx_nm_id` на `nm_id`
- `idx_order_date` на `order_date`
- `idx_order_status` на `status`
- `uq_cabinet_order_id` на `(cabinet_id, order_id)` - UNIQUE

**wb_sales:**
- `idx_sales_nm_id` на `nm_id`
- `idx_sales_date` на `sale_date`
- `idx_sales_type` на `type`
- `idx_sales_is_cancel` на `is_cancel`
- `uq_cabinet_sale_id` на `(cabinet_id, sale_id)` - UNIQUE

**wb_stocks:**
- `idx_stocks_nm_id` на `nm_id`

**wb_reviews:**
- `idx_reviews_nm_id` на `nm_id`

---

## ⚡ ПРОИЗВОДИТЕЛЬНОСТЬ

### Количество SQL запросов для одного заказа:

1. **Получение пользователя** - 1 запрос
2. **Получение связи user-cabinet** - 1 запрос
3. **Получение заказа** - 1 запрос
4. **Получение товара** - 1 запрос
5. **Получение остатков** - 1 запрос
6. **Подсчет отзывов** - 1 запрос
7. **Статистика заказов** - 1 запрос
8. **Статистика продаж** - 1 запрос
9. **Распределение рейтингов** - 1 запрос
10. **Средний рейтинг** - 1 запрос
11. **Выкупы за 3 периода** - 3 запроса

**ИТОГО: ~13 SQL запросов**

### Оптимизация:
- Используются индексы на всех полях фильтрации
- Группировка данных на уровне SQL (GROUP BY)
- Агрегация в одном запросе (COUNT, AVG)

---

## 🔒 БЕЗОПАСНОСТЬ

### Проверка прав доступа:

1. **Telegram ID → User ID** (таблица `users`)
2. **User ID → Cabinet ID** (таблица `cabinet_users`)
3. **Order.cabinet_id == Cabinet.id** - проверка владения заказом

**Пользователь может видеть только заказы своих кабинетов!**

---

## 🚀 МАСШТАБИРУЕМОСТЬ

### Текущие ограничения:
- Все данные в одной базе SQLite
- Синхронные SQL запросы
- Нет кэширования

### Возможные улучшения:
1. **Кэширование** часто запрашиваемых данных (Redis)
2. **Объединение запросов** (JOIN вместо множественных SELECT)
3. **Асинхронные запросы** (SQLAlchemy async)
4. **Пагинация** для больших объемов данных

---

## 📝 КЛЮЧЕВЫЕ ФАЙЛЫ

| Файл | Назначение | Строки |
|------|-----------|--------|
| `bot/handlers/orders.py` | Обработчик команд бота | 151-215 |
| `bot/api/client.py` | HTTP клиент | 351-354 |
| `server/app/features/bot_api/routes.py` | API эндпоинты | - |
| `server/app/features/bot_api/service.py` | Бизнес-логика | 247-429 |
| `server/app/features/bot_api/formatter.py` | Форматирование сообщений | 458-606 |
| `server/app/features/wb_api/models.py` | Модели БД (заказы) | 74-125 |
| `server/app/features/wb_api/models_sales.py` | Модели БД (продажи) | 9-48 |

---

## 🐛 ЛОГИРОВАНИЕ

### Ключевые логи:

**Bot:**
```python
logger.info(f"📢 Order detail response: {response}")
logger.info(f"📢 Order data: {order}")
logger.info(f"📢 Order image_url: {image_url}")
```

**Server:**
```python
logger.info(f"Order data for order {order_id}")
logger.info(f"Order data keys: {list(order_data.keys())}")
logger.error(f"Ошибка получения деталей заказа: {e}")
```

---

## ✅ ИТОГОВЫЙ ПОТОК ДАННЫХ

```
Telegram Bot (User clicks order)
  ↓ callback: "order_details_2207"
  
Bot Handler (orders.py)
  ↓ GET /api/v1/bot/orders/2207?telegram_id=5101525651
  
Server API (routes.py)
  ↓ BotAPIService.get_order_detail()
  
Database Queries:
  ├─ wb_orders (основной заказ)
  ├─ wb_products (рейтинг, изображение)
  ├─ wb_stocks (остатки)
  ├─ wb_reviews (отзывы, рейтинги)
  └─ wb_sales (выкупы, возвраты)
  
Formatter (formatter.py)
  ↓ format_order_detail()
  
Server Response (JSON)
  ↓ {success, data, telegram_text, order}
  
Bot Client (client.py)
  ↓ BotAPIResponse
  
Telegram Message
  ↓ Photo + Caption OR Text + Keyboard
  
User sees formatted order details
```

---

**Дата создания:** 23.10.2025  
**Автор:** WB Assist Development Team  
**Версия:** 1.0
