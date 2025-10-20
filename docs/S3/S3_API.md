# 📘 S3 API: Система уведомлений

## 🎯 Что реализовано

Централизованная система уведомлений для отслеживания событий Wildberries с поддержкой общих кабинетов. Уведомления доставляются через Telegram в реальном времени с настраиваемыми пользователем параметрами.

## 🔔 Типы уведомлений

| Тип | Описание | Статус |
|-----|----------|--------|
| 📦 Новые заказы | Новый заказ за период | ✅ Работает |
| 💰 Выкупы | Заказ перешел в статус "выкуплен" | ✅ Работает |
| ❌ Отмены | Заказ перешел в статус "отменен" | ✅ Работает |
| 🔄 Возвраты | Заказ перешел в статус "возврат" | ✅ Работает |
| ⭐ Негативные отзывы | Оценка 1–3★ | ✅ Работает |
| 📉 Критичные остатки | Количество товара ниже порога | ✅ Работает |

## 🔧 API Endpoints

### **Пользователи**

#### **POST /users/**
Создание пользователя
```bash
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

### **Кабинеты Wildberries**

#### **POST /wb/cabinets/**
Создание/подключение к кабинету
```bash
# Создание нового кабинета
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=1&api_key=YOUR_API_KEY&name=Test%20Cabinet"

# Подключение к существующему кабинету
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=2&api_key=EXISTING_API_KEY&name=Team%20Cabinet"
```

#### **GET /wb/cabinets/**
Получение кабинетов пользователя
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=1"
```

### **Настройки уведомлений**

#### **GET /api/v1/notifications/settings**
Получение настроек пользователя
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

#### **POST /api/v1/notifications/settings**
Обновление настроек
```bash
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{"notifications_enabled": true, "new_orders_enabled": true}' \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

### **Тестирование уведомлений**

#### **POST /api/v1/notifications/test**
Отправка тестового уведомления
```bash
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{"notification_type": "new_order", "test_data": {"order_id": 999, "product_name": "Тестовый товар", "amount": 1000}}' \
     "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789"
```

**Доступные типы уведомлений:**
- `new_order` - новый заказ
- `order_buyout` - выкуп заказа
- `order_cancellation` - отмена заказа
- `order_return` - возврат заказа
- `negative_review` - негативный отзыв
- `critical_stocks` - критичные остатки

### **Заказы и статистика**

#### **GET /api/v1/bot/orders/recent**
Последние заказы с фильтрацией
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

#### **GET /api/v1/bot/orders/statistics**
Полная статистика по заказам
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/statistics?telegram_id=123456789"
```

### **Продажи и возвраты**

#### **GET /api/v1/bot/sales/recent**
Последние продажи и возвраты
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/recent?user_id=1&limit=10"
```

#### **GET /api/v1/bot/sales/buyouts**
Только выкупы
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/buyouts?user_id=1"
```

#### **GET /api/v1/bot/sales/returns**
Только возвраты
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/returns?user_id=1"
```

#### **GET /api/v1/bot/sales/statistics**
Статистика продаж
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/statistics?user_id=1"
```

### **Валидация кабинетов**

#### **POST /api/v1/wb/cabinets/validation/validate-all**
Валидация всех кабинетов
```bash
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/wb/cabinets/validation/validate-all"
```

## 🧪 Ручное тестирование

### **1. Создание пользователей и кабинетов**
```bash
# Создание первого пользователя
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{
       "telegram_id": 123456789,
       "username": "test_user",
       "first_name": "Test",
       "last_name": "User"
     }' \
     "http://localhost:8000/users/"

# Создание кабинета
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=1&api_key=YOUR_API_KEY&name=Test%20Cabinet"

# Создание второго пользователя
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{
       "telegram_id": 987654321,
       "username": "second_user",
       "first_name": "Second",
       "last_name": "User"
     }' \
     "http://localhost:8000/users/"

# Подключение к существующему кабинету
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=2&api_key=EXISTING_API_KEY&name=Team%20Cabinet"
```

### **2. Тест настроек уведомлений**
```bash
# Получить настройки
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"

# Обновить настройки
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{"notifications_enabled": true, "new_orders_enabled": true}' \
     "http://localhost:8000/api/v1/notifications/settings?telegram_id=123456789"
```

### **3. Тест уведомлений**
```bash
# Тест нового заказа
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{"notification_type": "new_order", "test_data": {"order_id": 999, "product_name": "Тестовый товар", "amount": 1000}}' \
     "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789"

# Тест выкупа
curl -X POST -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     -H "Content-Type: application/json" \
     -d '{"notification_type": "order_buyout", "test_data": {"order_id": 999, "product_name": "Тестовый товар", "amount": 1000}}' \
     "http://localhost:8000/api/v1/notifications/test?telegram_id=123456789"
```

### **4. Тест заказов и статистики**
```bash
# Полная статистика заказов
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/statistics?telegram_id=123456789"

# Последние заказы (все)
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&limit=5"

# Только активные заказы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&status=active&limit=5"

# Только отмененные заказы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/orders/recent?telegram_id=123456789&status=canceled&limit=5"
```

### **5. Тест продаж**
```bash
# Статистика продаж
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/statistics?user_id=1"

# Последние продажи
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/recent?user_id=1&limit=10"

# Только выкупы
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/buyouts?user_id=1"

# Только возвраты
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/bot/sales/returns?user_id=1"
```

### **6. Тест общих кабинетов**
```bash
# Проверка кабинетов первого пользователя
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=1"

# Проверка кабинетов второго пользователя
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/wb/cabinets/?user_id=2"
```

### **7. Тест валидации API ключей**
```bash
# Валидация всех кабинетов
curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8000/api/v1/wb/cabinets/validation/validate-all"
```

## 🔄 Как работает система

### **Архитектура:**
```
WBSyncService → NotificationService → WebhookSender → Bot
     ↓              ↓                    ↓
Event Detector → Notification Generator → BotMessageFormatter
     ↓              ↓
Status Monitor → Settings CRUD
     ↓
   Redis Cache
```

### **Поток данных:**
1. **WBSyncService** синхронизирует данные с WB API каждые 3 минуты
2. **EventDetector** сравнивает текущие данные с предыдущими
3. **NotificationService** обрабатывает события и генерирует уведомления
4. **WebhookSender** отправляет уведомления в бот через webhook
5. **Bot** доставляет уведомления пользователю в Telegram

### **Настройки по умолчанию:**
- Все типы уведомлений включены
- Синхронизация каждые 3 минуты
- Retry логика: 3 попытки с экспоненциальной задержкой

## 📊 Мониторинг

### **Логи сервера:**
```bash
docker-compose logs -f server
```

### **Логи Celery:**
```bash
docker-compose logs -f celery-worker
```

### **Проверка Redis:**
```bash
docker-compose exec redis redis-cli
> KEYS notifications:*
```

## 🚨 Устранение неполадок

### **Проблема: Уведомления не приходят**
1. Проверить настройки пользователя: `GET /api/v1/notifications/settings`
2. Проверить логи сервера на ошибки
3. Проверить webhook URL в настройках

### **Проблема: Ошибка синхронизации**
1. Проверить API ключи WB
2. Проверить логи Celery worker
3. Проверить подключение к Redis

### **Проблема: Дубликаты уведомлений**
1. Проверить Redis на наличие старых состояний
2. Очистить кэш: `docker-compose exec redis redis-cli FLUSHDB`

## 🆕 Новые возможности S3.03

### **Общие кабинеты**
- **POST /wb/cabinets/** - создание/подключение к кабинету
- **GET /wb/cabinets/** - получение кабинетов пользователя
- Несколько пользователей могут использовать один кабинет
- Автоматическое подключение к существующему кабинету при повторном API ключе

### **Валидация API ключей**
- **POST /api/v1/wb/cabinets/validation/validate-all** - валидация всех кабинетов
- Автоматическое удаление неактуальных кабинетов
- Уведомления пользователей об удалении кабинетов

### **Полная статистика заказов**
- **GET /api/v1/bot/orders/statistics** - полная статистика по заказам
- Показывает активные, отмененные заказы и заказы без статуса
- Включает статистику продаж и возвратов
- Честные проценты и детальная аналитика

### **Фильтрация заказов по статусу**
- **GET /api/v1/bot/orders/recent?status=active** - только активные заказы
- **GET /api/v1/bot/orders/recent?status=canceled** - только отмененные заказы
- **GET /api/v1/bot/orders/recent** - все заказы (включая отмененные)

### **Улучшенная статистика продаж**
- **GET /api/v1/bot/sales/statistics** - детальная статистика продаж
- Показывает выкупы, возвраты, суммы и проценты
- Корректная синхронизация возвратов из WB API

### **Исправления**
- ✅ Убран фильтр исключающий отмененные заказы
- ✅ Исправлена логика определения возвратов
- ✅ Добавлена синхронизация Claims API
- ✅ Период синхронизации установлен в 1 месяц
- ✅ Исправлена двойная retry логика (9 попыток → 3 попытки)

---

*Версия: S3.03*  
*Статус: ✅ Полностью реализовано + Обновлено*  
*Тесты: 151+ тестов проходят*  
*Готовность: 100%*  
*Новые возможности: Общие кабинеты, валидация API ключей, полная статистика*
