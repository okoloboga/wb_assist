# AI Chat Service - Техническое задание

## 📋 Общее описание

**AI Chat Service** — отдельный FastAPI-сервис для общения пользователей с AI-ассистентом по теме Wildberries и e-commerce. Сервис интегрируется с основным бэкендом, Telegram ботом и имеет собственную базу данных для отслеживания лимитов запросов.

### Основная цель
Предоставить пользователям возможность общаться с AI по темам:
- Аналитика продаж на Wildberries
- Работа с заказами и остатками
- Стратегии ценообразования
- Отзывы и рейтинги
- Логистика и склады WB
- Общие вопросы по e-commerce

### Ключевые требования
- ⚡ Ограничение запросов: **30 запросов в сутки на пользователя**
- 💾 Хранение истории чата в базе данных
- 🎯 Контекстное ограничение тематики (только WB и e-commerce)
- 🔌 Интеграция с Telegram ботом через REST API
- 🐳 Отдельный микросервис в Docker (аналогично `gpt_integration`)
- 🔒 Защита всех эндпоинтов API ключом
- 📊 Логирование всех операций

---

## 🏗️ Архитектура

### Компоненты системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Server   │    │   Telegram Bot  │    │  GPT Analysis   │    │   AI Chat       │
│   (port 8000)   │    │   (port 8001)   │    │   (port 9000)   │    │   (port 9001)   │
│                 │    │                 │    │                 │    │                 │
│ • PostgreSQL    │    │ • User Commands │    │ • Data Analysis │    │ • Chat History  │
│ • WB API        │◄───┤ • Notifications │    │ • Reports       │    │ • Rate Limits   │
│ • Bot API       │    │ • Webhooks      │───►│ • Async Tasks   │    │ • Context AI    │
│ • User Data     │    │                 │    │                 │    │ • PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                                              ▲
                                │                                              │
                                └──────────────────────────────────────────────┘
                                         POST /v1/chat/send
```

### Поток работы

1. **Пользователь отправляет сообщение** через Telegram бота
2. **Бот вызывает** `POST /v1/chat/send` с `telegram_id` и `message`
3. **AI Chat проверяет лимиты** в таблице `ai_chat_daily_limits`
4. **Если лимит превышен** → возвращает ошибку 429 (Too Many Requests)
5. **Если лимит не превышен**:
   - Формирует системный промпт с ограничением тематики
   - Получает последние N сообщений из истории для контекста
   - Отправляет запрос к OpenAI API
   - Сохраняет запрос и ответ в `ai_chat_requests`
   - Обновляет счетчик в `ai_chat_daily_limits`
   - Возвращает ответ боту
6. **Бот отправляет ответ** пользователю в Telegram

---

## 🗄️ База данных

### Структура таблиц

#### Таблица 1: `ai_chat_requests`
Хранит полную историю общения пользователей с AI.

```sql
CREATE TABLE ai_chat_requests (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    request_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Индексы для быстрого поиска
    INDEX idx_telegram_id (telegram_id),
    INDEX idx_user_id (user_id),
    INDEX idx_request_date (request_date),
    INDEX idx_created_at (created_at)
);
```

**Поля:**
- `id` — уникальный идентификатор записи
- `telegram_id` — ID пользователя в Telegram (обязательно)
- `user_id` — ID пользователя в таблице users (может быть NULL)
- `message` — текст запроса пользователя
- `response` — ответ AI
- `tokens_used` — количество использованных токенов (для статистики)
- `request_date` — дата запроса (для группировки по дням)
- `created_at` — точное время запроса

#### Таблица 2: `ai_chat_daily_limits`
Хранит счетчики запросов для быстрой проверки лимитов.

```sql
CREATE TABLE ai_chat_daily_limits (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    request_count INTEGER DEFAULT 0 NOT NULL,
    last_reset_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Индексы
    INDEX idx_telegram_id (telegram_id),
    INDEX idx_last_reset (last_reset_date)
);
```

**Поля:**
- `id` — уникальный идентификатор
- `telegram_id` — ID пользователя (уникальный)
- `request_count` — количество запросов за текущий день
- `last_reset_date` — дата последнего сброса счетчика
- `created_at` — дата создания записи
- `updated_at` — дата последнего обновления

**Логика работы:**
- Каждый день автоматически сбрасывается `request_count` на 0
- При каждом запросе увеличивается `request_count`
- Если `request_count >= 30` → отказ в обслуживании

---

## 📦 Модели данных (SQLAlchemy)

### Файл: `models.py`

**Требования к реализации:**

#### Модель `AIChatRequest`
Создать SQLAlchemy модель для хранения истории запросов:
- Наследуется от `Base`
- Имя таблицы: `ai_chat_requests`
- Содержит все поля из SQL схемы выше
- Использует `func.now()` для автоматического `created_at`
- Имеет понятный `__repr__` для отладки

#### Модель `AIChatDailyLimit`
Создать SQLAlchemy модель для счетчиков лимитов:
- Наследуется от `Base`
- Имя таблицы: `ai_chat_daily_limits`
- Содержит все поля из SQL схемы выше
- Использует `onupdate=func.now()` для автоматического `updated_at`
- Имеет понятный `__repr__` показывающий текущий счетчик (например: "15/30")

---

## 📝 Schemas (Pydantic)

### Файл: `schemas.py`

**Требования к реализации:**

Создать Pydantic схемы для валидации запросов/ответов API:

#### Request/Response схемы для `/v1/chat/send`:
- **ChatSendRequest**: `telegram_id` (int), `message` (str, 1-4000 символов)
- **ChatSendResponse**: `response` (str), `remaining_requests` (int), `tokens_used` (int)

#### Request/Response схемы для `/v1/chat/history`:
- **ChatHistoryRequest**: `telegram_id` (int), `limit` (int, 1-100, default=10), `offset` (int, >=0, default=0)
- **ChatHistoryItem**: `id`, `message`, `response`, `tokens_used`, `created_at` (с `from_attributes=True`)
- **ChatHistoryResponse**: `items` (List[ChatHistoryItem]), `total`, `limit`, `offset`

#### Response схема для `/v1/chat/limits/{telegram_id}`:
- **ChatLimitsResponse**: `telegram_id`, `requests_today`, `requests_remaining`, `daily_limit`, `reset_date`

#### Request/Response схемы для `/v1/chat/reset-limit`:
- **ResetLimitRequest**: `telegram_id` (int)
- **ResetLimitResponse**: `success` (bool), `message` (str)

**Требования:**
- Использовать `Field()` для описаний и валидации
- Добавлять docstring к каждой схеме
- Использовать type hints (typing.Optional, typing.List)

---

## 🔧 CRUD операции

### Файл: `crud.py`

**Требования к реализации:**

Создать класс `AIChatCRUD` с методами для работы с базой данных:

#### Константы:
- `DAILY_LIMIT = 30` - дневной лимит запросов

#### Конструктор:
- Принимает `db: Session` и сохраняет в `self.db`

#### Метод `check_and_update_limit(telegram_id: int) -> Tuple[bool, int]`
**Логика:**
1. Получить запись из `ai_chat_daily_limits` по `telegram_id`
2. Если записи нет → создать новую с `request_count=0`
3. Если `last_reset_date` < сегодня → сбросить счетчик (`request_count=0`)
4. Проверить: если `request_count >= DAILY_LIMIT` → вернуть `(False, 0)`
5. Увеличить `request_count` на 1, обновить `updated_at`
6. Вернуть `(True, remaining)` где `remaining = DAILY_LIMIT - request_count`
7. Логировать все операции с эмодзи (✨ создание, 🔄 сброс, ⛔ превышение, ✅ разрешение)

#### Метод `get_limits(telegram_id: int) -> dict`
**Возвращает словарь:**
- `requests_today`: текущий счетчик
- `requests_remaining`: осталось запросов
- `daily_limit`: дневной лимит (30)
- `reset_date`: дата последнего сброса
**НЕ изменяет** счетчик запросов!

#### Метод `save_chat_request(telegram_id, user_id, message, response, tokens_used) -> AIChatRequest`
- Создать запись `AIChatRequest` с текущей датой
- Сохранить в БД, вернуть объект
- Логировать: `💾 Saved chat request: telegram_id=..., tokens=...`

#### Метод `get_chat_history(telegram_id, limit=10, offset=0) -> Tuple[List[AIChatRequest], int]`
- Получить историю чата пользователя
- Сортировка: по `created_at` DESC (новые первые)
- Пагинация через `limit` и `offset`
- Вернуть `(список записей, общее количество)`
- Логировать: `📜 Retrieved chat history: telegram_id=..., total=..., returned=...`

#### Метод `get_recent_context(telegram_id, limit=5) -> List[dict]`
- Получить последние N сообщений для контекста AI
- Вернуть список словарей: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]`
- Порядок: от старых к новым (reversed)
- Логировать: `🔍 Retrieved context: telegram_id=..., messages=...`

#### Метод `reset_user_limit(telegram_id: int) -> bool`
- Сбросить лимит пользователя (admin функция)
- Установить `request_count=0`, `last_reset_date=today`, `updated_at=now`
- Вернуть `True` если успешно, `False` если пользователь не найден
- Логировать: `🔄 Admin reset limit for telegram_id=...`

#### Метод `get_user_stats(telegram_id: int, days=7) -> dict`
**Возвращает статистику за последние N дней:**
- `total_requests`: общее количество запросов
- `total_tokens`: общее количество токенов
- `days`: период анализа
- `avg_requests_per_day`: среднее запросов в день
- `avg_tokens_per_request`: среднее токенов на запрос

**Требования:**
- Все методы должны использовать logging
- Использовать эмодзи в логах для наглядности
- Обрабатывать граничные случаи (пользователь не найден, деление на 0)

---

## 🤖 Системный промпт

### Файл: `prompts.py`

**Требования к реализации:**

Создать системный промпт для ограничения тематики AI чата.

#### Переменная `SYSTEM_PROMPT`
Должна содержать детальную инструкцию для AI:

**Специализация AI:**
- Анализ продаж и статистики товаров на WB
- Работа с заказами, остатками и возвратами
- Отзывы клиентов и рейтинги товаров
- Ценообразование и мониторинг конкурентов
- Стратегии продвижения на Wildberries
- Работа с API и кабинетом продавца
- Логистика, склады и поставки WB
- Комиссии, финансы и налоги
- Создание и оптимизация карточек товаров

**Правила общения:**
1. Отвечать ТОЛЬКО на вопросы по теме Wildberries и e-commerce
2. Вежливо отказывать, если вопрос не по теме (с примером текста отказа)
3. Давать конкретные, практические советы
4. Использовать эмодзи: 📊 📈 💰 🛒 ⚠️ ✅ ❌ 📦 ⭐
5. Отвечать на русском языке, кратко и по делу
6. Максимальная длина ответа — 2000 символов
7. Предлагать использовать команды бота (/digest) для детальной аналитики

**Безопасность:**
- НЕ давать финансовых советов вне контекста WB
- НЕ обещать конкретных результатов
- НЕ рекомендовать нарушать правила маркетплейса
- НЕ обсуждать политику, религию и другие не относящиеся темы

**Стиль:**
- Дружелюбный, но профессиональный
- Практичный и конкретный
- С примерами и рекомендациями
- Структурированный (списки, заголовки)

#### Переменная `SYSTEM_PROMPT_SHORT` (опционально)
Короткая версия промпта для экономии токенов (до 500 символов).

---

## 🌐 FastAPI сервис

### Файл: `service.py`

**Требования к реализации:**

#### Инициализация приложения:
- Создать FastAPI приложение с метаданными:
  - `title="AI Chat Service"`
  - `description="AI чат-ассистент для продавцов Wildberries с ограничением запросов"`
  - `version="1.0.0"`
- Настроить логирование (level=INFO, с форматированием)

#### Событие `@app.on_event("startup")`:
- Создать таблицы БД: `Base.metadata.create_all(bind=engine)`
- Проверить наличие `OPENAI_API_KEY` в переменных окружения
- Логировать запуск: `🚀 Starting AI Chat Service...`
- Логировать создание таблиц: `✅ Database tables created/verified`

#### Вспомогательные функции:

##### `_verify_api_key(x_api_key: Optional[str])`:
- Проверять заголовок `X-API-KEY` против `API_SECRET_KEY` из env
- Если не совпадает → `HTTPException(403, "Invalid or missing API key")`

##### `_get_openai_client() -> OpenAI`:
- Создать клиент OpenAI с API ключом из env
- Поддержка `OPENAI_BASE_URL` (опционально)
- Если ключ не настроен → `HTTPException(500, "OpenAI API key not configured")`

##### `_call_openai(messages, model, max_tokens, temperature) -> tuple[str, int]`:
- Вызвать `client.chat.completions.create()` с параметрами
- Параметры из env (или defaults): `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE`
- Логировать: `🤖 Calling OpenAI: model=..., max_tokens=..., messages=...`
- Вернуть `(response_text, tokens_used)`
- При ошибке → `HTTPException(500, f"AI service error: {str(e)}")`
- Логировать: `✅ OpenAI response received: {len} chars, {tokens} tokens`

#### API Endpoints:

##### `GET /health`
- Вернуть `{"status": "ok", "service": "ai_chat", "version": "1.0.0"}`
- Без защиты API ключом

##### `POST /v1/chat/send` (response_model=ChatSendResponse)
**Процесс обработки:**
1. Проверить API ключ (`_verify_api_key`)
2. Создать `AIChatCRUD(db)`
3. Проверить лимиты: `crud.check_and_update_limit(telegram_id)`
4. Если `can_request=False` → `HTTPException(429, {...})` с деталями лимита
5. Получить контекст: `crud.get_recent_context(telegram_id, limit=5)`
6. Сформировать messages: `[system_prompt, ...context, user_message]`
7. Вызвать OpenAI: `_call_openai(messages)`
8. Сохранить в историю: `crud.save_chat_request(...)`
9. Вернуть `ChatSendResponse(response, remaining_requests, tokens_used)`

##### `POST /v1/chat/history` (response_model=ChatHistoryResponse)
- Проверить API ключ
- Получить историю: `crud.get_chat_history(telegram_id, limit, offset)`
- Вернуть `ChatHistoryResponse(items, total, limit, offset)`

##### `GET /v1/chat/limits/{telegram_id}` (response_model=ChatLimitsResponse)
- Проверить API ключ
- Получить лимиты: `crud.get_limits(telegram_id)`
- Вернуть `ChatLimitsResponse(telegram_id, ...limits)`

##### `POST /v1/chat/reset-limit` (response_model=ResetLimitResponse)
- Проверить API ключ
- Сбросить лимит: `crud.reset_user_limit(telegram_id)`
- Вернуть `ResetLimitResponse(success, message)`

##### `GET /v1/chat/stats/{telegram_id}`
- Проверить API ключ
- Параметр query: `days` (default=7)
- Получить статистику: `crud.get_user_stats(telegram_id, days)`
- Вернуть `{"telegram_id": ..., ...stats}`

#### Точка входа `if __name__ == "__main__"`:
- Получить порт из `AI_CHAT_PORT` (default=9001)
- Запустить: `uvicorn.run("ai_chat.service:app", host="0.0.0.0", port=port, reload=True)`

**Требования:**
- Все эндпоинты (кроме /health) защищены проверкой API ключа
- Все операции логируются с эмодзи
- Обработка всех ошибок с понятными сообщениями
- Dependency Injection для `db: Session`

---

## 🗄️ Database Configuration

### Файл: `database.py`

**Требования к реализации:**

#### Переменные модуля:

##### `DATABASE_URL`:
- Приоритет 1: `os.getenv("AI_CHAT_DATABASE_URL")`
- Приоритет 2: `os.getenv("DATABASE_URL")`
- По умолчанию: `"sqlite:///./ai_chat.db"`

##### `engine`:
- Создать через `create_engine(DATABASE_URL, ...)`
- Параметры:
  - `pool_pre_ping=True` (проверка соединения перед использованием)
  - `echo=False` (не логировать SQL запросы)

##### `SessionLocal`:
- Создать через `sessionmaker(autocommit=False, autoflush=False, bind=engine)`

##### `Base`:
- Создать через `declarative_base()` (для SQLAlchemy моделей)

#### Функция `get_db()`:
- Generator функция для FastAPI Dependency Injection
- Создает сессию, использует `yield`, закрывает в `finally`
- **Использование:** `db: Session = Depends(get_db)`

#### Функция `init_db()`:
- Создает все таблицы: `Base.metadata.create_all(bind=engine)`
- Вызывается при старте приложения (опционально)

---

## 🐳 Docker Configuration

### Файл: `Dockerfile`

**Требования к содержимому:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY ai_chat/requirements.txt /app/ai_chat/requirements.txt
RUN pip install --no-cache-dir -r ai_chat/requirements.txt

# Копирование кода сервиса
COPY ai_chat/ /app/ai_chat/

# Порт сервиса
EXPOSE 9001

# Команда запуска
CMD ["python", "-m", "uvicorn", "ai_chat.service:app", "--host", "0.0.0.0", "--port", "9001"]
```

### Файл: `requirements.txt`

**Список зависимостей:**
- `fastapi==0.109.0` (или выше)
- `uvicorn[standard]==0.27.0`
- `sqlalchemy==2.0.25`
- `psycopg2-binary==2.9.9` (для PostgreSQL)
- `pydantic==2.5.3`
- `pydantic-settings==2.1.0`
- `httpx==0.26.0` (для async HTTP запросов)
- `openai==1.10.0` (или выше)
- `python-dotenv==1.0.0` (для загрузки .env)

### Добавление в `docker-compose.yml`

**Добавить сервис:**

```yaml
ai_chat:
  build:
    context: .
    dockerfile: ai_chat/Dockerfile
  ports:
    - "9001:9001"
  environment:
    - AI_CHAT_PORT=9001
    - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    - API_SECRET_KEY=${API_SECRET_KEY}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - OPENAI_BASE_URL=${OPENAI_BASE_URL:-}
    - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
    - OPENAI_TEMPERATURE=${OPENAI_TEMPERATURE:-0.7}
    - OPENAI_MAX_TOKENS=${OPENAI_MAX_TOKENS:-1000}
  depends_on:
    db:
      condition: service_healthy
  networks:
    - app-network
  restart: unless-stopped
```

---

## 🔌 Интеграция с Telegram ботом

### Файл: `bot/handlers/ai_chat.py`

**Требования к реализации:**

#### Настройки модуля:
- `router = Router()`
- `AI_CHAT_URL` из env (default: `"http://ai_chat:9001"`)
- `API_SECRET_KEY` из env

#### FSM States:
Создать `AIChatStates(StatesGroup)`:
- `waiting_for_message = State()` - ожидание сообщения от пользователя

#### Команда `/ai_chat` или `/chat`:
**Handler:** `cmd_ai_chat(message, state)`

**Действия:**
1. Отправить приветственное сообщение с HTML форматированием:
   - Заголовок: "🤖 AI Ассистент Wildberries"
   - Список тем: продажи, остатки, отзывы, цены, стратегии
   - Инструкция: "/cancel для выхода"
   - Информация: "📊 У вас есть 30 запросов в сутки"
2. Установить состояние: `state.set_state(AIChatStates.waiting_for_message)`

#### Команда `/cancel` (в состоянии waiting_for_message):
**Handler:** `cancel_chat(message, state)`

**Действия:**
1. Очистить состояние: `state.clear()`
2. Отправить: "✅ Чат с AI завершен"

#### Обработка текстовых сообщений (в состоянии waiting_for_message):
**Handler:** `process_ai_message(message, state)`

**Логика:**
1. Получить `telegram_id` и `user_message`
2. Отправить индикатор печати: `send_chat_action(action="typing")`
3. Сделать POST запрос к `{AI_CHAT_URL}/v1/chat/send`:
   - Body: `{"telegram_id": ..., "message": ...}`
   - Headers: `{"X-API-KEY": API_SECRET_KEY}`
   - Timeout: 60 секунд
4. Обработать ответ:
   - **Если 429 (лимит исчерпан)**:
     - Отправить: "⛔ Лимит запросов исчерпан... Попробуйте завтра! 🌅"
     - Очистить состояние
     - return
   - **Если 200 (успех)**:
     - Получить `response` и `remaining_requests`
     - Отправить: "{response}\n\n_Осталось запросов: {remaining}/30_"
   - **При ошибке**:
     - Логировать ошибку
     - Отправить: "❌ Произошла ошибка при обращении к AI..."

#### Команда `/ai_limits`:
**Handler:** `cmd_ai_limits(message)`

**Логика:**
1. Получить `telegram_id`
2. Сделать GET запрос к `{AI_CHAT_URL}/v1/chat/limits/{telegram_id}`
3. Если 200:
   - Отправить: "📊 Ваши лимиты AI чата" с данными (`requests_today`, `requests_remaining`, `daily_limit`, `reset_date`)
4. При ошибке:
   - Отправить: "❌ Не удалось получить информацию о лимитах"

**Требования:**
- Использовать async/await
- Использовать `httpx.AsyncClient` для HTTP запросов
- Обрабатывать все исключения
- Логировать ошибки
- HTML форматирование в сообщениях

---

## 🧪 Примеры запросов

### 1. Отправка сообщения (PowerShell)

```powershell
$headers = @{ "X-API-KEY" = "$env:API_SECRET_KEY" }
$body = @{
    telegram_id = 123456789
    message = "Как увеличить конверсию карточки товара?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:9001/v1/chat/send" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body
```

### 2. Получение истории (curl)

```bash
curl -X POST "http://localhost:9001/v1/chat/history" \
  -H "X-API-KEY: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "limit": 10,
    "offset": 0
  }'
```

### 3. Проверка лимитов (curl)

```bash
curl -X GET "http://localhost:9001/v1/chat/limits/123456789" \
  -H "X-API-KEY: your-secret-key"
```

### 4. Сброс лимита (admin)

```bash
curl -X POST "http://localhost:9001/v1/chat/reset-limit" \
  -H "X-API-KEY: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789}'
```

---

## ⚙️ Переменные окружения

### Обязательные переменные:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `OPENAI_API_KEY` | OpenAI API ключ | - (обязательно) |
| `API_SECRET_KEY` | Секретный ключ для API | - (обязательно) |
| `DATABASE_URL` | URL подключения к PostgreSQL | `sqlite:///./ai_chat.db` |

### Опциональные переменные:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `AI_CHAT_PORT` | Порт сервиса | `9001` |
| `OPENAI_BASE_URL` | Кастомный эндпоинт OpenAI | - |
| `OPENAI_MODEL` | Модель OpenAI | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | Температура (0.0-2.0) | `0.7` |
| `OPENAI_MAX_TOKENS` | Макс токенов в ответе | `1000` |
| `AI_CHAT_DATABASE_URL` | Отдельная БД для AI Chat | - |

### Для Telegram бота:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `AI_CHAT_SERVICE_URL` | URL AI Chat сервиса | `http://ai_chat:9001` |

**Примечания:**
- Переменные добавляются в `.env` файл в корне проекта
- Для Docker переменные берутся из `docker-compose.yml`
- `API_SECRET_KEY` должен совпадать между всеми сервисами

---

## ✅ Этапы разработки

### Этап 1: Базовая структура
- [ ] Создать директорию `ai_chat/`
- [ ] Создать `models.py` (SQLAlchemy модели)
- [ ] Создать `schemas.py` (Pydantic схемы)
- [ ] Создать `database.py` (подключение к БД)
- [ ] Создать `crud.py` (CRUD операции)
- [ ] Создать `prompts.py` (системный промпт)

### Этап 2: FastAPI сервис
- [ ] Создать `service.py` (FastAPI приложение)
- [ ] Реализовать эндпоинт `/health`
- [ ] Реализовать эндпоинт `/v1/chat/send`
- [ ] Реализовать эндпоинт `/v1/chat/history`
- [ ] Реализовать эндпоинт `/v1/chat/limits/{telegram_id}`
- [ ] Реализовать эндпоинт `/v1/chat/reset-limit` (admin)

### Этап 3: Docker и деплой
- [ ] Создать `Dockerfile`
- [ ] Создать `requirements.txt`
- [ ] Добавить сервис в `docker-compose.yml`
- [ ] Настроить переменные окружения
- [ ] Проверить health check

### Этап 4: Интеграция с ботом
- [ ] Создать `bot/handlers/ai_chat.py`
- [ ] Реализовать команду `/ai_chat`
- [ ] Реализовать команду `/ai_limits`
- [ ] Добавить FSM для режима чата
- [ ] Добавить обработку ошибок 429 (лимит)

### Этап 5: Тестирование
- [ ] Unit тесты для CRUD операций
- [ ] Integration тесты для API эндпоинтов
- [ ] Тестирование лимитов (30 запросов)
- [ ] Тестирование сброса лимитов в новый день
- [ ] Ручное тестирование через Telegram бота

### Этап 6: Документация
- [ ] README.md для AI Chat сервиса
- [ ] Примеры запросов (curl, PowerShell)
- [ ] Документация API (OpenAPI/Swagger - автоматически из FastAPI)
- [ ] Инструкция для пользователей бота

---

## 🎯 Приоритеты и требования

### MVP (Must Have)
- ✅ Базовый чат с AI через OpenAI API
- ✅ Лимит 30 запросов в день (хранение в БД)
- ✅ Системный промпт с ограничением тематики (только WB/e-commerce)
- ✅ Интеграция с Telegram ботом через REST API
- ✅ Защита API ключом
- ✅ Docker контейнеризация

### Nice to Have (будущие версии)
- История чата с контекстом (последние 5 сообщений)
- Статистика использования (`/v1/chat/stats`)
- Admin панель для управления лимитами
- Доступ к данным пользователя из основной БД
- Персонализированные рекомендации
- Платные тарифы с расширенными лимитами

### Технические требования
- Python 3.11+
- FastAPI для REST API
- SQLAlchemy для работы с БД
- PostgreSQL (основная БД) или SQLite (для разработки)
- OpenAI API для LLM
- Docker + Docker Compose для деплоя
- Aiogram 3.x для Telegram бота

---

## 📝 Дополнительная информация

### Безопасность:
- Все эндпоинты (кроме `/health`) защищены `X-API-KEY`
- Rate limiting на уровне БД (30 запросов/день)
- Валидация входных данных через Pydantic
- SQL Injection защита через SQLAlchemy ORM
- Контекстное ограничение тематики через системный промпт

### Масштабирование (при необходимости):
- Горизонтальное: несколько инстансов + Load Balancer
- Оптимизация БД: индексы, партиционирование, очистка старых данных
- Кэширование: Redis для лимитов и частых запросов
- Асинхронность: asyncio, Celery для тяжелых операций

### Мониторинг:
- Логирование всех операций с эмодзи для наглядности
- Health check эндпоинт `/health`
- Swagger UI автоматически на `/docs`
- Метрики токенов и использования

---

**Версия**: 1.0.0  
**Дата**: 2025-10-29  
**Статус**: Technical Specification ✅  
**Формат**: Этапы разработки для LLM/Developer

