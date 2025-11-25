# Analytics Dashboard API Documentation

## Обзор

Документация по API эндпоинтам для аналитического дашборда.

## Аутентификация

Все запросы требуют передачи `telegram_id` пользователя в query параметрах.

## Эндпоинты

### 1. Аналитика продаж

**Endpoint:** `GET /api/v1/bot/analytics/sales`

**Описание:** Получение статистики продаж за выбранный период

**Параметры:**
- `telegram_id` (required, integer) - Telegram ID пользователя
- `period` (optional, string, default: "30d") - Период анализа

**Поддерживаемые периоды:**
- `7d` - 7 дней
- `30d` - 30 дней (по умолчанию)
- `60d` - 60 дней
- `90d` - 90 дней
- `180d` - 180 дней

**Примеры запросов:**

```bash
# 30 дней (по умолчанию)
curl "http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456"

# 60 дней
curl "http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456&period=60d"

# 90 дней
curl "http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456&period=90d"

# 180 дней
curl "http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456&period=180d"
```

**Пример ответа:**

```json
{
  "status": "success",
  "analytics": {
    "period": "30d",
    "period_days": 30,
    "date_range": {
      "start": "2025-10-26",
      "end": "2025-11-25"
    },
    "sales_periods": {
      "today": {
        "count": 10,
        "amount": 5000
      },
      "yesterday": {
        "count": 8,
        "amount": 4000
      },
      "7_days": {
        "count": 50,
        "amount": 25000
      },
      "30_days": {
        "count": 200,
        "amount": 100000
      },
      "selected_period": {
        "count": 200,
        "amount": 100000
      }
    },
    "dynamics": {
      "yesterday_growth_percent": 25.0,
      "week_growth_percent": 15.0,
      "average_check": 500.0,
      "conversion_percent": 0.0
    },
    "top_products": [
      {
        "nm_id": 12345,
        "name": "Футболка",
        "sales_count": 50,
        "sales_amount": 25000
      }
    ],
    "stocks_summary": {
      "critical_count": 5,
      "zero_count": 2,
      "attention_needed": 7,
      "total_products": 100
    },
    "recommendations": [
      "Пополнить остатки критичных товаров"
    ]
  },
  "telegram_text": "..."
}
```

---

### 2. Остатки на складах

**Endpoint:** `GET /api/v1/bot/stocks/all`

**Описание:** Получение отчета по всем остаткам с фильтрацией и поиском

**Параметры:**
- `telegram_id` (required, integer) - Telegram ID пользователя
- `limit` (optional, integer, default: 15, range: 1-100) - Количество товаров на странице
- `offset` (optional, integer, default: 0) - Смещение для пагинации
- `warehouse` (optional, string) - Фильтр по складу (можно несколько через запятую)
- `size` (optional, string) - Фильтр по размеру (можно несколько через запятую)
- `search` (optional, string) - Поиск по названию товара или артикулу

**Примеры запросов:**

```bash
# Все остатки (без фильтров)
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456"

# Фильтр по одному складу
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&warehouse=Коледино"

# Фильтр по нескольким складам
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&warehouse=Коледино,Казань"

# Фильтр по размеру
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&size=M"

# Фильтр по нескольким размерам
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&size=S,M,L"

# Поиск по названию
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&search=футболка"

# Комбинированный запрос
curl "http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&warehouse=Коледино&size=M&search=футболка&limit=20&offset=0"
```

**Пример ответа:**

```json
{
  "status": "success",
  "stocks": {
    "products": [
      {
        "nm_id": 12345,
        "name": "Футболка базовая",
        "total_quantity": 150,
        "warehouses": {
          "Коледино": {
            "warehouse_name": "Коледино",
            "total_quantity": 100,
            "sizes": {
              "S": 20,
              "M": 50,
              "L": 30
            }
          },
          "Казань": {
            "warehouse_name": "Казань",
            "total_quantity": 50,
            "sizes": {
              "S": 10,
              "M": 25,
              "L": 15
            }
          }
        }
      }
    ],
    "pagination": {
      "limit": 15,
      "offset": 0,
      "total": 50,
      "has_more": true
    },
    "filters": {
      "warehouse": "Коледино",
      "size": "M",
      "search": "футболка"
    },
    "available_filters": {
      "warehouses": [
        "Коледино",
        "Казань",
        "Подольск"
      ],
      "sizes": [
        "S",
        "M",
        "L",
        "XL"
      ]
    }
  },
  "telegram_text": "..."
}
```

---

## Коды ошибок

- `404` - Кабинет WB не найден
- `500` - Внутренняя ошибка сервера

## Пагинация

Все эндпоинты с пагинацией возвращают следующую структуру:

```json
{
  "pagination": {
    "limit": 15,
    "offset": 0,
    "total": 100,
    "has_more": true
  }
}
```

- `limit` - количество элементов на странице
- `offset` - смещение от начала
- `total` - общее количество элементов
- `has_more` - есть ли еще элементы

## Фильтрация

### Множественный выбор

Для параметров `warehouse` и `size` можно указать несколько значений через запятую:

```
?warehouse=Коледино,Казань,Подольск
?size=S,M,L,XL
```

### Поиск

Параметр `search` выполняет регистронезависимый поиск по следующим полям:
- Название товара (`name`)
- Артикул (`vendor_code`, `article`)

Поиск работает по принципу "содержит" (LIKE %search%).

## Обратная совместимость

Все новые параметры опциональны. API полностью обратно совместим с предыдущими версиями.

## Примеры использования

### JavaScript (Fetch API)

```javascript
// Получение аналитики за 60 дней
const response = await fetch(
  'http://localhost:8000/api/v1/bot/analytics/sales?telegram_id=123456&period=60d'
);
const data = await response.json();
console.log(data.analytics);

// Получение остатков с фильтрацией
const stocksResponse = await fetch(
  'http://localhost:8000/api/v1/bot/stocks/all?telegram_id=123456&warehouse=Коледино&size=M'
);
const stocksData = await stocksResponse.json();
console.log(stocksData.stocks);
```

### Python (requests)

```python
import requests

# Получение аналитики за 90 дней
response = requests.get(
    'http://localhost:8000/api/v1/bot/analytics/sales',
    params={'telegram_id': 123456, 'period': '90d'}
)
data = response.json()
print(data['analytics'])

# Получение остатков с поиском
stocks_response = requests.get(
    'http://localhost:8000/api/v1/bot/stocks/all',
    params={
        'telegram_id': 123456,
        'search': 'футболка',
        'warehouse': 'Коледино,Казань'
    }
)
stocks_data = stocks_response.json()
print(stocks_data['stocks'])
```

---

### 3. Список складов

**Endpoint:** `GET /api/v1/bot/warehouses`

**Описание:** Получение списка всех доступных складов для фильтра

**Параметры:**
- `telegram_id` (required, integer) - Telegram ID пользователя

**Примеры запросов:**

```bash
curl "http://localhost:8000/api/v1/bot/warehouses?telegram_id=123456" \
  -H "X-API-SECRET-KEY: your-key"
```

**Пример ответа:**

```json
{
  "success": true,
  "warehouses": [
    {
      "name": "Коледино",
      "product_count": 150
    },
    {
      "name": "Казань",
      "product_count": 80
    },
    {
      "name": "Подольск",
      "product_count": 45
    }
  ]
}
```

**Кэширование:** 1 час (3600 секунд)

---

### 4. Список размеров

**Endpoint:** `GET /api/v1/bot/sizes`

**Описание:** Получение списка всех доступных размеров для фильтра

**Параметры:**
- `telegram_id` (required, integer) - Telegram ID пользователя

**Примеры запросов:**

```bash
curl "http://localhost:8000/api/v1/bot/sizes?telegram_id=123456" \
  -H "X-API-SECRET-KEY: your-key"
```

**Пример ответа:**

```json
{
  "success": true,
  "sizes": [
    "XS",
    "S",
    "M",
    "L",
    "XL",
    "XXL",
    "42",
    "44",
    "46",
    "ONE SIZE"
  ]
}
```

**Примечание:** Размеры отсортированы логически (сначала буквенные, затем числовые)

**Кэширование:** 1 час (3600 секунд)

---

### 5. Сводная статистика

**Endpoint:** `GET /api/v1/bot/analytics/summary`

**Описание:** Получение агрегированных метрик для карточек дашборда

**Параметры:**
- `telegram_id` (required, integer) - Telegram ID пользователя
- `period` (optional, string, default: "30d") - Период анализа

**Поддерживаемые периоды:**
- `7d` - 7 дней
- `30d` - 30 дней (по умолчанию)
- `60d` - 60 дней
- `90d` - 90 дней
- `180d` - 180 дней

**Примеры запросов:**

```bash
# 30 дней (по умолчанию)
curl "http://localhost:8000/api/v1/bot/analytics/summary?telegram_id=123456" \
  -H "X-API-SECRET-KEY: your-key"

# 90 дней
curl "http://localhost:8000/api/v1/bot/analytics/summary?telegram_id=123456&period=90d" \
  -H "X-API-SECRET-KEY: your-key"
```

**Пример ответа:**

```json
{
  "success": true,
  "summary": {
    "orders": 2404,
    "purchases": 2034,
    "cancellations": 249,
    "returns": 121
  },
  "period": {
    "start": "2025-10-26",
    "end": "2025-11-25",
    "days": 30
  }
}
```

**Кэширование:** 15 минут (900 секунд)

---

## Changelog

### 2025-11-25 - Stage 5 Implementation

**Добавлено:**
- Эндпоинт `/warehouses` - список складов с количеством товаров
- Эндпоинт `/sizes` - список размеров с логической сортировкой
- Эндпоинт `/analytics/summary` - сводная статистика для карточек
- Кэширование для всех новых эндпоинтов

### 2025-11-25 - Stage 2 Implementation

**Добавлено:**
- Поддержка периодов 60d, 90d, 180d в `/analytics/sales`
- Фильтрация по складам в `/stocks/all`
- Фильтрация по размерам в `/stocks/all`
- Поиск по названию и артикулу в `/stocks/all`
- Поле `available_filters` в ответе `/stocks/all`
- Поля `period`, `period_days`, `date_range` в ответе `/analytics/sales`

**Изменено:**
- Период по умолчанию в `/analytics/sales` изменен с `7d` на `30d`
