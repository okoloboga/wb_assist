# Полное пересоздание БД и контейнеров с Event-Driven RAG

**Дата:** 2025-12-16
**Цель:** Чистое развертывание с новой архитектурой

---

## 🚀 Пошаговая инструкция

### Шаг 1: Остановка и очистка текущих контейнеров

```bash
cd /Users/core/code/wb_assist

# Остановить все контейнеры
docker-compose down

# Удалить volumes (ВАЖНО: удалит все данные БД!)
docker-compose down -v

# Опционально: удалить образы для полной пересборки
docker-compose down --rmi all -v

# Проверить, что все остановлено
docker ps -a | grep wb_assist
```

**Результат:** Все контейнеры остановлены, volumes удалены

---

### Шаг 2: Проверка docker-compose.yml

Убедитесь, что в `docker-compose.yml` правильно настроены:

```yaml
# Проверьте переменные окружения для RAG
environment:
  - RAG_ENABLED=true
  - RAG_INDEXING_INTERVAL_HOURS=6  # Больше не используется для incremental
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
  - RAG_EMBEDDING_BATCH_SIZE=100
```

---

### Шаг 3: Обновить Celery Beat schedule

**Файл:** `server/app/core/celery_app.py`

Найдите секцию `beat_schedule` и обновите:

```python
celery_app.conf.beat_schedule = {
    # ... другие задачи (sync, analytics и т.д.) ...

    # УДАЛЕНО: Инкрементальная RAG индексация по расписанию
    # "index-all-cabinets-rag": {
    #     "task": "app.features.rag.tasks.index_all_cabinets_rag",
    #     "schedule": crontab(hour='*/6', minute=0),
    # },

    # ДОБАВЛЕНО: Weekly full rebuild
    "index-full-rebuild-rag": {
        "task": "app.features.rag.tasks.full_rebuild_all_cabinets_rag",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Воскресенье 03:00 UTC
    },
}
```

**Важно:** Сохраните файл перед пересборкой.

---

### Шаг 4: Пересборка и запуск контейнеров

```bash
# Пересборка образов
docker-compose build --no-cache

# Запуск контейнеров
docker-compose up -d

# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs -f --tail=100
```

**Ожидаемый результат:**
```
NAME                    STATUS
wb_assist_db            Up
wb_assist_redis         Up
wb_assist_server        Up
wb_assist_gpt           Up
wb_assist_celery        Up
wb_assist_celery_beat   Up
wb_assist_bot           Up (опционально)
```

---

### Шаг 5: Дождаться инициализации БД

```bash
# Следить за логами основной БД
docker-compose logs -f db

# Должны увидеть:
# "database system is ready to accept connections"
```

**Подождите 10-20 секунд** после готовности БД.

---

### Шаг 6: Применить Alembic миграции (основная БД)

```bash
# Войти в контейнер server
docker-compose exec server bash

# Внутри контейнера:
cd /app
alembic upgrade head

# Проверить результат
# Должен вывести:
# INFO  [alembic.runtime.migration] Running upgrade ... -> 009_add_timestamp_indexes_for_rag

# Выйти из контейнера
exit
```

**Результат:** 20 новых индексов созданы в основной БД

---

### Шаг 7: Применить RAG миграции (RAG БД)

```bash
# Войти в контейнер gpt
docker-compose exec gpt bash

# Внутри контейнера:
cd /app

# Применить SQL миграцию
psql $RAG_DATABASE_URL -f gpt_integration/ai_chat/RAG/migrations/001_add_chunk_hash.sql

# Должен вывести:
# ALTER TABLE
# CREATE INDEX
# CREATE INDEX
# COMMENT
# ...

# Проверить результат
psql $RAG_DATABASE_URL -c "\d rag_metadata"

# Должен показать столбец chunk_hash:
# chunk_hash | character varying(64) |

# Выйти из контейнера
exit
```

**Результат:** RAG БД готова к работе с chunk_hash

---

### Шаг 8: Создать тестовый кабинет и запустить первую синхронизацию

```bash
# Опция А: Через API (если есть тестовый WB API ключ)
curl -X POST http://localhost:8000/api/v1/cabinets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $YOUR_TOKEN" \
  -d '{
    "name": "Test Cabinet",
    "api_key": "YOUR_WB_API_KEY"
  }'

# Опция Б: Через Django admin или БД напрямую
docker-compose exec db psql -U postgres -d wb_assist -c \
  "INSERT INTO wb_cabinets (name, api_key, is_active, created_at, updated_at)
   VALUES ('Test Cabinet', 'YOUR_WB_API_KEY', true, NOW(), NOW())
   RETURNING id;"

# Запустить синхронизацию
curl -X POST http://localhost:8000/api/v1/sync/cabinet/1 \
  -H "Authorization: Bearer $YOUR_TOKEN"
```

---

### Шаг 9: Проверить Event-driven RAG индексацию

```bash
# Следить за логами gpt сервиса
docker-compose logs -f gpt

# Ожидаемые логи (если sync_all_data() возвращает changed_ids):
# "Triggering Event-driven RAG indexing for cabinet 1 with 150 changes"
# "Starting incremental RAG indexing for cabinet 1 with 150 changed IDs"
# "Extracted data by IDs for cabinet 1: orders=45, products=30, ..."
# "Incremental indexing completed for cabinet 1: 150 chunks indexed"

# Или (если sync_all_data() еще не возвращает changed_ids):
# "Triggering RAG indexing for cabinet 1 (no delta available)"
# "Starting incremental RAG indexing for cabinet 1"
# "Extracted data for cabinet 1: orders=500, products=100, ..."
```

---

### Шаг 10: Проверить статус RAG индексации

```bash
# Получить API ключ из .env
export API_SECRET_KEY=$(grep API_SECRET_KEY .env | cut -d '=' -f2)

# Проверить статус
curl http://localhost:9000/v1/rag/status/1 \
  -H "X-API-KEY: $API_SECRET_KEY" | jq

# Ожидаемый ответ:
# {
#   "status": "success",
#   "cabinet_id": 1,
#   "indexing_status": "completed",
#   "last_indexed_at": null,
#   "last_incremental_at": "2025-12-16T15:30:00Z",
#   "total_chunks": 150,
#   "updated_at": "2025-12-16T15:30:10Z"
# }
```

---

### Шаг 11: Проверить работу Celery Beat

```bash
# Проверить логи celery_beat
docker-compose logs -f celery_beat

# Должны увидеть расписание:
# "celery beat v5.x.x is starting."
# Scheduler: PersistentScheduler
# -> index-full-rebuild-rag: app.features.rag.tasks.full_rebuild_all_cabinets_rag

# Убедиться, что НЕТ старого расписания:
# НЕ должно быть "index-all-cabinets-rag" каждые 6 часов
```

---

### Шаг 12: Тест Weekly Full Rebuild (вручную)

```bash
# Не дожидаясь воскресенья, запустить вручную
docker-compose exec celery celery -A app.core.celery_app call app.features.rag.tasks.full_rebuild_all_cabinets_rag

# Следить за логами
docker-compose logs -f gpt

# Ожидаемые логи:
# "Starting weekly full rebuild for all cabinets"
# "Starting full_rebuild RAG indexing for all active cabinets"
# "Found 1 active cabinets for full_rebuild RAG indexing"
# "Full_rebuild indexing started for cabinet 1"
# "Starting full_rebuild indexing for cabinet 1"
# "Extracted data for cabinet 1: orders=500, products=100, ..."
# "Full_rebuild indexing completed for cabinet 1: 650 chunks indexed"
```

---

## 🔍 Проверка успешного развертывания

### Чеклист:

- ✅ Контейнеры запущены и здоровы
- ✅ Alembic миграции применены (009_add_timestamp_indexes_for_rag)
- ✅ RAG миграция применена (chunk_hash добавлен)
- ✅ Celery Beat показывает только weekly full rebuild
- ✅ WB sync триггерит RAG индексацию
- ✅ RAG индексация завершается успешно
- ✅ Статус RAG показывает completed

### Команды для проверки:

```bash
# 1. Проверить контейнеры
docker-compose ps

# 2. Проверить Alembic версию
docker-compose exec server alembic current
# Должно быть: 009_add_timestamp_indexes_for_rag

# 3. Проверить RAG БД
docker-compose exec gpt psql $RAG_DATABASE_URL -c \
  "SELECT column_name, data_type FROM information_schema.columns
   WHERE table_name='rag_metadata' AND column_name='chunk_hash';"
# Должно вывести: chunk_hash | character varying

# 4. Проверить индексы в основной БД
docker-compose exec db psql -U postgres -d wb_assist -c \
  "SELECT indexname FROM pg_indexes
   WHERE tablename IN ('wb_orders', 'wb_products', 'wb_stocks', 'wb_reviews', 'wb_sales')
   AND indexname LIKE 'idx_%created_at' OR indexname LIKE 'idx_%updated_at';"
# Должно вывести 20 индексов

# 5. Проверить Celery Beat расписание
docker-compose exec celery_beat celery -A app.core.celery_app inspect scheduled
# Должно показать index-full-rebuild-rag
```

---

## 🐛 Troubleshooting

### Проблема 1: Alembic миграция не применяется

**Ошибка:**
```
Target database is not up to date.
```

**Решение:**
```bash
docker-compose exec server alembic stamp head
docker-compose exec server alembic upgrade head
```

---

### Проблема 2: RAG миграция не применяется

**Ошибка:**
```
ERROR: relation "rag_metadata" does not exist
```

**Решение:**
```bash
# Проверить, что RAG таблицы созданы
docker-compose exec gpt python -c "
from gpt_integration.ai_chat.RAG.database import RAGEngine, RAGBase
RAGBase.metadata.create_all(bind=RAGEngine)
print('RAG tables created')
"

# Затем применить миграцию
docker-compose exec gpt psql $RAG_DATABASE_URL -f gpt_integration/ai_chat/RAG/migrations/001_add_chunk_hash.sql
```

---

### Проблема 3: RAG индексация не триггерится после sync

**Проверка:**
```bash
# Проверить логи sync
docker-compose logs -f server | grep "RAG"

# Должно быть:
# "Triggering Event-driven RAG indexing for cabinet X"
# или
# "Triggering RAG indexing for cabinet X (no delta available)"
```

**Решение:**
Убедитесь, что `RAG_ENABLED=true` в `.env` файле

---

### Проблема 4: Weekly schedule не работает

**Проверка:**
```bash
docker-compose logs celery_beat | grep "index-full-rebuild-rag"
```

**Решение:**
Проверьте, что в `server/app/core/celery_app.py` добавлен правильный schedule

---

## 📊 Ожидаемые логи (успешное развертывание)

### 1. При запуске контейнеров:
```
server_1       | Running migrations
server_1       | INFO  [alembic.runtime.migration] Running upgrade ... -> 009_add_timestamp_indexes_for_rag
gpt_1          | Starting GPT integration service
celery_beat_1  | celery beat v5.x.x is starting
celery_1       | celery@worker ready
```

### 2. При WB синхронизации:
```
server_1       | Starting WB sync for cabinet 1
server_1       | WB sync completed for cabinet 1
server_1       | Triggering Event-driven RAG indexing for cabinet 1 with 150 changes
gpt_1          | Starting incremental RAG indexing for cabinet 1 with 150 changed IDs
gpt_1          | Extracted data by IDs for cabinet 1: orders=45, products=30, ...
gpt_1          | Generating embeddings: batch 1/2 (100 chunks)
gpt_1          | Generating embeddings: batch 2/2 (50 chunks)
gpt_1          | Saved 150 records to vector DB
gpt_1          | Incremental indexing completed for cabinet 1: 150 chunks indexed
```

### 3. При weekly full rebuild:
```
celery_1       | Starting weekly full rebuild for all cabinets
celery_1       | Starting full_rebuild RAG indexing for all active cabinets
celery_1       | Found 1 active cabinets for full_rebuild RAG indexing
gpt_1          | Starting full_rebuild indexing for cabinet 1
gpt_1          | Extracted data for cabinet 1: orders=500, products=100, ...
gpt_1          | Full_rebuild indexing completed for cabinet 1: 650 chunks indexed
```

---

## ✅ Критерии успеха

После выполнения всех шагов:

1. **Контейнеры:**
   - Все контейнеры работают без перезапусков
   - Нет критических ошибок в логах

2. **Миграции:**
   - Alembic: 009_add_timestamp_indexes_for_rag применена
   - RAG: chunk_hash колонка существует
   - 20 новых индексов созданы

3. **Event-driven работает:**
   - WB sync успешно завершается
   - RAG индексация триггерится автоматически
   - Логи показывают "Event-driven" или "no delta available"

4. **Celery Beat настроен:**
   - Только weekly full rebuild в расписании
   - НЕТ старого 6-часового расписания

5. **RAG работает:**
   - Статус показывает "completed"
   - Чанки сохранены в БД
   - last_incremental_at обновлен

---

## 🎯 Следующие шаги после развертывания

### 1. Обновить sync_all_data() (опционально)
Для полной оптимизации модифицируйте `sync_service.py` для возврата `changed_ids`.

### 2. Мониторинг
Настройте мониторинг метрик:
- Время индексации
- Количество обработанных чанков
- Стоимость API

### 3. Реализовать Этап 3
Добавить логику очистки устаревших чанков в full rebuild режиме.

---

**Статус:** ✅ Готово к развертыванию
**Время выполнения:** ~15-20 минут
**Требования:** Docker, docker-compose, доступ к БД
