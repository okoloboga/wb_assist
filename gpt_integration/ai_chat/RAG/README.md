# RAG Module - README

## 📋 Описание

Модуль RAG (Retrieval-Augmented Generation) для AI Chat Service. Предоставляет функциональность для индексации данных из основной БД в векторную БД и поиска релевантных данных для обогащения промптов.

## 🚀 Установка

### 1. Установка расширения pgvector в PostgreSQL

**Для Docker (рекомендуется):**

Используйте образ PostgreSQL с предустановленным pgvector:
```yaml
# В docker-compose.yml
db:
  image: pgvector/pgvector:pg15  # PostgreSQL 15 с pgvector
```

**Для локальной установки (Ubuntu/Debian):**

```bash
# Установка зависимостей
sudo apt-get update
sudo apt-get install -y postgresql-server-dev-15 build-essential git

# Клонирование репозитория
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector

# Компиляция и установка
make
sudo make install
```

**Создание расширения в БД:**

```sql
-- Подключиться к базе данных
\c your_database_name

-- Создать расширение
CREATE EXTENSION IF NOT EXISTS vector;

-- Проверить установку
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

### 2. Установка Python зависимостей

```bash
pip install -r gpt_integration/ai_chat/requirements.txt
```

Пакет `pgvector==0.3.0` уже добавлен в requirements.txt.

### 3. Выполнение миграции

**Вариант 1: SQL скрипт (рекомендуется для начала)**

```bash
psql -U postgres -d your_database -f gpt_integration/ai_chat/rag/migrations/001_create_rag_tables.sql
```

**Вариант 2: Через Python (при старте приложения)**

```python
from gpt_integration.ai_chat.rag.database import init_rag_db

# При старте приложения
init_rag_db()
```

## ⚙️ Конфигурация

### Переменные окружения

Добавьте в `.env` или `docker-compose.yml`:

```env
# RAG Configuration
RAG_ENABLED=true
RAG_VECTOR_DB_URL=postgresql://user:password@localhost:5432/wb_assist
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small

# Опциональные параметры
RAG_MAX_CHUNKS=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CONTEXT_MAX_LENGTH=3000
RAG_INDEXING_INTERVAL_HOURS=6
RAG_EMBEDDING_BATCH_SIZE=100
```

## 📁 Структура модуля

```
rag/
├── __init__.py              # Экспорты модуля
├── database.py              # Конфигурация БД
├── models.py                # SQLAlchemy модели
├── migrations/              # SQL миграции
│   └── 001_create_rag_tables.sql
└── README.md                # Этот файл
```

## 🧪 Тестирование

**Проверка установки pgvector:**
```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

**Проверка создания таблиц:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'rag_%';
```

**Тестовая вставка данных:**
```sql
-- Вставить тестовую запись
INSERT INTO rag_metadata (cabinet_id, source_table, source_id, chunk_type, chunk_text)
VALUES (1, 'wb_products', 123, 'product', 'Тестовый чанк для проверки');

-- Проверить вставку
SELECT * FROM rag_metadata WHERE cabinet_id = 1;
```

## 📚 Дополнительные ресурсы

- [Документация pgvector](https://github.com/pgvector/pgvector)
- [SQLAlchemy pgvector](https://github.com/pgvector/pgvector-python)
- [Детальный план разработки](./STAGE_1_INFRASTRUCTURE.md)

---

**Версия:** 1.0.0  
**Статус:** Этап 1 - Инфраструктура








