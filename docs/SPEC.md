### 1. 📘 Общая информация

* **Название проекта:** AI Telegram Bot для продавцов маркетплейсов (MVP для Wildberries)
* **Цель проекта:** ...
* **Целевая аудитория:** ...
* **Основная ценность (Value Proposition):** ...

(Здесь можно оставить краткое резюме из твоего ТЗ.)

---

### 2. 💡 Архитектурное видение

* **Основной стек:** `Aiogram`, `FastAPI`, `PostgreSQL`, `Redis`, `Docker`
* **Интеграции:** `WB API`, `Google Sheets API`, `OpenAI API`, `MJ API`
* **Деплой:** Docker-compose / VPS / CI-CD
* **Архитектурный паттерн:** microservice-style / modular monolith
* **Тестирование:** TDD, `pytest`, `pytest-asyncio`
* **ORM:** SQLAlchemy + Alembic (миграции)
* **Кэширование:** Redis
* **Асинхронность:** asyncio

---

### 3. ⚙️ Архитектура (high-level)

#### 3.1. Модули системы

* `core.bot` — Telegram интерфейс (Aiogram)
* `core.api` — REST API на FastAPI (для внутренних и внешних вызовов)
* `core.scheduler` — фоновый воркер (Celery/Asyncio)
* `core.db` — база данных
* `core.cache` — Redis
* `core.integrations` — клиенты API (WB, Google Sheets, OpenAI, MJ)
* `core.analytics` — модуль аналитики (AI, статистика)
* `core.users` — система аутентификации и ролей

#### 3.2. Потоки данных

* `Telegram` → `Bot` → `API` → `DB`
* `Scheduler` → `WB API` → `DB` → уведомления в `Telegram`
* `AI` → получает данные из `DB` → возвращает текст/аналитику в чат
* `Google Sheets` ↔ `API` ↔ `DB`

---

### 4. 🧩 Подсистемы и требования

#### 4.1. Пользователи и доступ

* **Сущности:** User, Shop, APIKey
* **Регистрация:** по Telegram ID
* **Авторизация:** Telegram ID → User
* **Связка с WB API:** один или несколько кабинетов на пользователя
* **Доступы:** равные в MVP, ACL позже

📌 *Тест-кейсы (TDD):*

* `test_user_registration`
* `test_add_api_key`
* `test_list_shops_by_user`

---

#### 4.2. Интеграция с Wildberries API *(Этап 2)*

* **Методы:** товары, заказы, остатки, цены, отзывы.
* **Интервалы обновления:** каждые 5 мин (Redis TTL)
* **Обработка ошибок:** retry + fallback cache
* **Формат хранения:** JSON → PostgreSQL (таблицы: `orders`, `reviews`, `stocks`, `prices`)
* **Настройка:** `/settings` → 🔑 Вставить API-ключ

📌 *Тест-кейсы (TDD):*

* `test_wb_auth_valid_key`
* `test_wb_orders_sync`
* `test_wb_reviews_sync`
* `test_wb_cache_fallback`

---

#### 4.3. Система уведомлений *(Этап 3)*

* **Типы уведомлений:**

  * Заказы (новые)
  * Отзывы (новые, 1–3★)
  * Остатки (ниже порога)
  * Слоты отгрузки
* **Частота:** каждые 5 минут
* **Настройки:** в профиле (`/settings → notifications`)
* **Хранилище:** Redis pub/sub
* **UI:** inline кнопки «отключить», «подробнее»

📌 *Тест-кейсы (TDD):*

* `test_new_order_notification`
* `test_low_stock_alert`
* `test_toggle_notifications`

---

#### 4.4. Google Sheets интеграция *(Этап 4)*

* **Авторизация:** OAuth 2.0
* **Шаблон:** предустановленный Google Sheet (вкладки: Orders, Reviews, Stocks)
* **Настройка:** вставка ID + Token
* **Данные:** экспорт заказов, остатков, отзывов
* **Расписание:** по команде или cron (раз в день)

📌 *Тест-кейсы (TDD):*

* `test_sheet_auth`
* `test_sheet_export_orders`
* `test_sheet_export_reviews`

---

#### 4.5. AI-модуль *(Этап 5)*

* **Функции:**

  * GPT-чат с лимитом (30 запросов)
  * Аналитика по данным (команда `/digest`)
  * Генерация текстов карточек
* **Контроль лимитов:** Redis counters
* **Интеграция:** OpenAI API
* **Контекст:** данные из DB (последние продажи, отзывы, остатки)
* **UI:** inline кнопки: примеры, выгрузка в GSheets

📌 *Тест-кейсы (TDD):*

* `test_chat_gpt_limit`
* `test_digest_ai_analysis`
* `test_generate_product_texts`

---

#### 4.6. Управление отзывами *(Этап 6)*

* **Функции:**

  * Уведомления о новых
  * Автоответы (4–5★)
  * Шаблоны ответов
* **AI-ответ:** шаблон или GPT
* **Хранилище:** таблица `reviews`

📌 *Тест-кейсы (TDD):*

* `test_review_notification`
* `test_auto_reply_positive`
* `test_no_auto_reply_negative`

---

#### 4.7. Генерация изображений *(Этап 7)*

* **API:** MJ / SD
* **Типы:**

  * Lifestyle
  * Инфографика
* **Хранилище:** локально / S3
* **История:** таблица `images`

📌 *Тест-кейсы (TDD):*

* `test_generate_lifestyle_image`
* `test_generate_infographic`
* `test_image_history`

---

#### 4.8. Мониторинг цен и конкурентов *(Этап 8)*

* **Ввод:** артикул / бренд
* **Сравнение:** текущая цена vs конкуренты
* **Уведомления:** об изменении
* **История:** таблица `price_history`

📌 *Тест-кейсы (TDD):*

* `test_add_competitor_item`
* `test_compare_prices`
* `test_price_change_alert`

---

### 5. 🧠 TDD Подход

Для каждого модуля:

* Создаём `tests/` с юнитами до написания логики.
* Используем `pytest-asyncio` для асинхронных функций.
* Покрытие не менее **80%**.
* Snapshot тесты для AI-ответов и шаблонов.

