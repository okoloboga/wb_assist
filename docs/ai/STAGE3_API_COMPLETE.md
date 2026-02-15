# ✅ Этап 3: API Endpoints - Завершен

Дата: 09.02.2026

## 📋 Выполненные задачи

### Созданы 3 новых API endpoint

**Файл:** `server/app/features/bot_api/routes.py`

#### 1. GET /api/v1/bot/ai-models
Получение списка доступных AI моделей

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-4o-mini",
      "name": "GPT-4o Mini (OpenAI)",
      "provider": "OpenAI",
      "description": "Быстрая и экономичная модель от OpenAI"
    },
    {
      "id": "claude-sonnet-3.5",
      "name": "Claude Sonnet 3.5 (Anthropic)",
      "provider": "Anthropic",
      "description": "Продвинутая модель с глубоким пониманием контекста"
    }
  ],
  "default_model": "gpt-4o-mini"
}
```

#### 2. GET /api/v1/bot/settings
Получение настроек пользователя

**Parameters:**
- `telegram_id` (query, required): Telegram ID пользователя

**Response:**
```json
{
  "telegram_id": 123456789,
  "preferred_ai_model": "gpt-4o-mini",
  "username": "john_doe",
  "first_name": "John"
}
```

**Errors:**
- `404`: Пользователь не найден
- `500`: Ошибка сервера

#### 3. PATCH /api/v1/bot/settings
Обновление настроек пользователя

**Parameters:**
- `telegram_id` (query, required): Telegram ID пользователя

**Request Body:**
```json
{
  "preferred_ai_model": "claude-sonnet-3.5"
}
```

**Response:**
```json
{
  "telegram_id": 123456789,
  "preferred_ai_model": "claude-sonnet-3.5",
  "username": "john_doe",
  "first_name": "John"
}
```

**Errors:**
- `400`: Недопустимая AI модель
- `404`: Пользователь не найден
- `500`: Ошибка сервера

## 🔧 Реализованный функционал

### Валидация моделей
```python
if not AIModel.is_valid(settings.preferred_ai_model):
    raise HTTPException(
        status_code=400,
        detail=f"Недопустимая AI модель. Доступные: {available_models}"
    )
```

### Логирование
```python
logger.info(
    f"Обновлена AI модель для пользователя {telegram_id}: "
    f"{settings.preferred_ai_model}"
)
```

### Обработка ошибок
- Graceful error handling
- Rollback при ошибках
- Детальные сообщения об ошибках

## 📊 Примеры использования

### cURL примеры

#### Получить список моделей
```bash
curl -X GET "http://localhost:8002/api/v1/bot/ai-models" \
  -H "accept: application/json"
```

#### Получить настройки пользователя
```bash
curl -X GET "http://localhost:8002/api/v1/bot/settings?telegram_id=123456789" \
  -H "accept: application/json"
```

#### Обновить модель пользователя
```bash
curl -X PATCH "http://localhost:8002/api/v1/bot/settings?telegram_id=123456789" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"preferred_ai_model": "claude-sonnet-3.5"}'
```

### Python примеры

```python
import requests

BASE_URL = "http://localhost:8002/api/v1/bot"

# Получить список моделей
response = requests.get(f"{BASE_URL}/ai-models")
models = response.json()
print(models)

# Получить настройки
response = requests.get(
    f"{BASE_URL}/settings",
    params={"telegram_id": 123456789}
)
settings = response.json()
print(f"Current model: {settings['preferred_ai_model']}")

# Обновить модель
response = requests.patch(
    f"{BASE_URL}/settings",
    params={"telegram_id": 123456789},
    json={"preferred_ai_model": "claude-sonnet-3.5"}
)
updated_settings = response.json()
print(f"Updated model: {updated_settings['preferred_ai_model']}")
```

### JavaScript/TypeScript примеры

```typescript
const BASE_URL = 'http://localhost:8002/api/v1/bot';

// Получить список моделей
const getModels = async () => {
  const response = await fetch(`${BASE_URL}/ai-models`);
  const data = await response.json();
  return data;
};

// Получить настройки
const getSettings = async (telegramId: number) => {
  const response = await fetch(
    `${BASE_URL}/settings?telegram_id=${telegramId}`
  );
  const data = await response.json();
  return data;
};

// Обновить модель
const updateModel = async (telegramId: number, model: string) => {
  const response = await fetch(
    `${BASE_URL}/settings?telegram_id=${telegramId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        preferred_ai_model: model
      })
    }
  );
  const data = await response.json();
  return data;
};
```

## 🧪 Тестирование

### Ручное тестирование

1. **Запустить сервер:**
```bash
cd server
uvicorn main:app --reload --port 8002
```

2. **Открыть Swagger UI:**
```
http://localhost:8002/docs
```

3. **Протестировать endpoints:**
- GET /api/v1/bot/ai-models
- GET /api/v1/bot/settings
- PATCH /api/v1/bot/settings

### Автоматические тесты

Создать файл `server/tests/unit/test_ai_settings_api.py`:

```python
import pytest
from fastapi.testclient import TestClient

def test_get_ai_models(client):
    """Тест получения списка моделей"""
    response = client.get("/api/v1/bot/ai-models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "default_model" in data
    assert len(data["models"]) == 2

def test_get_user_settings(client, test_user):
    """Тест получения настроек пользователя"""
    response = client.get(
        f"/api/v1/bot/settings?telegram_id={test_user.telegram_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == test_user.telegram_id
    assert "preferred_ai_model" in data

def test_update_user_settings(client, test_user):
    """Тест обновления настроек"""
    response = client.patch(
        f"/api/v1/bot/settings?telegram_id={test_user.telegram_id}",
        json={"preferred_ai_model": "claude-sonnet-3.5"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_ai_model"] == "claude-sonnet-3.5"

def test_invalid_model(client, test_user):
    """Тест с невалидной моделью"""
    response = client.patch(
        f"/api/v1/bot/settings?telegram_id={test_user.telegram_id}",
        json={"preferred_ai_model": "invalid-model"}
    )
    assert response.status_code == 400
```

## 📁 Измененные файлы

```
server/app/features/bot_api/
└── routes.py                    # ✅ Добавлены 3 новых endpoint
```

## 🎯 Следующие этапы

- [x] **Этап 1:** Миграция БД ✅
- [x] **Этап 2:** Обновление моделей ✅
- [x] **Этап 3:** Создать API endpoints ✅
- [ ] **Этап 4:** Обновить Telegram бота
- [ ] **Этап 5:** Обновить GPT сервис
- [ ] **Этап 6:** Обновить .env файлы
- [ ] **Этап 7:** Тестирование
- [ ] **Этап 8:** Документация для пользователей

## 📝 Примечания

- Все endpoints используют Pydantic схемы для валидации
- Реализована полная обработка ошибок
- Добавлено логирование всех операций
- API готов к интеграции с Telegram ботом
- Swagger документация доступна автоматически

**Статус:** ✅ Готово к следующему этапу
