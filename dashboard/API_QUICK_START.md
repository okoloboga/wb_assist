# API Quick Start Guide

## Быстрый старт для разработчиков

### 1. Настройка окружения (2 минуты)

```bash
# Скопировать пример
cp .env.example .env

# Отредактировать .env
nano .env
```

**Минимальная конфигурация:**
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1/bot
VITE_API_SECRET_KEY=CnWvwoDwwGKh
VITE_TELEGRAM_ID=123456789
```

### 2. Установка зависимостей (1 минута)

```bash
npm install @tanstack/react-query
```

### 3. Добавить Provider в main.tsx (1 минута)

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
```

### 4. Использовать hooks (готово!)

```tsx
import { useAnalyticsSummary, useWarehouses, useStocks } from './api/hooks';

function Dashboard() {
  // Сводная статистика
  const { data: summary } = useAnalyticsSummary('30d');
  
  // Список складов
  const { data: warehouses } = useWarehouses();
  
  // Остатки с фильтрацией
  const { data: stocks } = useStocks({
    limit: 15,
    filters: { warehouse: 'Коледино' }
  });

  return <div>...</div>;
}
```

## Доступные hooks

- `useWarehouses()` - список складов
- `useSizes()` - список размеров
- `useAnalyticsSummary(period)` - сводная статистика
- `useStocks(options)` - остатки с фильтрацией
- `useAnalyticsSales(period)` - аналитика продаж

## Периоды

- `7d` - 7 дней
- `30d` - 30 дней (по умолчанию)
- `60d` - 60 дней
- `90d` - 90 дней
- `180d` - 180 дней

## Фильтры для stocks

```tsx
const { data } = useStocks({
  limit: 20,
  offset: 0,
  filters: {
    warehouse: 'Коледино,Казань',  // Несколько через запятую
    size: 'M,L',                    // Несколько через запятую
    search: 'футболка'              // Поиск по названию/артикулу
  }
});
```

## Полная документация

- **Интеграция:** `INTEGRATION_GUIDE.md`
- **API:** `../docs/api/ANALYTICS_DASHBOARD_API.md`
- **Backend:** `../docs/stages/DASHBOARD.md`
