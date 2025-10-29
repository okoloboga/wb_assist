# 📋 ДЕТАЛЬНОЕ ТЗ: AI-Анализ данных через GPT

## 🎯 Цель

Пользователь нажимает кнопку **"🧠 AI-анализ"** в боте → система собирает данные из БД → отправляет в OpenAI → получает структурированный анализ → доставляет пользователю в Telegram

---

## 🏗️ Архитектура системы

### Компоненты

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   USER      │      │     BOT      │      │  GPT SERVICE │
│  Telegram   │◄────►│   (8001)     │◄────►│   (9000)     │
└─────────────┘      └──────────────┘      └──────────────┘
                            ▲                      ▲
                            │                      │
                            ▼                      ▼
                     ┌──────────────┐      ┌──────────────┐
                     │   SERVER     │◄─────┤   OpenAI     │
                     │   (8000)     │      │     API      │
                     └──────────────┘      └──────────────┘
                            ▲
                            │
                            ▼
                     ┌──────────────┐
                     │ PostgreSQL   │
                     │    +Redis    │
                     └──────────────┘
```

---

## 🔄 Полный поток данных (Step-by-Step)

### **ШАГ 1: Пользователь инициирует анализ**

**Файл**: `bot/handlers/gpt.py` → функция `cb_ai_analysis`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Пользователь нажимает кнопку "🧠 AI-анализ" (callback_data = `"ai_analysis"`)
2. Бот моментально отвечает: `"⏳ Запускаю AI‑анализ…"`
3. Бот делает POST запрос:
   ```python
   POST http://gpt:9000/v1/analysis/start
   Headers: {"X-API-KEY": "{API_SECRET_KEY}"}
   Body: {"telegram_id": 123456789, "period": "7d", "validate_output": true}
   ```
4. При успехе (HTTP 200): `"✅ Анализ запущен. Я пришлю результаты сообщениями..."`
5. При ошибке: `"❌ Не удалось запустить анализ. HTTP {status}"`

**Конфигурация**:
```python
# bot/core/config.py
gpt_service_url = os.getenv("GPT_SERVICE_URL", "http://127.0.0.1:9000")  # ✅ УЖЕ ЕСТЬ
```

---

### **ШАГ 2: GPT сервис принимает запрос**

**Файл**: `gpt_integration/service.py` → эндпоинт `/v1/analysis/start`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Валидация `X-API-KEY` (должен совпадать с `API_SECRET_KEY`)
2. Проверка параметров: `telegram_id`, `period`, `validate_output`
3. **Fire-and-forget**: запуск асинхронной задачи `_orchestrate_analysis()`
4. Немедленный ответ боту: `{"status": "accepted", "message": "analysis started"}`

**Код**:
```python
@app.post("/v1/analysis/start")
async def analysis_start(req: AnalysisStartRequest, x_api_key: Optional[str] = Header(None)):
    # Проверка API ключа
    if not x_api_key or x_api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    # Асинхронный запуск
    asyncio.create_task(_orchestrate_analysis(req.telegram_id, req.period, req.validate_output))
    return {"status": "accepted", "message": "analysis started"}
```

---

### **ШАГ 3: Сбор данных из Server (Bot API)**

**Файл**: `gpt_integration/service.py` → функция `_orchestrate_analysis`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит** (параллельные запросы):

#### 3.1 Получение аналитики продаж
```http
GET http://server:8000/api/v1/bot/analytics/sales?telegram_id=123&period=7d
Headers: {"X-API-SECRET-KEY": "{API_SECRET_KEY}"}
```

**Ответ** (схема `AnalyticsSalesAPIResponse`):
```json
{
  "status": "success",
  "analytics": {
    "date_range": {"start_date": "2025-10-21", "end_date": "2025-10-28"},
    "sales_periods": {
      "today": {"count": 45, "sum_rub": 120000},
      "yesterday": {"count": 41, "sum_rub": 110000}
    },
    "dynamics": {
      "yesterday_growth_percent": 9.8,
      "week_growth_percent": 15.2
    },
    "top_products": [
      {"sku": "SKU-123", "name": "Товар 1", "revenue_rub": 48000, "count": 16}
    ]
  },
  "telegram_text": "📊 Аналитика за 7 дней..."
}
```

#### 3.2 Получение критических остатков
```http
GET http://server:8000/api/v1/bot/stocks/critical?telegram_id=123&limit=20&offset=0
```

**Ответ** (`CriticalStocksAPIResponse`):
```json
{
  "status": "success",
  "stocks": {
    "critical_items": [
      {"sku": "SKU-456", "name": "Товар 2", "stock": 3, "warehouse": "Коледино"}
    ],
    "total_critical": 12
  }
}
```

#### 3.3 Получение сводки по отзывам
```http
GET http://server:8000/api/v1/bot/reviews/summary?telegram_id=123&limit=10&offset=0
```

**Ответ** (`ReviewsSummaryAPIResponse`):
```json
{
  "status": "success",
  "reviews": {
    "total_reviews": 156,
    "rating_distribution": {"1": 5, "2": 3, "3": 10, "4": 38, "5": 100},
    "negative_reviews": [...],
    "average_rating": 4.6
  }
}
```

#### 3.4 Получение последних заказов
```http
GET http://server:8000/api/v1/bot/orders/recent?telegram_id=123&limit=10&offset=0
```

**Ответ**:
```json
{
  "status": "success",
  "orders": [
    {"id": 123, "date": "2025-10-28T10:30:00+03:00", "amount": 2670, "status": "delivered"}
  ],
  "pagination": {"total": 450, "limit": 10, "offset": 0}
}
```

**Код** (все запросы параллельно):
```python
sales_task = _fetch_analytics_sales(telegram_id, period, server_host, api_secret_key)
stocks_task = _fetch_stocks_critical(telegram_id, server_host, api_secret_key)
reviews_task = _fetch_reviews_summary(telegram_id, server_host, api_secret_key)
orders_task = _fetch_orders_recent(telegram_id, server_host, api_secret_key)

fetched = await asyncio.gather(sales_task, stocks_task, reviews_task, orders_task, 
                                return_exceptions=True)
```

---

### **ШАГ 4: Агрегация данных**

**Файл**: `gpt_integration/aggregator.py` → функция `aggregate`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Объединение всех источников данных в единый словарь
2. Вычисление метрик:
   - `day_over_day`: изменение к вчера (%)
   - `week_over_week`: изменение к прошлой неделе (%)
   - `top_products_count`: количество топ-товаров
   - `critical_stocks_count`: количество критических позиций

**Входные данные**:
```python
sources = {
    "meta": {"telegram_id": 123, "period": "7d"},
    "sales": {...},  # из analytics/sales
    "stocks_critical": {...},  # из stocks/critical
    "reviews_summary": {...},  # из reviews/summary
    "orders_recent": {...}  # из orders/recent
}
```

**Выходные данные** (для LLM):
```python
{
  "meta": {
    "telegram_id": 123,
    "period": "7d",
    "computed_metrics": {
      "day_over_day": 9.8,
      "week_over_week": 15.2,
      "top_products_count": 5,
      "critical_stocks_count": 12
    }
  },
  "sales": {...},
  "stocks_critical": {...},
  "reviews_summary": {...},
  "orders_recent": {...},
  "top_products": [...]
}
```

---

### **ШАГ 5: Формирование промпта для LLM**

**Файл**: `gpt_integration/pipeline.py` → функция `compose_messages`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Загрузка шаблона из `LLM_ANALYSIS_TEMPLATE.md`
2. Извлечение секций:
   - `SYSTEM` — роль и стиль ассистента
   - `TASKS` — что анализировать
   - `OUTPUT_JSON_SCHEMA` — контракт выходного JSON
   - `OUTPUT_TG_GUIDE` — правила для Telegram-текста

3. Формирование сообщений для OpenAI:
```python
[
  {
    "role": "system",
    "content": "Ты аналитик e-commerce (Wildberries). Отвечай кратко..."
  },
  {
    "role": "user",
    "content": """
### DATA
{aggregated_data_json}

### TASKS
1) Ключевые метрики (key_metrics)
...

### OUTPUT_JSON_SCHEMA
{...}

### OUTPUT_TG_GUIDE
{...}

Верни ответ строго в формате OUTPUT_JSON...
    """
  }
]
```

---

### **ШАГ 6: Вызов OpenAI API**

**Файл**: `gpt_integration/gpt_client.py` → класс `GPTClient`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Конфигурация**:
```bash
# Переменные окружения
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

**Запрос**:
```python
client = GPTClient.from_env()
response_text = client.complete_messages(messages)
```

**Ответ от OpenAI** (пример):
```json
{
  "key_metrics": {
    "date_range": {"start_date": "2025-10-21", "end_date": "2025-10-28"},
    "orders_count": 450,
    "revenue_rub": 1200000,
    "avg_order_value": 2670,
    "day_over_day": 9.8,
    "week_over_week": 15.2,
    "top_products_count": 5,
    "critical_stocks_count": 12
  },
  "anomalies": [
    {
      "type": "low_stock",
      "description": "Критический остаток по SKU-456 (3 шт.)",
      "severity": "high",
      "affected_items": ["SKU-456"]
    }
  ],
  "insights": [
    {
      "title": "Топ-5 товаров дают 65% выручки",
      "detail": "SKU-123, SKU-789... Стоит расширить ассортимент похожих позиций"
    }
  ],
  "recommendations": [
    {
      "action": "replenish_stock",
      "why": "Остатки SKU-456 < 5 шт., риск дефицита",
      "impact": "high",
      "effort": "medium",
      "items": ["SKU-456", "SKU-789"]
    }
  ],
  "telegram": {
    "chunks": [
      "📊 Отчёт по кабинету: 2025-10-21 — 2025-10-28\n\n📈 Ключевые метрики...",
      "⚠️ Аномалии\n• Критический остаток по SKU-456...",
      "✅ Рекомендации\n• Пополнить остатки SKU-456..."
    ]
  },
  "sheets": {
    "headers": ["SKU", "Название", "Выручка ₽", "Заказы", "Остаток"],
    "rows": [
      ["SKU-123", "Товар 1", 480000, 160, 45],
      ["SKU-456", "Товар 2", 120000, 40, 3]
    ]
  }
}
```

---

### **ШАГ 7: Парсинг и валидация ответа**

**Файл**: `gpt_integration/pipeline.py` → функция `run_analysis`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Извлечение JSON из ответа LLM (функция `_safe_json_extract`)
2. Валидация структуры (если `validate=True`):
   - Проверка обязательных ключей: `key_metrics`, `anomalies`, `insights`, `recommendations`, `telegram`, `sheets`
   - Проверка `telegram.chunks` или `telegram.mdv2`
   - Проверка `sheets.headers` и `sheets.rows`

3. Нормализация `telegram`:
   - Экранирование спецсимволов для MarkdownV2
   - Разбивка на чанки (если текст >3500 символов)
   - Добавление счетчика символов

4. Обработка ошибок:
   - Если JSON невалидный → попытка извлечь текст после `OUTPUT_TG`
   - Если LLM вернул ошибку → фолбэк текст `"⚠️ Ошибка запроса к LLM..."`

**Результат**:
```python
{
  "messages": [...],  # промпт для отладки
  "raw_response": "...",  # сырой ответ LLM
  "json": {...},  # распарсенный JSON
  "telegram": {
    "chunks": ["чанк 1", "чанк 2", ...],
    "character_count": 2345
  },
  "sheets": {
    "headers": [...],
    "rows": [...]
  },
  "validation_errors": []  # если validate=True
}
```

---

### **ШАГ 8: Отправка результата в бот (webhook)**

**Файл**: `gpt_integration/service.py` → функция `_post_bot_webhook`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Извлечение чанков из результата:
   ```python
   chunks = result["telegram"]["chunks"]
   if not chunks and result["telegram"].get("mdv2"):
       chunks = [result["telegram"]["mdv2"]]
   if not chunks:
       chunks = ["❌ Не удалось сформировать текст отчёта"]
   ```

2. **Последовательная** отправка каждого чанка:
   ```python
   for chunk in chunks:
       POST http://bot:8001/webhook/notifications/{telegram_id}
       Headers: {"Content-Type": "application/json"}
       Body: {
         "telegram_id": 123456789,
         "user_id": 123456789,
         "type": "analysis_completed",
         "telegram_text": chunk
       }
   ```

3. Обработка ошибок:
   - При любой ошибке на этапах 3-7 → отправка фолбэк сообщения:
     ```python
     fallback_text = f"❌ Ошибка запуска анализа: {e}"
     await _post_bot_webhook(telegram_id, fallback_text, webhook_base)
     ```

---

### **ШАГ 9: Бот получает и доставляет результат пользователю**

**Файл**: `bot/handlers/webhook.py` → эндпоинт `/webhook/notifications/{telegram_id}`

**Статус**: ✅ **УЖЕ РЕАЛИЗОВАНО**

**Что происходит**:
1. Получение POST запроса от GPT сервиса
2. Проверка `telegram_id` (URL vs payload)
3. Извлечение `telegram_text` и `notification_type`
4. Обработка в зависимости от типа:
   ```python
   if notification_type == "analysis_completed":
       # Отправка текста БЕЗ parse_mode (чтобы избежать ошибок MarkdownV2)
       await bot.send_message(
           chat_id=telegram_id,
           text=telegram_text,
           parse_mode=None  # ← ВАЖНО!
       )
   ```

5. **Результат**: пользователь получает 1-3 сообщения с анализом в Telegram

---

## 📊 Структура данных на каждом этапе

### Таблица трансформации данных

| Этап | Компонент | Входные данные | Выходные данные |
|------|-----------|----------------|-----------------|
| 1 | Бот → GPT | `{"telegram_id": 123, "period": "7d"}` | HTTP 202 Accepted |
| 2 | GPT → Server | `telegram_id`, `period` | 4 JSON ответа (sales, stocks, reviews, orders) |
| 3 | Aggregator | 4 JSON объекта | Единый `data` словарь с `computed_metrics` |
| 4 | Pipeline | `data` + шаблон | Промпт для OpenAI (system + user messages) |
| 5 | OpenAI | Промпт | JSON с анализом (key_metrics, anomalies, insights, recommendations, telegram, sheets) |
| 6 | Pipeline | JSON от OpenAI | Валидация + нормализация (`telegram.chunks`, экранирование) |
| 7 | GPT → Бот | `telegram.chunks` | Webhook запросы (по 1 на чанк) |
| 8 | Бот → User | `telegram_text` | Telegram сообщения |

---

## 🔧 Конфигурация (переменные окружения)

### BOT (.env для бота)
```bash
BOT_TOKEN=123456:ABC...                  # Telegram Bot Token
SERVER_HOST=http://server:8000           # Адрес Backend сервера
API_SECRET_KEY=your_secret_key_here      # Общий секрет для всех сервисов
GPT_SERVICE_URL=http://gpt:9000          # Адрес GPT сервиса
REQUEST_TIMEOUT=600                      # Таймаут запросов (10 мин)
WEBHOOK_SECRET=default_webhook_secret    # Секрет для вебхука (опционально)
```

### GPT SERVICE (.env для gpt_integration)
```bash
SERVER_HOST=http://server:8000                      # Откуда брать данные
API_SECRET_KEY=your_secret_key_here                 # Для доступа к Server API
BOT_WEBHOOK_BASE=http://bot:8001                    # Куда слать результаты
OPENAI_API_KEY=sk-...                               # OpenAI API ключ
OPENAI_BASE_URL=https://api.openai.com/v1           # OpenAI endpoint
OPENAI_MODEL=gpt-4o-mini                            # Модель (gpt-4o-mini, gpt-4, gpt-3.5-turbo)
GPT_PORT=9000                                       # Порт GPT сервиса
```

### SERVER (.env для backend)
```bash
DATABASE_URL=postgresql://user:pass@db:5432/wb_assist
API_SECRET_KEY=your_secret_key_here                 # Тот же секрет!
REDIS_URL=redis://redis:6379/0
```

---

## ✅ Чек-лист: Что уже реализовано

| # | Компонент | Файл | Статус |
|---|-----------|------|--------|
| 1 | Кнопка "🧠 AI-анализ" | `bot/keyboards/keyboards.py:104` | ✅ |
| 2 | Обработчик нажатия кнопки | `bot/handlers/gpt.py:20-69` | ✅ |
| 3 | Конфиг `gpt_service_url` | `bot/core/config.py:43` | ✅ |
| 4 | Эндпоинт `/v1/analysis/start` | `gpt_integration/service.py:190-199` | ✅ |
| 5 | Оркестрация `_orchestrate_analysis` | `gpt_integration/service.py:124-188` | ✅ |
| 6 | Сбор данных из Server | `gpt_integration/service.py:59-110` | ✅ |
| 7 | Агрегация данных | `gpt_integration/aggregator.py` | ✅ |
| 8 | Формирование промпта | `gpt_integration/pipeline.py:14-43` | ✅ |
| 9 | GPT клиент | `gpt_integration/gpt_client.py` | ✅ |
| 10 | Парсинг и валидация | `gpt_integration/pipeline.py:111-170` | ✅ |
| 11 | Отправка в webhook бота | `gpt_integration/service.py:112-122, 177-178` | ✅ |
| 12 | Webhook обработчик | `bot/handlers/webhook.py:62-262` | ✅ |
| 13 | Server Bot API эндпоинты | `server/app/features/bot_api/routes.py` | ✅ |
| 14 | Docker Compose конфигурация | `docker-compose.yml:124-142` | ✅ |

**Вывод**: Все ключевые компоненты реализованы! 🎉