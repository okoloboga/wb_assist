# Production Setup: Dashboard на Vercel + Backend

## Обзор

Этот гайд описывает полный процесс деплоя dashboard на Vercel с подключением к production backend.

---

## Часть 1: Подготовка Backend

### Вариант A: Backend на облачном сервисе (рекомендуется)

#### Railway.app (самый простой)

1. Зарегистрируйтесь на [railway.app](https://railway.app)
2. Создайте новый проект
3. Добавьте PostgreSQL database
4. Добавьте Redis
5. Деплойте backend из GitHub:
   - Выберите репозиторий
   - Root directory: `server`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

6. Настройте environment variables (скопируйте из `.env`)

7. Получите public URL (например, `https://your-app.railway.app`)

#### Render.com

1. Зарегистрируйтесь на [render.com](https://render.com)
2. Создайте PostgreSQL database
3. Создайте Redis instance
4. Создайте Web Service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Root Directory: `server`

5. Настройте environment variables

### Вариант B: Backend на VPS (DigitalOcean, AWS, etc.)

1. Настройте Docker на сервере
2. Клонируйте репозиторий
3. Настройте nginx как reverse proxy
4. Получите SSL сертификат (Let's Encrypt)
5. Запустите через docker-compose

### Настройка CORS для Vercel

После получения URL от Vercel (например, `https://wb-analytics.vercel.app`), обновите CORS в backend:

#### Через environment variable:

```bash
CORS_ORIGINS=https://wb-analytics.vercel.app,http://localhost:5173
```

#### Или в docker-compose.yml:

```yaml
environment:
  - CORS_ORIGINS=https://wb-analytics.vercel.app,http://localhost:5173
```

---

## Часть 2: Деплой Dashboard на Vercel

### Шаг 1: Подготовка кода

1. Убедитесь, что все изменения закоммичены:
```bash
git add .
git commit -m "Prepare dashboard for production"
git push
```

### Шаг 2: Создание проекта в Vercel

#### Через Web UI:

1. Перейдите на [vercel.com](https://vercel.com)
2. Нажмите "Add New" → "Project"
3. Импортируйте ваш Git репозиторий
4. Настройте проект:
   - **Project Name**: `wb-analytics-dashboard`
   - **Framework Preset**: Vite
   - **Root Directory**: `dashboard`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### Шаг 3: Настройка Environment Variables

В разделе "Environment Variables" добавьте:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_BASE_URL` | `https://your-backend.railway.app/api/v1/bot` | Production |
| `VITE_API_SECRET_KEY` | `CnWvwoDwwGKh` | Production |
| `VITE_TELEGRAM_ID` | `1621927129` | Production |

**Важно**: 
- Используйте реальный URL вашего backend
- Не используйте localhost или ngrok в production
- Храните API ключ в секрете

### Шаг 4: Deploy

1. Нажмите "Deploy"
2. Дождитесь завершения сборки (2-3 минуты)
3. Получите URL проекта (например, `https://wb-analytics.vercel.app`)

### Шаг 5: Обновление CORS на Backend

Добавьте полученный URL Vercel в CORS origins на backend:

```bash
# На Railway/Render
CORS_ORIGINS=https://wb-analytics.vercel.app,http://localhost:5173

# Или в docker-compose.yml
environment:
  - CORS_ORIGINS=https://wb-analytics.vercel.app,http://localhost:5173
```

Перезапустите backend после изменения.

---

## Часть 3: Проверка и тестирование

### 1. Проверка доступности

Откройте `https://wb-analytics.vercel.app` в браузере.

### 2. Проверка API подключения

Откройте DevTools (F12) → Network tab:
- ✅ Запросы идут на правильный backend URL
- ✅ Статус ответов 200 OK
- ✅ Нет ошибок CORS
- ✅ Данные загружаются

### 3. Проверка функциональности

- ✅ Метрики отображаются
- ✅ Графики работают
- ✅ Таблица остатков загружается
- ✅ Фильтры работают
- ✅ Переключение периодов работает

### 4. Проверка производительности

Используйте Lighthouse в Chrome DevTools:
- Performance: > 90
- Accessibility: > 90
- Best Practices: > 90
- SEO: > 80

---

## Часть 4: Настройка Custom Domain (опционально)

### Добавление домена в Vercel

1. В Vercel Dashboard → Settings → Domains
2. Нажмите "Add Domain"
3. Введите ваш домен (например, `analytics.yourdomain.com`)
4. Следуйте инструкциям для настройки DNS

### Настройка DNS

Добавьте CNAME запись:
```
Type: CNAME
Name: analytics
Value: cname.vercel-dns.com
```

### Обновление CORS

После настройки custom domain обновите CORS:
```bash
CORS_ORIGINS=https://analytics.yourdomain.com,https://wb-analytics.vercel.app,http://localhost:5173
```

---

## Часть 5: Мониторинг и обслуживание

### Vercel Analytics

1. Включите Vercel Analytics в настройках проекта
2. Мониторьте:
   - Page views
   - Unique visitors
   - Performance metrics
   - Error rates

### Sentry для отслеживания ошибок

1. Создайте проект на [sentry.io](https://sentry.io)
2. Установите SDK:
```bash
npm install @sentry/react
```

3. Настройте в `main.tsx`:
```typescript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: "production",
});
```

### Логирование

Backend логи доступны в:
- Railway: Dashboard → Logs
- Render: Dashboard → Logs
- VPS: `docker-compose logs -f server`

---

## Часть 6: Автоматизация

### Автоматический деплой

Vercel автоматически деплоит при:
- Push в `main` → Production
- Pull Request → Preview deployment

### CI/CD Pipeline

Создайте `.github/workflows/deploy.yml`:

```yaml
name: Deploy Dashboard

on:
  push:
    branches: [main]
    paths:
      - 'dashboard/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd dashboard && npm ci
      - name: Run tests
        run: cd dashboard && npm test
      - name: Build
        run: cd dashboard && npm run build
```

---

## Troubleshooting

### Ошибка: "Failed to fetch"

**Причины**:
1. Backend недоступен
2. CORS не настроен
3. Неправильный URL в `VITE_API_BASE_URL`

**Решение**:
```bash
# Проверьте backend
curl https://your-backend.railway.app/system/health

# Проверьте CORS
curl -H "Origin: https://wb-analytics.vercel.app" \
     -H "X-API-SECRET-KEY: CnWvwoDwwGKh" \
     https://your-backend.railway.app/api/v1/bot/analytics/summary?telegram_id=123&period=30d
```

### Ошибка: "401 Unauthorized"

**Причина**: Неправильный API ключ

**Решение**:
1. Проверьте `VITE_API_SECRET_KEY` в Vercel
2. Проверьте `API_SECRET_KEY` на backend
3. Убедитесь, что ключи совпадают

### Build failed

**Причина**: TypeScript ошибки или отсутствующие зависимости

**Решение**:
```bash
# Локально
cd dashboard
npm run build

# Проверьте логи в Vercel
# Исправьте ошибки и закоммитьте
```

### Медленная загрузка

**Причины**:
1. Backend медленный
2. Большой объем данных
3. Нет кэширования

**Решение**:
1. Оптимизируйте запросы к БД (индексы уже применены ✅)
2. Настройте кэширование на backend
3. Используйте Vercel Edge Network

---

## Чеклист Production Readiness

### Backend
- [ ] Деплой на облачный сервис
- [ ] HTTPS настроен
- [ ] CORS настроен для Vercel домена
- [ ] Environment variables настроены
- [ ] База данных в production режиме
- [ ] Индексы БД применены
- [ ] Логирование настроено
- [ ] Мониторинг настроен

### Dashboard
- [ ] Деплой на Vercel
- [ ] Environment variables настроены
- [ ] Custom domain настроен (опционально)
- [ ] Analytics включен
- [ ] Error tracking настроен
- [ ] Performance оптимизирован

### Безопасность
- [ ] API ключи в секрете
- [ ] CORS ограничен конкретными доменами
- [ ] HTTPS везде
- [ ] Rate limiting настроен
- [ ] Логирование безопасности включено

### Мониторинг
- [ ] Vercel Analytics
- [ ] Sentry для ошибок
- [ ] Backend логи
- [ ] Uptime monitoring

---

## Стоимость

### Vercel
- **Hobby**: Бесплатно
  - 100 GB bandwidth
  - Unlimited deployments
  - Automatic HTTPS

- **Pro**: $20/месяц
  - 1 TB bandwidth
  - Advanced analytics
  - Team collaboration

### Railway
- **Starter**: $5/месяц
  - 500 часов выполнения
  - 100 GB bandwidth

- **Developer**: $20/месяц
  - Unlimited execution
  - 1 TB bandwidth

### Render
- **Free**: $0
  - 750 часов/месяц
  - Автоматический sleep после 15 мин неактивности

- **Starter**: $7/месяц
  - Always on
  - 400 часов выполнения

---

## Поддержка

- [Vercel Documentation](https://vercel.com/docs)
- [Railway Documentation](https://docs.railway.app)
- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
