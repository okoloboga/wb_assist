# Деплой Dashboard на Vercel

## Вариант 1: Через Vercel Dashboard (рекомендуется)

### Шаг 1: Подготовка репозитория

1. Убедитесь, что код закоммичен в Git:
```bash
git add .
git commit -m "Add analytics dashboard"
git push
```

### Шаг 2: Импорт проекта в Vercel

1. Перейдите на [vercel.com](https://vercel.com)
2. Нажмите "Add New" → "Project"
3. Выберите ваш Git репозиторий
4. В настройках проекта:
   - **Framework Preset**: Vite
   - **Root Directory**: `dashboard`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Шаг 3: Настройка Environment Variables

В разделе "Environment Variables" добавьте:

```
VITE_API_BASE_URL=https://your-backend-url.com/api/v1/bot
VITE_API_SECRET_KEY=CnWvwoDwwGKh
VITE_TELEGRAM_ID=1621927129
```

**Важно**: 
- Замените `your-backend-url.com` на реальный URL вашего backend
- Backend должен быть доступен публично (не localhost)
- Настройте CORS на backend для домена Vercel

### Шаг 4: Deploy

Нажмите "Deploy" и дождитесь завершения сборки.

---

## Вариант 2: Через Vercel CLI

### Установка CLI

```bash
npm install -g vercel
```

### Вход в аккаунт

```bash
vercel login
```

### Деплой

```bash
cd dashboard
vercel
```

При первом деплое CLI задаст вопросы:
- Set up and deploy? **Y**
- Which scope? Выберите ваш аккаунт
- Link to existing project? **N**
- What's your project's name? **wb-analytics-dashboard**
- In which directory is your code located? **./**

### Настройка переменных окружения

```bash
vercel env add VITE_API_BASE_URL
# Введите значение: https://your-backend-url.com/api/v1/bot

vercel env add VITE_API_SECRET_KEY
# Введите значение: CnWvwoDwwGKh

vercel env add VITE_TELEGRAM_ID
# Введите значение: 1621927129
```

### Production деплой

```bash
vercel --prod
```

---

## Настройка Backend для работы с Vercel

### 1. Публичный доступ к Backend

Backend должен быть доступен по HTTPS. Варианты:

#### Вариант A: Деплой backend на облачный сервис
- Railway.app
- Render.com
- DigitalOcean
- AWS/GCP/Azure

#### Вариант B: Использование туннеля (для разработки)
```bash
# Установите ngrok
npm install -g ngrok

# Запустите туннель
ngrok http 8002
```

Используйте полученный URL (например, `https://abc123.ngrok.io`) как `VITE_API_BASE_URL`.

### 2. Настройка CORS

Добавьте в `server/app/core/middleware.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-vercel-app.vercel.app",
        "http://localhost:5173",  # для локальной разработки
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Проверка деплоя

### 1. Откройте URL проекта

После деплоя Vercel покажет URL вида: `https://your-project.vercel.app`

### 2. Проверьте консоль браузера

Откройте DevTools (F12) → Console и проверьте:
- ✅ Нет ошибок CORS
- ✅ API запросы успешны (статус 200)
- ✅ Данные загружаются

### 3. Проверьте Network tab

- Запросы должны идти на правильный backend URL
- Заголовок `X-API-SECRET-KEY` должен присутствовать
- Ответы должны содержать данные

---

## Troubleshooting

### Ошибка: "Failed to fetch"

**Причина**: Backend недоступен или CORS не настроен

**Решение**:
1. Проверьте, что backend доступен публично
2. Проверьте CORS настройки
3. Проверьте `VITE_API_BASE_URL` в Vercel

### Ошибка: "401 Unauthorized"

**Причина**: Неправильный API ключ

**Решение**:
1. Проверьте `VITE_API_SECRET_KEY` в Vercel
2. Убедитесь, что ключ совпадает с backend

### Пустые данные

**Причина**: Неправильный Telegram ID или нет данных

**Решение**:
1. Проверьте `VITE_TELEGRAM_ID` в Vercel
2. Убедитесь, что у пользователя есть данные в БД

### Build failed

**Причина**: Ошибки TypeScript или отсутствующие зависимости

**Решение**:
1. Проверьте логи сборки в Vercel
2. Запустите `npm run build` локально
3. Исправьте ошибки и закоммитьте

---

## Автоматический деплой

После настройки Vercel будет автоматически деплоить:
- **Production**: При push в ветку `main`/`master`
- **Preview**: При создании Pull Request

---

## Полезные команды

```bash
# Просмотр логов
vercel logs

# Список деплоев
vercel ls

# Удаление проекта
vercel remove

# Открыть проект в браузере
vercel open
```

---

## Рекомендации для Production

1. **Используйте custom domain**:
   ```bash
   vercel domains add your-domain.com
   ```

2. **Настройте мониторинг**:
   - Vercel Analytics
   - Sentry для отслеживания ошибок

3. **Оптимизируйте производительность**:
   - Включите Vercel Edge Network
   - Настройте кэширование

4. **Безопасность**:
   - Используйте HTTPS для backend
   - Ротируйте API ключи регулярно
   - Ограничьте CORS только нужными доменами

---

## Поддержка

- [Vercel Documentation](https://vercel.com/docs)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [React Query with Vercel](https://tanstack.com/query/latest/docs/react/guides/ssr)
