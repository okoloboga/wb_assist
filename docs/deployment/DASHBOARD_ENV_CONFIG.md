# Dashboard Environment Configuration

## Обзор

Документация по настройке переменных окружения для аналитического дашборда.

## Переменные окружения для CORS

Добавьте следующие переменные в файл `.env`:

```bash
# === CORS Configuration для Dashboard ===

# Разрешенные origins (домены, с которых разрешены запросы)
# Development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173

# Production (замените на ваш домен)
# CORS_ORIGINS=https://dashboard.example.com,https://app.example.com

# Разрешить отправку cookies и credentials
CORS_ALLOW_CREDENTIALS=true

# Разрешенные HTTP методы
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS

# Разрешенные заголовки
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-API-SECRET-KEY,X-Requested-With

# Заголовки, доступные клиенту
CORS_EXPOSE_HEADERS=Cache-Control,X-Cache-TTL,X-RateLimit-Limit,X-RateLimit-Remaining

# Время кэширования preflight запросов (в секундах)
CORS_MAX_AGE=600
```

## Переменные окружения для Redis

```bash
# === Redis Configuration ===

# URL подключения к Redis
REDIS_URL=redis://localhost:6379/0

# Для Docker Compose
# REDIS_URL=redis://redis:6379/0

# Для Redis с паролем
# REDIS_URL=redis://:password@localhost:6379/0
```

## Переменные окружения для безопасности

```bash
# === Security Configuration ===

# API Secret Key (используется для аутентификации запросов)
API_SECRET_KEY=your-secret-key-here

# Trusted hosts (домены, которым разрешен доступ)
TRUSTED_HOSTS=*

# Production
# TRUSTED_HOSTS=dashboard.example.com,api.example.com
```

## Полный пример .env для дашборда

```bash
# === Dashboard Configuration ===

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-API-SECRET-KEY,X-Requested-With
CORS_EXPOSE_HEADERS=Cache-Control,X-Cache-TTL,X-RateLimit-Limit,X-RateLimit-Remaining
CORS_MAX_AGE=600

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
API_SECRET_KEY=CnWvwoDwwGKh
TRUSTED_HOSTS=*

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/wb_assist_db

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Logging
LOG_LEVEL=INFO
```

## Настройка для разных окружений

### Development

```bash
# .env.development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
DEBUG=true
LOG_LEVEL=DEBUG
REDIS_URL=redis://localhost:6379/0
```

### Staging

```bash
# .env.staging
CORS_ORIGINS=https://staging-dashboard.example.com
DEBUG=false
LOG_LEVEL=INFO
REDIS_URL=redis://redis-staging:6379/0
TRUSTED_HOSTS=staging-dashboard.example.com,staging-api.example.com
```

### Production

```bash
# .env.production
CORS_ORIGINS=https://dashboard.example.com
DEBUG=false
LOG_LEVEL=WARNING
REDIS_URL=redis://redis-prod:6379/0
TRUSTED_HOSTS=dashboard.example.com,api.example.com
API_SECRET_KEY=<strong-random-key>
```

## Генерация безопасного API ключа

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32

# Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

## Проверка конфигурации

### Проверка CORS

```bash
# Проверка preflight запроса
curl -X OPTIONS http://localhost:8000/api/v1/bot/stocks/all \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-API-SECRET-KEY" \
  -v

# Ожидаемые заголовки в ответе:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS
# Access-Control-Allow-Headers: Content-Type,Authorization,X-API-SECRET-KEY,X-Requested-With
# Access-Control-Expose-Headers: Cache-Control,X-Cache-TTL
# Access-Control-Max-Age: 600
```

### Проверка аутентификации

```bash
# Запрос без API ключа (должен вернуть 403)
curl http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123

# Запрос с API ключом (должен вернуть 200)
curl http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123 \
  -H "X-API-SECRET-KEY: CnWvwoDwwGKh"
```

### Проверка Redis

```bash
# Проверка подключения
redis-cli ping
# Ожидаемый ответ: PONG

# Проверка ключей кэша
redis-cli keys "wb:*"

# Проверка TTL ключа
redis-cli ttl "wb:stocks:all:cabinet:1:limit:15:offset:0"
```

## Docker Compose конфигурация

Добавьте в `docker-compose.yml`:

```yaml
services:
  server:
    environment:
      - CORS_ORIGINS=http://localhost:3000,http://localhost:5173
      - CORS_ALLOW_CREDENTIALS=true
      - REDIS_URL=redis://redis:6379/0
      - API_SECRET_KEY=${API_SECRET_KEY}
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

## Troubleshooting

### CORS ошибки

**Проблема:** `Access to fetch at 'http://localhost:8000/api/v1/bot/stocks/all' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Решение:**
1. Проверьте, что origin добавлен в `CORS_ORIGINS`
2. Убедитесь, что сервер перезапущен после изменения .env
3. Проверьте, что заголовки правильно настроены

### Redis ошибки

**Проблема:** `Failed to connect to Redis`

**Решение:**
1. Проверьте, что Redis запущен: `redis-cli ping`
2. Проверьте URL подключения в `REDIS_URL`
3. Проверьте firewall и сетевые настройки

### Аутентификация

**Проблема:** `403 Forbidden: Invalid or missing API Secret Key`

**Решение:**
1. Проверьте, что заголовок `X-API-SECRET-KEY` передается
2. Убедитесь, что ключ совпадает с `API_SECRET_KEY` в .env
3. Проверьте логи сервера для деталей

## Мониторинг

### Логи аутентификации

Неудачные попытки аутентификации логируются с уровнем WARNING:

```
❌ Неудачная попытка аутентификации: отсутствует API ключ | 
   Путь: /api/v1/bot/stocks/all | IP: 192.168.1.100 | 
   User-Agent: Mozilla/5.0...
```

### Метрики CORS

Отслеживайте количество preflight запросов и ошибок CORS в логах.

## Безопасность

### Рекомендации

1. **Никогда не коммитьте .env файлы в Git**
   ```bash
   # Добавьте в .gitignore
   .env
   .env.*
   !.env.example
   ```

2. **Используйте разные API ключи для разных окружений**

3. **Ограничьте CORS origins в production**
   ```bash
   # НЕ используйте * в production
   CORS_ORIGINS=https://dashboard.example.com
   ```

4. **Регулярно ротируйте API ключи**

5. **Используйте HTTPS в production**

6. **Настройте rate limiting для защиты от DDoS**

## Changelog

### 2025-11-25 - Initial configuration
- Добавлена конфигурация CORS для дашборда
- Добавлены expose headers для кэширования
- Улучшено логирование аутентификации
- Добавлены рекомендации по безопасности
