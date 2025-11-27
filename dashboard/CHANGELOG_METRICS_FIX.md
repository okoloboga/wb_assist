# Changelog - Исправление динамики метрик

## [Исправление] - 2025-11-27

### Исправлено
- 🐛 **Графики не отображались** - исправлено несоответствие структуры данных между фронтендом и бэкендом
- 🐛 **Неправильное поле для выкупов** - изменено с `purchases` на `buyouts` в `time_series`
- 🐛 **Отсутствие обработки пустых данных** - добавлена проверка на пустой массив данных

### Изменено

#### `dashboard/src/App.tsx`
```diff
- if (!dailyTrendsData?.daily_data) {
+ if (!dailyTrendsData?.time_series) {
    return []
  }
  
- return dailyTrendsData.daily_data.map((day: any) => ({
+ return dailyTrendsData.time_series.map((day: any) => ({
    date: new Date(day.date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }),
    orders: day.orders || 0,
-   purchases: day.purchases || 0,
+   purchases: day.buyouts || 0,  // В API это называется buyouts (выкупы)
    cancellations: day.cancellations || 0,
    returns: day.returns || 0,
  }))
```

#### `dashboard/src/api/client.ts`
- Добавлена полная типизация для структуры ответа `analytics.time_series`
- Уточнено, что поле называется `buyouts`, а не `purchases`

#### `dashboard/src/components/charts/MetricsCharts.tsx`
```diff
+ {data && data.length > 0 ? (
  <ResponsiveContainer width="100%" height={400}>
    <LineChart data={data}>
      ...
    </LineChart>
  </ResponsiveContainer>
+ ) : (
+   <div className="flex items-center justify-center h-[400px] text-gray-400">
+     <p>Нет данных для отображения</p>
+   </div>
+ )}
```

### Добавлено
- 📄 `dashboard/METRICS_CHART_FIX.md` - подробное описание проблемы и решения
- 📄 `dashboard/TESTING_METRICS_FIX.md` - инструкция по тестированию
- 📄 `dashboard/CHANGELOG_METRICS_FIX.md` - этот файл

### Технические детали

#### Структура данных API (до исправления)
Фронтенд ожидал:
```typescript
{
  daily_data: [
    { date: string, orders: number, purchases: number, ... }
  ]
}
```

#### Структура данных API (после исправления)
Бэкенд возвращает:
```typescript
{
  analytics: {
    time_series: [
      { date: string, orders: number, buyouts: number, ... }
    ]
  }
}
```

#### Маппинг полей
| Фронтенд (UI) | Бэкенд (API) | Описание |
|---------------|--------------|----------|
| orders | orders | Заказы |
| purchases | buyouts | Выкупы |
| cancellations | cancellations | Отмены |
| returns | returns | Возвраты |

### Проверено
- ✅ Графики отображаются корректно
- ✅ Все 4 метрики показываются правильно
- ✅ Переключение периодов работает
- ✅ Кнопки скрытия/показа метрик работают
- ✅ Обработка пустых данных работает
- ✅ Нет ошибок в консоли браузера

### Связанные файлы
- `dashboard/src/App.tsx`
- `dashboard/src/api/client.ts`
- `dashboard/src/api/hooks.ts`
- `dashboard/src/components/charts/MetricsCharts.tsx`
- `server/app/features/bot_api/service.py` (метод `get_daily_trends`)
- `server/app/features/bot_api/routes.py` (endpoint `/analytics/daily-trends`)
- `server/app/features/bot_api/schemas.py` (схема `DailyTrendsAPIResponse`)

### Примечания
- Терминология: в API используется `buyouts` (выкупы), а в UI отображается как "Выкупы"
- Summary endpoint использует `purchases` вместо `buyouts` - это правильно и не требует изменений
- График поддерживает до 4 метрик одновременно с возможностью скрытия любой из них
