# Инструкции по настройке RAG - Этап 1

## ✅ Что уже сделано

1. ✅ Создана структура модуля RAG:
   - `rag/__init__.py` - инициализация модуля
   - `rag/database.py` - конфигурация БД
   - `rag/models.py` - SQLAlchemy модели (RAGMetadata, RAGEmbedding, RAGIndexStatus)
   - `rag/migrations/001_create_rag_tables.sql` - SQL миграция

2. ✅ Обновлены зависимости:
   - Добавлен `pgvector==0.3.0` в `requirements.txt`

3. ✅ Обновлена конфигурация:
   - Добавлены переменные окружения RAG в `docker-compose.yml`

## 🔧 Что нужно сделать вручную

### 1. Установить расширение pgvector в PostgreSQL

**Вариант A: Docker (рекомендуется)**

Обновите `docker-compose.yml`, секция `db`:
```yaml
db:
  image: pgvector/pgvector:pg15  # Вместо postgres:15-alpine
```

Затем пересоздайте контейнер:
```bash
docker-compose down
docker-compose up -d db
```

**Вариант B: Локальная установка**

См. инструкции в `README.md` в разделе "Установка расширения pgvector".

### 2. Создать расширение в базе данных

Подключитесь к PostgreSQL и выполните:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Проверьте установку:
```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

### 3. Выполнить миграцию

**Вариант A: SQL скрипт**
```bash
psql -U postgres -d your_database -f gpt_integration/ai_chat/rag/migrations/001_create_rag_tables.sql
```

**Вариант B: Через Python (при старте приложения)**
Добавьте в код инициализации приложения:
```python
from gpt_integration.ai_chat.rag.database import init_rag_db

# При старте
init_rag_db()
```

### 4. Установить Python зависимости

```bash
pip install -r gpt_integration/ai_chat/requirements.txt
```

Или если используете Docker:
```bash
docker-compose build gpt
```

### 5. Настроить переменные окружения

Добавьте в `.env` (если еще не добавлено):
```env
# RAG Configuration
RAG_ENABLED=true
RAG_VECTOR_DB_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small
RAG_MAX_CHUNKS=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CONTEXT_MAX_LENGTH=3000
RAG_INDEXING_INTERVAL_HOURS=6
RAG_EMBEDDING_BATCH_SIZE=100
```

## ✅ Проверка готовности

После выполнения всех шагов проверьте:

1. **Расширение pgvector установлено:**
   ```sql
   SELECT extversion FROM pg_extension WHERE extname = 'vector';
   ```

2. **Таблицы созданы:**
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name LIKE 'rag_%';
   ```
   Должны быть: `rag_metadata`, `rag_embeddings`, `rag_index_status`

3. **Индексы созданы:**
   ```sql
   SELECT indexname 
   FROM pg_indexes 
   WHERE tablename LIKE 'rag_%';
   ```
   Должен быть HNSW индекс `idx_rag_embeddings_vector`

4. **Тестовая вставка:**
   ```sql
   INSERT INTO rag_metadata (cabinet_id, source_table, source_id, chunk_type, chunk_text)
   VALUES (1, 'wb_products', 123, 'product', 'Тестовый чанк');
   
   SELECT * FROM rag_metadata WHERE cabinet_id = 1;
   ```

## 🚀 Следующие шаги

После завершения Этапа 1 можно переходить к:
- **Этап 2:** Модуль индексации данных (см. `STAGE_2_INDEXING.md`)

---

**Статус:** Этап 1 - Инфраструктура ✅  
**Дата:** 2025-01-XX







