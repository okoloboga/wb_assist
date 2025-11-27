/**
 * React Query hooks для API
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { apiClient, Warehouse, AnalyticsSummary, Period, StocksFilters } from './client';

// Telegram ID пользователя (в реальном приложении получать из контекста/auth)
const TELEGRAM_ID = parseInt(import.meta.env.VITE_TELEGRAM_ID || '123456789');

/**
 * Hook для получения списка складов
 */
export function useWarehouses(options?: UseQueryOptions<Warehouse[]>) {
  return useQuery({
    queryKey: ['warehouses', TELEGRAM_ID],
    queryFn: () => apiClient.getWarehouses(TELEGRAM_ID),
    staleTime: 1000 * 60 * 60, // 1 час
    ...options,
  });
}

/**
 * Hook для получения списка размеров
 */
export function useSizes(options?: UseQueryOptions<string[]>) {
  return useQuery({
    queryKey: ['sizes', TELEGRAM_ID],
    queryFn: () => apiClient.getSizes(TELEGRAM_ID),
    staleTime: 1000 * 60 * 60, // 1 час
    ...options,
  });
}

/**
 * Hook для получения сводной статистики
 */
export function useAnalyticsSummary(
  period: string = '30d',
  options?: UseQueryOptions<{ summary: AnalyticsSummary; period: Period }>
) {
  return useQuery({
    queryKey: ['analytics-summary', TELEGRAM_ID, period],
    queryFn: () => apiClient.getAnalyticsSummary(TELEGRAM_ID, period),
    staleTime: 1000 * 60 * 15, // 15 минут
    ...options,
  });
}

/**
 * Hook для получения остатков
 */
export function useStocks(
  options: {
    limit?: number;
    offset?: number;
    filters?: StocksFilters;
  } = {},
  queryOptions?: UseQueryOptions<any>
) {
  const { limit = 15, offset = 0, filters = {} } = options;

  return useQuery({
    queryKey: ['stocks', TELEGRAM_ID, limit, offset, filters],
    queryFn: () => apiClient.getStocks(TELEGRAM_ID, { limit, offset, filters }),
    staleTime: 1000 * 60 * 5, // 5 минут
    ...queryOptions,
  });
}

/**
 * Hook для получения ежедневной динамики
 */
export function useAnalyticsDailyTrends(
  period: string = '30d',
  options?: UseQueryOptions<any>
) {
  // Преобразуем период в количество дней
  const daysMap: Record<string, number> = {
    '7d': 7,
    '30d': 30,
    '60d': 60,
    '90d': 90,
    '180d': 180,
  }
  const days = daysMap[period] || 30
  
  return useQuery({
    queryKey: ['analytics-daily-trends', TELEGRAM_ID, days],
    queryFn: () => apiClient.getAnalyticsDailyTrends(TELEGRAM_ID, days),
    staleTime: 1000 * 60 * 15, // 15 минут
    ...options,
  });
}
