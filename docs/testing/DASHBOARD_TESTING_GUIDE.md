# Dashboard Testing Guide

## Обзор

Руководство по тестированию API эндпоинтов аналитического дашборда.

## Типы тестов

### 1. Unit тесты
### 2. Integration тесты
### 3. Load тесты (нагрузочное тестирование)

---

## Unit тесты

**Файл:** `server/tests/unit/test_bot_api_validators.py`

**Что тестируется:**
- Валидация входных параметров
- Защита от SQL injection
- Защита от XSS
- Граничные значения
- Форматы данных

### Запуск unit тестов

```bash
# Установка зависимостей
pip install pytest pytest-cov

# Запуск всех unit тестов
pytest server/tests/unit/ -v

# Запуск с покрытием кода
pytest server/tests/unit/ --cov=app.features.bot_api.validators --cov-report=html

# Запуск конкретного теста
pytest server/tests/unit/test_bot_api_validators.py::TestStocksQueryParams::test_valid_params -v
```

### Ожидаемые результаты

```
test_bot_api_validators.py::TestStocksQueryParams::test_valid_params PASSED
test_bot_api_validators.py::TestStocksQueryParams::test_default_values PASSED
test_bot_api_validators.py::TestStocksQueryParams::test_invalid_telegram_id PASSED
...
======================== 50 passed in 2.34s ========================
```

**Целевое покрытие:** минимум 80%

---

## Integration тесты

**Файл:** `server/tests/integration/test_dashboard_endpoints.py`

**Что тестируется:**
- Эндпоинты с реальной БД
- Аутентификация
- CORS
- Кэширование
- Формат ответов
- Производительность

### Подготовка

```bash
# Создать тестовую БД
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/test_db"

# Или использовать SQLite для быстрых тестов
export TEST_DATABASE_URL="sqlite:///./test.db"

# Установить зависимости
pip install pytest pytest-asyncio httpx
```

### Запуск integration тестов

```bash
# Запуск всех integration тестов
pytest server/tests/integration/ -v

# Запуск с подробным выводом
pytest server/tests/integration/ -v -s

# Запуск конкретного класса тестов
pytest server/tests/integration/test_dashboard_endpoints.py::TestAuthentication -v

# Запуск с маркерами
pytest server/tests/integration/ -m "not slow" -v
```

### Ожидаемые результаты

```
test_dashboard_endpoints.py::TestAuthentication::test_missing_api_key PASSED
test_dashboard_endpoints.py::TestAuthentication::test_invalid_api_key PASSED
test_dashboard_endpoints.py::TestWarehousesEndpoint::test_get_warehouses_success PASSED
...
======================== 35 passed in 15.67s ========================
```

---

## Нагрузочное тестирование (Load Testing)

**Файл:** `server/tests/load/locustfile.py`

**Инструмент:** Locust

**Что тестируется:**
- Производительность под нагрузкой
- Время ответа
- Пропускная способность
- Эффективность кэширования
- Поведение при высокой нагрузке

### Установка Locust

```bash
pip install locust
```

### Запуск нагрузочных тестов

#### Вариант 1: Веб-интерфейс

```bash
# Запуск с веб-интерфейсом
cd server/tests/load
locust -f locustfile.py --host=http://localhost:8000

# Открыть браузер
# http://localhost:8089

# Настроить:
# - Number of users: 100
# - Spawn rate: 10 users/second
# - Host: http://localhost:8000
```

#### Вариант 2: Headless режим

```bash
# Легкая нагрузка (10 пользователей)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 10 --spawn-rate 2 --run-time 5m --headless

# Средняя нагрузка (50 пользователей)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 5 --run-time 10m --headless

# Тяжелая нагрузка (100 пользователей)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 15m --headless

# Экстремальная нагрузка (200 пользователей)
locust -f locustfile.py --host=http://localhost:8000 \
  --users 200 --spawn-rate 20 --run-time 20m --headless
```

#### Вариант 3: Тестирование кэша

```bash
# Запуск только CacheTestUser
locust -f locustfile.py --host=http://localhost:8000 \
  --users 50 --spawn-rate 10 --run-time 5m \
  --headless --class-picker CacheTestUser
```

### Интерпретация результатов

**Целевые метрики:**

| Метрика | Целевое значение | Критическое значение |
|---------|------------------|---------------------|
| Response Time (median) | < 100ms | < 500ms |
| Response Time (95th percentile) | < 300ms | < 1000ms |
| Requests per second | > 100 | > 50 |
| Failure rate | < 1% | < 5% |
| Cache hit rate | > 70% | > 50% |

**Пример хорошего результата:**

```
Name                              # reqs      # fails  |     Avg     Min     Max  Median  |   req/s failures/s
----------------------------------|------------|---------|-------|-------|-------|-------|--------|-----------
GET /warehouses                   1234        0        |      45      12     234      38  |   41.1       0.00
GET /sizes                        1156        0        |      42      11     198      36  |   38.5       0.00
GET /analytics/summary            2345        0        |      89      23     456      76  |   78.2       0.00
GET /stocks/all                   1876        0        |     156      45     789     134  |   62.5       0.00
----------------------------------|------------|---------|-------|-------|-------|-------|--------|-----------
Aggregated                        6611        0        |      83      11     789      67  |  220.3       0.00

Response time percentiles (approximated)
Type     Name                              50%    66%    75%    80%    90%    95%    98%    99%  99.9% 99.99%   100%
--------|--------------------------------|--------|------|------|------|------|------|------|------|------|------|------|
GET      /warehouses                        38     45     52     58     78     98    145    189    230    234    234
GET      /analytics/summary                 76     89    102    112    145    189    267    345    450    456    456
```

**Признаки проблем:**

1. **Высокое время ответа (> 1s):**
   - Проверить индексы БД
   - Проверить кэширование
   - Оптимизировать SQL запросы

2. **Высокий процент ошибок (> 5%):**
   - Проверить логи сервера
   - Проверить подключение к БД
   - Проверить лимиты соединений

3. **Низкий RPS (< 50):**
   - Увеличить workers
   - Оптимизировать код
   - Масштабировать сервер

---

## Тестирование кэширования

### Проверка Redis

```bash
# Проверка подключения
redis-cli ping
# Ожидаемый ответ: PONG

# Мониторинг команд в реальном времени
redis-cli monitor

# Проверка ключей
redis-cli keys "wb:*"

# Проверка TTL ключа
redis-cli ttl "wb:warehouses:list:cabinet:1"

# Статистика
redis-cli INFO stats
```

### Тест cache hit rate

```bash
# 1. Очистить кэш
redis-cli FLUSHDB

# 2. Первый запрос (cache MISS)
time curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"
# Ожидаемое время: ~100-200ms

# 3. Второй запрос (cache HIT)
time curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"
# Ожидаемое время: ~20-50ms

# 4. Проверить логи
# Должно быть: "Warehouses cache HIT for cabinet 1"
```

### Тест инвалидации кэша

```bash
# 1. Запрос данных
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"

# 2. Запуск синхронизации (инвалидирует кэш)
curl -X POST "http://localhost:8000/api/v1/bot/sync/start?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"

# 3. Повторный запрос (должен быть cache MISS)
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"

# Проверить логи: "Cache invalidated for cabinet 1"
```

---

## Тестирование безопасности

### SQL Injection

```bash
# Попытка SQL injection (должна быть заблокирована)
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123&search='; DROP TABLE users--" \
  -H "X-API-SECRET-KEY: your-key"

# Ожидаемый ответ: 422 Validation Error
```

### XSS

```bash
# Попытка XSS (должна быть заблокирована)
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123&warehouse=<script>alert('xss')</script>" \
  -H "X-API-SECRET-KEY: your-key"

# Ожидаемый ответ: 422 Validation Error
```

### Аутентификация

```bash
# Без API ключа (должна быть ошибка 403)
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123"

# С неверным API ключом (должна быть ошибка 403)
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: wrong-key"

# С правильным API ключом (должен быть успех)
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123" \
  -H "X-API-SECRET-KEY: your-key"
```

---

## Автоматизация тестирования

### GitHub Actions (CI/CD)

Создайте файл `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run unit tests
        run: pytest server/tests/unit/ -v --cov
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
        run: pytest server/tests/integration/ -v
```

### Pre-commit hooks

Создайте файл `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest unit tests
        entry: pytest server/tests/unit/ -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## Мониторинг в production

### Метрики для отслеживания

1. **Response Time:**
   - P50, P95, P99
   - По эндпоинтам

2. **Error Rate:**
   - 4xx ошибки
   - 5xx ошибки

3. **Cache Hit Rate:**
   - Общий
   - По типам кэша

4. **Database:**
   - Количество запросов
   - Медленные запросы (> 100ms)

5. **Redis:**
   - Использование памяти
   - Количество ключей
   - Evictions

### Инструменты

- **Prometheus + Grafana** - метрики и дашборды
- **Sentry** - отслеживание ошибок
- **ELK Stack** - логирование
- **New Relic / DataDog** - APM

---

## Troubleshooting

### Тесты падают

**Проблема:** `Connection refused`

**Решение:**
```bash
# Проверить, что сервер запущен
curl http://localhost:8000/system/health

# Проверить порт
netstat -an | grep 8000
```

**Проблема:** `Database connection error`

**Решение:**
```bash
# Проверить подключение к БД
psql -h localhost -U user -d wb_assist_db

# Проверить переменные окружения
echo $DATABASE_URL
```

### Низкая производительность

**Проблема:** Время ответа > 1s

**Решение:**
1. Проверить индексы БД
2. Проверить кэширование
3. Проверить логи медленных запросов
4. Оптимизировать SQL

### Высокий процент ошибок

**Проблема:** Failure rate > 5%

**Решение:**
1. Проверить логи сервера
2. Проверить лимиты соединений
3. Проверить ресурсы сервера (CPU, RAM)
4. Масштабировать сервер

---

## Чеклист перед production

- [ ] Все unit тесты проходят
- [ ] Все integration тесты проходят
- [ ] Нагрузочное тестирование пройдено (100+ пользователей)
- [ ] Cache hit rate > 70%
- [ ] Response time P95 < 500ms
- [ ] Failure rate < 1%
- [ ] Индексы БД применены
- [ ] Мониторинг настроен
- [ ] Алерты настроены

---

## Дополнительные ресурсы

- [Pytest Documentation](https://docs.pytest.org/)
- [Locust Documentation](https://docs.locust.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Redis Testing](https://redis.io/docs/manual/testing/)
