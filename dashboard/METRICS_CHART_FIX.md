# Исправление динамики метрик в дашборде

## Проблема
Графики динамики метрик не отображались из-за несоответствия структуры данных между фронтендом и бэкендом.

## Причина
1. **Фронтенд ожидал**: `dailyTrendsData.daily_data`
2. **Бэкенд возвращал**: `analytics.time_series`
3. **Неправильное поле**: фронтенд использовал `purchases`, а бэкенд возвращает `buyouts`

## Исправления

### 1. App.tsx
Изменена обработка данных графика:

```typescript
// Было:
if (!dailyTrendsData?.daily_data) {
  return []
}
return dailyTrendsData.daily_data.map((day: any) => ({
  date: new Date(day.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
  orders: day.orders || 0,
  purchases: day.purchases || 0,  // ❌ Неправильное поле
  cancellations: day.cancellations || 0,
  returns: day.returns || 0,
}))

// Стало:
if (!dailyTrendsData?.time_series) {
  return []
}
return dailyTrendsData.time_series.map((day: any) => ({
  date: new Date(day.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
  orders: day.orders || 0,
  purchases: day.buyouts || 0,  // ✅ Правильное поле (выкупы)
  cancellations: day.cancellations || 0,
  returns: day.returns || 0,
}))
```

### 2. client.ts
Добавлена типизация для структуры данных API:

```typescript
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
        buyouts: number;  // ✅ Выкупы
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
```

## Структура данных API

### Endpoint: `/api/v1/bot/analytics/daily-trends`

**Ответ:**
```json
{
  "status": "success",
  "analytics": {
    "meta": {
      "days_window": 30,
      "date_range": {
        "start": "2025-10-28",
        "end": "2025-11-26"
      },
      "generated_at": "2025-11-27T10:00:00"
    },
    "time_series": [
      {
        "date": "2025-10-28",
        "orders": 45,
        "orders_amount": 12500.50,
        "cancellations": 5,
        "cancellations_amount": 1200.00,
        "buyouts": 38,
        "buyouts_amount": 10500.00,
        "returns": 2,
        "returns_amount": 500.00,
        "avg_rating": 4.5
      }
    ],
    "aggregates": {
      "totals": {
        "orders": 1350,
        "orders_amount": 375000.00,
        "cancellations": 150,
        "cancellations_amount": 36000.00,
        "buyouts": 1140,
        "buyouts_amount": 315000.00,
        "returns": 60,
        "returns_amount": 15000.00
      },
      "conversion": {
        "buyout_rate_percent": 84.44,
        "return_rate_percent": 5.26
      }
    },
    "top_products": [...],
    "chart": {...}
  }
}
```

## Терминология

- **orders** - заказы (созданные заказы)
- **cancellations** - отмены (отмененные заказы)
- **buyouts** - выкупы (оплаченные и полученные заказы)
- **returns** - возвраты (возвращенные товары после выкупа)

## Проверка

После исправления графики должны корректно отображать:
1. ✅ Заказы (синяя линия)
2. ✅ Выкупы (зеленая линия)
3. ✅ Отмены (оранжевая линия)
4. ✅ Возвраты (красная линия)

## Дата исправления
27 ноября 2025
