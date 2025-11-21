# Аналитический дашборд

Веб-дашборд для визуализации аналитики продаж и состояния складов Wildberries.

## Технологии

- **React 18** - UI библиотека
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Стилизация
- **React Query** - Управление серверным состоянием
- **Recharts** - Визуализация данных
- **Axios** - HTTP клиент

## Установка

```bash
# Установить зависимости
npm install
```

## Разработка

```bash
# Запустить dev сервер
npm run dev

# Сервер будет доступен на http://localhost:3000
```

## Сборка

```bash
# Production build
npm run build

# Preview production build
npm run preview
```

## Структура проекта

```
dashboard/
├── src/
│   ├── api/              # API клиенты
│   ├── components/       # React компоненты
│   │   ├── charts/       # Компоненты графиков
│   │   ├── warehouse/    # Компоненты складов
│   │   ├── common/       # Общие компоненты
│   │   └── layout/       # Layout компоненты
│   ├── hooks/            # Custom hooks
│   ├── types/            # TypeScript типы
│   ├── utils/            # Utility функции
│   ├── App.tsx           # Главный компонент
│   ├── main.tsx          # Entry point
│   └── index.css         # Глобальные стили
├── public/               # Статические файлы
└── index.html            # HTML template
```

## Конфигурация

Скопируйте `.env.example` в `.env.development` и настройте переменные:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Аналитический дашборд
```

## Deployment

### Nginx

1. Соберите проект:
```bash
npm run build
```

2. Скопируйте содержимое `dist/` на сервер

3. Используйте конфигурацию nginx (см. `nginx.conf`)

## Статус разработки

✅ Этап 1: Инициализация проекта (завершён)
- Структура проекта создана
- Конфигурация окружения настроена
- Базовые типы данных определены

⏳ Следующие этапы:
- Этап 2: API клиент и хуки
- Этап 3: Layout и общие компоненты
- Этап 4: Графики и метрики
- И далее...
