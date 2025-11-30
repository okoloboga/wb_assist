# Этап 1: Подготовка инфраструктуры

## 📋 Обзор этапа

**Цель:** Настроить векторную базу данных PostgreSQL с расширением pgvector и создать необходимые таблицы для хранения векторных представлений данных.

**Длительность:** 1-2 дня

**Зависимости:** Нет (первый этап)

**Результат:** Готова инфраструктура для хранения и поиска векторов в PostgreSQL.

---

## 🎯 Задачи этапа

### Задача 1.1: Установка расширения pgvector в PostgreSQL

#### Описание
Расширение pgvector необходимо для хранения векторных данных и выполнения векторного поиска в PostgreSQL. Это основа всей RAG-системы.

#### Действия

**1. Проверка версии PostgreSQL**
- Требуется версия PostgreSQL >= 11
- Проверить текущую версию: `SELECT version();`
- Если версия < 11, необходимо обновить PostgreSQL

**2. Установка pgvector на сервере**

**Для Ubuntu/Debian:**
```bash
# Установка зависимостей
sudo apt-get update
sudo apt-get install -y postgresql-server-dev-XX build-essential git

# Клонирование репозитория
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector

# Компиляция и установка
make
sudo make install
```

**Для Docker:**
- Использовать образ PostgreSQL с предустановленным pgvector
- Или добавить установку в Dockerfile

**3. Создание расширения в базе данных**
```sql
-- Подключиться к базе данных
\c your_database_name

-- Создать расширение
CREATE EXTENSION IF NOT EXISTS vector;

-- Проверить установку
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**4. Проверка установки**
```sql
-- Проверить версию расширения
SELECT extversion FROM pg_extension WHERE extname = 'vector';

-- Проверить доступные операторы
\dx+ vector
```

#### Критерии готовности
- ✅ Расширение pgvector установлено
- ✅ Расширение создано в базе данных
- ✅ Версия расширения отображается корректно

#### Документация
- Записать версию pgvector в документацию
- Сохранить команды установки для других окружений (dev, staging, production)
- Добавить в README инструкции по установке

---

### Задача 1.2: Создание таблиц для RAG

#### Описание
Создание трех основных таблиц для хранения метаданных, векторных представлений и статуса индексации.

#### Структура таблиц

**Таблица 1: `rag_metadata`**
Хранит метаданные и исходный текст чанков. Связывает векторные представления с исходными данными.

**Поля:**
- `id` — SERIAL PRIMARY KEY
- `cabinet_id` — INTEGER NOT NULL (ID кабинета Wildberries)
- `source_table` — VARCHAR(50) NOT NULL (wb_orders, wb_products, wb_stocks, wb_reviews, wb_sales)
- `source_id` — INTEGER NOT NULL (ID записи в исходной таблице)
- `chunk_type` — VARCHAR(20) NOT NULL (order, product, stock, review, sale)
- `chunk_text` — TEXT NOT NULL (исходный текст чанка)
- `created_at` — TIMESTAMP WITH TIME ZONE DEFAULT NOW()
- `updated_at` — TIMESTAMP WITH TIME ZONE

**Индексы:**
- `idx_rag_metadata_cabinet_id` на `cabinet_id`
- `idx_rag_metadata_cabinet_type` на `(cabinet_id, chunk_type)`
- `idx_rag_metadata_source` на `(source_table, source_id)`
- `idx_rag_metadata_created_at` на `created_at`

**Ограничения:**
- UNIQUE на `(cabinet_id, source_table, source_id)` — предотвращение дубликатов

**Таблица 2: `rag_embeddings`**
Хранит векторные представления документов. Связана с `rag_metadata` через `metadata_id`.

**Поля:**
- `id` — SERIAL PRIMARY KEY
- `embedding` — vector(1536) NOT NULL (векторное представление)
- `metadata_id` — INTEGER NOT NULL (FK на rag_metadata.id)
- `created_at` — TIMESTAMP WITH TIME ZONE DEFAULT NOW()
- `updated_at` — TIMESTAMP WITH TIME ZONE

**Индексы:**
- `idx_rag_embeddings_metadata_id` на `metadata_id`
- HNSW индекс на `embedding` для векторного поиска

**Ограничения:**
- FOREIGN KEY на `rag_metadata.id` с ON DELETE CASCADE

**Таблица 3: `rag_index_status`**
Отслеживает статус индексации для каждого кабинета. Предотвращает параллельную индексацию и хранит метрики.

**Поля:**
- `id` — SERIAL PRIMARY KEY
- `cabinet_id` — INTEGER UNIQUE NOT NULL (ID кабинета)
- `last_indexed_at` — TIMESTAMP WITH TIME ZONE (дата последней полной индексации)
- `last_incremental_at` — TIMESTAMP WITH TIME ZONE (дата последнего инкрементального обновления)
- `indexing_status` — VARCHAR(20) DEFAULT 'pending' (pending, in_progress, completed, failed)
- `total_chunks` — INTEGER DEFAULT 0 (количество проиндексированных чанков)
- `created_at` — TIMESTAMP WITH TIME ZONE DEFAULT NOW()
- `updated_at` — TIMESTAMP WITH TIME ZONE

**Индексы:**
- `idx_rag_index_status_cabinet_id` на `cabinet_id` (уже есть UNIQUE)

#### SQLAlchemy модели

**Файл:** `gpt_integration/ai_chat/rag/models.py`

**Структура файла:**

```python
"""
SQLAlchemy models for RAG system.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import BYTEA
from pgvector.sqlalchemy import Vector
from ..database import Base


class RAGMetadata(Base):
    """
    Метаданные и исходный текст чанков.
    
    Связывает векторные представления с исходными данными из основной БД.
    """
    __tablename__ = "rag_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, nullable=False, index=True)
    source_table = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    chunk_type = Column(String(20), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    embeddings = relationship("RAGEmbedding", back_populates="metadata", cascade="all, delete-orphan")
    
    # Индексы и ограничения
    __table_args__ = (
        Index('idx_rag_metadata_cabinet_type', 'cabinet_id', 'chunk_type'),
        Index('idx_rag_metadata_source', 'source_table', 'source_id'),
        UniqueConstraint('cabinet_id', 'source_table', 'source_id', name='uq_rag_metadata_cabinet_source'),
    )
    
    def __repr__(self) -> str:
        return f"<RAGMetadata(id={self.id}, cabinet_id={self.cabinet_id}, chunk_type={self.chunk_type})>"


class RAGEmbedding(Base):
    """
    Векторные представления документов.
    
    Хранит embedding размерности 1536 (для OpenAI text-embedding-3-small).
    """
    __tablename__ = "rag_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    embedding = Column(Vector(1536), nullable=False)
    metadata_id = Column(Integer, ForeignKey("rag_metadata.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    metadata = relationship("RAGMetadata", back_populates="embeddings")
    
    def __repr__(self) -> str:
        return f"<RAGEmbedding(id={self.id}, metadata_id={self.metadata_id})>"


class RAGIndexStatus(Base):
    """
    Статус индексации для каждого кабинета.
    
    Отслеживает прогресс индексации и предотвращает параллельную обработку.
    """
    __tablename__ = "rag_index_status"
    
    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, unique=True, nullable=False, index=True)
    last_indexed_at = Column(DateTime(timezone=True), nullable=True)
    last_incremental_at = Column(DateTime(timezone=True), nullable=True)
    indexing_status = Column(String(20), default='pending', nullable=False)
    total_chunks = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<RAGIndexStatus(cabinet_id={self.cabinet_id}, status={self.indexing_status}, chunks={self.total_chunks})>"
```

**Зависимости:**
- Установить пакет `pgvector` для SQLAlchemy: `pip install pgvector`

#### Действия

1. **Создать файл `gpt_integration/ai_chat/rag/models.py`**
   - Импортировать необходимые зависимости
   - Создать классы моделей
   - Определить все поля, индексы и ограничения

2. **Проверить корректность моделей**
   - Все поля определены
   - Тип `Vector(1536)` правильно указан
   - Индексы и ограничения определены
   - Relationships настроены

#### Критерии готовности
- ✅ Файл `models.py` создан
- ✅ Все три модели определены
- ✅ Поля, индексы и ограничения корректны
- ✅ Relationships настроены

---

### Задача 1.3: Создание миграций базы данных

#### Описание
Создание SQL скриптов или Alembic миграций для создания таблиц и индексов в базе данных.

#### Вариант 1: SQL скрипт миграции

**Файл:** `gpt_integration/ai_chat/rag/migrations/001_create_rag_tables.sql`

**Содержимое:**

```sql
-- Миграция: Создание таблиц для RAG системы
-- Дата: 2025-01-XX
-- Версия: 1.0.0

-- Проверка наличия расширения pgvector
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE EXTENSION IF NOT EXISTS vector;
    END IF;
END $$;

-- Таблица 1: rag_metadata
CREATE TABLE IF NOT EXISTS rag_metadata (
    id SERIAL PRIMARY KEY,
    cabinet_id INTEGER NOT NULL,
    source_table VARCHAR(50) NOT NULL,
    source_id INTEGER NOT NULL,
    chunk_type VARCHAR(20) NOT NULL,
    chunk_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Уникальное ограничение: один чанк на одну запись
    CONSTRAINT uq_rag_metadata_cabinet_source UNIQUE (cabinet_id, source_table, source_id)
);

-- Таблица 2: rag_embeddings
CREATE TABLE IF NOT EXISTS rag_embeddings (
    id SERIAL PRIMARY KEY,
    embedding vector(1536) NOT NULL,
    metadata_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Внешний ключ с каскадным удалением
    CONSTRAINT fk_rag_embeddings_metadata 
        FOREIGN KEY (metadata_id) 
        REFERENCES rag_metadata(id) 
        ON DELETE CASCADE
);

-- Таблица 3: rag_index_status
CREATE TABLE IF NOT EXISTS rag_index_status (
    id SERIAL PRIMARY KEY,
    cabinet_id INTEGER UNIQUE NOT NULL,
    last_indexed_at TIMESTAMP WITH TIME ZONE,
    last_incremental_at TIMESTAMP WITH TIME ZONE,
    indexing_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    total_chunks INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Индексы для rag_metadata
CREATE INDEX IF NOT EXISTS idx_rag_metadata_cabinet_id 
    ON rag_metadata(cabinet_id);
CREATE INDEX IF NOT EXISTS idx_rag_metadata_cabinet_type 
    ON rag_metadata(cabinet_id, chunk_type);
CREATE INDEX IF NOT EXISTS idx_rag_metadata_source 
    ON rag_metadata(source_table, source_id);
CREATE INDEX IF NOT EXISTS idx_rag_metadata_created_at 
    ON rag_metadata(created_at);

-- Индексы для rag_embeddings
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_metadata_id 
    ON rag_embeddings(metadata_id);

-- HNSW индекс для векторного поиска (важно для производительности)
-- Параметры: m=16 (количество связей), ef_construction=64 (точность построения)
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector 
    ON rag_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Индекс для rag_index_status (уже есть UNIQUE на cabinet_id)
-- Дополнительные индексы не требуются

-- Комментарии к таблицам
COMMENT ON TABLE rag_metadata IS 'Метаданные и исходный текст чанков для RAG системы';
COMMENT ON TABLE rag_embeddings IS 'Векторные представления документов (embeddings)';
COMMENT ON TABLE rag_index_status IS 'Статус индексации для каждого кабинета';

-- Комментарии к полям
COMMENT ON COLUMN rag_metadata.cabinet_id IS 'ID кабинета Wildberries';
COMMENT ON COLUMN rag_metadata.source_table IS 'Исходная таблица (wb_orders, wb_products, и т.д.)';
COMMENT ON COLUMN rag_metadata.chunk_type IS 'Тип данных (order, product, stock, review, sale)';
COMMENT ON COLUMN rag_embeddings.embedding IS 'Векторное представление размерности 1536 (OpenAI)';
```

#### Вариант 2: Alembic миграция

Если проект использует Alembic, создать миграцию:

```python
"""create_rag_tables

Revision ID: 001_create_rag_tables
Revises: 
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = '001_create_rag_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Создать расширение pgvector
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Создать таблицы
    op.create_table(
        'rag_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cabinet_id', sa.Integer(), nullable=False),
        sa.Column('source_table', sa.String(50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(20), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cabinet_id', 'source_table', 'source_id', name='uq_rag_metadata_cabinet_source')
    )
    
    op.create_table(
        'rag_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('metadata_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['metadata_id'], ['rag_metadata.id'], ondelete='CASCADE')
    )
    
    op.create_table(
        'rag_index_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cabinet_id', sa.Integer(), nullable=False),
        sa.Column('last_indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_incremental_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('indexing_status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('total_chunks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cabinet_id')
    )
    
    # Создать индексы
    op.create_index('idx_rag_metadata_cabinet_id', 'rag_metadata', ['cabinet_id'])
    op.create_index('idx_rag_metadata_cabinet_type', 'rag_metadata', ['cabinet_id', 'chunk_type'])
    op.create_index('idx_rag_metadata_source', 'rag_metadata', ['source_table', 'source_id'])
    op.create_index('idx_rag_metadata_created_at', 'rag_metadata', ['created_at'])
    op.create_index('idx_rag_embeddings_metadata_id', 'rag_embeddings', ['metadata_id'])
    
    # HNSW индекс для векторного поиска
    op.execute("""
        CREATE INDEX idx_rag_embeddings_vector 
        ON rag_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    op.drop_index('idx_rag_embeddings_vector', 'rag_embeddings')
    op.drop_index('idx_rag_embeddings_metadata_id', 'rag_embeddings')
    op.drop_index('idx_rag_metadata_created_at', 'rag_metadata')
    op.drop_index('idx_rag_metadata_source', 'rag_metadata')
    op.drop_index('idx_rag_metadata_cabinet_type', 'rag_metadata')
    op.drop_index('idx_rag_metadata_cabinet_id', 'rag_metadata')
    
    op.drop_table('rag_index_status')
    op.drop_table('rag_embeddings')
    op.drop_table('rag_metadata')
```

#### Действия

1. **Выбрать метод миграции**
   - SQL скрипт (проще, если не используется Alembic)
   - Alembic миграция (если проект использует Alembic)

2. **Создать файл миграции**
   - Создать папку `gpt_integration/ai_chat/rag/migrations/` (если нужно)
   - Создать файл миграции

3. **Выполнить миграцию на тестовой БД**
   ```bash
   # Для SQL скрипта
   psql -U postgres -d your_database -f migrations/001_create_rag_tables.sql
   
   # Для Alembic
   alembic upgrade head
   ```

4. **Проверить создание таблиц**
   ```sql
   -- Проверить наличие таблиц
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name LIKE 'rag_%';
   
   -- Проверить структуру таблиц
   \d rag_metadata
   \d rag_embeddings
   \d rag_index_status
   
   -- Проверить индексы
   SELECT indexname, indexdef 
   FROM pg_indexes 
   WHERE tablename LIKE 'rag_%';
   ```

5. **Вставить тестовые данные**
   ```sql
   -- Тестовая запись в rag_metadata
   INSERT INTO rag_metadata (cabinet_id, source_table, source_id, chunk_type, chunk_text)
   VALUES (1, 'wb_products', 123, 'product', 'Тестовый чанк');
   
   -- Проверить вставку
   SELECT * FROM rag_metadata;
   ```

#### Критерии готовности
- ✅ Миграция создана
- ✅ Миграция успешно выполнена на тестовой БД
- ✅ Все таблицы созданы
- ✅ Все индексы созданы (включая HNSW)
- ✅ Тестовые данные вставляются корректно

---

### Задача 1.4: Настройка подключения к векторной БД

#### Описание
Создание модуля для подключения к векторной базе данных. Может использовать ту же БД, что и основная, или отдельную.

#### Файл: `gpt_integration/ai_chat/rag/database.py`

**Структура:**

```python
"""
Database configuration for RAG system.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Приоритет 1: RAG_VECTOR_DB_URL (отдельная БД для векторов)
# Приоритет 2: DATABASE_URL (основная БД, может быть та же)
RAG_VECTOR_DB_URL = os.getenv(
    "RAG_VECTOR_DB_URL",
    os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
)

# Создание engine для векторной БД
# Параметры для оптимизации:
# - pool_pre_ping=True - проверка соединения перед использованием
# - pool_size=5 - размер пула соединений
# - max_overflow=10 - максимальное количество дополнительных соединений
rag_engine = create_engine(
    RAG_VECTOR_DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False  # Установить True для отладки SQL запросов
)

# Session factory
RAGSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=rag_engine
)

# Base для моделей RAG
RAGBase = declarative_base()


def get_rag_db() -> Generator[Session, None, None]:
    """
    Dependency injection для получения сессии БД RAG.
    
    Использование:
        db: Session = Depends(get_rag_db)
    """
    db = RAGSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_rag_db() -> None:
    """
    Инициализация БД: создание всех таблиц.
    
    Вызывается при старте приложения.
    """
    from .models import RAGMetadata, RAGEmbedding, RAGIndexStatus
    
    RAGBase.metadata.create_all(bind=rag_engine)
```

**Важно:** Если используется та же БД, что и основная, можно использовать существующий engine и Base. Но для изоляции лучше создать отдельные.

#### Действия

1. **Создать файл `gpt_integration/ai_chat/rag/database.py`**
   - Определить URL подключения
   - Создать engine
   - Создать SessionLocal
   - Создать Base (или использовать существующий)

2. **Обновить модели**
   - В `models.py` использовать `RAGBase` из `database.py`

3. **Проверить подключение**
   ```python
   # Тестовый скрипт
   from gpt_integration.ai_chat.rag.database import get_rag_db
   
   db = next(get_rag_db())
   # Выполнить простой запрос
   result = db.execute("SELECT 1")
   print(result.scalar())
   ```

#### Критерии готовности
- ✅ Файл `database.py` создан
- ✅ Подключение к БД работает
- ✅ Можно выполнить запрос к таблицам RAG
- ✅ `get_rag_db()` работает для dependency injection

---

### Задача 1.5: Обновление переменных окружения

#### Описание
Добавление новых переменных окружения для конфигурации RAG системы.

#### Файлы для обновления

**1. `.env` (локальная разработка)**
```env
# RAG Configuration
RAG_ENABLED=true
RAG_VECTOR_DB_URL=postgresql://user:password@localhost:5432/wb_assist
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small

# Опциональные параметры RAG
RAG_MAX_CHUNKS=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CONTEXT_MAX_LENGTH=3000
RAG_INDEXING_INTERVAL_HOURS=6
RAG_EMBEDDING_BATCH_SIZE=100
```

**2. `docker-compose.yml`**
```yaml
services:
  gpt:
    environment:
      # RAG Configuration
      - RAG_ENABLED=${RAG_ENABLED:-true}
      - RAG_VECTOR_DB_URL=${RAG_VECTOR_DB_URL:-postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}}
      - OPENAI_EMBEDDINGS_MODEL=${OPENAI_EMBEDDINGS_MODEL:-text-embedding-3-small}
      - RAG_MAX_CHUNKS=${RAG_MAX_CHUNKS:-5}
      - RAG_SIMILARITY_THRESHOLD=${RAG_SIMILARITY_THRESHOLD:-0.7}
      - RAG_CONTEXT_MAX_LENGTH=${RAG_CONTEXT_MAX_LENGTH:-3000}
      - RAG_INDEXING_INTERVAL_HOURS=${RAG_INDEXING_INTERVAL_HOURS:-6}
      - RAG_EMBEDDING_BATCH_SIZE=${RAG_EMBEDDING_BATCH_SIZE:-100}
```

**3. `.env.example` (шаблон)**
```env
# RAG Configuration
RAG_ENABLED=true
RAG_VECTOR_DB_URL=postgresql://user:password@localhost:5432/wb_assist
OPENAI_EMBEDDINGS_MODEL=text-embedding-3-small

# Опциональные параметры RAG
RAG_MAX_CHUNKS=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CONTEXT_MAX_LENGTH=3000
RAG_INDEXING_INTERVAL_HOURS=6
RAG_EMBEDDING_BATCH_SIZE=100
```

#### Описание переменных

| Переменная | Описание | Значение по умолчанию | Обязательная |
|------------|----------|----------------------|--------------|
| `RAG_ENABLED` | Включить/выключить RAG | `true` | Нет |
| `RAG_VECTOR_DB_URL` | URL подключения к векторной БД | `DATABASE_URL` | Нет |
| `OPENAI_EMBEDDINGS_MODEL` | Модель для генерации эмбеддингов | `text-embedding-3-small` | Нет |
| `RAG_MAX_CHUNKS` | Максимальное количество чанков в контексте | `5` | Нет |
| `RAG_SIMILARITY_THRESHOLD` | Минимальный порог релевантности (0-1) | `0.7` | Нет |
| `RAG_CONTEXT_MAX_LENGTH` | Максимальная длина контекста в символах | `3000` | Нет |
| `RAG_INDEXING_INTERVAL_HOURS` | Интервал индексации в часах | `6` | Нет |
| `RAG_EMBEDDING_BATCH_SIZE` | Размер батча для генерации эмбеддингов | `100` | Нет |

#### Действия

1. **Обновить `.env`**
   - Добавить все переменные
   - Установить значения для локальной разработки

2. **Обновить `docker-compose.yml`**
   - Добавить переменные в секцию `environment` сервиса `gpt`

3. **Обновить `.env.example`**
   - Добавить все переменные с описаниями

4. **Создать документацию**
   - Описать каждую переменную
   - Указать рекомендуемые значения

#### Критерии готовности
- ✅ Все переменные добавлены в `.env`
- ✅ Docker-compose обновлен
- ✅ `.env.example` обновлен
- ✅ Документация создана

---

## ✅ Критерии готовности Этапа 1

### Общие критерии

- ✅ Расширение pgvector установлено и работает
- ✅ Все три таблицы созданы в БД
- ✅ Индексы созданы (включая HNSW на embedding)
- ✅ SQLAlchemy модели созданы и протестированы
- ✅ Подключение к векторной БД работает
- ✅ Переменные окружения настроены
- ✅ Документация обновлена

### Тестирование

**1. Проверка расширения pgvector:**
```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

**2. Проверка таблиц:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'rag_%';
```

**3. Проверка индексов:**
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename LIKE 'rag_%';
```

**4. Тестовая вставка данных:**
```sql
-- Вставить тестовую запись
INSERT INTO rag_metadata (cabinet_id, source_table, source_id, chunk_type, chunk_text)
VALUES (1, 'wb_products', 123, 'product', 'Тестовый чанк для проверки');

-- Проверить вставку
SELECT * FROM rag_metadata WHERE cabinet_id = 1;
```

**5. Тест векторного типа:**
```sql
-- Создать тестовый вектор
INSERT INTO rag_embeddings (embedding, metadata_id)
VALUES (
    '[0.1, 0.2, 0.3]'::vector(1536),  -- Упрощенный пример
    1
);

-- Проверить вставку
SELECT id, embedding FROM rag_embeddings WHERE metadata_id = 1;
```

---

## 🐛 Возможные проблемы и решения

### Проблема 1: pgvector не устанавливается

**Симптомы:** Ошибка при создании расширения `CREATE EXTENSION vector;`

**Решения:**
- Проверить версию PostgreSQL (требуется >= 11)
- Установить зависимости для компиляции (build-essential, postgresql-server-dev)
- Проверить права доступа к базе данных

### Проблема 2: Ошибка при создании HNSW индекса

**Симптомы:** Ошибка при создании индекса `USING hnsw`

**Решения:**
- Проверить, что расширение pgvector установлено
- Убедиться, что версия pgvector поддерживает HNSW (>= 0.4.0)
- Попробовать создать индекс с меньшими параметрами (m=8, ef_construction=32)

### Проблема 3: Модели SQLAlchemy не работают с Vector типом

**Симптомы:** Ошибка импорта или создания таблицы

**Решения:**
- Установить пакет `pgvector` для Python: `pip install pgvector`
- Проверить импорт: `from pgvector.sqlalchemy import Vector`
- Убедиться, что версия SQLAlchemy совместима

---

## 📚 Дополнительные ресурсы

- [Документация pgvector](https://github.com/pgvector/pgvector)
- [SQLAlchemy pgvector](https://github.com/pgvector/pgvector-python)
- [HNSW индексы в pgvector](https://github.com/pgvector/pgvector#hnsw)

---

**Версия:** 1.0.0  
**Дата:** 2025-01-XX  
**Статус:** Детальный план Этапа 1

