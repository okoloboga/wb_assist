# AI Chat Service - Архитектура

## 📐 Общая схема системы

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          WB Assist Ecosystem                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐ │
│  │   Server    │    │     Bot     │    │ GPT Service │    │ AI Chat  │ │
│  │  (port 8000)│    │ (port 8001) │    │ (port 9000) │    │(port 9001)│ │
│  │             │    │             │    │             │    │          │ │
│  │ • WB API    │◄───┤ • Commands  │───►│ • Analysis  │    │ • Chat   │ │
│  │ • PostgreSQL│    │ • Webhooks  │    │ • Reports   │    │ • Limits │ │
│  │ • Bot API   │    │ • Polling   │    │             │    │ • History│ │
│  └─────────────┘    └──────┬──────┘    └─────────────┘    └────┬─────┘ │
│                            │                                     │       │
│                            └─────────────────────────────────────┘       │
│                                   POST /v1/chat/send                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Поток данных

### 1. Пользовательский запрос

```
┌──────────┐
│ Telegram │
│   User   │
└────┬─────┘
     │ 1. Отправка команды /chat
     │    "Как увеличить продажи?"
     ▼
┌────────────┐
│ Telegram   │
│    Bot     │
│ (port 8001)│
└─────┬──────┘
      │ 2. POST /v1/chat/send
      │    {telegram_id, message}
      │    Header: X-API-KEY
      ▼
┌─────────────┐
│  AI Chat    │
│  Service    │
│ (port 9001) │
└──────┬──────┘
       │
       │ 3. Проверка лимитов
       │    └─► ai_chat_daily_limits (PostgreSQL)
       │
       │ 4. Получение контекста
       │    └─► ai_chat_requests (последние 5 сообщений)
       │
       │ 5. Формирование промпта
       │    └─► System Prompt + Context + User Message
       │
       │ 6. Вызов OpenAI API
       ▼
┌─────────────┐
│   OpenAI    │
│     API     │
└──────┬──────┘
       │ 7. Ответ от AI
       ▼
┌─────────────┐
│  AI Chat    │
│  Service    │
└──────┬──────┘
       │ 8. Сохранение в историю
       │    └─► ai_chat_requests
       │
       │ 9. Обновление счетчика
       │    └─► ai_chat_daily_limits
       │
       │ 10. Возврат ответа
       ▼
┌────────────┐
│ Telegram   │
│    Bot     │
└─────┬──────┘
      │ 11. Отправка ответа пользователю
      ▼
┌──────────┐
│ Telegram │
│   User   │
└──────────┘
```

## 🗄️ Структура базы данных

### Схема таблиц

```sql
┌─────────────────────────────────────────────────────┐
│             ai_chat_daily_limits                    │
├─────────────────────────────────────────────────────┤
│ id (PK)                  SERIAL                     │
│ telegram_id              BIGINT UNIQUE NOT NULL     │
│ request_count            INTEGER DEFAULT 0          │
│ last_reset_date          DATE NOT NULL              │
│ created_at               TIMESTAMP WITH TIME ZONE   │
│ updated_at               TIMESTAMP WITH TIME ZONE   │
└─────────────────────────────────────────────────────┘
                                ▲
                                │
                                │ Проверка лимитов
                                │
┌─────────────────────────────────────────────────────┐
│             ai_chat_requests                        │
├─────────────────────────────────────────────────────┤
│ id (PK)                  SERIAL                     │
│ telegram_id              BIGINT NOT NULL            │
│ user_id (FK)             INTEGER                    │
│ message                  TEXT NOT NULL              │
│ response                 TEXT NOT NULL              │
│ tokens_used              INTEGER DEFAULT 0          │
│ request_date             DATE NOT NULL              │
│ created_at               TIMESTAMP WITH TIME ZONE   │
└─────────────────────────────────────────────────────┘
```

### Связи

```
users (server/app/features/user/models.py)
  │
  └─► user_id (FK) ──┐
                     │
ai_chat_requests     │
  • История чата     │
  • Контекст AI      │
                     │
telegram_id ◄────────┘
  │
  └─► ai_chat_daily_limits
        • Счетчики
        • Лимиты
```

## 🏗️ Структура кода

```
ai_chat/
│
├── __init__.py                 # Инициализация модуля
├── service.py                  # FastAPI приложение (main)
├── models.py                   # SQLAlchemy модели
├── schemas.py                  # Pydantic схемы
├── database.py                 # Подключение к БД
├── crud.py                     # CRUD операции
├── prompts.py                  # Системные промпты
│
├── README.md                   # Краткая документация
├── AI_CHAT_SPECIFICATION.md    # Полное ТЗ
├── ARCHITECTURE.md             # Этот файл
├── requirements.txt            # Python зависимости
├── Dockerfile                  # Docker образ
├── env_example.txt             # Пример переменных окружения
└── .gitignore                  # Игнорируемые файлы
```

## 🔐 Безопасность

### Уровни защиты

```
┌─────────────────────────────────────────┐
│  1. API Key Authentication              │
│     └─► X-API-KEY header check          │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  2. Rate Limiting (Database)            │
│     └─► 30 requests/day per user        │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  3. Input Validation (Pydantic)         │
│     └─► Schema validation               │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  4. SQL Injection Protection            │
│     └─► SQLAlchemy ORM                  │
└─────────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  5. Context Limitation (AI Prompt)      │
│     └─► Only WB/e-commerce topics       │
└─────────────────────────────────────────┘
```

## 📊 Масштабирование

### Вертикальное масштабирование

```
┌────────────────────────────────────┐
│  Increase Resources                │
│  • CPU: 2 → 4 cores               │
│  • RAM: 2GB → 8GB                 │
│  • Database: Upgrade connection   │
│    pool size                       │
└────────────────────────────────────┘
```

### Горизонтальное масштабирование

```
                ┌─────────────┐
                │Load Balancer│
                │  (Nginx)    │
                └──────┬──────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │AI Chat 1│    │AI Chat 2│    │AI Chat 3│
  │ (9001)  │    │ (9002)  │    │ (9003)  │
  └────┬────┘    └────┬────┘    └────┬────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
              ┌───────▼────────┐
              │  PostgreSQL    │
              │  (Shared DB)   │
              └────────────────┘
```

### Кэширование (будущее улучшение)

```
┌────────────┐
│   Redis    │
│  (Cache)   │
└─────┬──────┘
      │ • Cache daily limits (faster than DB)
      │ • Cache recent contexts
      │ • Cache common questions/answers
      │
      ▼
┌─────────────┐
│  AI Chat    │
│  Service    │
└─────┬───────┘
      │ Fallback to PostgreSQL
      ▼
┌─────────────┐
│ PostgreSQL  │
└─────────────┘
```

## 🔄 Жизненный цикл запроса

### Успешный запрос

```
1. User sends message
2. Bot calls AI Chat API
3. Check API key ✓
4. Check rate limit (25/30) ✓
5. Get context from history (last 5 messages)
6. Build prompt (system + context + user message)
7. Call OpenAI API
8. Receive response
9. Save to ai_chat_requests ✓
10. Update ai_chat_daily_limits (26/30)
11. Return response to bot
12. Bot sends to user
```

### Запрос с превышением лимита

```
1. User sends message
2. Bot calls AI Chat API
3. Check API key ✓
4. Check rate limit (30/30) ✗
5. Return 429 Too Many Requests
6. Bot informs user about limit
```

### Ошибка OpenAI API

```
1. User sends message
2. Bot calls AI Chat API
3. Check API key ✓
4. Check rate limit (15/30) ✓
5. Get context from history
6. Build prompt
7. Call OpenAI API → ERROR (timeout/rate limit/etc)
8. Catch exception
9. Return 500 Internal Server Error with details
10. Bot shows error message to user
```

## 📈 Метрики производительности

### Целевые показатели

| Метрика | Целевое значение | Критическое значение |
|---------|------------------|---------------------|
| Время ответа API | < 3 секунды | > 10 секунд |
| Время запроса к OpenAI | < 2 секунды | > 8 секунд |
| Время проверки лимитов | < 50ms | > 200ms |
| Время сохранения в БД | < 100ms | > 500ms |
| Доступность сервиса | > 99.5% | < 95% |

### Мониторинг точки отказа

```
┌────────────────────────────────────────┐
│  Health Check Endpoint                 │
│  GET /health                           │
│  └─► Returns: {"status": "ok"}        │
└────────────────────────────────────────┘
                  │
                  │ Every 30 seconds
                  ▼
┌────────────────────────────────────────┐
│  Monitoring System                     │
│  (Prometheus/Grafana/Uptime Robot)    │
└────────────────────────────────────────┘
                  │
                  │ If DOWN
                  ▼
┌────────────────────────────────────────┐
│  Alert System                          │
│  • Email notification                  │
│  • Slack/Telegram alert                │
│  • Auto-restart (Docker)               │
└────────────────────────────────────────┘
```

## 🧩 Интеграция с другими сервисами

### Текущее состояние

```
┌─────────────┐
│   Server    │ ──► Потенциальная интеграция (получение данных пользователя)
│  (8000)     │     • Продажи
│             │     • Остатки
└─────────────┘     • Заказы

┌─────────────┐
│     Bot     │ ──► Активная интеграция
│  (8001)     │     • Отправка сообщений
│             │     • Получение ответов
└─────────────┘

┌─────────────┐
│GPT Analysis │ ──► Независимые сервисы (не пересекаются)
│  (9000)     │     • Анализ данных
│             │     • Отчеты
└─────────────┘
```

### Будущие улучшения

```
┌─────────────┐
│   Server    │
│  (8000)     │
└──────┬──────┘
       │ GET /api/v1/bot/user-context/{telegram_id}
       │ Returns: {sales, stocks, orders, reviews}
       ▼
┌─────────────┐
│  AI Chat    │ ──► Персонализированные ответы
│  (9001)     │     на основе реальных данных пользователя
└─────────────┘
```

## 🎯 Ключевые особенности архитектуры

### 1. Независимость (Loose Coupling)
- AI Chat работает автономно
- Не зависит от других микросервисов
- Может быть развернут отдельно

### 2. Масштабируемость (Scalability)
- Stateless сервис (можно запустить N копий)
- Общая БД для всех инстансов
- Load balancer для распределения нагрузки

### 3. Отказоустойчивость (Resilience)
- Health check для мониторинга
- Retry логика для OpenAI API
- Graceful degradation при ошибках

### 4. Безопасность (Security)
- API key authentication
- Rate limiting в БД
- Input validation
- Context limitation

### 5. Простота разработки (Simplicity)
- Чистая структура кода
- Понятные абстракции (Models, Schemas, CRUD)
- Подробная документация

---

**Версия:** 1.0.0  
**Дата:** 2025-10-29  
**Статус:** Production Ready

