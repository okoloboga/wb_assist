# Запуск Dashboard через Docker

## Быстрый старт

### 1. Настройка переменных окружения

Отредактируйте `.env` в корне проекта и добавьте/обновите:

```env
# Dashboard Configuration
DASHBOARD_TELEGRAM_ID=ваш_telegram_id
```

### 2. Сборка и запуск

```bash
# Сборка и запуск dashboard
docker-compose up -d --build dashboard

# Или запуск всех сервисов включая dashboard
docker-compose up -d --build
```

### 3. Проверка

Dashboard будет доступен по адресу: **http://localhost:3000**

## Проверка статуса

```bash
# Проверить статус контейнеров
docker-compose ps

# Посмотреть логи dashboard
docker-compose logs -f dashboard

# Проверить health
curl http://localhost:3000/health
```

## Остановка

```bash
# Остановить dashboard
docker-compose stop dashboard

# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v
```

## Пересборка

Если изменили код или конфигурацию:

```bash
# Пересобрать dashboard
docker-compose up -d --build dashboard

# Пересобрать без кэша
docker-compose build --no-cache dashboard
docker-compose up -d dashboard
```

## Troubleshooting

### Dashboard не запускается

1. Проверьте логи:
```bash
docker-compose logs dashboard
```

2. Проверьте, что server запущен:
```bash
docker-compose ps server
curl http://localhost:8002/system/health
```

### Ошибка сборки

1. Очистите Docker кэш:
```bash
docker system prune -a
```

2. Пересоберите:
```bash
docker-compose build --no-cache dashboard
```

### Не загружаются данные

1. Проверьте переменные окружения:
```bash
docker-compose exec dashboard env | grep VITE
```

2. Проверьте подключение к backend:
```bash
docker-compose exec dashboard wget -O- http://server:8000/system/health
```

3. Проверьте CORS:
```bash
curl -H "Origin: http://localhost:3000" \
     -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     http://localhost:8002/api/v1/bot/analytics/summary?telegram_id=123&period=30d
```

## Архитектура

```
┌─────────────┐
│  Browser    │
│ :3000       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Dashboard  │
│  (nginx)    │
│  :80        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Server    │
│  (FastAPI)  │
│  :8000      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │
│  :5432      │
└─────────────┘
```

## Production

Для production используйте:
- Vercel для dashboard (см. VERCEL_DEPLOY.md)
- Railway/Render для backend
- Managed PostgreSQL

Docker подходит для:
- Локальной разработки
- Тестирования
- Self-hosted deployment на VPS

## Полезные команды

```bash
# Перезапустить dashboard
docker-compose restart dashboard

# Войти в контейнер
docker-compose exec dashboard sh

# Посмотреть использование ресурсов
docker stats wb_assist-dashboard-1

# Экспортировать логи
docker-compose logs dashboard > dashboard.log
```
