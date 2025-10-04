# 📘 S2 BOT: Техническое задание для Telegram бота

## 🎯 Цель этапа

Реализовать полнофункциональный Telegram бот для интеграции с Wildberries API, обеспечивающий получение данных через Bot API сервера, отображение аналитики, управление заказами и остатками, а также получение уведомлений в реальном времени.

## ✅ СТАТУС РЕАЛИЗАЦИИ

**Дата начала:** 4 января 2025  
**Готовность:** 15%  
**Статус:** Базовая структура создана, требуется интеграция с Bot API

### 🚀 Что уже реализовано:

#### **✅ Базовая структура:**
- **Основной бот** — инициализация Aiogram 3.x (реализовано)
- **Роутеры** — handlers для команд и регистрации (реализовано)
- **Клавиатуры** — полный набор inline клавиатур (реализовано)
- **API клиент** — базовый клиент для регистрации пользователей (реализовано)
- **Навигация** — система меню и переходов (реализовано)

#### **❌ Требует реализации:**
- **Bot API интеграция** — подключение к эндпоинтам сервера
- **WB кабинет подключение** — ввод и валидация API ключей
- **Обработчики данных** — заказы, остатки, отзывы, аналитика
- **Уведомления** — получение real-time уведомлений
- **Обработка ошибок** — fallback и retry логика
- **Тестирование** — unit и integration тесты

---

## 🏗 Архитектура бота

### Основные компоненты

* **Main Bot** — основная точка входа и конфигурация
* **Handlers** — обработчики команд и callback'ов
* **Keyboards** — inline клавиатуры для навигации
* **API Client** — клиент для взаимодействия с сервером
* **Notification Handler** — обработчик уведомлений от сервера
* **Error Handler** — обработка ошибок и fallback
* **State Manager** — управление состояниями пользователей

### Поток данных

```
User → Bot → API Client → Server Bot API → Server WB API → Database
  ↓
Bot ← Notification Handler ← Webhook ← Server Notification System
```

---

## 📋 Детальный план задач

### 1. 🔌 Bot API интеграция

#### **1.1 Расширение API клиента**
**Файл:** `bot/api/client.py`

**Задачи:**
- Добавить методы для всех Bot API эндпоинтов
- Реализовать аутентификацию через API ключ
- Добавить обработку ошибок и retry логику
- Создать типизированные методы для каждого эндпоинта

**Методы для реализации:**
```python
async def get_dashboard(user_id: int) -> Dict[str, Any]
async def get_recent_orders(user_id: int, limit: int = 10) -> Dict[str, Any]
async def get_order_details(order_id: int) -> Dict[str, Any]
async def get_critical_stocks(user_id: int) -> Dict[str, Any]
async def get_reviews_summary(user_id: int) -> Dict[str, Any]
async def get_analytics_sales(user_id: int, period: str = "7d") -> Dict[str, Any]
async def start_sync(user_id: int) -> Dict[str, Any]
async def get_sync_status(user_id: int) -> Dict[str, Any]
async def connect_wb_cabinet(user_id: int, api_key: str) -> Dict[str, Any]
```

#### **1.2 Конфигурация и настройки**
**Файл:** `bot/core/config.py` (новый)

**Задачи:**
- Создать конфигурацию для Bot API
- Добавить настройки retry и timeout
- Реализовать валидацию конфигурации
- Добавить логирование

---

### 2. 🔑 Подключение WB кабинета

#### **2.1 Обработчик подключения кабинета**
**Файл:** `bot/handlers/wb_cabinet.py` (новый)

**Задачи:**
- Создать FSM для процесса подключения
- Реализовать ввод API ключа
- Добавить валидацию ключа через сервер
- Создать обработчики успеха/ошибки

**Состояния FSM:**
```python
class WBConnectionStates(StatesGroup):
    waiting_for_api_key = State()
    validating_key = State()
    connection_success = State()
    connection_error = State()
```

#### **2.2 Интеграция с настройками**
**Файл:** `bot/handlers/settings.py` (новый)

**Задачи:**
- Реализовать меню настроек
- Добавить управление подключенными кабинетами
- Создать отображение статуса кабинетов
- Добавить возможность отключения кабинетов

---

### 3. 📊 Дашборд и общая информация

#### **3.1 Обработчик дашборда**
**Файл:** `bot/handlers/dashboard.py` (новый)

**Задачи:**
- Реализовать получение данных дашборда
- Создать форматирование для отображения
- Добавить обновление данных по кнопке
- Реализовать обработку ошибок

**Функции:**
```python
async def show_dashboard(callback: CallbackQuery)
async def refresh_dashboard(callback: CallbackQuery)
async def format_dashboard_data(data: Dict[str, Any]) -> str
```

#### **3.2 Интеграция с главным меню**
**Файл:** `bot/handlers/commands.py` (обновить)

**Задачи:**
- Обновить обработчик "connect_wb"
- Добавить проверку подключенных кабинетов
- Реализовать переключение между дашбордом и подключением

---

### 4. 🛒 Обработчики заказов

#### **4.1 Обработчик заказов**
**Файл:** `bot/handlers/orders.py` (новый)

**Задачи:**
- Реализовать отображение последних заказов
- Создать детальный просмотр заказа
- Добавить пагинацию для списка заказов
- Реализовать форматирование отчетов

**Функции:**
```python
async def show_recent_orders(callback: CallbackQuery)
async def show_order_details(callback: CallbackQuery, order_id: int)
async def format_order_list(orders: List[Dict]) -> str
async def format_order_report(order: Dict) -> str
```

#### **4.2 Интеграция с клавиатурами**
**Файл:** `bot/keyboards/keyboards.py` (обновить)

**Задачи:**
- Добавить клавиатуры для заказов
- Реализовать кнопки навигации
- Создать inline кнопки для детального просмотра

---

### 5. 📦 Обработчики остатков

#### **5.1 Обработчик остатков**
**Файл:** `bot/handlers/stocks.py` (новый)

**Задачи:**
- Реализовать отображение критичных остатков
- Создать список всех товаров с остатками
- Добавить фильтрацию по складам
- Реализовать прогноз остатков

**Функции:**
```python
async def show_critical_stocks(callback: CallbackQuery)
async def show_all_stocks(callback: CallbackQuery)
async def show_stock_forecast(callback: CallbackQuery)
async def format_stocks_data(stocks: List[Dict]) -> str
```

#### **5.2 Уведомления об остатках**
**Файл:** `bot/handlers/notifications.py` (новый)

**Задачи:**
- Реализовать получение уведомлений о критичных остатках
- Создать обработчик нулевых остатков
- Добавить настройки уведомлений
- Реализовать группировку уведомлений

---

### 6. ⭐ Обработчики отзывов

#### **6.1 Обработчик отзывов**
**Файл:** `bot/handlers/reviews.py` (новый)

**Задачи:**
- Реализовать отображение новых отзывов
- Создать фильтр критичных отзывов (1-3⭐)
- Добавить просмотр неотвеченных вопросов
- Реализовать статистику отзывов

**Функции:**
```python
async def show_new_reviews(callback: CallbackQuery)
async def show_critical_reviews(callback: CallbackQuery)
async def show_unanswered_questions(callback: CallbackQuery)
async def format_reviews_data(reviews: List[Dict]) -> str
```

#### **6.2 Автоответы (подготовка к S3)**
**Файл:** `bot/handlers/auto_replies.py` (новый)

**Задачи:**
- Создать базовую структуру для автоответов
- Реализовать настройки шаблонов
- Добавить логику определения положительных отзывов
- Подготовить интеграцию с AI (S5)

---

### 7. 📈 Обработчики аналитики

#### **7.1 Обработчик аналитики**
**Файл:** `bot/handlers/analytics.py` (новый)

**Задачи:**
- Реализовать отображение статистики продаж
- Создать графики динамики (текстовые)
- Добавить сравнение периодов
- Реализовать топ товаров

**Функции:**
```python
async def show_sales_analytics(callback: CallbackQuery)
async def show_dynamics(callback: CallbackQuery)
async def show_conversion_rates(callback: CallbackQuery)
async def format_analytics_data(data: Dict) -> str
```

#### **7.2 Экспорт данных (подготовка к S4)**
**Файл:** `bot/handlers/export.py` (новый)

**Задачи:**
- Создать базовую структуру для экспорта
- Реализовать подготовку данных для Google Sheets
- Добавить кнопки экспорта в меню
- Подготовить интеграцию с Google API (S4)

---

### 8. 🔄 Обработчики синхронизации

#### **8.1 Обработчик синхронизации**
**Файл:** `bot/handlers/sync.py` (новый)

**Задачи:**
- Реализовать запуск ручной синхронизации
- Создать отображение статуса синхронизации
- Добавить прогресс-бар (текстовый)
- Реализовать уведомления о завершении

**Функции:**
```python
async def start_manual_sync(callback: CallbackQuery)
async def show_sync_status(callback: CallbackQuery)
async def handle_sync_completion(notification: Dict)
async def format_sync_progress(status: Dict) -> str
```

#### **8.2 Автоматические обновления**
**Файл:** `bot/handlers/auto_updates.py` (новый)

**Задачи:**
- Реализовать периодическое обновление данных
- Создать систему кэширования в боте
- Добавить обновление дашборда
- Реализовать уведомления об изменениях

---

### 9. 🔔 Система уведомлений

#### **9.1 Webhook обработчик**
**Файл:** `bot/handlers/webhook.py` (новый)

**Задачи:**
- Реализовать получение уведомлений от сервера
- Создать обработчики для разных типов уведомлений
- Добавить валидацию webhook'ов
- Реализовать retry логику

**Типы уведомлений:**
```python
async def handle_new_order_notification(notification: Dict)
async def handle_critical_stocks_notification(notification: Dict)
async def handle_new_review_notification(notification: Dict)
async def handle_sync_completion_notification(notification: Dict)
```

#### **9.2 Настройки уведомлений**
**Файл:** `bot/handlers/notification_settings.py` (новый)

**Задачи:**
- Реализовать включение/выключение уведомлений
- Создать настройки частоты уведомлений
- Добавить фильтры по типам уведомлений
- Реализовать тестовые уведомления

---

### 10. ⚠️ Обработка ошибок

#### **10.1 Централизованная обработка ошибок**
**Файл:** `bot/middleware/error_handler.py` (новый)

**Задачи:**
- Создать middleware для обработки ошибок
- Реализовать логирование ошибок
- Добавить fallback сообщения для пользователей
- Создать систему retry для API запросов

**Типы ошибок:**
```python
class BotAPIError(Exception)
class WBConnectionError(Exception)
class NotificationError(Exception)
class ValidationError(Exception)
```

#### **10.2 Graceful degradation**
**Файл:** `bot/utils/fallback.py` (новый)

**Задачи:**
- Реализовать fallback на кэшированные данные
- Создать заглушки для недоступных функций
- Добавить уведомления о временных проблемах
- Реализовать восстановление соединения

---

### 11. 🧪 Тестирование

#### **11.1 Unit тесты**
**Файл:** `bot/tests/unit/` (новая папка)

**Задачи:**
- Создать тесты для всех обработчиков
- Реализовать мокирование API клиента
- Добавить тесты форматирования данных
- Создать тесты навигации

**Тесты для создания:**
```python
test_api_client.py          # Тесты API клиента
test_handlers_orders.py      # Тесты обработчиков заказов
test_handlers_stocks.py      # Тесты обработчиков остатков
test_handlers_reviews.py     # Тесты обработчиков отзывов
test_handlers_analytics.py   # Тесты обработчиков аналитики
test_keyboards.py            # Тесты клавиатур
test_formatters.py           # Тесты форматирования
test_error_handling.py       # Тесты обработки ошибок
```

#### **11.2 Integration тесты**
**Файл:** `bot/tests/integration/` (новая папка)

**Задачи:**
- Создать тесты интеграции с сервером
- Реализовать тесты полного цикла
- Добавить тесты уведомлений
- Создать тесты производительности

---

### 12. 📁 Структура файлов

#### **Новая структура бота:**
```
bot/
├── __main__.py                    ✅ Основной файл (обновить)
├── requirements.txt               ✅ Зависимости (обновить)
├── core/
│   ├── __init__.py
│   ├── config.py                  🔄 Конфигурация
│   └── states.py                  🔄 FSM состояния
├── handlers/
│   ├── __init__.py
│   ├── commands.py                ✅ Команды (обновить)
│   ├── registration.py            ✅ Регистрация (обновить)
│   ├── dashboard.py               🔄 Дашборд
│   ├── wb_cabinet.py              🔄 WB кабинет
│   ├── orders.py                  🔄 Заказы
│   ├── stocks.py                  🔄 Остатки
│   ├── reviews.py                 🔄 Отзывы
│   ├── analytics.py               🔄 Аналитика
│   ├── sync.py                    🔄 Синхронизация
│   ├── settings.py                🔄 Настройки
│   ├── notifications.py           🔄 Уведомления
│   ├── webhook.py                 🔄 Webhook
│   ├── auto_replies.py            🔄 Автоответы
│   ├── export.py                  🔄 Экспорт
│   └── auto_updates.py            🔄 Автообновления
├── keyboards/
│   ├── __init__.py
│   ├── keyboards.py               ✅ Клавиатуры (обновить)
│   ├── orders_keyboards.py        🔄 Клавиатуры заказов
│   ├── stocks_keyboards.py        🔄 Клавиатуры остатков
│   ├── reviews_keyboards.py       🔄 Клавиатуры отзывов
│   └── analytics_keyboards.py     🔄 Клавиатуры аналитики
├── api/
│   ├── __init__.py
│   ├── client.py                  ✅ API клиент (обновить)
│   ├── bot_api_client.py          🔄 Bot API клиент
│   └── webhook_client.py          🔄 Webhook клиент
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py           🔄 Обработка ошибок
│   ├── auth_middleware.py         🔄 Аутентификация
│   └── logging_middleware.py      🔄 Логирование
├── utils/
│   ├── __init__.py
│   ├── formatters.py              🔄 Форматирование
│   ├── validators.py              🔄 Валидация
│   ├── fallback.py                🔄 Fallback логика
│   └── helpers.py                 🔄 Вспомогательные функции
├── tests/
│   ├── __init__.py
│   ├── conftest.py                🔄 Фикстуры
│   ├── unit/                      🔄 Unit тесты
│   └── integration/               🔄 Integration тесты
└── .env.example                   🔄 Пример конфигурации
```

---

## 🔧 Технические требования

### Зависимости

#### **Обновить requirements.txt:**
```
aiogram>=3.0.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
pydantic>=2.0.0
asyncio-mqtt>=0.11.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0
```

### Конфигурация

#### **Переменные окружения (.env):**
```
BOT_TOKEN=your_telegram_bot_token
SERVER_HOST=http://127.0.0.1:8000
API_SECRET_KEY=your_api_secret_key
WEBHOOK_URL=http://your-bot-url/webhook
WEBHOOK_SECRET=your_webhook_secret
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379
```

### Производительность

#### **Цели:**
- **Время ответа:** < 2 секунды для всех команд
- **Память:** < 100MB для бота
- **Надежность:** 99% uptime
- **Масштабируемость:** поддержка 1000+ пользователей

---

## 📊 Контрольные точки

### Функциональность

* ❌ **Bot API интеграция** — подключение к эндпоинтам сервера
* ❌ **WB кабинет подключение** — ввод и валидация API ключей
* ❌ **Дашборд** — отображение общей информации по кабинету
* ❌ **Заказы** — просмотр последних заказов и детальных отчетов
* ❌ **Остатки** — отображение критичных остатков и прогнозов
* ❌ **Отзывы** — просмотр новых отзывов и вопросов
* ❌ **Аналитика** — статистика продаж и динамика
* ❌ **Синхронизация** — ручная и автоматическая синхронизация
* ❌ **Уведомления** — получение real-time уведомлений
* ❌ **Обработка ошибок** — fallback и retry логика

### Производительность

* ❌ **Время ответа** — < 2 секунды для всех команд
* ❌ **Надежность** — обработка ошибок и fallback
* ❌ **Масштабируемость** — поддержка множественных пользователей
* ❌ **Кэширование** — локальное кэширование данных

### Тестирование

* ❌ **Unit тесты** — покрытие 80%+ кода
* ❌ **Integration тесты** — тесты с реальным сервером
* ❌ **E2E тесты** — полный цикл пользователя
* ❌ **Performance тесты** — нагрузочное тестирование

---

## 🎯 Результат этапа

* ✅ **Полнофункциональный бот** для работы с WB кабинетом
* ✅ **Интеграция с Bot API** сервера
* ✅ **Real-time уведомления** о новых заказах и остатках
* ✅ **Детальные отчеты** заказов в формате Telegram
* ✅ **Управление кабинетами** и настройками
* ✅ **Надежная система** с обработкой ошибок
* ✅ **Готовность к S3** — уведомления и автоответы
* ✅ **Готовность к S4** — интеграция с Google Sheets
* ✅ **Готовность к S5** — AI-ассистент и аналитика

## 📝 Приоритеты реализации

### **Высокий приоритет (неделя 1):**
1. Bot API интеграция
2. WB кабинет подключение
3. Дашборд
4. Обработчики заказов

### **Средний приоритет (неделя 2):**
5. Обработчики остатков
6. Обработчики отзывов
7. Обработчики аналитики
8. Синхронизация

### **Низкий приоритет (неделя 3):**
9. Система уведомлений
10. Обработка ошибок
11. Тестирование
12. Оптимизация

---

*Последнее обновление: 4 января 2025*
*Версия: 1.0*
*Статус: В разработке*
