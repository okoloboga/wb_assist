/**
 * Временной период для фильтрации данных
 */
export type TimePeriod = 'day' | 'week' | 'month' | 'year'

/**
 * Общий формат ответа API
 */
export interface ApiResponse<T> {
  data: T
  timestamp: string
}

/**
 * Состояние загрузки данных
 */
export interface LoadingState {
  isLoading: boolean
  error: Error | null
}
