# WB Assistant Analytics Dashboard

Аналитический дашборд для мониторинга продаж и остатков на Wildberries.

## Деплой на Vercel

### Быстрый деплой

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-repo/wb_assist&project-name=wb-analytics-dashboard&root-directory=dashboard)

### Ручной деплой

1. Установите Vercel CLI:
```bash
npm install -g vercel
```

2. Войдите в аккаунт:
```bash
vercel login
```

3. Деплой из папки dashboard:
```bash
cd dashboard
vercel
```

4. Настройте environment variables в Vercel Dashboard:
   - `VITE_API_BASE_URL` - URL вашего backend API
   - `VITE_API_SECRET_KEY` - секретный ключ API
   - `VITE_TELEGRAM_ID` - ваш Telegram ID

### Environment Variables

Создайте в Vercel Dashboard следующие переменные:

```
VITE_API_BASE_URL=https://your-backend-url.com/api/v1/bot
VITE_API_SECRET_KEY=your_secret_key
VITE_TELEGRAM_ID=your_telegram_id
```

**Важно**: Backend должен быть доступен публично и иметь настроенный CORS для домена Vercel.

## Локальная разработка

```bash
# Установка зависимостей
npm install

# Запуск dev сервера
npm run dev

# Production build
npm run build

# Предпросмотр production build
npm run preview
```

## Технологии

- React 18 + TypeScript
- Vite
- React Query
- Tailwind CSS
- Recharts
- Lucide React

## Документация

- [Quick Start](./QUICK_START.md)
- [Integration Guide](./INTEGRATION_COMPLETE.md)
- [API Documentation](../docs/api/ANALYTICS_DASHBOARD_API.md)

## Поддержка

При возникновении проблем создайте issue в репозитории.
