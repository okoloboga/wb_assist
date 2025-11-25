# Frontend Integration Guide

## Обзор

Руководство по интеграции фронтенда дашборда с backend API.

## Шаг 1: Установка зависимостей

```bash
cd dashboard

# Установка React Query
npm install @tanstack/react-query

# Или с yarn
yarn add @tanstack/react-query
```

## Шаг 2: Настройка переменных окружения

```bash
# Копирование примера
cp .env.example .env

# Редактирование
nano .env
```

**Содержимое .env:**

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1/bot
VITE_API_SECRET_KEY=CnWvwoDwwGKh
VITE_TELEGRAM_ID=123456789
```

## Шаг 3: Настройка React Query Provider

Обновите `dashboard/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import './index.css';

// Создание Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5, // 5 минут по умолчанию
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

## Шаг 4: Использование API hooks

### Пример 1: Получение сводной статистики

```tsx
import { useAnalyticsSummary } from './api/hooks';

function MetricsCards() {
  const { data, isLoading, error } = useAnalyticsSummary('30d');

  if (isLoading) return <div>Загрузка...</div>;
  if (error) return <div>Ошибка: {error.message}</div>;

  const { summary } = data!;

  return (
    <div className="grid grid-cols-4 gap-4">
      <MetricCard title="Заказы" value={summary.orders} />
      <MetricCard title="Выкупы" value={summary.purchases} />
      <MetricCard title="Отмены" value={summary.cancellations} />
      <MetricCard title="Возвраты" value={summary.returns} />
    </div>
  );
}
```

### Пример 2: Получение складов для фильтра

```tsx
import { useWarehouses } from './api/hooks';

function WarehouseFilter() {
  const { data: warehouses, isLoading } = useWarehouses();

  if (isLoading) return <div>Загрузка складов...</div>;

  return (
    <select>
      <option value="">Все склады</option>
      {warehouses?.map((warehouse) => (
        <option key={warehouse.name} value={warehouse.name}>
          {warehouse.name} ({warehouse.product_count})
        </option>
      ))}
    </select>
  );
}
```

### Пример 3: Получение остатков с фильтрацией

```tsx
import { useState } from 'react';
import { useStocks } from './api/hooks';

function WarehouseTable() {
  const [filters, setFilters] = useState({
    warehouse: '',
    size: '',
    search: '',
  });
  const [page, setPage] = useState(0);
  const limit = 15;

  const { data, isLoading, error } = useStocks({
    limit,
    offset: page * limit,
    filters,
  });

  if (isLoading) return <div>Загрузка...</div>;
  if (error) return <div>Ошибка: {error.message}</div>;

  const { products, pagination, available_filters } = data!;

  return (
    <div>
      {/* Фильтры */}
      <div className="filters">
        <select
          value={filters.warehouse}
          onChange={(e) => setFilters({ ...filters, warehouse: e.target.value })}
        >
          <option value="">Все склады</option>
          {available_filters.warehouses.map((w) => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>

        <select
          value={filters.size}
          onChange={(e) => setFilters({ ...filters, size: e.target.value })}
        >
          <option value="">Все размеры</option>
          {available_filters.sizes.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Поиск..."
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
        />
      </div>

      {/* Таблица */}
      <table>
        <thead>
          <tr>
            <th>Товар</th>
            <th>Всего</th>
            <th>Склады</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.nm_id}>
              <td>{product.name}</td>
              <td>{product.total_quantity}</td>
              <td>
                {Object.values(product.warehouses).map((wh) => (
                  <div key={wh.warehouse_name}>
                    {wh.warehouse_name}: {wh.total_quantity}
                  </div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Пагинация */}
      <div className="pagination">
        <button
          disabled={page === 0}
          onClick={() => setPage(page - 1)}
        >
          Назад
        </button>
        <span>
          Страница {page + 1} из {Math.ceil(pagination.total / limit)}
        </span>
        <button
          disabled={!pagination.has_more}
          onClick={() => setPage(page + 1)}
        >
          Вперед
        </button>
      </div>
    </div>
  );
}
```

### Пример 4: Выбор периода

```tsx
import { useState } from 'react';
import { useAnalyticsSummary } from './api/hooks';

function Dashboard() {
  const [period, setPeriod] = useState('30d');
  const { data, isLoading } = useAnalyticsSummary(period);

  return (
    <div>
      <select value={period} onChange={(e) => setPeriod(e.target.value)}>
        <option value="7d">7 дней</option>
        <option value="30d">30 дней</option>
        <option value="60d">60 дней</option>
        <option value="90d">90 дней</option>
        <option value="180d">180 дней</option>
      </select>

      {isLoading ? (
        <div>Загрузка...</div>
      ) : (
        <MetricsCards summary={data!.summary} />
      )}
    </div>
  );
}
```

## Шаг 5: Обработка ошибок

### Глобальная обработка ошибок

```tsx
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      onError: (error) => {
        console.error('Query error:', error);
        // Показать toast уведомление
        // toast.error(error.message);
      },
    },
  },
});
```

### Локальная обработка ошибок

```tsx
function Component() {
  const { data, error, isError } = useAnalyticsSummary();

  if (isError) {
    return (
      <div className="error">
        <h3>Ошибка загрузки данных</h3>
        <p>{error.message}</p>
        <button onClick={() => refetch()}>Повторить</button>
      </div>
    );
  }

  // ...
}
```

## Шаг 6: Состояния загрузки

### Скелетоны

```tsx
function MetricsCards() {
  const { data, isLoading } = useAnalyticsSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton-title" />
            <div className="skeleton-value" />
          </div>
        ))}
      </div>
    );
  }

  // ...
}
```

### Индикаторы загрузки

```tsx
import { useIsFetching } from '@tanstack/react-query';

function GlobalLoadingIndicator() {
  const isFetching = useIsFetching();

  if (!isFetching) return null;

  return (
    <div className="loading-bar">
      <div className="loading-bar-progress" />
    </div>
  );
}
```

## Шаг 7: Инвалидация кэша

### После обновления данных

```tsx
import { useQueryClient } from '@tanstack/react-query';

function SyncButton() {
  const queryClient = useQueryClient();

  const handleSync = async () => {
    // Запуск синхронизации
    await fetch('/api/v1/bot/sync/start', {
      method: 'POST',
      headers: {
        'X-API-SECRET-KEY': API_KEY,
      },
    });

    // Инвалидация всех запросов
    queryClient.invalidateQueries();
  };

  return <button onClick={handleSync}>Синхронизировать</button>;
}
```

### Автоматическое обновление

```tsx
function Dashboard() {
  const { data } = useAnalyticsSummary('30d', {
    refetchInterval: 1000 * 60 * 5, // Обновлять каждые 5 минут
  });

  // ...
}
```

## Шаг 8: Тестирование

### Запуск dev сервера

```bash
# Убедитесь, что backend запущен
cd server
docker-compose up -d

# Запуск фронтенда
cd dashboard
npm run dev
```

### Проверка интеграции

1. Откройте http://localhost:5173
2. Откройте DevTools -> Network
3. Проверьте запросы к API
4. Проверьте заголовки (X-API-SECRET-KEY)
5. Проверьте ответы

### React Query DevTools

React Query DevTools автоматически доступны в development режиме. Нажмите на иконку в правом нижнем углу для просмотра:
- Активных запросов
- Кэшированных данных
- Статуса запросов

## Troubleshooting

### CORS ошибки

**Проблема:** `Access to fetch at 'http://localhost:8000/api/v1/bot/warehouses' from origin 'http://localhost:5173' has been blocked by CORS policy`

**Решение:**
1. Проверьте, что в `.env` сервера указан правильный origin:
   ```bash
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000
   ```
2. Перезапустите сервер

### 403 Forbidden

**Проблема:** `403 Forbidden: Invalid or missing API Secret Key`

**Решение:**
1. Проверьте, что `VITE_API_SECRET_KEY` в `.env` совпадает с `API_SECRET_KEY` на сервере
2. Проверьте, что заголовок передается в запросах

### Данные не обновляются

**Проблема:** Данные остаются старыми после изменений

**Решение:**
1. Проверьте `staleTime` в настройках React Query
2. Используйте `queryClient.invalidateQueries()` после изменений
3. Проверьте кэширование на сервере

## Дополнительные ресурсы

- [React Query Documentation](https://tanstack.com/query/latest)
- [API Documentation](../docs/api/ANALYTICS_DASHBOARD_API.md)
- [Backend Documentation](../docs/stages/DASHBOARD.md)
