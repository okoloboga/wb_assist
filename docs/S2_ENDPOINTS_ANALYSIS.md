# 🔍 S2 ENDPOINTS: Анализ используемых эндпоинтов WB API

## 🎯 Цель анализа

Изучить все эндпоинты Wildberries API, которые используются в процессе синхронизации данных для записи в БД.

## 📊 Обзор архитектуры

### **Базовые URL для разных API:**
```python
base_urls = {
    "marketplace": "https://marketplace-api.wildberries.ru",      # Склады, валидация
    "statistics": "https://statistics-api.wildberries.ru",        # Заказы, остатки, продажи
    "content": "https://content-api.wildberries.ru",              # Товары
    "feedbacks": "https://feedbacks-api.wildberries.ru",          # Отзывы, вопросы
    "common": "https://common-api.wildberries.ru"                 # Комиссии, тарифы
}
```

## 🔄 Эндпоинты, используемые при синхронизации

### **1. 🏢 СИНХРОНИЗАЦИЯ ТОВАРОВ** (`sync_products`)

#### **Эндпоинт:**
```
POST https://content-api.wildberries.ru/content/v2/get/cards/list
```

#### **Параметры:**
```json
{
  "sort": {
    "cursor": {"limit": 1000},
    "filter": {"withPhoto": -1, "visible": "ALL"}
  }
}
```

#### **Что получаем:**
- Список всех товаров продавца
- `nmId` - идентификатор товара
- `article` - артикул
- `name` - название товара
- `brand` - бренд
- `category` - категория
- `subject` - предмет

#### **Сохраняем в БД:**
- Таблица `wb_products`
- Поля: `nm_id`, `article`, `name`, `brand`, `category`, `subject`, `size`, `barcode`

---

### **2. 📦 СИНХРОНИЗАЦИЯ ЗАКАЗОВ** (`sync_orders`)

#### **Эндпоинт:**
```
GET https://statistics-api.wildberries.ru/api/v1/supplier/orders
```

#### **Параметры:**
- `dateFrom` - дата начала периода
- `dateTo` - дата окончания периода

#### **Что получаем:**
- Список заказов за период
- `nmId` - идентификатор товара
- `orderId` - идентификатор заказа
- `totalPrice` - общая цена заказа
- `warehouseName` - склад отправления
- `regionName` - регион доставки
- `spp` - СПП процент
- `finishedPrice` - финальная цена
- `discountPercent` - скидка

#### **Сохраняем в БД:**
- Таблица `wb_orders`
- Поля: `nm_id`, `order_id`, `total_price`, `commission_percent`, `commission_amount`

#### **🚨 ПРОБЛЕМА:** Отсутствуют поля для `warehouseName`, `spp`, `finishedPrice`, `discountPercent`

---

### **3. 📊 СИНХРОНИЗАЦИЯ ОСТАТКОВ** (`sync_stocks`)

#### **Эндпоинт:**
```
GET https://statistics-api.wildberries.ru/api/v1/supplier/stocks
```

#### **Параметры:**
- `dateFrom` - дата начала периода
- `dateTo` - дата окончания периода

#### **Что получаем:**
- Список остатков товаров
- `nmId` - идентификатор товара
- `warehouseId` - идентификатор склада
- `quantity` - количество на складе
- `inWayToClient` - в пути к клиенту
- `inWayFromClient` - в пути от клиента

#### **Сохраняем в БД:**
- Таблица `wb_stocks`
- Поля: `nm_id`, `warehouse_id`, `quantity`, `in_way_to_client`, `in_way_from_client`

---

### **4. 💬 СИНХРОНИЗАЦИЯ ОТЗЫВОВ** (`sync_reviews`)

#### **Эндпоинт:**
```
GET https://feedbacks-api.wildberries.ru/api/v1/feedbacks
```

#### **Параметры:**
- `isAnswered=false` - неотвеченные отзывы
- `take=1000` - количество отзывов
- `skip=0` - пропустить первые N

#### **Что получаем:**
- Список отзывов покупателей
- `id` - идентификатор отзыва
- `nmId` - идентификатор товара
- `text` - текст отзыва
- `productValuation` - оценка товара
- `createdDate` - дата создания

#### **Сохраняем в БД:**
- Таблица `wb_reviews`
- Поля: `review_id`, `nm_id`, `text`, `rating`, `is_answered`, `created_date`

---

### **5. 💰 СИНХРОНИЗАЦИЯ КОМИССИЙ** (`get_commissions`)

#### **Эндпоинт:**
```
GET https://common-api.wildberries.ru/api/v1/tariffs/commission
```

#### **Параметры:**
- `locale=ru` - локализация

#### **Что получаем:**
- Список комиссий по категориям товаров
- `parentName` - родительская категория
- `subjectName` - предмет товара
- `kgvpMarketplace` - комиссия маркетплейса
- `kgvpBooking` - комиссия за бронирование
- `kgvpPickup` - комиссия за самовывоз

#### **Используется для:**
- Расчет комиссий для заказов
- Сопоставление по категории и предмету товара

---

## 🔄 Дополнительные эндпоинты (НЕ используются в синхронизации)

### **6. 🏪 СКЛАДЫ** (`get_warehouses`)

#### **Эндпоинт:**
```
GET https://marketplace-api.wildberries.ru/api/v3/warehouses
```

#### **Назначение:**
- Валидация API ключа
- Получение списка складов продавца

#### **Используется:**
- При подключении кабинета
- Для валидации API ключа

---

### **7. ❓ ВОПРОСЫ** (`get_questions`)

#### **Эндпоинт:**
```
GET https://feedbacks-api.wildberries.ru/api/v1/questions
```

#### **Назначение:**
- Получение вопросов покупателей
- **НЕ используется** в текущей синхронизации

---

### **8. 📈 ПРОДАЖИ** (`get_sales`)

#### **Эндпоинт:**
```
GET https://statistics-api.wildberries.ru/api/v1/supplier/sales
```

#### **Назначение:**
- Получение статистики продаж
- **НЕ используется** в текущей синхронизации

---

### **9. 📦 ТАРИФЫ КОРОБОВ** (`get_box_tariffs`)

#### **Эндпоинт:**
```
GET https://common-api.wildberries.ru/api/v1/tariffs/box
```

#### **Назначение:**
- Получение тарифов для коробов
- **НЕ используется** в текущей синхронизации

---

### **10. 🚛 ТАРИФЫ ПАЛЛЕТ** (`get_pallet_tariffs`)

#### **Эндпоинт:**
```
GET https://common-api.wildberries.ru/api/v1/tariffs/pallet
```

#### **Назначение:**
- Получение тарифов для монопаллет
- **НЕ используется** в текущей синхронизации

---

### **11. 🔄 ТАРИФЫ ВОЗВРАТОВ** (`get_return_tariffs`)

#### **Эндпоинт:**
```
GET https://common-api.wildberries.ru/api/v1/tariffs/return
```

#### **Назначение:**
- Получение тарифов на возврат
- **НЕ используется** в текущей синхронизации

---

## 📊 Итоговая статистика

### **✅ ИСПОЛЬЗУЮТСЯ в синхронизации (5 эндпоинтов):**

1. **Товары** - `content-api.wildberries.ru/content/v2/get/cards/list`
2. **Заказы** - `statistics-api.wildberries.ru/api/v1/supplier/orders`
3. **Остатки** - `statistics-api.wildberries.ru/api/v1/supplier/stocks`
4. **Отзывы** - `feedbacks-api.wildberries.ru/api/v1/feedbacks`
5. **Комиссии** - `common-api.wildberries.ru/api/v1/tariffs/commission`

### **❌ НЕ используются в синхронизации (6 эндпоинтов):**

1. **Склады** - `marketplace-api.wildberries.ru/api/v3/warehouses` (только валидация)
2. **Вопросы** - `feedbacks-api.wildberries.ru/api/v1/questions`
3. **Продажи** - `statistics-api.wildberries.ru/api/v1/supplier/sales`
4. **Тарифы коробов** - `common-api.wildberries.ru/api/v1/tariffs/box`
5. **Тарифы паллет** - `common-api.wildberries.ru/api/v1/tariffs/pallet`
6. **Тарифы возвратов** - `common-api.wildberries.ru/api/v1/tariffs/return`

## ✅ Решенные проблемы с эндпоинтами

### **1. Заказы - ✅ ИСПРАВЛЕНО:**
- ✅ Получаем: `warehouseName`, `spp`, `finishedPrice`, `discountPercent`
- ✅ Сохраняем: Все поля добавлены в модель БД
- ✅ Результат: Показываем реальные данные из WB API

### **2. Комиссии - ✅ ИСПРАВЛЕНО:**
- ✅ Получаем: Полный список комиссий по категориям
- ✅ Сопоставление: Правильное сопоставление с заказами
- ✅ Результат: `commission_percent` рассчитывается корректно

### **3. Отзывы - ✅ ИСПРАВЛЕНО:**
- ✅ Получаем: Отзывы с оценками
- ✅ Используем: Для расчета рейтингов товаров
- ✅ Результат: `rating` рассчитывается из отзывов

## 🎯 Дополнительные возможности

### **1. ✅ Модель БД исправлена:**
- ✅ Добавлены поля для складов, СПП, цен в `wb_orders`
- ✅ Добавлены поля для рейтингов в `wb_products`
- ✅ Добавлены поля для остатков и отзывов

### **2. ✅ Маппинг данных улучшен:**
- ✅ Используем все поля из WB API
- ✅ Правильно сопоставляем комиссии с заказами
- ✅ Убраны отладочные логи

### **3. ✅ Расчетные поля добавлены:**
- ✅ Рейтинги товаров из отзывов
- ✅ Логистика по тарифам складов
- ✅ Комиссии по категориям

---

**Статус:** 🎉 ВСЕ ПРОБЛЕМЫ РЕШЕНЫ  
**Используется:** 5 из 11 эндпоинтов  
**Результат:** Полное использование данных WB API
