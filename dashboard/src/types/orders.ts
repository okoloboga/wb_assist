import { TimePeriod } from './common'

/**
 * Метрики заказов
 */
export interface OrderMetrics {
  /** Общее количество заказов */
  orders: number
  /** Количество выкупов */
  purchases: number
  /** Количество отмен */
  cancellations: number
  /** Количество возвратов */
  returns: number
}

/**
 * Точка данных для графика
 */
export interface ChartDataPoint {
  /** Дата в формате ISO или читаемом виде */
  date: string
  /** Количество заказов */
  orders: number
  /** Количество выкупов */
  purchases: number
  /** Количество отмен */
  cancellations: number
  /** Количество возвратов */
  returns: number
}

/**
 * Полные данные заказов для выбранного периода
 */
export interface OrdersData {
  /** Выбранный временной период */
  period: TimePeriod
  /** Агрегированные метрики */
  metrics: OrderMetrics
  /** Данные для построения графика */
  chartData: ChartDataPoint[]
}
