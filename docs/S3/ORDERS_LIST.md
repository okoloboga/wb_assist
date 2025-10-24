# 📋 СПИСОК ЗАКАЗОВ - ТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ

## 🎯 Обзор

Этот документ описывает процесс получения и отображения списка заказов в Telegram боте WB Assist при нажатии на кнопку "Заказы" в главном меню.

---

## 📊 ПРИМЕР ОТОБРАЖЕНИЯ

```
🛒 ПОСЛЕДНИЕ ЗАКАЗЫ

🧾 8668325118281716101
   2025-10-24 11:02 | 10,500₽
   Коледино → Краснодарский край

🧾 10904
   2025-10-24 10:51 | 10,500₽
   Коледино → Республика Татарстан

🧾 10903
   2025-10-24 10:50 | 8,321₽
   Коледино → Республика Крым

🧾 10902
   2025-10-24 10:44 | 10,500₽
   Тула → Московская область

📊 СТАТИСТИКА ЗА СЕГОДНЯ
• Всего заказов: 4
• Общая сумма: 39,311₽
• Средний чек: 9,828₽
• Рост к вчера: +25% по количеству, +15% по сумме

💡 Нажмите номер заказа для детального отчета
```

---

## 🔄 ПРОЦЕСС ПОЛУЧЕНИЯ ДАННЫХ

### 1️⃣ **Инициализация запроса (Telegram Bot)**

**Файл:** `bot/handlers/orders.py`  
**Функция:** `show_orders(callback: CallbackQuery)`  

#### Входные данные:
- **Callback data:** `"orders"`
- **User ID:** `callback.from_user.id` (Telegram ID пользователя)

#### Процесс:
1. Вызываем API клиент: `bot_api_client.get_recent_orders(user_id=telegram_id)`

---

### 2️⃣ **HTTP запрос к серверу (Bot API Client)**

**Файл:** `bot/api/client.py`  
**Функция:** `get_recent_orders(user_id: int)`  

#### HTTP запрос:
```http
GET /api/v1/bot/orders/recent?telegram_id={user_id}
Headers:
  X-API-SECRET-KEY: {API_SECRET_KEY}
  Content-Type: application/json
```

**Пример:** `GET /api/v1/bot/orders/recent?telegram_id=5101525651`

---

### 3️⃣ **Обработка запроса на сервере (Bot API Service)**

**Файл:** `server/app/features/bot_api/routes.py`  
**Endpoint:** `GET /api/v1/bot/orders/recent`  
**Функция:** `get_recent_orders(telegram_id, limit, offset, status, bot_service)`

#### Процесс:
1. Получаем пользователя по `telegram_id` из таблицы `users`
2. Вызываем сервис: `BotAPIService.get_recent_orders(user, limit, offset, status)`

---

### 4️⃣ **Сбор данных о заказах (Bot API Service)**

**Файл:** `server/app/features/bot_api/service.py`  
**Функция:** `get_recent_orders(user, limit, offset, status)`  
**Строки:** 154-202

#### 📊 **ИСПОЛЬЗУЕМЫЕ ТАБЛИЦЫ БД:**

| Таблица | Назначение | Поля |
|---------|-----------|------|
| **users** | Связь Telegram → Cabinet | `id`, `telegram_id` |
| **cabinet_users** | Связь User → Cabinet | `user_id`, `cabinet_id` |
| **wb_cabinets** | WB кабинеты | `id`, `api_key`, `name` |
| **wb_orders** | Заказы WB | `id`, `order_id`, `nm_id`, `name`, `total_price`, `warehouse_from`, `warehouse_to`, `order_date`, `status` |
| **wb_products** | Товары WB | `nm_id`, `rating`, `image_url` |

---

#### 📝 **ДЕТАЛЬНЫЙ ПРОЦЕСС СБОРА ДАННЫХ:**

##### **Шаг 1: Получение заказов**
**Строки:** 1032-1050  
**Запрос:**
```sql
SELECT * FROM wb_orders 
WHERE cabinet_id = {cabinet_id}
ORDER BY created_at DESC
LIMIT {limit} OFFSET {offset}
```

**Получаемые данные:**
- Внутренний ID заказа
- WB Order ID (order_id)
- NM ID товара
- Название товара
- Цена заказа
- Склады (warehouse_from, warehouse_to)
- Дата заказа, статус

##### **Шаг 2: Получение информации о товарах**
**Строки:** 1076-1083  
**Запрос:**
```sql
SELECT * FROM wb_products 
WHERE cabinet_id = {cabinet_id} 
  AND nm_id IN ({nm_ids})
```

**Получаемые данные:**
- Рейтинг товара
- URL изображения

##### **Шаг 3: Формирование списка заказов**
**Строки:** 1087-1100

```python
# Конвертируем дату в МСК для отображения
order_date_msk = None
if order.order_date:
    # Если дата без timezone, считаем что это UTC
    if order.order_date.tzinfo is None:
        order_date_utc = order.order_date.replace(tzinfo=timezone.utc)
    else:
        order_date_utc = order.order_date
    # Конвертируем в МСК
    order_date_msk = TimezoneUtils.from_utc(order_date_utc)

orders_list.append({
    "id": order.id,                    # Внутренний ID БД
    "order_id": order.order_id,        # WB Order ID (отображается)
    "order_date": order_date_msk.isoformat() if order_date_msk else None,  # МСК!
    "amount": order.total_price,
    "product_name": order.name,
    "brand": order.brand,
    "warehouse_from": order.warehouse_from,
    "warehouse_to": order.warehouse_to,
    "status": order.status,
    "nm_id": order.nm_id,
    "rating": product.rating if product else 0.0,
    "image_url": product.image_url if product else None
})
```

---

### 5️⃣ **Форматирование сообщения (Bot API Formatter)**

**Файл:** `server/app/features/bot_api/formatter.py`  
**Функция:** `format_orders(data: Dict[str, Any])`  
**Строки:** 66-105

#### Процесс форматирования:

**1. Заголовок:**
```python
message = "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n"
```

**2. Список заказов:**
```python
for order in orders[:10]:
    wb_order_id = order.get('order_id', order.get('id', 'N/A'))
    # Простое форматирование: 2025-10-24T11:02:25+03:00 -> 2025-10-24 11:02
    order_date = self._format_datetime_simple(order.get("date", ""))
    amount = order.get('amount', 0)
    warehouse_from = order.get('warehouse_from', 'N/A')
    warehouse_to = order.get('warehouse_to', 'N/A')
    
    message += f"""🧾 {wb_order_id}
   {order_date} | {amount:,.0f}₽
   {warehouse_from} → {warehouse_to}

"""
```

**3. Статистика:**
```python
message += f"""📊 СТАТИСТИКА ЗА СЕГОДНЯ
• Всего заказов: {statistics.get('today_count', 0)}
• Общая сумма: {statistics.get('today_amount', 0):,.0f}₽
• Средний чек: {statistics.get('average_check', 0):,.0f}₽
• Рост к вчера: {statistics.get('growth_percent', 0):+.0f}% по количеству, {statistics.get('amount_growth_percent', 0):+.0f}% по сумме

💡 Нажмите номер заказа для детального отчета"""
```

---

### 6️⃣ **Отправка ответа клиенту**

**Файл:** `server/app/features/bot_api/service.py`  
**Строки:** 185-202

```python
return {
    "success": True,
    "data": orders_data,
    "telegram_text": telegram_text,
    "orders": orders_data.get("orders", []),
    "pagination": orders_data.get("pagination", {}),
    "statistics": orders_data.get("statistics", {}),
    "stocks": {},
    "reviews": {},
    "analytics": {},
    "order": None
}
```

**HTTP Response:**
```json
{
  "status": "success",
  "orders": [
    {
      "id": 2207,
      "order_id": "93388757485424359259",
      "order_date": "2025-09-23T20:01:28+00:00",
      "amount": 9990.0,
      "product_name": "Пиджаки",
      "brand": "SLAVALOOK BRAND",
      "warehouse_from": "Электросталь",
      "warehouse_to": "Краснодарский край",
      "status": "active"
    }
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 25,
    "has_more": true
  },
  "statistics": {
    "today_count": 4,
    "today_amount": 39311.0,
    "average_check": 9828.0,
    "growth_percent": 25.0,
    "amount_growth_percent": 15.0
  },
  "telegram_text": "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n🧾 93388757485424359259\n   2025-09-23 20:01 | 9,990₽\n   Электросталь → Краснодарский край\n\n..."
}
```

---

### 7️⃣ **Отображение в Telegram**

**Файл:** `bot/handlers/orders.py`  

#### Логика отображения:

**Отправка сообщения:**
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
        text="🔙 Главное меню",
        callback_data="main_menu"
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
  └─→ wb_products (cabinet_id, nm_id)
```

### Индексы для оптимизации:

**wb_orders:**
- `idx_cabinet_created` на `(cabinet_id, created_at)`
- `idx_order_id` на `order_id`
- `idx_order_date` на `order_date`
- `idx_order_status` на `status`

**wb_products:**
- `idx_products_cabinet_nm` на `(cabinet_id, nm_id)`

---

## ⚡ ПРОИЗВОДИТЕЛЬНОСТЬ

### Количество SQL запросов для списка заказов:

1. **Получение пользователя** - 1 запрос
2. **Получение связи user-cabinet** - 1 запрос
3. **Получение заказов** - 1 запрос
4. **Получение товаров (batch)** - 1 запрос
5. **Статистика заказов** - 1 запрос

**ИТОГО: ~5 SQL запросов**

### Оптимизации в текущей реализации:
- **Batch загрузка товаров** - все товары загружаются одним запросом
- **Eager loading** - кабинет загружается вместе с заказами
- **Индексы** - на всех полях фильтрации и сортировки

---

## 🔒 БЕЗОПАСНОСТЬ

### Проверка прав доступа:

1. **Telegram ID → User ID** (таблица `users`)
2. **User ID → Cabinet ID** (таблица `cabinet_users`)
3. **Order.cabinet_id == Cabinet.id** - проверка владения заказами

**Пользователь может видеть только заказы своих кабинетов!**

---

## 🚀 МАСШТАБИРУЕМОСТЬ

### Текущие ограничения:
- Все данные в одной базе SQLite
- Синхронные SQL запросы
- Нет кэширования

### Возможные улучшения:
1. **Кэширование** часто запрашиваемых данных (Redis)
2. **Пагинация** для больших объемов данных
3. **Асинхронные запросы** (SQLAlchemy async)
4. **Индексы** для оптимизации запросов

---

## 📝 КЛЮЧЕВЫЕ ФАЙЛЫ

| Файл | Назначение | Строки |
|------|-----------|--------|
| `bot/handlers/orders.py` | Обработчик команд бота | - |
| `bot/api/client.py` | HTTP клиент | - |
| `server/app/features/bot_api/routes.py` | API эндпоинты | 67-98 |
| `server/app/features/bot_api/service.py` | Бизнес-логика | 154-202 |
| `server/app/features/bot_api/formatter.py` | Форматирование сообщений | 66-105 |
| `server/app/features/bot_api/schemas.py` | Схемы данных | 46-67 |

---

## 🐛 ЛОГИРОВАНИЕ

### Ключевые логи:

**Bot:**
```python
logger.info(f"📋 Orders response: {response}")
logger.info(f"📋 Orders data: {orders}")
```

**Server:**
```python
logger.info(f"🔍 [get_recent_orders] Starting for telegram_id={user['telegram_id']}")
logger.info(f"📋 [get_recent_orders] Fetched {len(orders_list)} orders from DB")
logger.info(f"   Order {i+1}: ID={order.get('id')}, WB_ID={order.get('order_id')}")
```

---

## ✅ ИТОГОВЫЙ ПОТОК ДАННЫХ

```
Telegram Bot (User clicks "Заказы")
  ↓ callback: "orders"
  
Bot Handler (orders.py)
  ↓ GET /api/v1/bot/orders/recent?telegram_id=5101525651
  
Server API (routes.py)
  ↓ BotAPIService.get_recent_orders()
  
Database Queries:
  ├─ wb_orders (список заказов)
  ├─ wb_products (информация о товарах)
  └─ статистика заказов
  
Formatter (formatter.py)
  ↓ format_orders()
  
Server Response (JSON)
  ↓ {success, orders, pagination, statistics, telegram_text}
  
Bot Client (client.py)
  ↓ BotAPIResponse
  
Telegram Message
  ↓ Text + Keyboard
  
User sees formatted orders list
```

---

**Дата создания:** 24.10.2025  
**Дата обновления:** 24.10.2025  
**Автор:** WB Assist Development Team  
**Версия:** 1.0

## 🔄 ИЗМЕНЕНИЯ В ВЕРСИИ 1.0

### ✅ Новый формат отображения:
- **WB Order ID:** Отображается WB Order ID вместо внутреннего ID БД
- **Форматирование даты:** Конвертация UTC → МСК в сервисе + форматирование (YYYY-MM-DD HH:MM)
- **Упрощенный формат:** Убраны название товара и бренд из списка
- **Компактное отображение:** Многострочный формат с эмодзи

### 🔧 Технические изменения:
- **`OrderData`:** Добавлено поле `order_id` для WB Order ID
- **`format_orders()`:** Обновлен формат отображения списка заказов
- **`_format_datetime_simple()`:** Оптимизированное форматирование МСК времени (простое обрезание строки)
- **`_fetch_orders_from_db()`:** Добавлена конвертация UTC → МСК перед передачей в форматтер
