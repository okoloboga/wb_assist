# Тестирование системы уведомлений

## 🎯 Цель
Проверить работу системы уведомлений после исправления критических ошибок.

## 📋 Подготовка

### 1. Проверьте настройки
Убедитесь, что у вас есть:
- Запущенный контейнер с проектом
- Пользователь в БД с `telegram_id`
- Настроенный `bot_webhook_url` для пользователя

### 2. Найдите ваш telegram_id
```sql
SELECT id, telegram_id, bot_webhook_url FROM users WHERE telegram_id IS NOT NULL;
```

## 🧪 Варианты тестирования

### Вариант 1: HTTP API запросы (рекомендуется)

#### 1.1 Запуск обработки событий синхронизации
```bash
curl -X POST "http://localhost:8000/notifications/test/trigger-sync-events?telegram_id=YOUR_TELEGRAM_ID"
```

**Ожидаемый результат:**
```json
{
  "success": true,
  "message": "Sync events processed",
  "result": {
    "status": "success",
    "events_processed": X,
    "notifications_sent": Y,
    "events": [...]
  }
}
```

#### 1.2 Отправка тестового уведомления
```bash
curl -X POST "http://localhost:8000/notifications/test/test" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "test",
    "test_data": {
      "message": "Тестовое уведомление",
      "timestamp": "2024-01-01T12:00:00Z"
    }
  }' \
  -G -d "telegram_id=YOUR_TELEGRAM_ID"
```

### Вариант 2: Python скрипты

#### 2.1 Создание тестовых данных
```bash
# В контейнере или локально
python create_test_data.py
```

#### 2.2 Запуск тестирования
```bash
# В контейнере или локально
python test_notification_system.py
```

#### 2.3 Простое тестирование через HTTP
```bash
# В контейнере или локально
python test_notifications_simple.py
```

### Вариант 3: Прямые SQL запросы

#### 3.1 Проверка данных
```sql
-- Проверка пользователя
SELECT id, telegram_id, bot_webhook_url FROM users WHERE telegram_id = YOUR_TELEGRAM_ID;

-- Проверка кабинета
SELECT id, user_id, last_sync_at FROM wb_cabinets WHERE user_id = YOUR_USER_ID;

-- Проверка заказов
SELECT order_id, status, created_at, updated_at FROM wb_orders 
WHERE cabinet_id = YOUR_CABINET_ID 
ORDER BY updated_at DESC LIMIT 10;

-- Проверка отзывов
SELECT review_id, rating, created_date FROM wb_reviews 
WHERE cabinet_id = YOUR_CABINET_ID 
ORDER BY created_date DESC LIMIT 10;

-- Проверка остатков
SELECT nm_id, quantity, updated_at FROM wb_stocks 
WHERE cabinet_id = YOUR_CABINET_ID 
ORDER BY updated_at DESC LIMIT 10;
```

#### 3.2 Создание тестовых данных
```sql
-- Создание тестового заказа
INSERT INTO wb_orders (cabinet_id, order_id, nm_id, status, order_date, created_at, updated_at)
VALUES (YOUR_CABINET_ID, 9999999999999999999, 123456789, 'active', NOW() - INTERVAL '1 day', NOW() - INTERVAL '15 minutes', NOW() - INTERVAL '10 minutes');

-- Создание тестового отзыва
INSERT INTO wb_reviews (cabinet_id, review_id, nm_id, rating, text, created_date)
VALUES (YOUR_CABINET_ID, 8888888888888888888, 123456789, 1, 'Тестовый негативный отзыв', NOW() - INTERVAL '12 minutes');

-- Создание тестового остатка
INSERT INTO wb_stocks (cabinet_id, nm_id, quantity, updated_at)
VALUES (YOUR_CABINET_ID, 123456789, 5, NOW() - INTERVAL '18 minutes');
```

#### 3.3 Обновление времени синхронизации
```sql
-- Установка времени последней синхронизации на 1 час назад
UPDATE wb_cabinets 
SET last_sync_at = NOW() - INTERVAL '1 hour' 
WHERE id = YOUR_CABINET_ID;
```

## 🔍 Проверка результатов

### 1. Проверка логов
```bash
# Логи сервера
docker logs -f server-container

# Логи celery
docker logs -f celery-worker-container

# Логи бота
docker logs -f bot-container
```

### 2. Проверка истории уведомлений
```sql
SELECT event_type, content, created_at, webhook_result 
FROM notification_history 
WHERE user_id = YOUR_USER_ID 
ORDER BY created_at DESC LIMIT 10;
```

### 3. Проверка Telegram бота
- Проверьте, приходят ли уведомления в Telegram
- Проверьте формат уведомлений
- Проверьте корректность данных

## 🚨 Возможные проблемы

### 1. Пользователь не найден
```
❌ User not found
```
**Решение:** Создайте пользователя через бота или напрямую в БД

### 2. Webhook URL не настроен
```
❌ Webhook URL not configured
```
**Решение:** Установите `bot_webhook_url` для пользователя

### 3. Нет тестовых данных
```
❌ No events found
```
**Решение:** Создайте тестовые данные с помощью скрипта или SQL

### 4. Ошибки подключения
```
❌ Connection error
```
**Решение:** Проверьте доступность API и правильность URL

## 📊 Ожидаемые результаты

### Успешное тестирование:
1. ✅ API доступен
2. ✅ Пользователь найден
3. ✅ Кабинет найден
4. ✅ Тестовые данные созданы
5. ✅ События обработаны
6. ✅ Уведомления отправлены
7. ✅ История уведомлений записана
8. ✅ Уведомления пришли в Telegram

### Критерии успеха:
- `events_processed > 0` - события найдены
- `notifications_sent > 0` - уведомления отправлены
- `webhook_result.success = true` - webhook успешно отправлен
- Уведомления приходят в Telegram бот

## 🔧 Дополнительные команды

### Проверка статуса системы
```bash
# Проверка здоровья API
curl http://localhost:8000/health

# Проверка статуса Celery
curl http://localhost:8000/celery/status

# Проверка метрик
curl http://localhost:8000/metrics
```

### Очистка тестовых данных
```sql
-- Удаление тестовых заказов
DELETE FROM wb_orders WHERE order_id >= 9999999999999999999;

-- Удаление тестовых отзывов
DELETE FROM wb_reviews WHERE review_id >= 8888888888888888888;

-- Удаление тестовых остатков
DELETE FROM wb_stocks WHERE nm_id = 123456789;

-- Удаление истории уведомлений
DELETE FROM notification_history WHERE user_id = YOUR_USER_ID;
```

## 📝 Отчет о тестировании

После тестирования заполните:

- [ ] API доступен
- [ ] Пользователь найден
- [ ] Кабинет найден
- [ ] Тестовые данные созданы
- [ ] События обработаны
- [ ] Уведомления отправлены
- [ ] История уведомлений записана
- [ ] Уведомления пришли в Telegram
- [ ] Формат уведомлений корректен
- [ ] Данные в уведомлениях актуальны

**Результат:** ✅ Успешно / ❌ Ошибки

**Комментарии:**
