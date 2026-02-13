-- Migration: Add preferred_ai_model to users table
-- Date: 2026-02-09
-- Description: Добавление поля для выбора AI модели пользователем

-- Добавляем колонку preferred_ai_model
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferred_ai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini';

-- Создаем индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_users_preferred_ai_model 
ON users(preferred_ai_model);

-- Комментарий к колонке
COMMENT ON COLUMN users.preferred_ai_model IS 'Предпочитаемая AI модель пользователя (gpt-4o-mini, claude-sonnet-3.5)';

-- Проверка результата
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'preferred_ai_model';
