# Design Document

## Overview

Аналитический дашборд представляет собой одностраничное веб-приложение (SPA) на React с использованием современного стека технологий. Приложение состоит из двух основных секций: графики продаж (верхняя часть) и информация о складах (нижняя часть). Дизайн минималистичный, с акцентом на читаемость данных и быструю навигацию.

## Architecture

### Technology Stack

**Frontend Framework:**
- React 18+ с TypeScript
- Vite для быстрой разработки и сборки
- React Router для маршрутизации (если потребуется)

**UI Libraries:**
- Recharts или Chart.js для визуализации данных
- Tailwind CSS для стилизации
- Lucide React для иконок

**State Management:**
- React Query (TanStack Query) для управления серверным состоянием
- React Context API для глобального состояния (если нужно)

**HTTP Client:**
- Axios для запросов к Backend API

**Development Tools:**
- ESLint + Prettier для code quality
- TypeScript для type safety

### Project Structure

```
dashboard/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/
│   │   ├── client.ts          # Axios instance
│   │   ├── orders.ts          # Orders API calls
│   │   └── warehouse.ts       # Warehouse API calls
│   ├── components/
│   │   ├── charts/
│   │   │   ├── OrdersChart.tsx
│   │   │   ├── MetricCard.tsx
│   │   │   └── ChartContainer.tsx
│   │   ├── warehouse/
│   │   │   ├── WarehouseTable.tsx
│   │   │   ├── WarehouseCard.tsx
│   │   │   └── StockItem.tsx
│   │   ├── common/
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorMessage.tsx
│   │   │   └── TimePeriodSelector.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       └── Container.tsx
│   ├── hooks/
│   │   ├── useOrders.ts
│   │   ├── useWarehouse.ts
│   │   └── useMediaQuery.ts
│   ├── types/
│   │   ├── orders.ts
│   │   ├── warehouse.ts
│   │   └── common.ts
│   ├── utils/
│   │   ├── formatters.ts
│   │   └── constants.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── .env.example
├── .env.development
├── nginx.conf
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Components and Interfaces

### 1. Data Types

```typescript
// types/common.ts
export type TimePeriod = 'day' | 'week' | 'month' | 'year';

export interface ApiResponse<T> {
  data: T;
  timestamp: string;
}

// types/orders.ts
export interface OrderMetrics {
  orders: number;
  purchases: number;
  cancellations: number;
  returns: number;
}

export interface OrdersData {
  period: TimePeriod;
  metrics: OrderMetrics;
  chartData: ChartDataPoint[];
}

export interface ChartDataPoint {
  date: string;
  orders: number;
  purchases: number;
  cancellations: number;
  returns: number;
}

// types/warehouse.ts
export interface WarehouseItem {
  id: string;
  nomenclature: string;
  size: string;
  warehouse: string;
  quantity: number;
  lastUpdated: string;
}

export interface WarehouseData {
  items: WarehouseItem[];
  summary: {
    totalItems: number;
    totalQuantity: number;
    warehouseCount: number;
  };
}
```

### 2. API Client

```typescript
// api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);
```

### 3. Custom Hooks

```typescript
// hooks/useOrders.ts
import { useQuery } from '@tanstack/react-query';
import { getOrders } from '../api/orders';
import { TimePeriod } from '../types/common';

export const useOrders = (period: TimePeriod) => {
  return useQuery({
    queryKey: ['orders', period],
    queryFn: () => getOrders(period),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
};

// hooks/useWarehouse.ts
import { useQuery } from '@tanstack/react-query';
import { getWarehouse } from '../api/warehouse';

export const useWarehouse = () => {
  return useQuery({
    queryKey: ['warehouse'],
    queryFn: getWarehouse,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
};

// hooks/useMediaQuery.ts
import { useState, useEffect } from 'react';

export const useMediaQuery = (query: string): boolean => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
};
```

### 4. Main Components

#### App Component
```typescript
// App.tsx
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './components/layout/Header';
import { Container } from './components/layout/Container';
import { TimePeriodSelector } from './components/common/TimePeriodSelector';
import { OrdersChart } from './components/charts/OrdersChart';
import { MetricCard } from './components/charts/MetricCard';
import { WarehouseTable } from './components/warehouse/WarehouseTable';
import { useOrders } from './hooks/useOrders';
import { useWarehouse } from './hooks/useWarehouse';
import { TimePeriod } from './types/common';

const queryClient = new QueryClient();

function Dashboard() {
  const [period, setPeriod] = useState<TimePeriod>('week');
  const { data: ordersData, isLoading: ordersLoading, error: ordersError } = useOrders(period);
  const { data: warehouseData, isLoading: warehouseLoading, error: warehouseError } = useWarehouse();

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <Container>
        {/* Time Period Selector */}
        <TimePeriodSelector value={period} onChange={setPeriod} />
        
        {/* Orders Section */}
        <section className="mb-8">
          <h2 className="text-2xl font-semibold mb-4">Метрики заказов</h2>
          
          {/* Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <MetricCard title="Заказы" value={ordersData?.metrics.orders} loading={ordersLoading} />
            <MetricCard title="Выкупы" value={ordersData?.metrics.purchases} loading={ordersLoading} />
            <MetricCard title="Отмены" value={ordersData?.metrics.cancellations} loading={ordersLoading} />
            <MetricCard title="Возвраты" value={ordersData?.metrics.returns} loading={ordersLoading} />
          </div>
          
          {/* Chart */}
          <OrdersChart data={ordersData?.chartData} loading={ordersLoading} error={ordersError} />
        </section>
        
        {/* Warehouse Section */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">Состояние складов</h2>
          <WarehouseTable data={warehouseData} loading={warehouseLoading} error={warehouseError} />
        </section>
      </Container>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
```

## Data Models

### API Endpoints

**Orders API:**
- `GET /api/analytics/orders?period={period}` - Получить метрики заказов
  - Response: `{ data: OrdersData, timestamp: string }`

**Warehouse API:**
- `GET /api/analytics/warehouse` - Получить состояние складов
  - Response: `{ data: WarehouseData, timestamp: string }`

### Data Flow

1. User opens dashboard → App component mounts
2. React Query fetches data from API using custom hooks
3. Data is cached and displayed in components
4. User changes time period → New API request with updated period
5. Components re-render with new data
6. Cache prevents unnecessary requests

## Error Handling

### Error Types

1. **Network Errors**: Connection timeout, no internet
2. **API Errors**: 4xx, 5xx responses
3. **Data Errors**: Invalid response format

### Error Handling Strategy

```typescript
// components/common/ErrorMessage.tsx
interface ErrorMessageProps {
  error: Error | null;
  retry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ error, retry }) => {
  if (!error) return null;
  
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <p className="text-red-800 mb-2">Ошибка загрузки данных</p>
      <p className="text-red-600 text-sm mb-3">{error.message}</p>
      {retry && (
        <button onClick={retry} className="text-red-700 underline text-sm">
          Попробовать снова
        </button>
      )}
    </div>
  );
};
```

## Testing Strategy

### Unit Tests
- Test utility functions (formatters, validators)
- Test custom hooks with mock data
- Test component rendering with different props

### Integration Tests
- Test API client with mock server
- Test data flow from API to components
- Test error handling scenarios

### E2E Tests (Optional)
- Test full user flow: load dashboard → change period → view data
- Test mobile responsiveness
- Test error recovery

### Testing Tools
- Vitest for unit tests
- React Testing Library for component tests
- MSW (Mock Service Worker) for API mocking

## Responsive Design

### Breakpoints

```typescript
// utils/constants.ts
export const BREAKPOINTS = {
  mobile: '320px',
  tablet: '768px',
  desktop: '1024px',
  wide: '1920px',
};
```

### Mobile Layout (< 768px)
- Single column layout
- Stacked metric cards
- Simplified charts (smaller height)
- Collapsible warehouse table
- Touch-friendly buttons (min 44px)

### Tablet Layout (768px - 1024px)
- Two column grid for metrics
- Full-width charts
- Scrollable warehouse table

### Desktop Layout (> 1024px)
- Four column grid for metrics
- Side-by-side charts if needed
- Full warehouse table with all columns

## Performance Optimization

### Code Splitting
```typescript
// Lazy load heavy components
const OrdersChart = lazy(() => import('./components/charts/OrdersChart'));
const WarehouseTable = lazy(() => import('./components/warehouse/WarehouseTable'));
```

### Data Caching
- React Query automatic caching (5-10 minutes)
- LocalStorage for user preferences (time period)

### Bundle Optimization
- Tree shaking with Vite
- Code splitting by route (if multiple pages)
- Lazy loading of chart libraries
- Image optimization (if any)

### Performance Targets
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Bundle size: < 500KB (gzipped)

## Deployment Configuration

### Environment Variables

```bash
# .env.example
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Analytics Dashboard
```

### Nginx Configuration

```nginx
# nginx.conf
server {
    listen 80;
    server_name dashboard.example.com;
    root /var/www/dashboard/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Build Process

```json
// package.json scripts
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\""
  }
}
```

## Accessibility

### WCAG 2.1 Compliance

1. **Color Contrast**: Minimum 4.5:1 for text
2. **Keyboard Navigation**: All interactive elements accessible via keyboard
3. **Screen Reader Support**: Proper ARIA labels
4. **Focus Indicators**: Visible focus states
5. **Semantic HTML**: Proper heading hierarchy

### Implementation

```typescript
// Accessible metric card
<div role="region" aria-label={`${title} metric`}>
  <h3 className="text-sm font-medium text-gray-600">{title}</h3>
  <p className="text-3xl font-bold" aria-live="polite">
    {formatNumber(value)}
  </p>
</div>
```

## Security Considerations

1. **API Authentication**: Include auth tokens in requests (if required)
2. **XSS Prevention**: React's built-in escaping
3. **HTTPS**: Enforce HTTPS in production
4. **Environment Variables**: Never commit sensitive data
5. **Content Security Policy**: Configure CSP headers in nginx

## Monitoring and Analytics

### Error Tracking
- Sentry or similar for error monitoring
- Log API errors to console in development

### Performance Monitoring
- Web Vitals tracking
- API response time monitoring

### User Analytics (Optional)
- Google Analytics or similar
- Track page views and user interactions
