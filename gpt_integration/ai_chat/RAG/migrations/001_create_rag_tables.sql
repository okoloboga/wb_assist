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

-- Комментарии к таблицам
COMMENT ON TABLE rag_metadata IS 'Метаданные и исходный текст чанков для RAG системы';
COMMENT ON TABLE rag_embeddings IS 'Векторные представления документов (embeddings)';
COMMENT ON TABLE rag_index_status IS 'Статус индексации для каждого кабинета';

-- Комментарии к полям
COMMENT ON COLUMN rag_metadata.cabinet_id IS 'ID кабинета Wildberries';
COMMENT ON COLUMN rag_metadata.source_table IS 'Исходная таблица (wb_orders, wb_products, и т.д.)';
COMMENT ON COLUMN rag_metadata.chunk_type IS 'Тип данных (order, product, stock, review, sale)';
COMMENT ON COLUMN rag_embeddings.embedding IS 'Векторное представление размерности 1536 (OpenAI)';










