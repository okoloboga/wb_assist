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

### 1. **Поля складов** - `warehouse_from` и `warehouse_to`
- **WB API дает:** `warehouseName: "Тула"`, `regionName: "Московская область"`
- **Мы показываем:** `"Неизвестно"` (заглушки в коде)
- **Проблема:** В `bot_api/service.py` строки 155-156 используются заглушки

### 2. **Цены и СПП** - `order_amount`, `spp_percent`, `customer_price`
- **WB API дает:** `totalPrice: 3000`, `spp: 36`, `finishedPrice: 768`
- **Мы показываем:** `0` (неправильный маппинг полей)
- **Проблема:** В `sync_service.py` неправильный маппинг полей

### 3. **Логистика** - `logistics_amount`
- **WB API дает:** Данные для расчета логистики
- **Мы показываем:** `0.0` (не рассчитывается)
- **Проблема:** Нет расчета логистики по тарифам

### 4. **Рейтинги** - `rating`
- **WB API дает:** Нет в заказах (нужно из отзывов)
- **Мы показываем:** `0.0` (заглушка)
- **Проблема:** Нужно получать из API отзывов

## 🎯 Корень проблемы

### **В `sync_service.py`:**
1. **Неправильный маппинг полей** - используем не те поля из WB API
2. **Отсутствуют поля в модели** - нет полей для складов, СПП, логистики
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

### **Этап 1: Модель данных**
- [ ] Добавить поля в WBOrder модель
- [ ] Создать миграцию БД
- [ ] Обновить индексы

### **Этап 2: Синхронизация**
- [ ] Исправить маппинг полей в sync_service.py
- [ ] Добавить расчет логистики
- [ ] Обновить логику сохранения

### **Этап 3: Bot API**
- [ ] Убрать заглушки в bot_api/service.py
- [ ] Использовать реальные поля из БД
- [ ] Добавить расчет недостающих данных

### **Этап 4: Тестирование**
- [ ] Протестировать синхронизацию
- [ ] Проверить отображение в боте
- [ ] Валидировать все поля

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

**Статус:** 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА - данные есть, но не используются  
**Приоритет:** 🔥 ВЫСОКИЙ - влияет на пользовательский опыт  
**Сложность:** 🟡 СРЕДНЯЯ - требует изменений в 4 файлах
