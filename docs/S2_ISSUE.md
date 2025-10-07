# 🚨 S2 ISSUE: Проблема с nm_id в API ответах

## 📋 Описание проблемы

**Критическая проблема:** Параметр `nm_id` корректно сохраняется в базе данных, но теряется при обращении к серверным API эндпоинтам.

## 🔍 Детальный анализ

### ✅ Что работает правильно:

1. **WB API данные:**
   ```
   Step 2: nm_id = order_data.get('nmId') = 255366802
   Step 2: nm_id type = <class 'int'>
   Step 2: nm_id is None? False
   ```

2. **Создание объекта WBOrder:**
   ```
   Step 5: WBOrder created, nm_id=255366802
   Step 5: WBOrder nm_id type = <class 'int'>
   Step 5: WBOrder nm_id value = 255366802
   ```

3. **Сохранение в БД:**
   ```
   Step 7: Order flushed to DB
   Step 8: Committing transaction
   Step 9: Transaction committed successfully
   ```

4. **Проверка БД:**
   ```sql
   SELECT id, order_id, nm_id, name FROM wb_orders WHERE order_id = '2946945013846881169';
   -- Результат: id=1, nm_id=255366802, name='Блузки' ✅
   ```

5. **Формирование остатков:**
   ```
   DEBUG stocks: Found 53 stocks by nm_id
   DEBUG stocks_dict: Final result={'L': 27, 'M': 0, 'XL': 0, 'S': 17}
   ```

### ❌ Что НЕ работает:

1. **API ответы:**
   ```json
   {
     "nm_id": null,  // ❌ Должно быть 255366802
     "stocks": {}    // ❌ Должно быть {'L': 27, 'M': 0, 'XL': 0, 'S': 17}
   }
   ```

2. **Отладочные логи не показываются:**
   ```
   DEBUG final stocks: {order_data.get('stocks', {})}
   DEBUG final nm_id: {order_data.get('nm_id', 'NOT_FOUND')}
   ```
   **Эти логи НЕ появляются в выводе!**

## 🔧 Технические детали

### Путь данных:

1. **WB API → Синхронизация:**
   - ✅ `nm_id` получается из WB API
   - ✅ `nm_id` передается в WBOrder
   - ✅ `nm_id` сохраняется в БД

2. **БД → API ответ:**
   - ✅ `nm_id` читается из БД
   - ✅ `stocks` формируются по `nm_id`
   - ❌ **Данные теряются где-то в процессе формирования ответа**

### Код формирования ответа:

```python
# Формируем остатки по размерам
stocks_dict = {}
for stock in stocks:
    size = stock.size or "ONE SIZE"
    quantity = stock.quantity or 0
    stocks_dict[size] = quantity
# Результат: {'L': 27, 'M': 0, 'XL': 0, 'S': 17} ✅

# Формируем данные заказа
order_data = {
    "stocks": stocks_dict,  # ✅ Передается правильно
    "nm_id": order.nm_id,  # ✅ Передается правильно
    # ... другие поля
}

# Отладочные логи НЕ показываются!
logger.info(f"DEBUG final stocks: {order_data.get('stocks', {})}")
logger.info(f"DEBUG final nm_id: {order_data.get('nm_id', 'NOT_FOUND')}")
```

## 🎯 Гипотезы проблемы

### 1. **Ошибка в `_get_product_statistics`:**
   - Метод вызывает исключение
   - Код прерывается до финальных логов
   - **Проверено:** Проблема остается даже после закомментирования

### 2. **Ошибка в `format_order_detail`:**
   - Форматтер изменяет данные
   - **Проверено:** Проблема остается даже после закомментирования

### 3. **Проблема с сериализацией JSON:**
   - FastAPI не может сериализовать данные
   - **✅ РЕШЕНО:** Pydantic схемы отбрасывают поля

### 4. **Проблема с кэшированием:**
   - Данные кэшируются на уровне API
   - **Проверено:** Полная пересборка контейнеров не помогает

### 5. **Проблема с SQLAlchemy сессией:**
   - Сессия не видит изменения
   - Lazy loading не работает

## 🔍 Текущее состояние отладки

### Добавленные логи:
```python
# В get_order_detail
logger.info(f"DEBUG stocks: order.nm_id={order.nm_id}, type={type(order.nm_id)}")
logger.info(f"DEBUG stocks_dict: Final result={stocks_dict}")
logger.info(f"DEBUG final stocks: {order_data.get('stocks', {})}")
logger.info(f"DEBUG final nm_id: {order_data.get('nm_id', 'NOT_FOUND')}")
```

### Результат:
- ✅ Логи `DEBUG stocks` показываются
- ✅ Логи `DEBUG stocks_dict` показываются  
- ❌ Логи `DEBUG final` НЕ показываются

**Вывод:** Код прерывается между формированием `stocks_dict` и финальными логами!

## 🚨 Критичность

**ВЫСОКАЯ:** Без `nm_id` и остатков заказы не могут быть правильно проанализированы пользователями.

## 📝 Следующие шаги

1. **Найти точное место ошибки** между `stocks_dict` и финальными логами
2. **Проверить все методы** между этими точками
3. **Добавить try-catch** вокруг каждого блока кода
4. **Проверить Pydantic схемы** на предмет отбрасывания полей
5. **Проверить FastAPI сериализацию** JSON

## 🎯 Ожидаемый результат

```json
{
  "nm_id": 255366802,
  "stocks": {
    "L": 27,
    "M": 0, 
    "XL": 0,
    "S": 17
  }
}
```

## ✅ РЕШЕНИЕ

**Проблема была в Pydantic схеме `OrderData`!**

**Причина:** Pydantic отбрасывает поля, которых нет в схеме модели.

**Решение:** Добавлены поля `nm_id` и `stocks` в схему `OrderData`:

```python
class OrderData(BaseModel):
    # ... существующие поля ...
    # Поля для остатков и nm_id
    nm_id: Optional[int] = None
    stocks: Optional[Dict[str, int]] = None
```

**Результат:**
```json
{
  "nm_id": 255366802,
  "stocks": {
    "L": 27,
    "M": 0, 
    "XL": 0,
    "S": 17
  }
}
```

## 📊 Статус

- **Проблема:** ✅ РЕШЕНА
- **Приоритет:** Критический
- **Ответственный:** Backend Team
- **Дата создания:** 2025-10-07
- **Дата решения:** 2025-10-07
- **Последнее обновление:** 2025-10-07
