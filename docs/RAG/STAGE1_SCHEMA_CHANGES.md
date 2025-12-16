# Этап 1.2: Проектирование изменений в схеме БД

**Дата:** 2025-12-16
**Статус:** ✅ Завершен

---

## 📋 Обзор изменений

### Изменения в RAG БД (векторная БД):

1. **Добавить поле `chunk_hash` в `RAGMetadata`**
   - Тип: `String(64)` (SHA256 hash)
   - Назначение: Hash-based change detection
   - Nullable: `True` (для обратной совместимости)
   - Index: `True` (для быстрого поиска)

2. **Добавить индекс на `cabinet_id + source_table + source_id`**
   - Цель: Оптимизация поиска при full rebuild (идентификация устаревших чанков)

### Изменения в основной БД:

3. **Добавить индексы на `created_at` и `updated_at`**
   - Для всех таблиц: orders, products, stocks, reviews, sales
   - Цель: Оптимизация инкрементальных запросов

4. **Добавить составные индексы**
   - `(cabinet_id, created_at)`
   - `(cabinet_id, updated_at)`
   - Цель: Максимальная оптимизация для инкремента

---

## 🗄️ Изменения в модели RAGMetadata

### Текущая модель (models.py):

```python
class RAGMetadata(RAGBase):
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
    embeddings = relationship("RAGEmbedding", back_populates="rag_metadata", cascade="all, delete-orphan")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_rag_metadata_cabinet_type', 'cabinet_id', 'chunk_type'),
        Index('idx_rag_metadata_source', 'source_table', 'source_id'),
        UniqueConstraint('cabinet_id', 'source_table', 'source_id', name='uq_rag_metadata_cabinet_source'),
    )
```

### Новая модель (с изменениями):

```python
class RAGMetadata(RAGBase):
    __tablename__ = "rag_metadata"

    id = Column(Integer, primary_key=True, index=True)
    cabinet_id = Column(Integer, nullable=False, index=True)
    source_table = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    chunk_type = Column(String(20), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)

    # ✨ НОВОЕ ПОЛЕ
    chunk_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash от chunk_text

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связи
    embeddings = relationship("RAGEmbedding", back_populates="rag_metadata", cascade="all, delete-orphan")

    # Индексы и ограничения
    __table_args__ = (
        Index('idx_rag_metadata_cabinet_type', 'cabinet_id', 'chunk_type'),
        Index('idx_rag_metadata_source', 'source_table', 'source_id'),

        # ✨ НОВЫЙ ИНДЕКС: для быстрого поиска при full rebuild
        Index('idx_rag_metadata_cabinet_source', 'cabinet_id', 'source_table', 'source_id'),

        UniqueConstraint('cabinet_id', 'source_table', 'source_id', name='uq_rag_metadata_cabinet_source'),
    )
```

### Назначение `chunk_hash`:

**Проблема:**
Запись может попасть в инкремент (updated_at изменился), но chunk_text остался прежним.

**Пример:**
```
Товар "Платье летнее":
- Было: price=1000.50₽, rating=4.5
- Стало: price=1000.51₽, rating=4.5
- updated_at изменился (запись в инкременте)
- chunk_text: "Товар 'Платье летнее' ... цена 1000₽ ... рейтинг 4.5"
  (округлили цену → текст тот же)
```

**Решение:**
1. При обработке инкремента вычисляем hash нового chunk_text
2. Сравниваем с сохраненным chunk_hash
3. Если hash совпадает → пропускаем генерацию эмбеддинга
4. Если не совпадает → генерируем эмбеддинг, обновляем chunk_text и chunk_hash

**Экономия:**
- ~30% изменений не меняют chunk_text
- Экономия API: **дополнительно 30%**
- Итоговая экономия: **93%** вместо 90%

---

## 📊 Миграция RAG БД

### Миграция: Добавление `chunk_hash`

**Файл:** `gpt_integration/ai_chat/RAG/migrations/001_add_chunk_hash.sql`

```sql
-- Миграция: Добавление chunk_hash в RAGMetadata
-- Дата: 2025-12-16
-- Версия: 1.0.0

-- Добавить колонку chunk_hash
ALTER TABLE rag_metadata
ADD COLUMN chunk_hash VARCHAR(64);

-- Добавить индекс на chunk_hash
CREATE INDEX idx_rag_metadata_chunk_hash ON rag_metadata(chunk_hash);

-- Добавить составной индекс для оптимизации full rebuild
CREATE INDEX idx_rag_metadata_cabinet_source ON rag_metadata(cabinet_id, source_table, source_id);

-- Комментарии для документации
COMMENT ON COLUMN rag_metadata.chunk_hash IS 'SHA256 hash от chunk_text для hash-based change detection';
COMMENT ON INDEX idx_rag_metadata_chunk_hash IS 'Индекс для быстрого поиска чанков по hash';
COMMENT ON INDEX idx_rag_metadata_cabinet_source IS 'Составной индекс для оптимизации full rebuild (поиск устаревших чанков)';
```

### Скрипт для заполнения chunk_hash существующих записей

**Файл:** `gpt_integration/ai_chat/RAG/migrations/001_populate_chunk_hash.py`

```python
"""
Скрипт для заполнения chunk_hash существующих записей.

Выполняется один раз после миграции для обратной совместимости.
"""

import hashlib
import logging
from sqlalchemy.orm import Session
from gpt_integration.ai_chat.RAG.database import RAGSessionLocal
from gpt_integration.ai_chat.RAG.models import RAGMetadata

logger = logging.getLogger(__name__)


def calculate_chunk_hash(chunk_text: str) -> str:
    """Вычислить SHA256 hash от chunk_text."""
    return hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()


def populate_chunk_hash():
    """Заполнить chunk_hash для существующих записей."""
    db: Session = RAGSessionLocal()

    try:
        # Получить все записи без chunk_hash
        records = db.query(RAGMetadata).filter(
            RAGMetadata.chunk_hash.is_(None)
        ).all()

        total = len(records)
        logger.info(f"📊 Found {total} records without chunk_hash")

        # Обработать батчами
        batch_size = 1000
        updated = 0

        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]

            for record in batch:
                record.chunk_hash = calculate_chunk_hash(record.chunk_text)
                updated += 1

            db.commit()
            logger.info(f"✅ Updated {updated}/{total} records")

        logger.info(f"✅ Successfully populated chunk_hash for {updated} records")

    except Exception as e:
        logger.error(f"❌ Error populating chunk_hash: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    populate_chunk_hash()
```

**Запуск:**
```bash
# В контейнере gpt
docker-compose exec gpt python -m gpt_integration.ai_chat.RAG.migrations.001_populate_chunk_hash
```

---

## 🗄️ Миграции основной БД

### Миграция 1: Добавление индексов на created_at и updated_at

**Файл:** `server/alembic/versions/xxx_add_timestamp_indexes.py`

```python
"""
Add indexes on created_at and updated_at for incremental indexing

Revision ID: xxx_add_timestamp_indexes
Revises: <previous_revision>
Create Date: 2025-12-16
"""

from alembic import op


# revision identifiers
revision = 'xxx_add_timestamp_indexes'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes on created_at and updated_at."""

    # wb_orders
    op.create_index('idx_wb_orders_created_at', 'wb_orders', ['created_at'])
    op.create_index('idx_wb_orders_updated_at', 'wb_orders', ['updated_at'])
    op.create_index('idx_wb_orders_cabinet_created', 'wb_orders', ['cabinet_id', 'created_at'])
    op.create_index('idx_wb_orders_cabinet_updated', 'wb_orders', ['cabinet_id', 'updated_at'])

    # wb_products
    op.create_index('idx_wb_products_created_at', 'wb_products', ['created_at'])
    op.create_index('idx_wb_products_updated_at', 'wb_products', ['updated_at'])
    op.create_index('idx_wb_products_cabinet_created', 'wb_products', ['cabinet_id', 'created_at'])
    op.create_index('idx_wb_products_cabinet_updated', 'wb_products', ['cabinet_id', 'updated_at'])

    # wb_stocks
    op.create_index('idx_wb_stocks_created_at', 'wb_stocks', ['created_at'])
    op.create_index('idx_wb_stocks_updated_at', 'wb_stocks', ['updated_at'])
    op.create_index('idx_wb_stocks_cabinet_created', 'wb_stocks', ['cabinet_id', 'created_at'])
    op.create_index('idx_wb_stocks_cabinet_updated', 'wb_stocks', ['cabinet_id', 'updated_at'])

    # wb_reviews
    op.create_index('idx_wb_reviews_created_at', 'wb_reviews', ['created_at'])
    op.create_index('idx_wb_reviews_updated_at', 'wb_reviews', ['updated_at'])
    op.create_index('idx_wb_reviews_cabinet_created', 'wb_reviews', ['cabinet_id', 'created_at'])
    op.create_index('idx_wb_reviews_cabinet_updated', 'wb_reviews', ['cabinet_id', 'updated_at'])

    # wb_sales
    op.create_index('idx_wb_sales_created_at', 'wb_sales', ['created_at'])
    op.create_index('idx_wb_sales_updated_at', 'wb_sales', ['updated_at'])
    op.create_index('idx_wb_sales_cabinet_created', 'wb_sales', ['cabinet_id', 'created_at'])
    op.create_index('idx_wb_sales_cabinet_updated', 'wb_sales', ['cabinet_id', 'updated_at'])


def downgrade():
    """Remove indexes on created_at and updated_at."""

    # wb_orders
    op.drop_index('idx_wb_orders_cabinet_updated', table_name='wb_orders')
    op.drop_index('idx_wb_orders_cabinet_created', table_name='wb_orders')
    op.drop_index('idx_wb_orders_updated_at', table_name='wb_orders')
    op.drop_index('idx_wb_orders_created_at', table_name='wb_orders')

    # wb_products
    op.drop_index('idx_wb_products_cabinet_updated', table_name='wb_products')
    op.drop_index('idx_wb_products_cabinet_created', table_name='wb_products')
    op.drop_index('idx_wb_products_updated_at', table_name='wb_products')
    op.drop_index('idx_wb_products_created_at', table_name='wb_products')

    # wb_stocks
    op.drop_index('idx_wb_stocks_cabinet_updated', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_cabinet_created', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_updated_at', table_name='wb_stocks')
    op.drop_index('idx_wb_stocks_created_at', table_name='wb_stocks')

    # wb_reviews
    op.drop_index('idx_wb_reviews_cabinet_updated', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_cabinet_created', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_updated_at', table_name='wb_reviews')
    op.drop_index('idx_wb_reviews_created_at', table_name='wb_reviews')

    # wb_sales
    op.drop_index('idx_wb_sales_cabinet_updated', table_name='wb_sales')
    op.drop_index('idx_wb_sales_cabinet_created', table_name='wb_sales')
    op.drop_index('idx_wb_sales_updated_at', table_name='wb_sales')
    op.drop_index('idx_wb_sales_created_at', table_name='wb_sales')
```

---

## 📊 Оценка размера индексов

### Расчет размера индексов:

**Формула:** `Размер индекса ≈ Количество записей × (размер ключа + overhead)`

**Оценка для кабинета с 10,000 записей в каждой таблице:**

| Индекс | Тип | Размер ключа | Overhead | Итого на 10k записей |
|--------|-----|-------------|----------|---------------------|
| created_at | timestamp | 8 bytes | 12 bytes | ~195 KB |
| updated_at | timestamp | 8 bytes | 12 bytes | ~195 KB |
| (cabinet_id, created_at) | composite | 12 bytes | 12 bytes | ~234 KB |
| (cabinet_id, updated_at) | composite | 12 bytes | 12 bytes | ~234 KB |

**Итого на таблицу:** ~858 KB для 10,000 записей

**Итого на 5 таблиц:** ~4.3 MB для 10,000 записей в каждой

**Для 100 кабинетов × 10,000 записей:** ~430 MB дополнительных индексов

**Вывод:** Приемлемый overhead для существенного прироста производительности

---

## 🚀 План применения миграций

### Этап 1: RAG БД (векторная БД)

```bash
# 1. Добавить chunk_hash в модель
# Отредактировать: gpt_integration/ai_chat/RAG/models.py

# 2. Применить SQL миграцию
docker-compose exec db psql -U <user> -d <db> -f /path/to/001_add_chunk_hash.sql

# 3. Заполнить chunk_hash для существующих записей
docker-compose exec gpt python -m gpt_integration.ai_chat.RAG.migrations.001_populate_chunk_hash

# 4. Проверить результаты
docker-compose exec db psql -U <user> -d <db> -c "
SELECT COUNT(*) as total,
       COUNT(chunk_hash) as with_hash,
       COUNT(*) - COUNT(chunk_hash) as without_hash
FROM rag_metadata;
"

# Ожидаемый результат: without_hash = 0
```

### Этап 2: Основная БД (индексы)

```bash
# 1. Создать Alembic миграцию
docker-compose exec server alembic revision -m "add_timestamp_indexes"

# 2. Отредактировать миграцию (использовать код выше)

# 3. Применить миграцию
docker-compose exec server alembic upgrade head

# 4. Проверить индексы
docker-compose exec db psql -U <user> -d <db> -c "
SELECT tablename, indexname
FROM pg_indexes
WHERE indexname LIKE '%created_at%' OR indexname LIKE '%updated_at%'
ORDER BY tablename, indexname;
"

# Ожидаемый результат: 20 новых индексов (4 на таблицу × 5 таблиц)
```

---

## ✅ Проверка готовности

### Чеклист перед применением миграций:

- [ ] Создан бэкап обеих БД (основная и векторная)
- [ ] Миграции протестированы на dev окружении
- [ ] Оценено время выполнения миграций (зависит от размера БД)
- [ ] Запланировано окно обслуживания (если нужно)
- [ ] Подготовлен rollback план

### Чеклист после применения миграций:

- [ ] Проверены индексы в обеих БД
- [ ] Заполнен chunk_hash для всех существующих записей
- [ ] Протестированы запросы с новыми индексами
- [ ] Проверена производительность (EXPLAIN ANALYZE)
- [ ] Обновлена документация

---

## 📈 Ожидаемое улучшение производительности

### Запросы без индексов (ДО):

```sql
EXPLAIN ANALYZE
SELECT * FROM wb_orders
WHERE cabinet_id = 1
  AND created_at > '2025-12-15 12:00:00';

-- Execution time: ~50-100ms (Seq Scan)
-- Cost: 1000-2000
```

### Запросы с индексами (ПОСЛЕ):

```sql
EXPLAIN ANALYZE
SELECT * FROM wb_orders
WHERE cabinet_id = 1
  AND created_at > '2025-12-15 12:00:00';

-- Execution time: ~1-5ms (Index Scan)
-- Cost: 10-50
```

**Ускорение:** 10-50x для инкрементальных запросов

---

## 🎯 Следующие шаги

**Этап 1.3: Документирование API контрактов**
- Добавить параметр `full_rebuild` в API
- Документировать новые метрики

**После завершения Этапа 1:**
- Переход к Этапу 2: Реализация инкрементальной индексации

---

**Дата завершения:** 2025-12-16
**Статус:** ✅ Этап 1.2 завершен успешно
**Следующий этап:** 1.3 - Документирование API контрактов
