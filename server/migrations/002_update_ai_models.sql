-- Migration: Update AI models to GPT-5.1 and Claude Sonnet 4.5
-- Date: 2026-02-15
-- Description: Обновление моделей AI на новые версии

-- Обновляем дефолтное значение колонки
ALTER TABLE users 
ALTER COLUMN preferred_ai_model SET DEFAULT 'gpt-5.1';

-- Обновляем существующие записи с gpt-4o-mini на gpt-5.1
UPDATE users 
SET preferred_ai_model = 'gpt-5.1' 
WHERE preferred_ai_model = 'gpt-4o-mini';

-- Обновляем существующие записи с claude-sonnet-3.5 на claude-sonnet-4.5
UPDATE users 
SET preferred_ai_model = 'claude-sonnet-4.5' 
WHERE preferred_ai_model = 'claude-sonnet-3.5';

-- Обновляем комментарий к колонке
COMMENT ON COLUMN users.preferred_ai_model IS 'Предпочитаемая AI модель пользователя (gpt-5.1, claude-sonnet-4.5)';

-- Проверка результата
SELECT 
    preferred_ai_model, 
    COUNT(*) as count 
FROM users 
GROUP BY preferred_ai_model;
