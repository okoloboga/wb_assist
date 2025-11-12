# Smoke Test для GPT Integration Service

Скрипты для быстрой проверки всех критичных эндпоинтов после слияния AI Chat модуля.

## Использование

### Windows (PowerShell)

```powershell
# Установите API ключ
$env:API_SECRET_KEY = "CnWvwoDwwGKh"

# Запустите тест (по умолчанию http://localhost:9000)
.\gpt_integration\smoke_test.ps1

# Или укажите другой URL
.\gpt_integration\smoke_test.ps1 -BaseUrl "http://localhost:9000" -ApiKey "your-key"
```

### Linux/Mac (Bash)

```bash
# Установите API ключ
export API_SECRET_KEY="CnWvwoDwwGKh"

# Запустите тест
chmod +x gpt_integration/smoke_test.sh
./gpt_integration/smoke_test.sh

# Или укажите другой URL
./gpt_integration/smoke_test.sh http://localhost:9000
```

## Что проверяется

### 📋 General Endpoints
- ✅ Health Check (`GET /health`)

### 💬 AI Chat Endpoints
- ✅ Get Chat Limits (`GET /v1/chat/limits/{telegram_id}`)
- ✅ Send Chat Message (`POST /v1/chat/send`)
- ✅ Get Chat History (`POST /v1/chat/history`)
- ✅ Get Chat Stats (`GET /v1/chat/stats/{telegram_id}`)

### 📊 Analysis Endpoints
- ✅ Start Analysis (`POST /v1/analysis/start`)

## Требования

### Перед запуском

1. **Сервис запущен**: GPT Integration Service должен быть запущен на указанном URL
2. **База данных**: PostgreSQL должна быть доступна и настроена
3. **API ключ**: Установите переменную окружения `API_SECRET_KEY`
4. **OpenAI ключ**: Установите `OPENAI_API_KEY` для работы AI Chat

### Локальный запуск сервиса

```bash
# 1. Запустите PostgreSQL
docker-compose up -d db

# 2. Установите переменные окружения
export DATABASE_URL="postgresql://user:password@localhost:5432/wb_assist_db"
export OPENAI_API_KEY="your-openai-key"
export API_SECRET_KEY="your-secret-key"

# 3. Запустите сервис
python -m gpt_integration.service
```

### Docker Compose

```bash
# Запустите все сервисы
docker-compose up -d --build

# Проверьте логи
docker-compose logs -f gpt

# Запустите smoke test
$env:API_SECRET_KEY = "CnWvwoDwwGKh"
.\gpt_integration\smoke_test.ps1
```

## Интерпретация результатов

### ✅ Успешный тест
```
Testing: Health Check ✅ PASSED
Testing: Get Chat Limits ✅ PASSED
Testing: Send Chat Message ✅ PASSED
...
📊 Test Summary
Passed: 6
Failed: 0
Total:  6

✅ All tests passed!
```

### ❌ Провальный тест
```
Testing: Health Check ✅ PASSED
Testing: Get Chat Limits ❌ FAILED
  Error: 403 Forbidden
...
📊 Test Summary
Passed: 1
Failed: 5
Total:  6

❌ Some tests failed. Please check the logs.
```

## Troubleshooting

### Ошибка: "Invalid or missing API key"
**Решение:** Проверьте, что `API_SECRET_KEY` установлен и совпадает с конфигурацией сервиса.

### Ошибка: "Connection refused"
**Решение:** Убедитесь, что сервис запущен на указанном URL.

### Ошибка: "OpenAI API key not configured"
**Решение:** Установите переменную окружения `OPENAI_API_KEY` для сервиса.

### Ошибка: "Database connection failed"
**Решение:** Проверьте, что PostgreSQL запущен и `DATABASE_URL` настроен корректно.

## CI/CD Integration

Скрипты можно использовать в CI/CD пайплайнах:

```yaml
# GitHub Actions example
- name: Run Smoke Tests
  env:
    API_SECRET_KEY: ${{ secrets.API_SECRET_KEY }}
  run: |
    ./gpt_integration/smoke_test.sh http://localhost:9000
```

```yaml
# GitLab CI example
smoke_test:
  script:
    - export API_SECRET_KEY=$API_SECRET_KEY
    - ./gpt_integration/smoke_test.sh http://gpt:9000
```
