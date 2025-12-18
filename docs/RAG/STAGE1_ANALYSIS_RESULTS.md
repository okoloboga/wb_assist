# Этап 1: Анализ схем таблиц - Результаты

**Дата:** 2025-12-16
**Статус:** ✅ Завершен

---

## 📊 Анализ полей timestamp в таблицах основной БД

### Сводная таблица

| Таблица | created_at | updated_at | Дополнительные поля | Вывод |
|---------|-----------|-----------|-------------------|-------|
| **wb_orders** | ✅ | ✅ | `order_date` | Полная поддержка инкремента |
| **wb_products** | ✅ | ✅ | `is_active` | Полная поддержка инкремента |
| **wb_stocks** | ✅ | ✅ | `last_updated` | Полная поддержка инкремента |
| **wb_reviews** | ✅ | ✅ | `created_date`, `updated_date` | Полная поддержка инкремента |
| **wb_sales** | ✅ | ✅ | `sale_date`, `last_change_date` | Полная поддержка инкремента |

---

## ✅ Вывод: Идеальные условия для инкрементальной индексации!

**Все таблицы имеют необходимые поля для отслеживания изменений:**
- `created_at` → Время создания записи (server_default=func.now())
- `updated_at` → Время последнего обновления (onupdate=func.now())

**Это означает:**
1. ✅ Можем легко найти новые записи: `created_at > last_incremental_at`
2. ✅ Можем легко найти измененные записи: `updated_at > last_incremental_at`
3. ✅ Не нужны snapshot-based или hash-based стратегии для обнаружения изменений
4. ✅ Простая и эффективная реализация инкрементальной индексации

---

## 📋 Детальный анализ по таблицам

### 1. WBOrder (wb_orders)

**Схема полей:**
```python
id = Column(Integer, primary_key=True, index=True)
cabinet_id = Column(Integer, ForeignKey(...), index=True)
order_id = Column(String(100), index=True)
nm_id = Column(Integer, index=True)
name = Column(String(500))
# ... другие поля ...
order_date = Column(DateTime(timezone=True))  # Дата заказа
status = Column(String(50))
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Стратегия для инкрементальной индексации:**
```sql
-- Новые заказы
SELECT * FROM wb_orders
WHERE cabinet_id = ?
  AND order_date >= NOW() - INTERVAL '90 days'  -- Фильтр актуальности
  AND created_at > ?  -- Новые с last_incremental_at

-- Измененные заказы
SELECT * FROM wb_orders
WHERE cabinet_id = ?
  AND order_date >= NOW() - INTERVAL '90 days'
  AND updated_at > ?  -- Измененные с last_incremental_at
  AND created_at <= ?  -- Не новые (уже были проиндексированы)
```

**Критерий устаревания:**
- `order_date < NOW() - INTERVAL '90 days'` → Удалить из RAG

---

### 2. WBProduct (wb_products)

**Схема полей:**
```python
id = Column(Integer, primary_key=True, index=True)
cabinet_id = Column(Integer, ForeignKey(...), index=True)
nm_id = Column(Integer, index=True)
name = Column(String(500))
brand = Column(String(255))
category = Column(String(255))
price = Column(Float)
rating = Column(Float)
reviews_count = Column(Integer)
is_active = Column(Boolean, default=True)  # Флаг активности!
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Стратегия для инкрементальной индексации:**
```sql
-- Новые товары
SELECT * FROM wb_products
WHERE cabinet_id = ?
  AND is_active = true
  AND created_at > ?

-- Измененные товары
SELECT * FROM wb_products
WHERE cabinet_id = ?
  AND is_active = true
  AND updated_at > ?
  AND created_at <= ?
```

**Критерий устаревания:**
- `is_active = false` → Удалить из RAG

**Примечание:**
- Товары могут изменяться часто (цена, rating, reviews_count)
- Hash-based change detection поможет избежать лишних эмбеддингов при незначительных изменениях

---

### 3. WBStock (wb_stocks)

**Схема полей:**
```python
id = Column(Integer, primary_key=True, index=True)
cabinet_id = Column(Integer, ForeignKey(...), index=True)
nm_id = Column(Integer, index=True)
name = Column(String(500))
size = Column(String(50))
warehouse_name = Column(String(255))
quantity = Column(Integer)
last_updated = Column(DateTime(timezone=True))  # Время обновления от WB
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Стратегия для инкрементальной индексации:**
```sql
-- Новые остатки
SELECT * FROM wb_stocks
WHERE cabinet_id = ?
  AND quantity > 0  -- Только ненулевые остатки
  AND created_at > ?

-- Измененные остатки
SELECT * FROM wb_stocks
WHERE cabinet_id = ?
  AND quantity > 0
  AND updated_at > ?
  AND created_at <= ?
```

**Критерий устаревания:**
- `quantity = 0` → Удалить из RAG

**Особенность:**
- Поле `last_updated` - время обновления от WB API
- Поле `updated_at` - время изменения в нашей БД
- Используем `updated_at` для инкремента

---

### 4. WBReview (wb_reviews)

**Схема полей:**
```python
id = Column(Integer, primary_key=True, index=True)
cabinet_id = Column(Integer, ForeignKey(...), index=True)
nm_id = Column(Integer, index=True)
review_id = Column(String(100))
text = Column(Text)
rating = Column(Integer)
created_date = Column(DateTime(timezone=True))  # Дата от WB
updated_date = Column(DateTime(timezone=True))  # Обновление от WB
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Стратегия для инкрементальной индексации:**
```sql
-- Новые отзывы
SELECT * FROM wb_reviews
WHERE cabinet_id = ?
  AND created_date >= NOW() - INTERVAL '90 days'
  AND created_at > ?

-- Измененные отзывы
SELECT * FROM wb_reviews
WHERE cabinet_id = ?
  AND created_date >= NOW() - INTERVAL '90 days'
  AND updated_at > ?
  AND created_at <= ?
```

**Критерий устаревания:**
- `created_date < NOW() - INTERVAL '90 days'` → Удалить из RAG

**Примечание:**
- `created_date` / `updated_date` - время от WB API
- `created_at` / `updated_at` - время в нашей БД
- Используем `created_at` / `updated_at` для инкремента

---

### 5. WBSales (wb_sales)

**Схема полей:**
```python
id = Column(Integer, primary_key=True, index=True)
cabinet_id = Column(Integer, ForeignKey(...), index=True)
sale_id = Column(String(100), index=True)
nm_id = Column(Integer, index=True)
product_name = Column(String(500))
amount = Column(Float)
sale_date = Column(DateTime(timezone=True))  # Дата продажи от WB
type = Column(String(20), index=True)  # 'buyout' или 'return'
last_change_date = Column(DateTime(timezone=True))  # Последнее изменение от WB
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Стратегия для инкрементальной индексации:**
```sql
-- Новые продажи
SELECT * FROM wb_sales
WHERE cabinet_id = ?
  AND sale_date >= NOW() - INTERVAL '90 days'
  AND created_at > ?

-- Измененные продажи
SELECT * FROM wb_sales
WHERE cabinet_id = ?
  AND sale_date >= NOW() - INTERVAL '90 days'
  AND updated_at > ?
  AND created_at <= ?
```

**Критерий устаревания:**
- `sale_date < NOW() - INTERVAL '90 days'` → Удалить из RAG

**Примечание:**
- `sale_date` - дата продажи от WB
- `last_change_date` - последнее изменение от WB (например, возврат)
- `updated_at` имеет и `server_default` и `onupdate` - полная поддержка

---

## 🎯 Общая стратегия извлечения изменений

### Для новых записей:
```sql
WHERE cabinet_id = ?
  AND <актуальность_фильтр>  -- Зависит от типа данных
  AND created_at > ?  -- last_incremental_at
```

### Для измененных записей:
```sql
WHERE cabinet_id = ?
  AND <актуальность_фильтр>
  AND updated_at > ?  -- last_incremental_at
  AND created_at <= ?  -- Исключаем новые (уже обработаны)
```

### Фильтры актуальности:

| Таблица | Фильтр актуальности |
|---------|-------------------|
| wb_orders | `order_date >= NOW() - INTERVAL '90 days'` |
| wb_products | `is_active = true` |
| wb_stocks | `quantity > 0` |
| wb_reviews | `created_date >= NOW() - INTERVAL '90 days'` |
| wb_sales | `sale_date >= NOW() - INTERVAL '90 days'` |

---

## 🔧 Рекомендации по реализации

### 1. Использовать UNION для новых и измененных

**Преимущество:** Один запрос вместо двух

```sql
-- Пример для заказов
(
  -- Новые
  SELECT *, 'new' as change_type FROM wb_orders
  WHERE cabinet_id = ? AND order_date >= NOW() - INTERVAL '90 days'
    AND created_at > ?
)
UNION ALL
(
  -- Измененные
  SELECT *, 'updated' as change_type FROM wb_orders
  WHERE cabinet_id = ? AND order_date >= NOW() - INTERVAL '90 days'
    AND updated_at > ?
    AND created_at <= ?
)
```

---

### 2. Добавить индексы для оптимизации

**Текущие индексы:**
- ✅ `cabinet_id` - уже есть
- ✅ `created_at` - НЕТ! Нужно добавить
- ✅ `updated_at` - НЕТ! Нужно добавить

**Рекомендуемые индексы для добавления:**

```sql
-- Для всех таблиц (orders, products, stocks, reviews, sales)
CREATE INDEX idx_wb_orders_created_at ON wb_orders(created_at);
CREATE INDEX idx_wb_orders_updated_at ON wb_orders(updated_at);

CREATE INDEX idx_wb_products_created_at ON wb_products(created_at);
CREATE INDEX idx_wb_products_updated_at ON wb_products(updated_at);

CREATE INDEX idx_wb_stocks_created_at ON wb_stocks(created_at);
CREATE INDEX idx_wb_stocks_updated_at ON wb_stocks(updated_at);

CREATE INDEX idx_wb_reviews_created_at ON wb_reviews(created_at);
CREATE INDEX idx_wb_reviews_updated_at ON wb_reviews(updated_at);

CREATE INDEX idx_wb_sales_created_at ON wb_sales(created_at);
CREATE INDEX idx_wb_sales_updated_at ON wb_sales(updated_at);
```

**Составные индексы для еще большей оптимизации:**

```sql
-- Индексы для инкрементальных запросов
CREATE INDEX idx_wb_orders_cabinet_created ON wb_orders(cabinet_id, created_at);
CREATE INDEX idx_wb_orders_cabinet_updated ON wb_orders(cabinet_id, updated_at);

-- Аналогично для остальных таблиц
```

---

### 3. Hash-based change detection (опционально)

**Цель:** Избежать генерации эмбеддингов для записей, где chunk_text не изменился

**Пример:** Товар изменил `price` с 1000₽ на 1001₽
- `updated_at` изменился → запись попадает в инкремент
- Но chunk_text может остаться тем же: "Товар 'Платье' ... цена 1000₽"
  (если округляем цены или не включаем копейки)
- Hash не изменился → пропускаем генерацию эмбеддинга

**Реализация:**
- Добавить `chunk_hash` в `RAGMetadata`
- При обработке изменений сравнивать hash нового chunk_text с сохраненным
- Если совпадает → UPDATE только `updated_at` в RAG, не трогаем эмбеддинг

---

## 📊 Оценка эффективности

### Текущая ситуация (полная переиндексация):
- **Данные за 90 дней:**
  - Заказы: ~500 записей
  - Товары: ~100 записей
  - Остатки: ~300 записей
  - Отзывы: ~200 записей
  - Продажи: ~400 записей
- **Итого:** ~1500 чанков каждые 6 часов
- **Затраты:** $0.015 за индексацию

### Инкрементальная индексация (прогноз):
- **Изменения за 6 часов (оценка):**
  - Новые заказы: ~20-30
  - Измененные заказы: ~10-20 (смена статуса)
  - Измененные товары: ~5-10 (цена, рейтинг)
  - Измененные остатки: ~30-50 (количество)
  - Новые отзывы: ~2-5
  - Новые продажи: ~20-30
- **Итого:** ~100-150 чанков за индексацию
- **Экономия:** **90%** (1500 → 150)
- **Затраты:** $0.0015 за индексацию

### С hash-based optimization:
- Из 100-150 изменений ~30% не меняют chunk_text
- **Реальное количество:** ~70-105 чанков
- **Экономия:** **93%** (1500 → 105)
- **Затраты:** $0.001 за индексацию

---

## ✅ Выводы и следующие шаги

### Выводы:

1. ✅ **Все таблицы поддерживают инкрементальную индексацию**
   - Наличие `created_at` и `updated_at` во всех таблицах

2. ✅ **Простая реализация**
   - Не нужны snapshot или CDC
   - Стандартные SQL запросы с фильтрами по timestamp

3. ✅ **Высокая эффективность**
   - Прогнозируемая экономия: **90-93%** затрат на API
   - Ускорение индексации: **10-15x**

4. ⚠️ **Требуются индексы БД**
   - Добавить индексы на `created_at` и `updated_at`
   - Для оптимизации производительности

### Следующие шаги:

**Этап 1.2: Проектирование изменений в схеме RAG БД**
- [ ] Добавить `chunk_hash` в `RAGMetadata`
- [ ] Спроектировать миграцию для добавления индексов

**Этап 1.3: Документирование API контрактов**
- [ ] Добавить параметр `full_rebuild` в API
- [ ] Документировать новые метрики

**Этап 2: Реализация инкрементальной индексации**
- [ ] Реализовать `extract_incremental_changes()`
- [ ] Реализовать hash-based change detection
- [ ] Обновить Celery tasks

---

**Дата завершения:** 2025-12-16
**Статус:** ✅ Этап 1.1 завершен успешно
**Следующий этап:** 1.2 - Проектирование изменений в схеме RAG БД
