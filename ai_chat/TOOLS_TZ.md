# ТЗ: Инструменты (function calling) для AI Chat Service

## Цель
Реализовать набор инструментов (function calling) для AI‑ассистента, чтобы он самостоятельно получал данные из БД/сервисов и выполнял базовую аналитику без участия пользователя.

## Объем работ
- Агентный цикл в `/v1/chat/send` с поддержкой инструментов.
- 6 инструментов: `get_dashboard`, `run_report`, `run_sql_template`, `get_sales_timeseries`, `compute_kpis`, `forecast_sales`.
- Слой БД с allowlist SQL‑шаблонов, пулом и таймаутами.
- Кэш 5–15 минут, логи, тесты, критерии приемки.

## Архитектура
- Агент вызывает модель с `tools`; при `tool_calls` — выполняет инструменты, возвращает результат модели и получает финальный ответ.
- Безопасность: SQL только по белому списку с параметрами; проверка доступа по `telegram_id`; таймауты/лимиты.

## Реестр инструментов (JSON Schema)
```python
registry = [
    {"type":"function","function":{"name":"get_dashboard","description":"Сводка: выручка, заказы, AOV, рейтинг, негатив, остатки.","parameters":{"type":"object","properties":{"telegram_id":{"type":"integer","minimum":1},"period":{"type":"string","default":"7d","enum":["7d","14d","30d","90d"]}},"required":["telegram_id"]}}},
    {"type":"function","function":{"name":"run_report","description":"Предопределенные отчеты (топы, просадки, маржинальность, отзывы, реклама).","parameters":{"type":"object","properties":{"report_name":{"type":"string","enum":["top_products","decliners","margins","reviews","ad_performance"]},"params":{"type":"object","additionalProperties":true}},"required":["report_name","params"]}}},
    {"type":"function","function":{"name":"run_sql_template","description":"SQL-шаблон из allowlist с параметрами.","parameters":{"type":"object","properties":{"name":{"type":"string","enum":["timeseries_sales","top_products_by_revenue","orders_summary","stock_levels","neg_reviews_agg"]},"params":{"type":"object","additionalProperties":true}},"required":["name","params"]}}},
    {"type":"function","function":{"name":"get_sales_timeseries","description":"Таймсерия продаж (qty, revenue).","parameters":{"type":"object","properties":{"telegram_id":{"type":"integer","minimum":1},"period":{"type":"string","default":"30d","enum":["7d","14d","30d","90d","180d"]},"granularity":{"type":"string","default":"day","enum":["day","week"]}},"required":["telegram_id"]}}},
    {"type":"function","function":{"name":"compute_kpis","description":"KPI по области (all/sku/category) и периоду.","parameters":{"type":"object","properties":{"kpi_list":{"type":"array","items":{"type":"string","enum":["revenue","orders","aov","conversion","roas","margin"]},"minItems":1},"scope":{"type":"object","properties":{"level":{"type":"string","enum":["all","sku","category"],"default":"all"},"sku_id":{"type":"integer"},"category_id":{"type":"integer"},"telegram_id":{"type":"integer","minimum":1}},"required":["level","telegram_id"]},"period":{"type":"string","default":"7d","enum":["7d","14d","30d","90d"]}},"required":["kpi_list","scope","period"]}}},
    {"type":"function","function":{"name":"forecast_sales","description":"Прогноз продаж/спроса.","parameters":{"type":"object","properties":{"telegram_id":{"type":"integer","minimum":1},"sku_id":{"type":"integer"},"horizon":{"type":"integer","default":14,"minimum":7,"maximum":60},"method":{"type":"string","default":"auto","enum":["auto","sma","prophet","arima"]},"include_ci":{"type":"boolean","default":true}},"required":["telegram_id"]}}}
]
```

## Контракты ответов (примеры)
```json
{"period":"7d","orders":0,"revenue":0,"aov":0,"stocks_total":0,"avg_rating":0,"neg_reviews":0,"notes":[]}
```
```json
{"report":"top_products","period":"7d","items":[{"sku_id":0,"name":"","revenue":0,"qty":0,"share":0,"wow":0}]}
```
```json
[{"d":"2025-10-01","qty":0,"revenue":0}]
```
```json
{"granularity":"day","series":[{"date":"2025-10-01","qty":0,"revenue":0}],"wow":0}
```
```json
{"period":"7d","scope":{"level":"sku","sku_id":0},"kpis":{"revenue":0,"orders":0,"aov":0,"conversion":0,"roas":0,"margin":0}}
```
```json
{"horizon":14,"level":"sku","sku_id":0,"forecast":[{"date":"2025-10-31","qty":0,"ci_low":0,"ci_high":0}],"method":"auto"}
```

## Слой БД
- Пул `asyncpg` с таймаутами; строгая параметризация; только allowlist шаблонов.
- Примеры SQL:
```sql
SELECT date_trunc($3, sale_date)::date AS d, SUM(qty) qty, SUM(revenue) revenue
FROM sales
WHERE telegram_id = $1 AND sale_date >= CURRENT_DATE - $2::interval
GROUP BY d ORDER BY d;
```

## Кэш/таймауты/логи/безопасность
- Кэш 5–15 минут для частых вызовов; таймауты 10–30 сек; ограничение размера ответа.
- Логи: инструмент, аргументы (без PII), длительность, строки, статус; аудит ошибок.
- Доступ по `telegram_id`; валидация `period/granularity/horizon`; отказ для неизвестных шаблонов/отчетов.

## Тесты и критерии приемки
- Юнит‑тесты: маппинг SQL‑параметров, KPI/прогнозы на фикстурах.
- Интеграционные: agent loop (tool_calls → исполнение → финальный ответ).
- Приемка: корректные tool_calls, ответы с цифрами и рекомендациями; SLA P50<2.5с/P95<8с; отсутствие SQL‑инъекций.

## Этапы разработки (по спринтам)

### Этап 0 — Подготовка (0.5 спринта)
- Определить доступ к БД, переменные окружения, ключи LLM.
- Добавить каркас `ai_chat/tools/` и `ai_chat/agent.py` без реализации.
- Готовность: приложение стартует, тесты-заглушки проходят.

### Этап 1 — Базовые инструменты и агент (1 спринт)
- Реализовать агентный цикл в `/v1/chat/send` с `tools`.
- Инструменты: `get_dashboard`, `get_sales_timeseries` (с простыми SQL/кешем).
- Пул БД, таймауты, базовые логи.
- Приемка: чат отвечает цифрами по сводке и трендам; P50<2.5с.

### Этап 2 — Отчеты и SQL allowlist (1 спринт)
- Инструменты: `run_report` (top/decliners), `run_sql_template` (allowlist + маппинг параметров).
- Добавить 3–5 SQL-шаблонов: `timeseries_sales`, `top_products_by_revenue`, `orders_summary`, `stock_levels`, `neg_reviews_agg`.
- Кэш 5–15 минут для отчётов.
- Приемка: корректные ответы по топам/просадкам, защита от инъекций.

### Этап 3 — KPI и диагностика (0.5–1 спринт)
- Инструмент: `compute_kpis` (revenue, orders, AOV, conversion, ROAS, margin) для `all/sku/category`.
- Сравнение WoW и краткие выводы.
- Приемка: ответы на «почему просела выручка?» с разложением по KPI.

### Этап 4 — Прогноз и дозаказ (1 спринт)
- Инструмент: `forecast_sales` (horizon 14–30, method=auto, CI) и расчёт дозаказа в отчётах.
- Интеграция остатков (days_to_oos), рекомендации по пополнению.
- Приемка: план дозаказа по SKU с цифрами и допущениями.

### Этап 5 — UX и экспорт (0.5 спринта)
- Рендер табличек/мини‑графиков, экспорт CSV/XLSX.
- Короткие шаблоны рекомендаций в ответах.
- Приемка: ответы удобны для копирования/экспорта.

### Этап 6 — Проактивность и планировщик (1 спринт)
- Алёрты (низкие остатки, просадки), расписание отчетов.
- Создание задач (hook в ваш трекер/бота).
- Приемка: автоматические сообщения по условиям, задания создаются.

### Этап 7 — Безопасность и аудит (0.5 спринта)
- Роли/доступы по `telegram_id`, маскирование PII.
- Аудит вызовов инструментов, rate limiting.
- Приемка: логи без PII, доступы ограничены.

### Этап 8 — Производительность и стабильность (0.5 спринта)
- Оптимизация SQL/индексов, расширение кэша, ретраи/фьюзы.
- Наблюдаемость: метрики SLA, алерты ошибок.
- Приемка: P95<8с стабильно, fallback‑стратегии работают.

### Этап 9 — E2E и релиз (0.5 спринта)
- Полный тестовый прогон сценариев: «как улучшить продажи», «топ 7д», «просадки».
- Документация и handover.
- Приемка: сценарии проходят, команда подтверждает готовность.
