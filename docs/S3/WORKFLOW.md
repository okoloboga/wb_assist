# 📋 Система синхронизации и уведомлений - Детальная документация

## 🎯 Общая архитектура системы

### **Основной принцип работы:**
Система работает по принципу **инкрементальной синхронизации** с уведомлениями только о **новых событиях**, произошедших с момента последней синхронизации.

---

## 🔄 Процесс синхронизации

### **1. Первичная синхронизация (First Sync)**

**Триггер:** Пользователь вводит WB API ключ впервые

**Процесс:**
1. **Проверка API ключа** - валидация через WB API
2. **Создание кабинета** - `WBCabinet` с `last_sync_at = NULL`
3. **Загрузка исторических данных** за период `SYNC_DAYS` дней
4. **Флаг уведомлений:** `should_notify = False` (НЕ отправляем уведомления)
5. **Сохранение в БД** как "базовая линия" для сравнений
6. **Обновление** `cabinet.last_sync_at = now()`
7. **Отправка одного уведомления** о завершении с главным меню

**Код:**
```python
# server/app/features/wb_api/sync_service.py:1466-1488
async def _should_send_notification(self, cabinet: WBCabinet) -> bool:
    if not cabinet.last_sync_at:  # Первая синхронизация
        return False
    # ... проверки времени
```

### **2. Последующие синхронизации (Incremental Sync)**

**Триггер:** Celery Beat каждые `SYNC_INTERVAL` секунд

**Процесс:**
1. **Проверка времени:** `cabinet.last_sync_at` существует и < 24 часов
2. **Флаг уведомлений:** `should_notify = True`
3. **Получение данных** с WB API с момента `last_sync_at`
4. **Сравнение** с предыдущим состоянием в БД
5. **Обнаружение изменений** и отправка уведомлений
6. **Обновление** `cabinet.last_sync_at = now()`

---

## 🔍 Определение новых событий

### **Критерий "новизны":**
Система использует **`created_at`** (время добавления в БД), а НЕ `order_date` из WB API

**Код:**
```python
# server/app/features/notifications/notification_service.py:834
orders = self.db.query(WBOrder).filter(
    WBOrder.created_at > last_check,  # ← КЛЮЧЕВОЕ ПОЛЕ!
    ~WBOrder.order_id.in_(sent_order_ids)  # Исключаем дубликаты
).all()
```

**Логика:**
- `created_at` - время когда запись появилась в нашей БД
- `order_date` - время создания заказа в WB (может быть старым)
- Используем `created_at` чтобы ловить именно **новые записи в БД**

---

## 📊 Отслеживание изменений статуса заказов

### **Механика работы:**

**Сценарий:**
```
Заказ #12345: new → buyout → return
```

**Уведомления:**
1. **new_order** - при создании заказа
2. **order_buyout** - при выкупе (тот же order_id)
3. **order_return** - при возврате (тот же order_id)

### **Отслеживание статусов:**

**1. Через Redis (StatusChangeMonitor):**
```python
# server/app/features/notifications/status_monitor.py:33-47
def get_previous_state(self, user_id: int, redis_client) -> Dict[str, str]:
    state_data = redis_client.get(f"notifications:order_status:{user_id}")
    # Сохраняет: {order_id: status}
```

**2. Через БД (OrderStatusHistory):**
```python
# server/app/features/notifications/models.py:60-75
class OrderStatusHistory(Base):
    order_id = Column(Integer, nullable=False, index=True)
    previous_status = Column(String(50), nullable=True)
    current_status = Column(String(50), nullable=False)
    notification_sent = Column(Boolean, default=False)
```

**3. Сравнение состояний:**
```python
# server/app/features/notifications/status_monitor.py:66-96
def compare_order_states(self, previous_state, current_orders):
    for order in current_orders:
        previous_status = previous_state.get(order_id)
        current_status = order.get("status")
        
        if previous_status != current_status:
            # Создаем событие изменения статуса
```

---

## 🏪 Критические остатки - Агрегация по складам

### **Проблема межскладских переводов:**
```
Склад A: 100 → 0 (перевод на склад B)
Склад B: 0 → 100 (получение с склада A)
Общий остаток: 100 (не изменился)
```

### **Решение - агрегация по товарам:**
```python
# server/app/features/notifications/notification_service.py:1043-1070
def group_stocks_by_product(stocks):
    grouped = {}
    for stock in stocks:
        key = (stock.nm_id, stock.size or "")  # Группируем по товару+размер
        grouped[key] = stock.quantity

# Суммируем остатки по всем складам
current_total = sum(stock.quantity for stock in current_stock_list)
previous_total = sum(stock.quantity for stock in prev_stock_list)

# Проверяем реальное уменьшение
if (previous_total > threshold and 
    current_total <= threshold and 
    current_total < previous_total):
    # Отправляем уведомление
```

---

## 🛡️ Защита от дублирования уведомлений

### **Многоуровневая защита:**

**Уровень 1: NotificationHistory (основная)**
```python
# server/app/features/notifications/notification_service.py:1201-1269
def _save_notification_to_history(self, user_id, notification, result):
    # Генерируем уникальный ID
    notification_id = f"notif_{type}_{unique_key}_{timestamp}"
    
    # Проверяем существование
    existing = self.db.query(NotificationHistory).filter(
        NotificationHistory.id == notification_id
    ).first()
```

**Уровень 2: Проверка уже отправленных**
```python
# server/app/features/notifications/notification_service.py:810-827
sent_notifications = self.db.query(NotificationHistory).filter(
    NotificationHistory.user_id == user_id,
    NotificationHistory.notification_type == "new_order",
    NotificationHistory.sent_at > last_check - timedelta(hours=24)
).all()

# Извлекаем order_id из JSON content
sent_order_ids = set()
for n in sent_notifications:
    content_data = json.loads(n.content)
    sent_order_ids.add(content_data["order_id"])
```

**Уровень 3: Исключение из запросов**
```python
# server/app/features/notifications/notification_service.py:834-836
orders = self.db.query(WBOrder).filter(
    ~WBOrder.order_id.in_(sent_order_ids)  # Исключаем уже отправленные
).all()
```

---

## 📝 Типы уведомлений и их обработка

### **1. Новые заказы (new_order)**
- **Триггер:** `WBOrder.created_at > last_check`
- **Фильтр:** Исключаем уже отправленные по `order_id`
- **Формат:** Детальная информация о заказе

### **2. Изменения статуса заказов**
- **order_buyout** - заказ выкуплен
- **order_cancellation** - заказ отменен  
- **order_return** - заказ возвращен
- **Триггер:** Изменение `status` в `WBOrder`
- **Отслеживание:** Через `StatusChangeMonitor` (Redis) + `OrderStatusHistory` (БД)

### **3. Негативные отзывы (negative_review)**
- **Триггер:** `WBReview.rating <= 3` И `WBReview.created_date > last_check`
- **Фильтр:** Только новые отзывы (не исторические)
- **Формат:** Рейтинг + текст отзыва

### **4. Критические остатки (critical_stocks)**
- **Триггер:** Сумма остатков по всем складам перешла порог (≤ 2)
- **Фильтр:** Реальное уменьшение (не межскладские переводы)
- **Агрегация:** По `nm_id` + `size`

---

## ⚙️ Настройки пользователя

### **Глобальные настройки:**
```python
# server/app/features/notifications/models.py:10-35
class NotificationSettings(Base):
    notifications_enabled = Column(Boolean, default=True)
    new_orders_enabled = Column(Boolean, default=True)
    order_buyouts_enabled = Column(Boolean, default=True)
    order_cancellations_enabled = Column(Boolean, default=True)
    order_returns_enabled = Column(Boolean, default=True)
    negative_reviews_enabled = Column(Boolean, default=True)
    critical_stocks_enabled = Column(Boolean, default=True)
```

### **Применение настроек:**
```python
# server/app/features/notifications/notification_service.py:100-103
if not user_settings.notifications_enabled:
    return {"status": "disabled", "notifications_sent": 0}

# Проверка конкретного типа
if user_settings.new_orders_enabled:
    # Обрабатываем новые заказы
```

---

## 🔄 Обработка пропущенных синхронизаций

### **Сценарий пропуска:**
```
Синхронизация 1: 10:00 (успешно)
Синхронизация 2: 10:05 (пропущена - ошибка)
Синхронизация 3: 10:10 (получает данные за 10:00-10:10)
```

### **Результат:**
- Пользователь получит уведомления за **2 окна** сразу
- Это **нормальное поведение** - не критично
- Система автоматически восстановится

### **Защита от старых событий:**
```python
# server/app/features/wb_api/sync_service.py:1479-1480
if time_diff > timedelta(hours=24):
    return False  # Не отправляем уведомления при долгом перерыве
```

---

## 📊 Форматирование уведомлений

### **Единый формат через BotMessageFormatter:**
```python
# server/app/features/notifications/notification_service.py:144
telegram_text = self._format_notification_for_telegram(clean_event)

# Для заказов используется детальный формат
if notification_type in ["new_order", "order_buyout", "order_cancellation", "order_return"]:
    order_data = self._convert_notification_to_order_format(notification)
    return self.message_formatter.format_order_detail({"order": order_data})
```

### **Структура уведомления:**
```python
{
    "type": "new_order",
    "user_id": 123,
    "data": {
        "order_id": "12345",
        "product_name": "Товар",
        "amount": 1500,
        "image_url": "https://...",
        # ... другие поля
    },
    "telegram_text": "🧾 НОВЫЙ ЗАКАЗ [#12345]...",
    "created_at": "2024-01-28T10:00:00",
    "priority": "MEDIUM"
}
```

---

## 🚨 Проблемы с дублированием (текущие)

### **1. Race Conditions**
**Проблема:** Два процесса синхронизации одновременно
**Решение:** Блокировки через `_get_sync_lock()`

### **2. Временные окна**
**Проблема:** Защита работает только 24 часа
**Текущее решение:** При долгом перерыве отключаем уведомления

### **3. Сложная логика парсинга JSON**
**Проблема:** Извлечение ID из `NotificationHistory.content`
**Риск:** Ошибки парсинга могут пропустить дубликаты

### **4. Производительность**
**Проблема:** Множественные запросы к `NotificationHistory`
**Решение:** Использовать Redis для быстрых проверок

---

## 🎯 Рекомендации по улучшению

### **1. Упростить логику дублирования**
- Использовать Redis Set для быстрых проверок
- Единый метод проверки для всех типов уведомлений

### **2. Улучшить отслеживание статусов**
- Унифицировать логику через `StatusChangeMonitor`
- Убрать дублирование между Redis и БД

### **3. Оптимизировать производительность**
- Кэшировать часто используемые данные
- Батчевые операции для БД

### **4. Добавить мониторинг**
- Метрики дублирования
- Алерты при проблемах

---

## 📈 Итоговая оценка системы

**Текущее состояние:** 7/10
- ✅ Правильная архитектура инкрементальной синхронизации
- ✅ Корректное определение новых событий через `created_at`
- ✅ Умная агрегация остатков по складам
- ✅ Многоуровневая защита от дублирования
- ❌ Сложная логика проверки дублирования
- ❌ Потенциальные race conditions
- ❌ Производительность при больших объемах

**После улучшений:** 9/10
- ✅ Упрощенная логика дублирования
- ✅ Оптимизированная производительность
- ✅ Надежная защита от race conditions
- ✅ Мониторинг и метрики
