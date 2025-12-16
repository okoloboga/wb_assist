-- Миграция: Добавление chunk_hash в RAGMetadata
-- Дата: 2025-12-16
-- Версия: 1.0.0
-- Описание: Добавление поля chunk_hash для hash-based change detection
--           и индексов для оптимизации инкрементальной индексации

-- Добавить колонку chunk_hash
ALTER TABLE rag_metadata
ADD COLUMN IF NOT EXISTS chunk_hash VARCHAR(64);

-- Добавить индекс на chunk_hash
CREATE INDEX IF NOT EXISTS idx_rag_metadata_chunk_hash ON rag_metadata(chunk_hash);

-- Добавить составной индекс для оптимизации full rebuild
-- (поиск устаревших чанков по cabinet_id + source_table + source_id)
CREATE INDEX IF NOT EXISTS idx_rag_metadata_cabinet_source
ON rag_metadata(cabinet_id, source_table, source_id);

-- Комментарии для документации
COMMENT ON COLUMN rag_metadata.chunk_hash IS 'SHA256 hash от chunk_text для hash-based change detection';
COMMENT ON INDEX idx_rag_metadata_chunk_hash IS 'Индекс для быстрого поиска чанков по hash';
COMMENT ON INDEX idx_rag_metadata_cabinet_source IS 'Составной индекс для оптимизации full rebuild (поиск устаревших чанков)';

-- Вывод статистики
SELECT
    COUNT(*) as total_records,
    COUNT(chunk_hash) as with_hash,
    COUNT(*) - COUNT(chunk_hash) as without_hash
FROM rag_metadata;
