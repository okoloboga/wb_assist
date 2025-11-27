/**
 * API Client для аналитического дашборда
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/bot';
const API_SECRET_KEY = import.meta.env.VITE_API_SECRET_KEY || '';

// Типы данных
export interface Warehouse {
  name: string;
  product_count: number;
}

export interface AnalyticsSummary {
  orders: number;
  purchases: number;
  cancellations: number;
  returns: number;
}

export interface Period {
  start: string;
  end: string;
  days: number;
}

export interface StockProduct {
  nm_id: number;
  name: string;
  total_quantity: number;
  warehouses: {
    [key: string]: {
      warehouse_name: string;
      total_quantity: number;
      sizes: {
        [key: string]: number;
      };
    };
  };
}

export interface Pagination {
  limit: number;
  offset: number;
  total: number;
  has_more: boolean;
}

export interface StocksFilters {
  warehouse?: string;
  size?: string;
  search?: string;
}

export interface AvailableFilters {
  warehouses: string[];
  sizes: string[];
}

// API Client класс
class DashboardAPIClient {
  private baseURL: string;
  private apiKey: string;

  constructor(baseURL: string, apiKey: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers = {
      'X-API-SECRET-KEY': this.apiKey,
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }));
        throw new Error(error.detail || 'API request failed');
      }

      return response.json();
    } catch (error) {
      console.error('API request error:', error);
      throw error;
    }
  }

  /**
   * Получение списка складов
   */
  async getWarehouses(telegramId: number): Promise<Warehouse[]> {
    const response = await this.request<{ success: boolean; warehouses: Warehouse[] }>(
      `/warehouses?telegram_id=${telegramId}`
    );
    return response.warehouses;
  }

  /**
   * Получение списка размеров
   */
  async getSizes(telegramId: number): Promise<string[]> {
    const response = await this.request<{ success: boolean; sizes: string[] }>(
      `/sizes?telegram_id=${telegramId}`
    );
    return response.sizes;
  }

  /**
   * Получение сводной статистики
   */
  async getAnalyticsSummary(
    telegramId: number,
    period: string = '30d'
  ): Promise<{ summary: AnalyticsSummary; period: Period }> {
    const response = await this.request<{
      success: boolean;
      summary: AnalyticsSummary;
      period: Period;
    }>(`/analytics/summary?telegram_id=${telegramId}&period=${period}`);
    
    return {
      summary: response.summary,
      period: response.period,
    };
  }

  /**
   * Получение остатков с фильтрацией
   */
  async getStocks(
    telegramId: number,
    options: {
      limit?: number;
      offset?: number;
      filters?: StocksFilters;
    } = {}
  ): Promise<{
    stocks: any[];
    pagination: Pagination;
    filters: StocksFilters;
    available_filters: AvailableFilters;
  }> {
    const { limit = 15, offset = 0, filters = {} } = options;
    
    const params = new URLSearchParams({
      telegram_id: telegramId.toString(),
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (filters.warehouse) {
      params.append('warehouse', filters.warehouse);
    }
    if (filters.size) {
      params.append('size', filters.size);
    }
    if (filters.search) {
      params.append('search', filters.search);
    }

    const response = await this.request<{
      success: boolean;
      stocks: any[];
      pagination: Pagination;
      filters: StocksFilters;
      available_filters: AvailableFilters;
    }>(`/stocks/all?${params}`);

    return {
      stocks: response.stocks,
      pagination: response.pagination,
      filters: response.filters,
      available_filters: response.available_filters,
    };
  }

  /**
   * Получение ежедневной динамики
   */
  async getAnalyticsDailyTrends(
    telegramId: number,
    days: number = 30
  ): Promise<any> {
    const response = await this.request<{
      status: string;
      analytics: {
        meta: {
          days_window: number;
          date_range: { start: string; end: string };
          generated_at: string;
        };
        time_series: Array<{
          date: string;
          orders: number;
          cancellations: number;
          buyouts: number;
          returns: number;
          orders_amount: number;
          cancellations_amount: number;
          buyouts_amount: number;
          returns_amount: number;
          avg_rating: number;
        }>;
        aggregates: any;
        top_products: any[];
        chart: any;
      };
    }>(`/analytics/daily-trends?telegram_id=${telegramId}&days=${days}`);
    
    return response.analytics;
  }
}

// Экспорт singleton instance
export const apiClient = new DashboardAPIClient(API_BASE_URL, API_SECRET_KEY);

// Экспорт класса для тестирования
export { DashboardAPIClient };
