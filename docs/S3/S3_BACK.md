# 📘 S3 Backend: Система уведомлений

## 🎯 Что реализовано

Полнофункциональная система уведомлений для отслеживания событий Wildberries с поддержкой общих кабинетов и polling архитектуры. Система работает в реальном времени с настраиваемыми пользователем параметрами.

## 🏗️ Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WB API        │───▶│  Sync Service    │───▶│   Database      │
│   (Wildberries) │    │  (Celery Tasks)  │    │   (PostgreSQL)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bot           │◀───│  Polling API     │◀───│ Notification   │
│   (Telegram)    │    │  (/poll)         │    │ Service         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📁 Структура файлов

### **Backend (Server)**
```
server/app/features/notifications/
├── notification_service.py      # Центральный сервис (обновлен)
├── event_detector.py           # Обнаружение событий (обновлен)
├── notification_generator.py   # Генерация уведомлений (обновлен)
├── models.py                   # Модели БД
├── crud.py                     # CRUD операции
├── schemas.py                  # Pydantic схемы
└── api/
    ├── polling.py              # Polling API endpoint
    ├── settings.py             # Настройки уведомлений
    └── test.py                 # Тестовые уведомления

server/app/utils/
└── timezone.py                 # Централизованный модуль timezone (новый)

server/app/features/wb_api/
├── sync_service.py             # Синхронизация с WB (обновлен)
├── client.py                   # WB API клиент (обновлен)
└── models.py                   # Модели WB данных
```

### **Frontend (Bot)**
```
bot/handlers/
├── polling.py                  # Polling система
├── notifications.py            # Обработка уведомлений
└── orders.py                   # Команды заказов
```

### **Sync Service**
```
server/app/features/wb_api/
├── sync_service.py             # Синхронизация с WB
├── models.py                   # Модели WB данных
└── crud_cabinet_users.py       # Управление кабинетами
```

## 🗄️ База данных

### **Основные таблицы**
- `wb_orders` - заказы WB
- `wb_products` - товары с изображениями
- `wb_stocks` - остатки товаров
- `wb_reviews` - отзывы
- `wb_sync_logs` - логи синхронизации
- `notification_settings` - настройки уведомлений
- `notification_history` - история отправленных уведомлений
- `cabinet_users` - связь пользователей с кабинетами

### **Ключевые поля**
- `WBProduct.image_url` - URL изображения товара
- `WBSyncLog.completed_at` - время завершения синхронизации
- `NotificationSettings.notifications_enabled` - глобальное включение/отключение

## 🔧 Как работает система

### **Поток данных:**
1. **Celery Beat** запускает периодические задачи синхронизации
2. **WBSyncService** получает данные из WB API с улучшенным rate limiting (Retry-After)
3. **NotificationService** сравнивает данные и обнаруживает события с защитой от дублирования
4. **TimezoneUtils** обеспечивает единую работу с МСК во всех компонентах
5. **Polling API** возвращает новые события боту
6. **Bot** отправляет уведомления пользователю в Telegram

### **Типы уведомлений:**
- 📦 **Новые заказы** - с изображениями товаров и защитой от дублирования
- 💰 **Выкупы заказов** - уведомления о выкупе
- ❌ **Отмены заказов** - уведомления об отмене
- 🔄 **Возвраты заказов** - уведомления о возврате
- ⭐ **Негативные отзывы** - отзывы с оценкой 1-3 звезды
- 📉 **Критичные остатки** - умная детекция с исключением межскладских переводов

## 🔧 API Endpoints

### **Polling API**
```bash
# Получение новых уведомлений
GET /api/v1/notifications/poll?telegram_id=123456789&last_check=2025-10-20T15:00:00Z

# Batch polling для нескольких пользователей
GET /api/v1/notifications/poll/batch?telegram_ids=123456789,987654321&last_check=2025-10-20T15:00:00Z
```

### **Настройки уведомлений**
```bash
# Получение настроек
GET /api/v1/notifications/settings?telegram_id=123456789

# Обновление настроек
POST /api/v1/notifications/settings?telegram_id=123456789
Content-Type: application/json
{
  "notifications_enabled": true,
  "new_orders_enabled": true,
  "order_buyouts_enabled": true,
  "order_cancellations_enabled": true,
  "order_returns_enabled": true,
  "negative_reviews_enabled": true,
  "critical_stocks_enabled": true,
  "grouping_enabled": true,
  "max_group_size": 5,
  "group_timeout": 300
}
```

### **Bot API**
```bash
# Dashboard
GET /api/v1/bot/dashboard?telegram_id=123456789

# Заказы
GET /api/v1/bot/orders/recent?telegram_id=123456789&limit=10&status=active
GET /api/v1/bot/orders/recent?telegram_id=123456789&limit=10&status=canceled

# Критические остатки
GET /api/v1/bot/stocks/critical?telegram_id=123456789&limit=20

# Отзывы
GET /api/v1/bot/reviews/summary?telegram_id=123456789&limit=10

# Аналитика
GET /api/v1/bot/analytics/sales?telegram_id=123456789&period=7d

# Синхронизация
POST /api/v1/bot/sync/start?telegram_id=123456789
GET /api/v1/bot/sync/status?telegram_id=123456789
```

### **Sales API**
```bash
# Последние продажи
GET /api/v1/bot/sales/recent?user_id=1&limit=10&sale_type=buyout

# Статистика продаж
GET /api/v1/bot/sales/statistics?user_id=1
```

## 🔧 Ручное тестирование

### **0. Подготовка системы**

#### **0.1 Запуск системы:**
```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps
```

#### **0.2 Создание пользователя:**
```bash
# Регистрация нового пользователя
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{
       "telegram_id": 123456789,
       "username": "test_user",
       "first_name": "Test",
       "last_name": "User"
     }' \
     "http://localhost:8000/users/"
```

#### **0.3 Подключение WB Cabinet:**
```bash
# Добавление API ключа WB (создает новый кабинет)
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=1&api_key=YOUR_API_KEY&name=Test%20Cabinet"

# Подключение к существующему кабинету (если API ключ уже есть)
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=2&api_key=EXISTING_API_KEY&name=Team%20Cabinet"
```

### **1. Тест polling системы:**

#### **1.1 Получение новых уведомлений:**
```bash
# Первый запрос (получить все события за последнюю минуту)
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/poll?telegram_id=123456789"

# Последующие запросы (только новые события)
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/poll?telegram_id=123456789&last_check=2025-10-20T15:00:00Z"
```

#### **1.2 Batch polling:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/poll/batch?telegram_ids=123456789,987654321"
```

### **2. Тест настроек уведомлений:**

#### **2.1 Получение текущих настроек:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

#### **2.2 Обновление настроек:**
```bash
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{
       "notifications_enabled": true,
       "new_orders_enabled": true,
       "order_buyouts_enabled": true,
       "order_cancellations_enabled": true,
       "order_returns_enabled": true,
       "negative_reviews_enabled": true,
       "critical_stocks_enabled": true
     }' \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

### **3. Тест Bot API:**

#### **3.1 Dashboard:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/dashboard?telegram_id=123456789"
```

#### **3.2 Заказы:**
```bash
# Все заказы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&limit=5"

# Только активные заказы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&status=active&limit=5"

# Только отмененные заказы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&status=canceled&limit=5"
```

#### **3.3 Критические остатки:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/stocks/critical?telegram_id=123456789&limit=20"
```

#### **3.4 Отзывы:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/reviews/summary?telegram_id=123456789&limit=10"
```

#### **3.5 Аналитика:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456789&period=7d"
```

### **4. Тест Sales API:**

#### **4.1 Последние продажи:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/recent?user_id=1&limit=10"

# Только выкупы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/recent?user_id=1&limit=10&sale_type=buyout"

# Только возвраты
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/recent?user_id=1&limit=10&sale_type=return"
```

### **5. Тест синхронизации:**

#### **5.1 Запуск синхронизации:**
```bash
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sync/start?telegram_id=123456789"
```

#### **5.2 Статус синхронизации:**
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sync/status?telegram_id=123456789"
```

## 📊 Мониторинг

### **Логи:**
```bash
# Логи сервера
docker-compose logs -f server

# Логи Celery
docker-compose logs -f celery-worker

# Логи бота
docker-compose logs -f bot
```

### **База данных:**
```bash
# Подключение к PostgreSQL
docker-compose exec postgres psql -U wb_user -d wb_assist

# Проверка логов синхронизации
SELECT * FROM wb_sync_logs ORDER BY created_at DESC LIMIT 10;

# Проверка настроек уведомлений
SELECT * FROM notification_settings;

# Проверка истории уведомлений
SELECT * FROM notification_history ORDER BY sent_at DESC LIMIT 10;
```

## 🚨 Устранение неполадок

### **Уведомления не приходят:**
1. Проверить настройки: `GET /api/v1/notifications/settings`
2. Проверить polling: `GET /api/v1/notifications/poll`
3. Проверить логи сервера и бота
4. Проверить статус синхронизации: `GET /api/v1/bot/sync/status`

### **Ошибка синхронизации:**
1. Проверить API ключи WB в логах Celery
2. Проверить таблицу `wb_sync_logs`
3. Проверить подключение к Redis
4. Проверить rate limiting WB API

### **Дубликаты уведомлений:**
1. Проверить логику фильтрации в `NotificationService._get_new_orders`
2. Проверить время `last_check` в polling
3. Проверить записи в `WBSyncLog`

### **Проблемы с изображениями:**
1. Проверить поле `WBProduct.image_url`
2. Проверить синхронизацию продуктов
3. Проверить URL изображений в WB API

## ⚙️ Настройки

### **Переменные окружения:**
```env
# Polling интервал (секунды)
POLLING_INTERVAL=30

# WB API rate limits
WB_API_RATE_LIMIT=30  # requests per minute
WB_API_INTERVAL=2000   # ms between requests

# API секретный ключ
API_SECRET_KEY=CnWvwoDwwGKh

# Синхронизация
SYNC_INTERVAL=180  # секунды (3 минуты)
```

### **Настройки по умолчанию:**
- Все типы уведомлений включены
- Polling каждые 30 секунд
- Синхронизация каждые 3 минуты
- Rate limiting: 30 запросов/минуту к WB API
- Retry логика: 3 попытки с экспоненциальной задержкой

## 🆕 Обновления S3.05

### **Новые возможности:**
- **Централизованный TimezoneUtils** - единый модуль для работы с МСК
- **Улучшенная обработка 429 ошибок** - чтение `Retry-After` заголовка
- **Защита от дублирования** - фильтрация через `NotificationHistory`
- **Умная детекция остатков** - исключение межскладских переводов
- **Оптимизация кода** - удаление неиспользуемых функций и дублирования

### **Исправления:**
- ✅ Создан централизованный `TimezoneUtils` модуль для единой работы с МСК
- ✅ Улучшена обработка 429 ошибок с чтением `Retry-After` заголовка
- ✅ Реализован агрессивный exponential backoff (до 5 минут для "sales" API)
- ✅ Добавлена защита от дублирования уведомлений через `NotificationHistory`
- ✅ Исправлена логика критических остатков - исключены межскладские переводы
- ✅ Удалены неиспользуемые webhook функции и параметры
- ✅ Устранено дублирование кода в форматировании времени
- ✅ Упрощена логика работы с timezone во всех компонентах

### **Новые компоненты:**
- `server/app/utils/timezone.py` - централизованный модуль timezone
- Улучшенная логика в `NotificationService._get_new_orders()`
- Улучшенная логика в `NotificationService._get_critical_stocks()`
- Улучшенная обработка в `WBAPIClient._make_request()`

### **Технические улучшения:**
- **Timezone consistency** - все операции через `TimezoneUtils`
- **Rate limiting** - улучшенная обработка 429 с `Retry-After`
- **Duplicate prevention** - защита через `NotificationHistory`
- **Smart detection** - умная фильтрация межскладских переводов
- **Code cleanup** - удалены неиспользуемые функции и дублирование

---

*Версия: S3.05*  
*Статус: ✅ Полностью реализовано + Оптимизация и исправления*  
*Архитектура: Polling + TimezoneUtils + Rate Limiting*  
*Готовность: 100%*  
*Новые возможности: TimezoneUtils, улучшенный rate limiting, защита от дублирования, умная детекция остатков*
