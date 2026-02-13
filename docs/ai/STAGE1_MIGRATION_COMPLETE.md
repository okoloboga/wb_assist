# ✅ Этап 1: Миграция БД - Завершен

Дата: 09.02.2026

## 📋 Выполненные задачи

### 1. Создана SQL миграция
**Файл:** `server/migrations/001_add_preferred_ai_model.sql`

**Изменения:**
- Добавлена колонка `preferred_ai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini'`
- Создан индекс `idx_users_preferred_ai_model` для оптимизации запросов
- Добавлен комментарий к колонке для документации

### 2. Созданы скрипты применения
- **PowerShell:** `server/migrations/apply_migration.ps1` (для Windows)
- **Bash:** `server/migrations/apply_migration.sh` (для Linux/Mac)

### 3. Документация
- **README:** `server/migrations/README.md` с инструкциями по применению и откату

### 4. Создан enum для моделей
**Файл:** `server/app/core/ai_models.py`

**Функционал:**
- Enum с доступными моделями (GPT-4o Mini, Claude Sonnet 3.5)
- Методы для получения метаданных моделей
- Валидация моделей
- Модель по умолчанию: `gpt-4o-mini`

## 📊 Структура миграции

```sql
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferred_ai_model VARCHAR(50) 
NOT NULL DEFAULT 'gpt-4o-mini';

CREATE INDEX IF NOT EXISTS idx_users_preferred_ai_model 
ON users(preferred_ai_model);
```

## 🚀 Как применить миграцию

### Вариант 1: PowerShell (Windows)
```powershell
cd server/migrations
.\apply_migration.ps1
```

### Вариант 2: Прямое выполнение
```bash
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferred_ai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o-mini';

CREATE INDEX IF NOT EXISTS idx_users_preferred_ai_model 
ON users(preferred_ai_model);
"
```

## ✅ Проверка

После применения миграции проверить:

```bash
# Структура таблицы
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "\d users"

# Значения по умолчанию
docker exec wb_assist-db-1 psql -U user -d wb_assist_db -c "
SELECT telegram_id, preferred_ai_model FROM users LIMIT 5;
"
```

## 📁 Созданные файлы

```
server/
├── migrations/
│   ├── 001_add_preferred_ai_model.sql    # SQL миграция
│   ├── apply_migration.ps1               # PowerShell скрипт
│   ├── apply_migration.sh                # Bash скрипт
│   └── README.md                         # Документация
└── app/
    └── core/
        └── ai_models.py                  # Enum моделей
```

## 🎯 Следующие этапы

- [ ] **Этап 2:** Обновить модель User в SQLAlchemy
- [ ] **Этап 3:** Создать API endpoints
- [ ] **Этап 4:** Обновить Telegram бота
- [ ] **Этап 5:** Обновить GPT сервис
- [ ] **Этап 6:** Обновить .env файлы
- [ ] **Этап 7:** Тестирование
- [ ] **Этап 8:** Документация для пользователей

## 📝 Примечания

- Миграция безопасна: использует `IF NOT EXISTS`
- Значение по умолчанию: `gpt-4o-mini`
- Индекс создается автоматически для оптимизации
- Поддерживается откат миграции

**Статус:** ✅ Готово к применению
