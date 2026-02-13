# Database Migrations

## Миграция 001: Добавление preferred_ai_model

### Описание
Добавляет поле `preferred_ai_model` в таблицу `users` для хранения предпочитаемой AI модели пользователя.

### Изменения
- Добавлена колонка `preferred_ai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini'`
- Создан индекс `idx_users_preferred_ai_model`
- Добавлен комментарий к колонке

### Применение миграции

#### Windows (PowerShell)
```powershell
cd server/migrations
.\apply_migration.ps1
```

#### Linux/Mac (Bash)
```bash
cd server/migrations
chmod +x apply_migration.sh
./apply_migration.sh
```

#### Вручную через Docker
```bash
# Скопировать SQL файл в контейнер
docker cp server/migrations/001_add_preferred_ai_model.sql wb_assist-db-1:/tmp/

# Применить миграцию
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -f /tmp/001_add_preferred_ai_model.sql
```

#### Прямое выполнение SQL
```bash
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferred_ai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini';

CREATE INDEX IF NOT EXISTS idx_users_preferred_ai_model 
ON users(preferred_ai_model);
"
```

### Проверка результата

```bash
# Проверить структуру таблицы
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "\d users"

# Проверить значения
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
SELECT telegram_id, preferred_ai_model 
FROM users 
LIMIT 5;
"

# Проверить индекс
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' AND indexname = 'idx_users_preferred_ai_model';
"
```

### Откат миграции

Если нужно откатить изменения:

```sql
-- Удалить индекс
DROP INDEX IF EXISTS idx_users_preferred_ai_model;

-- Удалить колонку
ALTER TABLE users DROP COLUMN IF EXISTS preferred_ai_model;
```

Или через Docker:

```bash
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
DROP INDEX IF EXISTS idx_users_preferred_ai_model;
ALTER TABLE users DROP COLUMN IF EXISTS preferred_ai_model;
"
```

### Статус
- ✅ SQL миграция создана
- ⏳ Ожидает применения
- ⏳ Требуется обновление моделей SQLAlchemy

### Следующие шаги
1. Применить миграцию
2. Обновить модель User в SQLAlchemy
3. Создать API endpoints для управления настройками
4. Обновить Telegram бота
