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

### **2. 📦 Склад (детализированный по складам, без размеров)**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | Фото | WBProduct | `image_url` | =IMAGE() |
| B | Артикул (nm_id) | WBStock | `nm_id` | Integer |
| C | Название товара | WBProduct | `name` | String(500) |
| D | Бренд | WBStock | `brand` | String(255) |
| E | Склад | WBStock | `warehouse_name` | String(255) |
| F | Количество | WBStock | `quantity` | Integer (суммировано по всем размерам) |
| G | В пути к клиенту | WBStock | `in_way_to_client` | Integer (суммировано) |
| H | В пути от клиента | WBStock | `in_way_from_client` | Integer (суммировано) |
| I | Заказ/Выкуп Неделя | WBOrder + WBSales | `orders_7d / buyouts_7d` | String (формат: "X / Y") |
| J | Заказ/Выкуп 2 Недели | WBOrder + WBSales | `orders_14d / buyouts_14d` | String (формат: "X / Y") |
| K | Заказ/Выкуп Месяц | WBOrder + WBSales | `orders_30d / buyouts_30d` | String (формат: "X / Y") |
| L | Цена | WBStock | `price` | Float |
| M | Скидка | WBStock | `discount` | Float |
| N | Рейтинг | WBProduct | `rating` | Float |
| O | % выкуп | WBOrder + WBSales | `(buyouts / orders) * 100` | Float |
| P | % возврат | WBOrder + WBSales | `(returns / orders) * 100` | Float |

**Источник данных:** Таблицы `wb_stocks` + `wb_products` + `wb_orders` + `wb_sales` (JOIN)
**Особенности:**
- Одна строка = один товар на одном складе (без размеров)
- Название товара берется из `wb_products` по `nm_id`
- Группировка по `nm_id` + `warehouse_name` (размеры объединены)
- Количества (`quantity`, `in_way_to_client`, `in_way_from_client`) суммируются по всем размерам
- **Статистика (колонки I, J, K, N, O, P):** Рассчитывается по товару в целом (nm_id), одинаковые значения для всех складов одного товара

**Колонки статистики:**
- **Заказ/Выкуп (I, J, K):** Формат "X / Y", где X - количество заказов за период, Y - количество выкупов за период
  - Неделя: заказы и выкупы за последние 7 дней
  - 2 Недели: заказы и выкупы за последние 14 дней
  - Месяц: заказы и выкупы за последние 30 дней
- **Рейтинг (N):** Рейтинг товара из `wb_products.rating`
- **% выкуп (O):** Процент выкупов от общего количества заказов: `(buyouts / orders) * 100`
- **% возврат (P):** Процент возвратов от общего количества заказов: `(returns / orders) * 100`

**SQL запрос (концептуальный):**
```sql
-- Основные данные остатков
SELECT 
    p.image_url, s.nm_id, p.name, s.brand, s.warehouse_name,
    SUM(s.quantity) as quantity,
    SUM(s.in_way_to_client) as in_way_to_client,
    SUM(s.in_way_from_client) as in_way_from_client,
    s.price, s.discount, p.rating
FROM wb_stocks s
LEFT JOIN wb_products p ON s.nm_id = p.nm_id AND s.cabinet_id = p.cabinet_id
WHERE s.cabinet_id = ? 
GROUP BY s.nm_id, s.warehouse_name, p.image_url, p.name, s.brand, s.price, s.discount, p.rating
ORDER BY s.nm_id, s.warehouse_name

-- Дополнительные запросы для статистики (для каждого nm_id):
-- Заказы за 7/14/30 дней: SELECT COUNT(*) FROM wb_orders WHERE nm_id = ? AND order_date >= ?
-- Выкупы за 7/14/30 дней: SELECT COUNT(*) FROM wb_sales WHERE nm_id = ? AND sale_date >= ? AND type = 'buyout'
-- Общие заказы/выкупы/возвраты: для расчета процентов
```

---

### **3. 🛒 Заказы (объединенные: заказы + выкупы + возвраты)**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | Фото | WBProduct | `image_url` | =IMAGE() |
| B | Номер заказа | WBOrder | `order_id` | String(100) |
| C | Номенклатура (nm_id) | WBOrder | `nm_id` | Integer |
| D | Название | WBProduct | `name` | String(500) |
| E | Размер | WBOrder | `size` | String(50) |
| F | Статус | WBOrder | `status` | String(50) |
| G | Дата заказа | WBOrder | `order_date` | DateTime |
| H | Склад отправки | WBOrder | `warehouse_from` | String(255) |
| I | Регион доставки | WBOrder | `warehouse_to` | String(255) |
| J | Общая сумма | WBOrder | `total_price` | Float |
| K | Комиссия WB | WBOrder | `commission_amount` | Float |
| L | Цена клиента | WBOrder | `customer_price` | Float |
| M | СПП % | WBOrder | `spp_percent` | Float |
| N | Скидка % | WBOrder | `discount_percent` | Float |
| O | % выкуп | WBOrder + WBSales | `(buyouts / orders) * 100` | Float |
| P | Рейтинг | WBProduct | `rating` | Float |

**Источник данных:** Таблицы `wb_orders` + `wb_products` + `wb_sales` (JOIN)
**Статусы:**
- `Активный` - активный заказ
- `Отменен` - заказ отменен

**Изменения:**
- Убраны колонки "Количество" (F) и "Цена" (G)
- Колонка "Общая сумма" перемещена после "Регион доставки"
- Колонки "Цена клиента" и "СПП %" поменяны местами
- Добавлены колонки "% выкуп" (O) и "Рейтинг" (P)

**Колонки статистики:**
- **% выкуп (O):** Процент выкупов от общего количества заказов товара: `(buyouts / orders) * 100`
- **Рейтинг (P):** Рейтинг товара из `wb_products.rating`
- Статистика рассчитывается по товару в целом (nm_id), одинаковые значения для всех заказов одного товара

**SQL запрос:**
```sql
SELECT 
    p.image_url, o.order_id, o.nm_id, p.name, o.size,
    o.status, o.order_date, o.warehouse_from, o.warehouse_to,
    o.total_price, o.commission_amount, o.customer_price, o.spp_percent, o.discount_percent
FROM wb_orders o
LEFT JOIN wb_products p ON o.nm_id = p.nm_id AND o.cabinet_id = p.cabinet_id
WHERE o.cabinet_id = ? 
ORDER BY o.order_date DESC
```

---

### **4. ⭐ Отзывы**

| Колонка | Описание | Источник данных | Поле БД | Тип данных |
|---------|----------|-----------------|---------|------------|
| A | Фото | WBProduct | `image_url` | =IMAGE() |
| B | ID отзыва | WBReview | `review_id` | String(100) |
| C | Артикул | WBReview | `nm_id` | Integer |
| D | Название | WBReview | (из WBProduct) | String(500) |
| E | Рейтинг | WBReview | `rating` | Integer |
| F | Текст отзыва | WBReview | `text` | Text |
| G | Плюсы | WBReview | `pros` | Text |
| H | Минусы | WBReview | `cons` | Text |
| I | Имя пользователя | WBReview | `user_name` | String(255) |
| J | Цвет | WBReview | `color` | String(100) |
| K | Размер | WBReview | `matching_size` | String(50) |
| L | Дата отзыва | WBReview | `created_date` | DateTime |
| M | Ответ продавца | WBReview | `is_answered` | ✅/❌ |
| N | Просмотрен | WBReview | `was_viewed` | ✅/❌ |

**Источник данных:** Таблица `wb_reviews` + `wb_products` (для названия товара)

**SQL запрос:**
```sql
SELECT 
    p.image_url, r.review_id, r.nm_id, p.name, r.rating, r.text, r.pros, r.cons,
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
- `wb_products` ← `wb_stocks` (nm_id + cabinet_id) ← **НОВОЕ**
- `wb_products` ← `wb_orders` (nm_id + cabinet_id) ← **НОВОЕ**
- `wb_products` ← `wb_reviews` (nm_id + cabinet_id)

### **Уникальные ограничения:**
- `wb_stocks`: `uq_cabinet_nm_warehouse` (cabinet_id, nm_id, warehouse_id)
- `wb_orders`: `uq_cabinet_order_id` (cabinet_id, order_id)
- `wb_reviews`: `uq_cabinet_review_id` (cabinet_id, review_id)

---

## 📊 Дополнительные поля БД (не используемые в таблице)

### **WBStock (неиспользуемые поля):**
- `article` - артикул поставщика
- `name` - название товара (теперь берется из WBProduct)
- `barcode` - штрихкод
- `category` - категория
- `subject` - предмет
- `quantity_full` - полное количество
- `is_supply` - поставка
- `is_realization` - реализация
- `sc_code` - код поставщика

### **WBOrder (неиспользуемые поля):**
- `article` - артикул поставщика
- `name` - название товара (теперь берется из WBProduct)
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
- Склад: 12 полей (включая фото)
- Заказы: 16 полей (включая фото)
- Отзывы: 14 полей (включая фото)
- **Итого: 42 поля данных**

**Источники данных:**
- `wb_stocks` - 10 полей + LEFT JOIN `wb_products` (name, image_url)
- `wb_orders` - 14 полей + LEFT JOIN `wb_products` (name, image_url)
- `wb_reviews` - 12 полей + LEFT JOIN `wb_products` (name, image_url)
- `wb_products` - название товара и фото (используется во всех трех листах)
- **Всего: 42 поля из PostgreSQL БД с JOIN на wb_products**

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
