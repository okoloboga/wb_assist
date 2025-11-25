# Analytics Dashboard - Quick Start ✅

Быстрый старт для запуска аналитического дашборда WB Assistant с реальными данными.

## Предварительные требования

- Node.js 18+ и npm
- Docker и Docker Compose (для backend)

## Шаг 1: Запуск Backend

```bash
# Из корневой директории проекта
docker-compose up -d

# Проверка статуса
docker-compose ps
```

## Шаг 2: Применение индексов БД (✅ уже выполнено)

Индексы для оптимизации запросов уже применены. Проверить можно так:

```bash
docker-compose exec db psql -U user -d wb_assist_db -c "\di"
```

## Шаг 3: Установка зависимостей Dashboard

```bash
cd dashboard
npm install
```

## Шаг 4: Конфигурация

Отредактируйте файл `.env` в папке `dashboard`:

```env
VITE_API_BASE_URL=http://localhost:8002/api/v1/bot
VITE_API_SECRET_KEY=CnWvwoDwwGKh
VITE_TELEGRAM_ID=ваш_telegram_id  # Замените на реальный ID
```

**Важно**: Замените `VITE_TELEGRAM_ID` на ваш реальный Telegram ID.

## Шаг 5: Запуск Dashboard

```bash
npm run dev
```

Dashboard будет доступен по адресу: http://localhost:5173

## Что вы увидите

### 1. Метрики заказов (реальные данные из API)
- Заказы (общее количество)
- Выкупы (успешные продажи)
- Отмены (отмененные заказы)
- Возвраты (возвращенные товары)

### 2. Графики динамики (реальные данные)
- Интерактивные графики с возможностью включения/выключения метрик
- Данные за выбранный период (30/60/90/180 дней)
- Hover эффекты с детальной информацией

### 3. Таблица остатков (реальные данные)
- Список товаров на складах
- Фильтрация по складу и размеру
- Поиск по номенклатуре
- Цветовая индикация количества

## Технологии

- **React 18** + **TypeScript**
- **React Query** - управление состоянием и кэширование
- **Vite** - build tool
- **Tailwind CSS** - стилизация
- **Recharts** - графики

## Особенности

### Кэширование
- Данные кэшируются на 5-60 минут
- Автоматическое обновление в фоне
- Мгновенный отклик при повторных запросах

### Обработка ошибок
- Автоматический retry до 3 раз
- Понятные сообщения об ошибках
- Skeleton loaders при загрузке

## Troubleshooting

### Dashboard не загружает данные

1. Проверьте backend:
   ```bash
   curl -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     "http://localhost:8002/api/v1/bot/analytics/summary?telegram_id=123456789&period=30d"
   ```

2. Откройте DevTools (F12) → Network tab

### Ошибка 401 Unauthorized

Проверьте, что `VITE_API_SECRET_KEY` совпадает с `API_SECRET_KEY` в корневом .env

## Документация

- [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md) - Полная документация по интеграции
- [API Documentation](../docs/api/ANALYTICS_DASHBOARD_API.md) - Описание API
