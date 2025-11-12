# AI Chat Merge Notes

## Stage 1 — Comparison Snapshot (2025-11-12)

### File structure differences
- `gpt_integration/ai_chat` содержит дополнительные артефакты разработки (`.coverage`, `.pytest_cache/`, `htmlcov/`) и модуль `service.py`, которого нет в standalone-сервисе. Требуется решить, какие артефакты сохраняем, а какие переносить/очищать.
- Остальная структура (`app/`, `tools/`, `tests/`, `docs/`) совпадает по составу файлов.

### Ключевые отличия в коде
- `app/service.py`: путь до `.env` различается (`../../..` vs `../../../../`) — связано с уровнем вложенности внутри `gpt_integration`.
- `app/service.py`: версия в `gpt_integration` не обрезает пробелы у `OPENAI_BASE_URL`; standalone-сервис использует `strip()`.
- `app/service.py`: в `gpt_integration` блок `try` внутри `send_message` потерял отступы — фактически код вне блока `try`, что приведёт к синтаксической ошибке при импорте.
- `agent.py`: аналогичная разница в обработке `OPENAI_BASE_URL` (`strip()` в standalone против прямого значения в модуле внутри `gpt_integration`).

### Документация и конфигурация
- Файлы `.env.example`, `requirements*.txt`, `pytest.ini`, `README.md`, `docs/*` совпадают по содержанию.
- Тестовые файлы идентичны по содержанию (за исключением pyc/кэшей в `gpt_integration`).

### Перечень зависимостей
- `requirements.txt`, `requirements-dev.txt`, `requirements-test.txt` полностью совпадают, дополнительных пакетов нет.
- Следовательно, уникальных зависимостей в standalone-варианте нет — можно использовать текущие списки в `gpt_integration`.

### Рекомендации по итогам этапа
1. Исправить потерянные отступы в `gpt_integration/ai_chat/app/service.py` перед интеграцией.
2. Решить, сохраняем ли логику с `strip()` для `OPENAI_BASE_URL` (в standalone она предотвращает ошибки с пробелами).
3. Очистить артефакты (`.coverage`, `.pytest_cache`, `htmlcov`) перед переносом в основную ветку.
4. Подготовить решение, как использовать (или удалить) `gpt_integration/ai_chat/service.py`, чтобы избежать дублирования основной точки входа.

---

## Stage 2 — Canonical Source Decision

- **Предположение:** актуальной и продакшн-версией считаем standalone-сервис `ai_chat/` (используется в текущей инфраструктуре и не содержит синтаксических дефектов).
- **Решение:** принимаем корневой `ai_chat` как каноничную базу, с учётом точечных правок, внесённых в `gpt_integration` (например, другой путь до `.env`).
- **Дальнейшие шаги:** переносим код из `ai_chat/` в `gpt_integration/ai_chat/` с сохранением изменений, необходимых для вложенного расположения (пути, импорты). Все синхронизации фиксируем диффами и обновляем тесты.
- **Примечание:** файл `gpt_integration/ai_chat/service.py` (обёртка над `GPTClient`) отсутствует в standalone-версии; решим его судьбу при интеграции маршрутов на следующих этапах.

---

## Stage 3 — Requirements & Environment Alignment

- Обновлён `gpt_integration/requirements.txt`: добавлены зависимости AI-чата (`sqlalchemy`, `psycopg2-binary`, `alembic`, `asyncpg`, `pydantic`, `pydantic-settings`, `python-dotenv`) при сохранении существующих версий FastAPI, Uvicorn, OpenAI, HTTPX и Aiogram.
- Расширен `gpt_integration/env_example.txt`: добавлены переменные `AI_CHAT_PORT`, `DATABASE_URL`, `AI_CHAT_DATABASE_URL`, `LOG_LEVEL`, а также примечание для совместимости с `BOT_HOST`.
- Dockerfile сервиса (`gpt_integration/Dockerfile`) дополняется установкой `gcc` и `postgresql-client`, чтобы новые зависимости (psycopg2-binary/asyncpg) собирались без ошибок.

