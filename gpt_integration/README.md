# GPT Integration Service

Отдельный FastAPI-сервис для LLM функций (чат и аналитика), интегрированный с сервером Bot API и Telegram ботом.

## Возможности
- /health: проверка здоровья сервиса
- /v1/chat: синхронный чат с LLM (OpenAI‑совместимый API)
- /v1/analysis: запуск анализа для произвольных данных по шаблону
- /v1/analysis/start: асинхронный запуск анализа для пользователя WB, доставка результата в бота

## Архитектура
- Компоненты:
  - `server` (порт `8000`) — источник данных (Bot API)
  - `bot` (порт `8001`) — Telegram бот и приёмник вебхуков
  - `gpt_integration` (порт `9000`) — отдельный сервис LLM
- Поток `/v1/analysis/start`:
  1) Бот вызывает `POST /v1/analysis/start` с `telegram_id` (+ `period`)
  2) gpt‑сервис собирает данные из `server` (`/api/v1/bot/analytics/sales`)
  3) Формирует промпт по `LLM_ANALYSIS_TEMPLATE.md` и вызывает LLM
  4) Валидирует JSON‑результат и готовит текст для Telegram
  5) Отправляет результат вебхуком на `bot /webhook/notifications/{telegram_id}`

## Переменные окружения
- Общие
  - `GPT_PORT` — порт сервиса (по умолчанию `9000`)
  - `API_SECRET_KEY` — секрет для авторизации (совпадает с сервером)
- Интеграция с сервером
  - `SERVER_HOST` — базовый URL сервера (например `http://server:8000`)
  - Заголовок для запросов к серверу: `X-API-SECRET-KEY: {API_SECRET_KEY}`
- Интеграция с ботом
  - `BOT_WEBHOOK_BASE` — базовый URL бота (например `http://bot:8001`)
- LLM (OpenAI‑совместимый)
  - `OPENAI_API_KEY` — ключ доступа (обязательно)
  - `OPENAI_BASE_URL` — кастомный эндпоинт (опционально)
  - `OPENAI_MODEL` — модель (по умолчанию `gpt-4o-mini`)
  - `OPENAI_TEMPERATURE` — креативность (по умолчанию `0.2`)
  - `OPENAI_MAX_TOKENS` — лимит токенов (по умолчанию `800`)
  - `OPENAI_TIMEOUT` — таймаут запросов (сек)
  - `OPENAI_SYSTEM_PROMPT` — системный промпт; если пусто, берётся из `LLM_ANALYSIS_TEMPLATE.md` (`## SYSTEM`)

## Запуск
### Docker Compose (рекомендуется)
- В корне проекта: `docker-compose up -d --build`
- Сервис доступен на `http://localhost:9000`

### Локально (Python)
```bash
cd gpt_integration
pip install -r requirements.txt
# Установите окружение (см. env_example.txt)
python -m gpt_integration.service
```
Примечание: для локального запуска импорт `utils.formatters` должен быть доступен в `PYTHONPATH`. Проще всего запускать из корня проекта или установить переменную `PYTHONPATH` на корень.

## Эндпоинты
### GET /health
Ответ: `{ "status": "ok" }`

### POST /v1/chat
Тело:
```json
{
  "messages": [{"role": "user", "content": "Привет"}],
  "system_prompt": "(опционально, переопределение системного промпта)"
}
```
Ответ:
```json
{ "text": "..." }
```

### POST /v1/analysis
Тело:
```json
{
  "data": {"sales": {"orders": 10}},
  "template_path": "gpt_integration/LLM_ANALYSIS_TEMPLATE.md",
  "validate_output": true
}
```
Ответ: объект с ключами `messages`, `raw_response`, `json`, `telegram`, `sheets`, опционально `validation_errors`.

### POST /v1/analysis/start
Заголовок: `X-API-KEY: {API_SECRET_KEY}`
Тело:
```json
{
  "telegram_id": 123456789,
  "period": "7d",
  "validate_output": true
}
```
Ответ:
```json
{ "status": "accepted", "message": "analysis started" }
```

## Примеры запросов (PowerShell)
Запуск анализа:
```powershell
$headers = @{ "X-API-KEY" = "$env:API_SECRET_KEY" }
$body = @{ telegram_id = 123456789; period = "7d"; validate_output = $true } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:9000/v1/analysis/start" -Headers $headers -ContentType "application/json" -Body $body
```
Проверка здоровья:
```powershell
Invoke-RestMethod -Method Get -Uri "http://localhost:9000/health"
```

## Шаблон анализа
Файл `LLM_ANALYSIS_TEMPLATE.md` содержит:
- `## SYSTEM` — роль ассистента
- `## TASKS` — задания для анализа
- `## OUTPUT_JSON_SCHEMA` — контракт JSON
- `## OUTPUT_TG_GUIDE` — правила формата сообщения для Telegram

## Замечания
- Для внутреннего запроса к серверу используется заголовок `X-API-SECRET-KEY`.
- В вебхуке к боту отправляется ready‑текст в MarkdownV2; бот сам отправляет текст пользователю.
- При ошибке запуска анализа сервис отправляет фолбэк сообщение в бота.