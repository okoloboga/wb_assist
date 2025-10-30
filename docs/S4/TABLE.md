# 📊 Структура таблицы Google Sheets для экспорта данных WB

## 🎯 Обзор

Данный документ описывает детальную структуру Google Sheets таблицы для экспорта данных Wildberries, включая все источники данных из PostgreSQL БД.

---

## 📋 Структура таблицы (4 вкладки)

### **1. ℹ️ Информация**

Лист с инструкцией по подключению и общей информацией о работе с таблицей.

**Рекомендуемый контент:**
- Инструкция по подключению бота
- Частота обновления данных
- Контактная информация для поддержки

**Пример содержимого:**
```
📊 Экспорт данных Wildberries

Это шаблон таблицы для экспорта данных вашего кабинета WB.

📋 Инструкция по подключению:

1️⃣ Скопируйте этот шаблон в свой Google Drive
2️⃣ Откройте настройки доступа
3️⃣ Добавьте email бота: wb-assist-sheets@wb-assist.iam.gserviceaccount.com
4️⃣ Дайте права "Редактор"
5️⃣ Отправьте ссылку на вашу таблицу боту в ответ на инструкцию

✅ После подключения данные обновляются автоматически

🔄 Ручное обновление:
Используйте команду /export в боте

💡 Поддержка: @wb_assist_bot
```

**Источник данных:** Информационный лист (не обновляется автоматически)

---

### **2. 📦 Склад (детализированный по складам)**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | Артикул | WBStock | `article` | String(100) |
| B | Название товара | WBStock | `name` | String(500) |
| C | Бренд | WBStock | `brand` | String(255) |
| D | Размер | WBStock | `size` | String(50) |
| E | Склад | WBStock | `warehouse_name` | String(255) |
| F | Количество | WBStock | `quantity` | Integer |
| G | В пути к клиенту | WBStock | `in_way_to_client` | Integer |
| H | В пути от клиента | WBStock | `in_way_from_client` | Integer |
| I | Цена | WBStock | `price` | Float |
| J | Скидка | WBStock | `discount` | Float |
| K | Последнее обновление | WBStock | `last_updated` | DateTime |

**Источник данных:** Таблица `wb_stocks`
**Особенности:**
- Одна строка = один товар на одном складе
- Группировка по `nm_id` + `warehouse_id`
- Уникальное ограничение: `uq_cabinet_nm_warehouse`

**SQL запрос:**
```sql
SELECT 
    article, name, brand, size, warehouse_name,
    quantity, in_way_to_client, in_way_from_client,
    price, discount, last_updated
FROM wb_stocks 
WHERE cabinet_id = ? 
ORDER BY nm_id, warehouse_name
```

---

### **3. 🛒 Заказы (объединенные: заказы + выкупы + возвраты)**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | Номер заказа | WBOrder | `order_id` | String(100) |
| B | Артикул | WBOrder | `article` | String(100) |
| C | Название | WBOrder | `name` | String(500) |
| D | Размер | WBOrder | `size` | String(50) |
| E | Количество | WBOrder | `quantity` | Integer |
| F | Цена | WBOrder | `price` | Float |
| G | Общая сумма | WBOrder | `total_price` | Float |
| H | Статус | WBOrder | `status` | String(50) |
| I | Дата заказа | WBOrder | `order_date` | DateTime |
| J | Склад отправки | WBOrder | `warehouse_from` | String(255) |
| K | Регион доставки | WBOrder | `warehouse_to` | String(255) |
| L | Комиссия WB | WBOrder | `commission_amount` | Float |
| M | СПП % | WBOrder | `spp_percent` | Float |
| N | Цена клиента | WBOrder | `customer_price` | Float |
| O | Скидка % | WBOrder | `discount_percent` | Float |

**Источник данных:** Таблица `wb_orders`
**Статусы:**
- `Заказ` - новый заказ
- `Выкуп` - товар выкуплен  
- `Отмена` - заказ отменен
- `Возврат` - товар возвращен

**SQL запрос:**
```sql
SELECT 
    order_id, article, name, size, quantity, price, total_price,
    status, order_date, warehouse_from, warehouse_to,
    commission_amount, spp_percent, customer_price, discount_percent
FROM wb_orders 
WHERE cabinet_id = ? 
ORDER BY order_date DESC
```

---

### **4. ⭐ Отзывы**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | ID отзыва | WBReview | `review_id` | String(100) |
| B | Артикул | WBReview | `nm_id` | Integer |
| C | Название | WBReview | (из WBProduct) | String(500) |
| D | Рейтинг | WBReview | `rating` | Integer |
| E | Текст отзыва | WBReview | `text` | Text |
| F | Плюсы | WBReview | `pros` | Text |
| G | Минусы | WBReview | `cons` | Text |
| H | Имя пользователя | WBReview | `user_name` | String(255) |
| I | Цвет | WBReview | `color` | String(100) |
| J | Размер | WBReview | `matching_size` | String(50) |
| K | Дата отзыва | WBReview | `created_date` | DateTime |
| L | Ответ продавца | WBReview | (из `is_answered`) | Boolean |
| M | Просмотрен | WBReview | `was_viewed` | Boolean |

**Источник данных:** Таблица `wb_reviews` + `wb_products` (для названия товара)

**SQL запрос:**
```sql
SELECT 
    r.review_id, r.nm_id, p.name, r.rating, r.text, r.pros, r.cons,
    r.user_name, r.color, r.matching_size, r.created_date,
    r.is_answered, r.was_viewed
FROM wb_reviews r
LEFT JOIN wb_products p ON r.nm_id = p.nm_id AND r.cabinet_id = p.cabinet_id
WHERE r.cabinet_id = ? 
ORDER BY r.created_date DESC
```

---

## 🔗 Связи между таблицами

### **Основные связи:**
- `wb_cabinets` ← `wb_stocks` (cabinet_id)
- `wb_cabinets` ← `wb_orders` (cabinet_id)  
- `wb_cabinets` ← `wb_reviews` (cabinet_id)
- `wb_products` ← `wb_reviews` (nm_id + cabinet_id)

### **Уникальные ограничения:**
- `wb_stocks`: `uq_cabinet_nm_warehouse` (cabinet_id, nm_id, warehouse_id)
- `wb_orders`: `uq_cabinet_order_id` (cabinet_id, order_id)
- `wb_reviews`: `uq_cabinet_review_id` (cabinet_id, review_id)

---

## 📊 Дополнительные поля БД (не используемые в таблице)

### **WBStock (неиспользуемые поля):**
- `barcode` - штрихкод
- `category` - категория
- `subject` - предмет
- `quantity_full` - полное количество
- `is_supply` - поставка
- `is_realization` - реализация
- `sc_code` - код поставщика

### **WBOrder (неиспользуемые поля):**
- `barcode` - штрихкод
- `category` - категория
- `subject` - предмет
- `commission_percent` - процент комиссии

### **WBReview (неиспользуемые поля):**
- `bables` - JSON массив
- `supplier_feedback_valuation` - оценка отзыва поставщиком
- `supplier_product_valuation` - оценка товара поставщиком

---

## 🎯 Итоговая структура

**4 вкладки:**
1. **ℹ️ Информация** - инструкция по подключению и работе (статический контент)
2. **📦 Склад** - остатки по складам (из `wb_stocks`)
3. **🛒 Заказы** - все события заказов (из `wb_orders`)
4. **⭐ Отзывы** - отзывы покупателей (из `wb_reviews` + `wb_products`)

**Общее количество полей:**
- Информация: информационный лист (без полей)
- Склад: 11 полей
- Заказы: 15 полей  
- Отзывы: 13 полей
- **Итого: 39 полей данных**

**Источники данных:**
- `wb_stocks` - 11 полей
- `wb_orders` - 15 полей
- `wb_reviews` - 12 полей
- `wb_products` - 1 поле (название товара)
- **Всего: 39 полей из PostgreSQL БД**

---

## 📝 Инструкция для пользователя

### Как подключить таблицу к боту:

1. **Скопируйте шаблон**
   - Откройте публичный шаблон по ссылке из бота
   - Выберите "File → Make a copy"

2. **Дайте доступ боту**
   - Нажмите кнопку "Настроить доступ" в Google Sheets
   - Добавьте email: `wb-assist-sheets@wb-assist.iam.gserviceaccount.com`
   - Дайте права "Редактор" (Editor)

3. **Отправьте ссылку боту**
   - Скопируйте ссылку на вашу скопированную таблицу
   - Отправьте ссылку боту в ответ на инструкцию

4. **Готово!**
   - Бот сохранит связь с вашей таблицей
   - Данные будут обновляться автоматически

### Частота обновления:
- ⏰ Автоматическое: с настраиваемым интервалом
- 🔄 Ручное: через команду `/export` в боте
