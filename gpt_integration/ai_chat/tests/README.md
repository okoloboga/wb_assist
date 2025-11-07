# AI Chat Service - Test Suite

Полный набор тестов для AI Chat Service.

## 📋 Содержание

### Unit Tests (`test_crud.py`)
- ✅ Проверка лимитов и обновление счетчика
- ✅ Получение текущих лимитов без изменения счетчика
- ✅ Сохранение запросов в историю
- ✅ Получение истории с пагинацией
- ✅ Получение контекста для AI
- ✅ Сброс лимитов (admin функция)
- ✅ Статистика пользователя

### Integration Tests (`test_api.py`)
- ✅ Health check эндпоинт
- ✅ POST /v1/chat/send (отправка сообщений)
- ✅ POST /v1/chat/history (получение истории)
- ✅ GET /v1/chat/limits/{telegram_id} (проверка лимитов)
- ✅ POST /v1/chat/reset-limit (сброс лимита)
- ✅ GET /v1/chat/stats/{telegram_id} (статистика)
- ✅ Проверка аутентификации (API ключ)
- ✅ Валидация запросов

### Rate Limiting Tests (`test_rate_limits.py`)
- ✅ Отслеживание лимитов (30 запросов/день)
- ✅ Превышение лимита (429 ошибка)
- ✅ Автоматический сброс в новый день
- ✅ Лимиты per-user
- ✅ Admin сброс лимита
- ✅ Контекст из предыдущих сообщений

## 🚀 Запуск тестов

### Установка зависимостей

```bash
# Установить тестовые зависимости
pip install -r ai_chat/requirements-dev.txt
```

### Запуск всех тестов

```bash
# Из корня проекта
pytest ai_chat/tests/ -v

# Или через скрипт
python -m ai_chat.tests.run_tests
```

### Запуск конкретных тестов

```bash
# Только unit тесты
pytest ai_chat/tests/test_crud.py -v

# Только integration тесты
pytest ai_chat/tests/test_api.py -v

# Только rate limiting тесты
pytest ai_chat/tests/test_rate_limits.py -v
```

### Запуск с coverage

```bash
# Генерация отчета о покрытии
pytest ai_chat/tests/ --cov=ai_chat --cov-report=html

# Открыть HTML отчет
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

### Ручное тестирование

```bash
# 1. Запустить сервис
python -m ai_chat.service

# 2. В другом терминале запустить ручные тесты
python ai_chat/tests/manual_test.py
```

## 🔧 Конфигурация

### Переменные окружения для тестов

```bash
# .env или environment
API_SECRET_KEY=test-api-key
OPENAI_API_KEY=test-openai-key  # Для integration тестов с реальным OpenAI
```

### pytest.ini

Конфигурация pytest находится в `ai_chat/pytest.ini`:
- Автоматическое добавление coverage
- Настройка asyncio mode
- Фильтрация warnings

## 📊 Test Coverage

Цель: **>90% покрытия кода**

### Текущее покрытие по модулям:

- `crud.py`: ~95% (все методы)
- `service.py`: ~90% (все эндпоинты)
- `models.py`: 100%
- `schemas.py`: 100%
- `database.py`: ~85%

### Не покрытые области:

- Error handling в редких edge cases
- Некоторые logging statements
- `if __name__ == "__main__"` блоки

## 🧪 Примеры тестов

### Unit Test Example

```python
def test_check_and_update_limit(test_db_session, sample_telegram_id):
    """Test rate limit checking and updating."""
    crud = AIChatCRUD(test_db_session)
    
    can_request, remaining = crud.check_and_update_limit(sample_telegram_id)
    
    assert can_request is True
    assert remaining == DAILY_LIMIT - 1
```

### Integration Test Example

```python
@patch("ai_chat.service._call_openai")
def test_send_message_success(mock_openai, client, headers):
    """Test sending message to AI."""
    mock_openai.return_value = ("Test response", 100)
    
    payload = {
        "telegram_id": 123456789,
        "message": "Test question"
    }
    
    response = client.post("/v1/chat/send", json=payload, headers=headers)
    
    assert response.status_code == 200
    assert "response" in response.json()
```

## 🐛 Debugging Tests

### Запуск с дополнительным выводом

```bash
# Максимальная детализация
pytest ai_chat/tests/ -vv -s

# Показать print statements
pytest ai_chat/tests/ -s

# Остановиться на первой ошибке
pytest ai_chat/tests/ -x

# Запустить только failed тесты
pytest ai_chat/tests/ --lf
```

### Запуск конкретного теста

```bash
# По имени класса
pytest ai_chat/tests/test_crud.py::TestCheckAndUpdateLimit -v

# По имени метода
pytest ai_chat/tests/test_crud.py::TestCheckAndUpdateLimit::test_new_user_creates_record -v
```

## 📝 Написание новых тестов

### Структура теста

```python
class TestFeatureName:
    """Tests for feature description."""
    
    def test_specific_behavior(self, test_db_session, fixture_name):
        """Test specific behavior description."""
        # Arrange
        # ... setup
        
        # Act
        # ... execute
        
        # Assert
        assert result == expected
```

### Использование fixtures

Доступные fixtures из `conftest.py`:
- `test_db_engine` - тестовая БД (in-memory SQLite)
- `test_db_session` - сессия БД
- `client` - FastAPI test client
- `sample_telegram_id` - тестовый telegram ID
- `sample_chat_request` - тестовый запрос в БД
- `sample_daily_limit` - тестовый лимит в БД
- `create_chat_history` - фабрика для создания истории
- `headers` - заголовки с API ключом

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run tests
  run: |
    pip install -r ai_chat/requirements-dev.txt
    pytest ai_chat/tests/ --cov=ai_chat --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## 📚 Дополнительная информация

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html)

## ✅ Checklist перед коммитом

- [ ] Все тесты проходят: `pytest ai_chat/tests/ -v`
- [ ] Coverage > 90%: `pytest ai_chat/tests/ --cov=ai_chat`
- [ ] Нет linter ошибок: `flake8 ai_chat/`
- [ ] Код отформатирован: `black ai_chat/`
- [ ] Imports отсортированы: `isort ai_chat/`

