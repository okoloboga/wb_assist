#!/bin/bash
# Скрипт для применения миграции добавления preferred_ai_model

echo "🔄 Применение миграции: добавление preferred_ai_model к таблице users"

# Проверка переменных окружения
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    echo "❌ Ошибка: Переменные POSTGRES_USER и POSTGRES_DB должны быть установлены"
    exit 1
fi

# Применение миграции
docker exec wb_assist-db-1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /migrations/001_add_preferred_ai_model.sql

if [ $? -eq 0 ]; then
    echo "✅ Миграция успешно применена"
else
    echo "❌ Ошибка при применении миграции"
    exit 1
fi

# Проверка результата
echo ""
echo "📊 Проверка структуры таблицы users:"
docker exec wb_assist-db-1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d users"

echo ""
echo "📊 Проверка значений по умолчанию:"
docker exec wb_assist-db-1 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT telegram_id, preferred_ai_model FROM users LIMIT 5;"
