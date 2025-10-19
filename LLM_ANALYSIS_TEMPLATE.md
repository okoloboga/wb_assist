# LLM Аналитика: шаблон для обработки сводок из БД

Цель: использовать LLM (GPT) для анализа сводок данных из БД, генерации компактной сводки и практических рекомендаций. Шаблон оптимизирован для устойчивого парсинга LLM и дальнейшей интеграции в Telegram и Google Sheets.

---

## Как использовать
- Заполните секцию DATA (пример ниже) актуальными сводками из БД.
- Передайте LLM секции SYSTEM, DATA и TASKS как единый prompt.
- Ожидайте ответ строго в формате OUTPUT_JSON и OUTPUT_TG, соблюдая описанные схемы и правила.

---

## SYSTEM
Вы — аналитик e‑commerce проекта, который:
- Анализирует сводки продаж, рекламы, остатков, отзывов и конкурентов.
- Выявляет тренды и аномалии с краткими причинами.
- Формирует рекомендации с ожидаемым эффектом и приоритетом (P0/P1/P2).
- Пишет кратко, ясно, по делу. Язык: русский.
- Не добавляет дисклеймеры, не «рассуждает» вслух — только выводы и действия.
- Учитывает, что фронт использует Telegram MarkdownV2 (см. правила в OUTPUT_TG_GUIDE).

---

## DATA
Формат входных данных — JSON-объект сводки из БД.

```json
{
  "meta": {
    "date_range": "2025-10-01..2025-10-07",
    "timezone": "Europe/Moscow",
    "currency": "RUB",
    "source": "db_summary_v1"
  },
  "sales": {
    "orders_count": 154,
    "revenue": 1250000.50,
    "avg_order_value": 8105.85,
    "conversion_rate": 2.9,
    "returns_count": 12,
    "returns_rate": 7.8
  },
  "ads": {
    "spend": 230000,
    "impressions": 1200000,
    "clicks": 45000,
    "ctr": 3.75,
    "cpc": 5.11,
    "roas": 3.2
  },
  "inventory": {
    "total_stock": 1540,
    "stockouts_products": ["SKU-1011", "SKU-2033"],
    "low_stock_products": ["SKU-3001", "SKU-3002", "SKU-4004"],
    "replenishment_needed": 12
  },
  "reviews": {
    "new_reviews_count": 48,
    "avg_rating": 4.4,
    "negative_reviews": [
      { "product_id": "SKU-3002", "rating": 2, "text": "качество упаковки плохое" }
    ],
    "unanswered_questions": 7
  },
  "prices": {
    "changes_count": 15,
    "changed_products": [
      { "product_id": "SKU-2001", "old_price": 1499, "new_price": 1599, "competitor_gap": -3.5 }
    ]
  },
  "competitors": {
    "tracked_count": 42,
    "anomalies": [
      { "competitor_id": "C-77", "product_id": "SKU-2001", "price_diff_percent": -12.0, "severity": "high" }
    ]
  },
  "top_products": [
    { "id": "SKU-1001", "name": "Топовый товар A", "revenue": 235000, "qty": 320, "margin": 0.32, "trend": "up" }
  ],
  "slow_products": [
    { "id": "SKU-3002", "name": "Медленный товар B", "revenue": 4500, "qty": 6, "stock": 85, "age_days": 120, "reason_hint": "низкий рейтинг, высокая цена" }
  ]
}
```

---

## TASKS
1) Проверь целостность и диапазоны данных (пропуски, некорректные значения).
2) Определи ключевые метрики и тренды (рост/падение, стабильность).
3) Выяви аномалии (всплески, провалы, необычные соотношения).
4) Сформируй инсайты с краткими причинами (drivers: цена, остатки, реклама, отзывы, конкуренция).
5) Сгенерируй рекомендации (действие, причина, приоритет, ожидаемый эффект, теги).
6) Подготовь Telegram‑сводку (MarkdownV2) и структуру для JSON/Sheets.

---

## OUTPUT_JSON_SCHEMA
Ответ должен быть ОДНИМ JSON-объектом строго по схеме ниже.

```json
{
  "meta": {
    "date_range": "string",
    "generated_at": "ISO-8601 datetime",
    "source": "string",
    "currency": "string"
  },
  "key_metrics": [
    { "name": "string", "value": "number", "unit": "string", "delta": "number|null", "trend": "up|down|flat" }
  ],
  "anomalies": [
    { "metric": "string", "severity": "low|medium|high|critical", "description": "string", "confidence": "number(0..1)" }
  ],
  "insights": [
    { "text": "string", "driver": "price|stock|ads|reviews|competition|other" }
  ],
  "recommendations": [
    {
      "action": "string",
      "reason": "string",
      "priority": "P0|P1|P2",
      "expected_impact": { "metric": "string", "delta": "number", "unit": "string" },
      "tags": ["string"]
    }
  ],
  "telegram": {
    "mdv2": "string",
    "chunks": ["string"],
    "character_count": "number"
  },
  "sheets": {
    "headers": ["Дата", "Метрика", "Значение", "Ед.", "Тренд/Δ", "Категория", "Приоритет", "Рекомендация"],
    "rows": [
      ["2025-10-01..2025-10-07", "Выручка", 1250000.5, "₽", "+3.2%", "sales", "—", "—"]
    ]
  }
}
```

Требования:
- Заполняй все поля; если данных нет — ставь `null` или пустой список.
- `telegram.mdv2` — полноценный текст (не более 4096 символов на блок до разбиения).
- `telegram.chunks` — логически разбитые куски mdv2 (для отправки в нескольких сообщениях).
- `sheets.rows` — компактные строки, готовые к записи в Google Sheets.

---

## OUTPUT_TG_GUIDE (MarkdownV2)
Правила формирования Telegram MarkdownV2:
- Экранируй символы: `_ * [ ] ( ) ~ \` > # + - = | { } . !`.
- Заголовки: используем `*…*` для жирного, не применяем `#`.
- Структура сообщения:
  - Блок 1: заголовок и ключевые метрики.
  - Блок 2: аномалии и инсайты.
  - Блок 3: рекомендации (списком, с приоритетами).
- Пример шаблона:


Этапы разработки 
Этап 1 — Подготовка

- Уточнить цели: источники БД, типы сводок, целевые каналы (Telegram, Sheets).
- Настроить конфигурацию LLM: ключи и параметры в bot/core/config.py , обновить bot/env_example.txt .
- Создать и заполнить LLM-шаблон: c:\Users\Lenovo\Desktop\wb_assist\LLM_ANALYSIS_TEMPLATE.md (SYSTEM/DATA/TASKS/SCHEMA).
- Оформить рабочую ветку gpt_integration , провести первичный коммит и проверку зависимостей ( openai ).
Этап 2 — Интеграция GPT в боте

- Добавить хендлеры: /gpt , ai_chat (кнопка), /exit ; состояние GPTStates.gpt_chat и GPTClient .
- Зарегистрировать роутер: импорт gpt_router в bot/__main__.py , включение в Dispatcher .
- Подключить утилиты форматирования: escape_markdown_v2 и split_telegram_message в bot/utils/formatters.py .
- Обновить зависимости: openai>=2.5.0 в bot/requirements.txt , проверить совместимость и импорт.
Этап 3 — Аналитический пайплайн LLM

- Сформировать DATA: агрегировать метрики из БД (sales, ads, inventory, reviews, prices, competitors) в единый JSON.
- Собрать prompt: секции SYSTEM + DATA + TASKS из шаблона, обеспечить стабильную структуру.
- Вызвать LLM и распарсить ответ: валидировать по OUTPUT_JSON_SCHEMA , логировать несоответствия.
- Подготовить каналы: собрать telegram.mdv2/chunks/character_count и sheets.headers/rows для доставки.
Этап 4 — Вывод и интеграции

- Telegram: экранировать MarkdownV2 и отправить chunks последовательно, контролировать лимиты и ошибки.
- Google Sheets: маппинг rows на диапазоны, обновление таблиц, отчёт об успешной записи.
- UI-навигация: добавить кнопки “❓ Примеры запросов” и “📤 Выгрузка анализа в Google Sheets”.
- Обработка ошибок: понятные сообщения пользователю, fallback при недоступности LLM или данных.
Этап 5 — Тестирование, наблюдаемость, релиз

- Тесты: unit для форматтеров и маппинга, интеграционные для хендлеров и пайплайна (моки GPTClient ).
- Мониторинг: логирование таймаутов/ошибок LLM, метрики качества (валидация схемы, доля успешных выгрузок).
- Документация: обновить bot/README.md и docs/S3.md сценариями использования и ограничениями.
- Релиз: CI/CD, безопасность ключей, rate limiting в middleware, выпуск ветки gpt_integration и обратная связь.

Архитектура данного этапа 
llm_service/

- app/
  - main.py
  - api/
    - routes/
      - analyze.py
      - chat.py
  - core/
    - config.py
    - rate_limit.py
    - cache.py
    - logging.py
  - services/
    - llm/
      - client.py
      - providers/
        - openai.py
      - prompts/
        - analysis.md
      - pipeline.py
    - formatters/
      - telegram.py
      - sheets.py
  - schemas/
    - analysis.py
    - common.py
  - utils/
- tests/
  - unit/
  - integration/
- Dockerfile
- requirements.txt