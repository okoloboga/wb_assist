# 🚨 S2 ISSUE: Проблема с маппингом данных WB API

## 🎯 Суть проблемы

**WB API возвращает ВСЕ необходимые данные, но наш код их НЕ ИСПОЛЬЗУЕТ!**

### 📊 Реальные данные от WB API

При запросе к `https://statistics-api.wildberries.ru/api/v1/supplier/orders` WB API возвращает полную структуру заказа:

```json
{
  "date": "2025-09-05T21:58:08",
  "lastChangeDate": "2025-09-06T00:21:11",
  "warehouseName": "Тула",                    // ✅ ЕСТЬ! Склад отправления
  "warehouseType": "Склад WB",
  "countryName": "Россия",
  "oblastOkrugName": "Центральный федеральный округ",
  "regionName": "Московская область",         // ✅ ЕСТЬ! Регион доставки
  "supplierArticle": "slavabrand_blouse_chiffon_white",
  "nmId": 255366800,
  "barcode": "2041002704600",
  "category": "Одежда",                       // ✅ ЕСТЬ! Категория товара
  "subject": "Блузки",                        // ✅ ЕСТЬ! Предмет товара
  "brand": "SLAVALOOK BRAND",
  "techSize": "S",
  "incomeID": 30272851,
  "isSupply": false,
  "isRealization": true,
  "totalPrice": 3000,                         // ✅ ЕСТЬ! Цена заказа
  "discountPercent": 60,                      // ✅ ЕСТЬ! Скидка
  "spp": 36,                                  // ✅ ЕСТЬ! СПП процент
  "finishedPrice": 768,                       // ✅ ЕСТЬ! Финальная цена
  "priceWithDisc": 1200,                      // ✅ ЕСТЬ! Цена со скидкой
  "isCancel": false,
  "cancelDate": "0001-01-01T00:00:00",
  "sticker": "35572238989",
  "gNumber": "91388477343660116602",
  "srid": "17911162113526944.0.0"
}
```

### ❌ Что показываем в боте (НЕПРАВИЛЬНО)

```json
{
  "id": 14807,
  "date": "2025-09-07T21:12:32+00:00",
  "amount": 3000.0,
  "product_name": "Блузки",
  "brand": "SLAVALOOK BRAND",
  "warehouse_from": "Неизвестно",             // ❌ ЗАГЛУШКА!
  "warehouse_to": "Неизвестно",               // ❌ ЗАГЛУШКА!
  "commission_percent": 20.0,                 // ✅ РАБОТАЕТ
  "rating": 0.0,                              // ❌ ЗАГЛУШКА!
  "order_amount": 0,                          // ❌ НЕПРАВИЛЬНО!
  "spp_percent": 0,                           // ❌ НЕПРАВИЛЬНО!
  "customer_price": 0,                        // ❌ НЕПРАВИЛЬНО!
  "logistics_amount": 0.0                     // ❌ НЕПРАВИЛЬНО!
}
```

## 🔍 Анализ проблемы

### 🚨 **КРИТИЧЕСКАЯ ПРОБЛЕМА: НЕСООТВЕТСТВИЕ БД И WB API**

**Проверка БД показала, что в таблице `wb_orders` ОТСУТСТВУЮТ НУЖНЫЕ ПОЛЯ!**

#### ✅ **Что ЕСТЬ в БД:**
```sql
-- Существующие поля в wb_orders:
id, cabinet_id, order_id, nm_id, article, name, brand, size, barcode, 
category, subject, quantity, price, total_price, commission_percent, 
commission_amount, order_date, status, created_at, updated_at
```

#### ❌ **Чего НЕТ в БД (но есть в WB API):**
```sql
-- ОТСУТСТВУЮЩИЕ поля:
warehouse_from    -- warehouseName от WB API
warehouse_to      -- regionName от WB API  
spp_percent       -- spp от WB API
customer_price    -- finishedPrice от WB API
discount_percent  -- discountPercent от WB API
logistics_amount  -- рассчитывается
```

### 📊 **Реальные данные из БД (заказ 14807):**
```sql
SELECT id, order_id, nm_id, name, brand, price, total_price, commission_percent 
FROM wb_orders WHERE id = 14807;

-- Результат:
id: 14807, order_id: 9929878247256676642, nm_id: 255366800, 
name: Блузки, brand: SLAVALOOK BRAND, price: 684, 
total_price: 3000, commission_percent: 20, commission_amount: 600
```

### 🎯 **Корень проблемы:**

1. **WB API возвращает:** `warehouseName: "Тула"`, `spp: 36`, `finishedPrice: 768`
2. **В БД НЕТ полей** для сохранения этих данных
3. **sync_service.py** не может сохранить данные, которых нет в модели
4. **bot_api/service.py** показывает заглушки, потому что данных нет в БД

### 1. **Поля складов** - `warehouse_from` и `warehouse_to`
- **WB API дает:** `warehouseName: "Тула"`, `regionName: "Московская область"`
- **В БД:** **ПОЛЕЙ НЕТ!** ❌
- **Мы показываем:** `"Неизвестно"` (заглушки в коде)
- **Проблема:** Модель WBOrder не содержит эти поля

### 2. **Цены и СПП** - `order_amount`, `spp_percent`, `customer_price`
- **WB API дает:** `totalPrice: 3000`, `spp: 36`, `finishedPrice: 768`
- **В БД:** **ПОЛЕЙ НЕТ!** ❌
- **Мы показываем:** `0` (заглушки)
- **Проблема:** Модель WBOrder не содержит эти поля

### 3. **Логистика** - `logistics_amount`
- **WB API дает:** Данные для расчета логистики
- **В БД:** **ПОЛЯ НЕТ!** ❌
- **Мы показываем:** `0.0` (заглушка)
- **Проблема:** Модель WBOrder не содержит это поле

### 4. **Рейтинги** - `rating`
- **WB API дает:** Нет в заказах (нужно из отзывов)
- **В БД:** **ПОЛЯ НЕТ!** ❌
- **Мы показываем:** `0.0` (заглушка)
- **Проблема:** Нужно получать из API отзывов

## 🎯 Корень проблемы

### **🚨 ГЛАВНАЯ ПРОБЛЕМА: МОДЕЛЬ БД НЕ СООТВЕТСТВУЕТ WB API**

**В модели `WBOrder` отсутствуют поля, которые возвращает WB API!**

### **В `models.py`:**
1. **Отсутствуют поля складов** - нет `warehouse_from`, `warehouse_to`
2. **Отсутствуют поля цен** - нет `spp_percent`, `customer_price`, `discount_percent`
3. **Отсутствуют поля логистики** - нет `logistics_amount`
4. **Отсутствуют поля рейтингов** - нет `rating`, `reviews_count`

### **В `sync_service.py`:**
1. **Не может сохранить данные** - поля отсутствуют в модели
2. **Неправильный маппинг** - используем не те поля из WB API
3. **Заглушки в Bot API** - вместо реальных данных показываем "Неизвестно"

### **В `bot_api/service.py`:**
1. **Заглушки вместо реальных данных** - строки 155-156
2. **Неправильные поля** - используем не те поля из БД
3. **Отсутствует логика расчета** - нет расчета логистики, СПП

## 🚀 Решение

### **1. Добавить поля в модель WBOrder:**
```python
# Поля складов
warehouse_from = Column(String(255), nullable=True)      # warehouseName
warehouse_to = Column(String(255), nullable=True)         # regionName
# Поля цен и СПП
order_amount = Column(Float, nullable=True)              # totalPrice
spp_percent = Column(Float, nullable=True)                # spp
customer_price = Column(Float, nullable=True)             # finishedPrice
discount_percent = Column(Float, nullable=True)           # discountPercent
# Поля логистики
logistics_amount = Column(Float, nullable=True)           # рассчитывается
```

### **2. Исправить маппинг в sync_service.py:**
```python
# Вместо:
existing.price = order_data.get("finishedPrice")
existing.total_price = order_data.get("totalPrice")

# Использовать:
existing.order_amount = order_data.get("totalPrice")
existing.spp_percent = order_data.get("spp")
existing.customer_price = order_data.get("finishedPrice")
existing.warehouse_from = order_data.get("warehouseName")
existing.warehouse_to = order_data.get("regionName")
```

### **3. Убрать заглушки в bot_api/service.py:**
```python
# Вместо:
"warehouse_from": "Неизвестно",
"warehouse_to": "Неизвестно",

# Использовать:
"warehouse_from": order.warehouse_from or "Неизвестно",
"warehouse_to": order.warehouse_to or "Неизвестно",
```

## 📋 План исправления

### **🚨 ПРИОРИТЕТ 1: Модель данных (КРИТИЧНО)**
- [ ] **Добавить поля в WBOrder модель** - `warehouse_from`, `warehouse_to`, `spp_percent`, `customer_price`, `discount_percent`, `logistics_amount`
- [ ] **Создать миграцию БД** - добавить новые колонки в таблицу `wb_orders`
- [ ] **Обновить индексы** - для новых полей
- [ ] **Протестировать миграцию** - убедиться, что БД обновилась

### **Этап 2: Синхронизация**
- [ ] **Исправить маппинг полей** в sync_service.py - использовать правильные поля WB API
- [ ] **Добавить расчет логистики** - по тарифам склада
- [ ] **Обновить логику сохранения** - сохранять все новые поля

### **Этап 3: Bot API**
- [ ] **Убрать заглушки** в bot_api/service.py - использовать реальные поля из БД
- [ ] **Использовать реальные поля** - `warehouse_from`, `spp_percent`, `customer_price`
- [ ] **Добавить расчет недостающих данных** - логистика, рейтинги

### **Этап 4: Тестирование**
- [ ] **Протестировать синхронизацию** - убедиться, что все поля сохраняются
- [ ] **Проверить отображение в боте** - все данные корректны
- [ ] **Валидировать все поля** - сравнить с WB API

## 🎯 Ожидаемый результат

После исправления в боте будет отображаться:

```json
{
  "id": 14807,
  "date": "2025-09-07T21:12:32+00:00",
  "amount": 3000.0,
  "product_name": "Блузки",
  "brand": "SLAVALOOK BRAND",
  "warehouse_from": "Тула",                    // ✅ РЕАЛЬНЫЕ ДАННЫЕ!
  "warehouse_to": "Московская область",       // ✅ РЕАЛЬНЫЕ ДАННЫЕ!
  "commission_percent": 20.0,                 // ✅ РАБОТАЕТ
  "order_amount": 3000,                       // ✅ РЕАЛЬНЫЕ ДАННЫЕ!
  "spp_percent": 36,                          // ✅ РЕАЛЬНЫЕ ДАННЫЕ!
  "customer_price": 768,                      // ✅ РЕАЛЬНЫЕ ДАННЫЕ!
  "logistics_amount": 161.5,                  // ✅ РАССЧИТАННЫЕ ДАННЫЕ!
  "rating": 4.8                               // ✅ ИЗ ОТЗЫВОВ!
}
```

## 🔧 Техническая информация

### **Файлы для изменения:**
1. `server/app/features/wb_api/models.py` - добавить поля
2. `server/app/features/wb_api/sync_service.py` - исправить маппинг
3. `server/app/features/bot_api/service.py` - убрать заглушки
4. `server/app/features/bot_api/formatter.py` - обновить форматирование

### **Поля WB API → Наши поля:**
- `warehouseName` → `warehouse_from`
- `regionName` → `warehouse_to`
- `totalPrice` → `order_amount`
- `spp` → `spp_percent`
- `finishedPrice` → `customer_price`
- `discountPercent` → `discount_percent`

### **Расчетные поля:**
- `logistics_amount` - по тарифам склада
- `rating` - из API отзывов
- `reviews_count` - из API отзывов

---

## 🎯 **ИТОГОВЫЙ ВЫВОД**

### **🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА НАЙДЕНА:**

**WB API возвращает ВСЕ необходимые данные, но в модели БД `WBOrder` ОТСУТСТВУЮТ поля для их сохранения!**

### **📊 Доказательства:**
- ✅ **WB API дает:** `warehouseName: "Тула"`, `spp: 36`, `finishedPrice: 768`
- ❌ **В БД НЕТ полей:** `warehouse_from`, `spp_percent`, `customer_price`
- ❌ **Результат:** Показываем заглушки "Неизвестно" и нули

### **🔧 Решение:**
1. **Добавить поля в модель** `WBOrder` (КРИТИЧНО!)
2. **Создать миграцию БД** 
3. **Исправить маппинг** в `sync_service.py`
4. **Убрать заглушки** в `bot_api/service.py`

---

**Статус:** 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА - несоответствие БД и WB API  
**Приоритет:** 🔥 ВЫСОКИЙ - влияет на пользовательский опыт  
**Сложность:** 🟡 СРЕДНЯЯ - требует изменений в 4 файлах + миграция БД
