# AI Chat Service

Отдельный FastAPI-сервис для общения пользователей с AI-ассистентом по теме Wildberries и e-commerce.

## 🎯 Основные возможности

- 🤖 **AI чат-ассистент** для продавцов Wildberries
- 🔒 **Ограничение запросов**: 30 запросов в сутки на пользователя
- 📜 **История чата** с хранением в PostgreSQL
- 🎯 **Контекстное ограничение**: только темы WB и e-commerce
- 🔌 **API интеграция** с Telegram ботом
- 🎯 **Персонализация**: ответы на основе реальных данных пользователя

## 📁 Структура проекта

```
ai_chat/
├── app/                           # 📦 Код приложения
│   ├── __init__.py               # Инициализация пакета
│   ├── service.py                # FastAPI приложение
│   ├── database.py               # SQLAlchemy конфигурация
│   ├── models.py                 # ORM модели
│   ├── schemas.py                # Pydantic схемы
│   ├── crud.py                   # Операции с БД
│   └── prompts.py                # Системные промпты
├── docs/                          # 📚 Документация
│   ├── AI_CHAT_SPECIFICATION.md  # Полное ТЗ
│   ├── ARCHITECTURE.md           # Архитектура
│   ├── CHANGELOG.md              # История изменений
│   ├── PERSONALIZATION_GUIDE.md  # Руководство по персонализации
│   └── ...
├── tests/                         # 🧪 Тесты
│   ├── conftest.py               # Фикстуры pytest
│   ├── test_api.py               # Тесты API
│   ├── test_crud.py              # Тесты CRUD
│   └── test_rate_limits.py       # Тесты лимитов
├── Dockerfile                     # Docker образ
├── requirements.txt               # Зависимости
├── requirements-dev.txt           # Dev зависимости
├── requirements-test.txt          # Test зависимости
├── pytest.ini                     # Конфигурация pytest
└── README.md                      # Этот файл
```

## 📋 Эндпоинты

### `GET /health`
Проверка здоровья сервиса.

**Ответ:**
```json
{
  "status": "ok",
  "service": "ai_chat",
  "version": "1.0.0"
}
```

### `POST /v1/chat/send`
Отправка сообщения в AI чат.

**Заголовки:**
- `X-API-KEY: {API_SECRET_KEY}`

**Тело запроса:**
```json
{
  "telegram_id": 123456789,
  "message": "Как увеличить конверсию карточки товара?"
}
```

**Ответ (успех):**
```json
{
  "response": "Для увеличения конверсии карточки товара...",
  "remaining_requests": 25,
  "tokens_used": 234
}
```

**Ответ (лимит исчерпан):**
```json
{
  "error": "Daily limit exceeded",
  "message": "Вы исчерпали дневной лимит запросов (30 в сутки). Попробуйте завтра.",
  "requests_remaining": 0,
  "daily_limit": 30
}
```
HTTP Status: `429 Too Many Requests`

### `POST /v1/chat/history`
Получение истории чата пользователя.

**Тело запроса:**
```json
{
  "telegram_id": 123456789,
  "limit": 10,
  "offset": 0
}
```

**Ответ:**
```json
{
  "items": [
    {
      "id": 1,
      "message": "Как увеличить продажи?",
      "response": "Для увеличения продаж...",
      "tokens_used": 150,
      "created_at": "2025-10-29T10:15:23Z"
    }
  ],
  "total": 45,
  "limit": 10,
  "offset": 0
}
```

### `GET /v1/chat/limits/{telegram_id}`
Проверка лимитов пользователя.

**Ответ:**
```json
{
  "telegram_id": 123456789,
  "requests_today": 5,
  "requests_remaining": 25,
  "daily_limit": 30,
  "reset_date": "2025-10-29"
}
```

### `POST /v1/chat/reset-limit` (Admin)
Сброс лимита пользователя.

**Тело запроса:**
```json
{
  "telegram_id": 123456789
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Limit reset successfully for telegram_id=123456789"
}
```

### `GET /v1/chat/stats/{telegram_id}`
Статистика пользователя за последние N дней.

**Query параметры:**
- `days` (опционально, по умолчанию 7)

**Ответ:**
```json
{
  "telegram_id": 123456789,
  "total_requests": 42,
  "total_tokens": 8500,
  "days": 7,
  "avg_requests_per_day": 6.0,
  "avg_tokens_per_request": 202.38
}
```

## 🚀 Быстрый старт

### Docker Compose (рекомендуется)

1. Добавьте сервис в `docker-compose.yml`:
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
    - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
    - OPENAI_TEMPERATURE=${OPENAI_TEMPERATURE:-0.7}
    - OPENAI_MAX_TOKENS=${OPENAI_MAX_TOKENS:-1000}
  depends_on:
    db:
      condition: service_healthy
  networks:
    - app-network
```

2. Запустите:
```bash
docker-compose up -d --build ai_chat
```

3. Проверьте здоровье:
```bash
curl http://localhost:9001/health
```

### Локальный запуск

1. Установите зависимости:
```bash
cd ai_chat
pip install -r requirements.txt
```

2. Настройте `.env`:
```bash
cp env_example.txt .env
# Отредактируйте .env файл
```

3. Запустите сервис:
```bash
python -m uvicorn ai_chat.service:app --host 0.0.0.0 --port 9001 --reload
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| `AI_CHAT_PORT` | Порт сервиса | `9001` |
| `DATABASE_URL` | URL подключения к БД | `sqlite:///./ai_chat.db` |
| `API_SECRET_KEY` | Секретный ключ API | - |
| `OPENAI_API_KEY` | OpenAI API ключ | - |
| `OPENAI_BASE_URL` | Кастомный эндпоинт OpenAI | - |
| `OPENAI_MODEL` | Модель OpenAI | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | Температура (0.0-2.0) | `0.7` |
| `OPENAI_MAX_TOKENS` | Максимум токенов в ответе | `1000` |

### Настройка лимитов

По умолчанию: **30 запросов в сутки**.

Для изменения лимита отредактируйте константу `DAILY_LIMIT` в `app/crud.py`:
```python
DAILY_LIMIT = 30  # Измените на нужное значение
```

## 🗄️ База данных

### Миграции

При первом запуске таблицы создаются автоматически:
- `ai_chat_requests` - история чата
- `ai_chat_daily_limits` - счетчики лимитов

### Очистка старых данных

Рекомендуется периодически очищать старые записи (>6 месяцев):
```sql
DELETE FROM ai_chat_requests 
WHERE request_date < CURRENT_DATE - INTERVAL '6 months';
```

## 🧪 Тестирование

### Примеры запросов

#### PowerShell
```powershell
# Отправка сообщения
$headers = @{ "X-API-KEY" = "your-secret-key" }
$body = @{
    telegram_id = 123456789
    message = "Как увеличить продажи?"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:9001/v1/chat/send" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body
```

#### curl
```bash
# Проверка лимитов
curl -X GET "http://localhost:9001/v1/chat/limits/123456789" \
  -H "X-API-KEY: your-secret-key"

# Получение истории
curl -X POST "http://localhost:9001/v1/chat/history" \
  -H "X-API-KEY: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "limit": 10,
    "offset": 0
  }'
```

## 📊 Мониторинг

### Логи

Сервис логирует все важные события:
```
2025-10-29 10:15:23 - INFO - ✅ Request allowed for telegram_id=123456789: 5/30
2025-10-29 10:15:23 - INFO - 🤖 Calling OpenAI: model=gpt-4o-mini, messages=2
2025-10-29 10:15:25 - INFO - ✅ OpenAI response received: 456 chars, 234 tokens
2025-10-29 10:15:25 - INFO - 💾 Saved chat request: telegram_id=123456789
```

### Health Check

Для мониторинга доступности используйте `/health` эндпоинт:
```bash
curl http://localhost:9001/health
```

## 🔒 Безопасность

- ✅ Все эндпоинты защищены API ключом
- ✅ Rate limiting на уровне БД (30 запросов/день)
- ✅ Валидация входных данных (Pydantic)
- ✅ SQL Injection защита (SQLAlchemy ORM)
- ✅ Контекстное ограничение тематики (системный промпт)

## 📚 Документация

- **Полное ТЗ**: `docs/AI_CHAT_SPECIFICATION.md`
- **Архитектура**: `docs/ARCHITECTURE.md`
- **История изменений**: `docs/CHANGELOG.md`
- **Персонализация**: `docs/PERSONALIZATION_GUIDE.md`
- **API документация**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc`

## 🤝 Интеграция с ботом

См. `docs/AI_CHAT_SPECIFICATION.md` раздел "Интеграция с Telegram ботом".

Пример использования в боте:
```python
# bot/handlers/ai_chat.py

@router.message(Command("chat"))
async def cmd_ai_chat(message: Message):
    telegram_id = message.from_user.id
    user_message = message.text
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AI_CHAT_URL}/v1/chat/send",
            json={"telegram_id": telegram_id, "message": user_message},
            headers={"X-API-KEY": API_SECRET_KEY}
        )
        
        data = response.json()
        await message.answer(data["response"])
```

## 🐛 Troubleshooting

### Ошибка: "OpenAI API key not configured"
**Решение:** Установите `OPENAI_API_KEY` в переменных окружения.

### Ошибка: "Invalid or missing API key"
**Решение:** Проверьте, что `X-API-KEY` в заголовке совпадает с `API_SECRET_KEY`.

### Ошибка: 429 Too Many Requests
**Решение:** Пользователь исчерпал дневной лимит. Подождите до следующего дня или используйте admin endpoint для сброса.

## 📞 Поддержка

Для вопросов и предложений создайте issue в репозитории проекта.

---

**Версия:** 1.0.0  
**Лицензия:** MIT  
**Автор:** WB Assist Team

