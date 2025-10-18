# Этап 1 — Подготовка окружения и зависимостей (gpt_integration)

Этот раздел предназначен для локальной подготовки и проверки подключения GPT перед внесением изменений в `bot/`.

## Шаги

- Установка зависимостей:
  - Выполните: `pip install -r gpt_integration/requirements.txt`
- Настройка переменных окружения:
  - Скопируйте `.env.example` → `.env` в каталоге `gpt_integration/`
  - Заполните `OPENAI_API_KEY` (и при необходимости `OPENAI_BASE_URL`, `OPENAI_MODEL` и пр.)
- Проверка подключения:
  - Запустите: `python gpt_integration/test_openai.py`
  - Ожидаемый результат: вывод краткого ответа модели ("pong" или аналогичный текст).

## Переменные окружения (.env)

- `OPENAI_API_KEY` — ключ доступа к LLM
- `OPENAI_BASE_URL` — базовый URL (по умолчанию: `https://api.openai.com/v1`)
- `OPENAI_MODEL` — название модели (пример: `gpt-4o-mini`)
- `OPENAI_TEMPERATURE` — температура (например: `0.2`)
- `OPENAI_MAX_TOKENS` — максимум токенов ответа (например: `800`)
- `OPENAI_TIMEOUT` — таймаут запроса (сек)
- `OPENAI_SYSTEM_PROMPT` — системная инструкция (опционально)

## Примечание

Эти шаги не изменяют код бота и служат для подготовки окружения. После успешной проверки соединения перейдём к Этапу 2 и начнём изменения в `bot/`.

---

# Этап 2 — Реализация GPTClient и утилит форматирования

На этом этапе мы добавляем обёртку `GPTClient` для обращения к LLM и утилиты форматирования текста, которые понадобятся для Телеграм (MarkdownV2, разбиение длинных сообщений).

## Новые файлы

- `gpt_integration/gpt_client.py` — класс `GPTClient` с конфигом `LLMConfig`
- `gpt_integration/formatters.py` — функции `escape_markdown_v2`, `split_telegram_message`, `truncate`
- `gpt_integration/demo_gpt_client.py` — демо-скрипт для локальной проверки `GPTClient`

## Использование демо

- Убедитесь, что заполнен `gpt_integration/.env`
- Запустите: `python gpt_integration/demo_gpt_client.py "Напиши 'pong'"`
- Ожидаемый результат: `[OK] Ответ: pong` (или короткий аналогичный ответ)

## Пример кода

```python
from dotenv import load_dotenv
from gpt_client import GPTClient

load_dotenv("gpt_integration/.env")
client = GPTClient()
answer = client.complete("Скажи 'pong'.")
print(answer)
```

## Дальше

После подтверждения работоспособности клиента и утилит переходим к Этапу 3: подключение к `bot/` — добавление FSM-стейтов, хендлеров `/gpt` и регистрации роутера в `__main__.py`.