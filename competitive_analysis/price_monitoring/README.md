# Модуль мониторинга цен конкурентов

Модуль для автоматизированного мониторинга цен конкурентов с интеграцией Google Sheets API, анализом ценовых стратегий и системой уведомлений.

## Возможности

- 🔍 **Мониторинг цен конкурентов** - автоматический сбор и анализ ценовой информации
- 📊 **Интеграция с Google Sheets** - создание и управление таблицами для отчетности
- 📈 **Анализ ценовых стратегий** - расчет рекомендаций по ценообразованию
- 🔔 **Система уведомлений** - оповещения о значительных изменениях цен
- ⚙️ **Гибкая конфигурация** - настройка параметров мониторинга и интеграций
- 🧪 **Полное тестовое покрытие** - unit и интеграционные тесты

## Структура проекта

```
price_monitoring/
├── __init__.py                 # Основной модуль
├── config/                     # Конфигурация
│   ├── __init__.py
│   ├── settings.py            # Настройки модуля
│   └── config.json            # Файл конфигурации
├── core/                      # Основные компоненты
│   ├── __init__.py
│   └── google_sheets_client.py # Клиент Google Sheets API
├── models/                    # Модели данных
│   ├── __init__.py
│   └── product.py            # Модель продукта
├── utils/                     # Утилиты
│   ├── __init__.py
│   └── auth_helper.py        # Помощник аутентификации
├── templates/                 # Шаблоны отчетов
│   └── __init__.py
├── tests/                     # Тесты
│   ├── __init__.py
│   ├── test_google_sheets_client.py
│   ├── test_auth_helper.py
│   ├── test_models.py
│   ├── test_settings.py
│   └── test_integration.py
├── requirements.txt           # Зависимости
└── README.md                 # Документация
```

## Установка

1. **Клонирование и установка зависимостей:**
```bash
cd competitive_analysis/price_monitoring
pip install -r requirements.txt
```

2. **Настройка Google Sheets API:**
   - Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
   - Создайте новый проект или выберите существующий
   - Включите Google Sheets API и Google Drive API
   - Создайте учетные данные OAuth 2.0
   - Скачайте файл `credentials.json` в папку `config/`

3. **Конфигурация модуля:**
```python
from config.settings import Settings

# Создание настроек с пользовательскими параметрами
settings = Settings(config_dir='path/to/config')
settings.monitoring.update_interval_hours = 6
settings.notifications.email_enabled = True
settings.save_config()
```

## Быстрый старт

### 1. Базовое использование

```python
from price_monitoring import GoogleSheetsClient, Product
from utils.auth_helper import AuthHelper
from config.settings import get_settings

# Загрузка настроек
settings = get_settings()

# Инициализация аутентификации
auth_helper = AuthHelper(
    credentials_file=str(settings.get_credentials_path()),
    token_file=str(settings.get_token_path()),
    scopes=settings.google_sheets.scopes
)

# Создание клиента Google Sheets
client = GoogleSheetsClient(auth_helper=auth_helper)

# Создание продукта для мониторинга
product = Product(
    id="PROD001",
    name="iPhone 15 Pro",
    brand="Apple",
    current_price=99990.0,
    competitor_prices=[95000.0, 102000.0, 98500.0]
)

# Анализ ценовой позиции
recommendations = product.get_pricing_recommendations()
print(f"Рекомендация: {recommendations['action']}")
print(f"Рекомендуемая цена: {recommendations['recommended_price']}")
```

### 2. Работа с Google Sheets

```python
# Создание новой таблицы
spreadsheet = client.create_spreadsheet("Мониторинг цен - Январь 2024")
spreadsheet_id = spreadsheet['spreadsheetId']

# Запись заголовков
headers = Product.get_sheets_headers()
client.update_values(
    spreadsheet_id=spreadsheet_id,
    range_name='A1:J1',
    values=[headers]
)

# Запись данных о продуктах
products = [product1, product2, product3]  # Ваши продукты
product_rows = [p.to_sheets_row() for p in products]
client.update_values(
    spreadsheet_id=spreadsheet_id,
    range_name='A2:J4',
    values=product_rows
)

# Чтение данных
data = client.read_values(
    spreadsheet_id=spreadsheet_id,
    range_name='A1:J10'
)
```

### 3. Пакетные операции

```python
# Пакетное обновление для большого количества продуктов
batch_data = []
for i, product in enumerate(products):
    batch_data.append({
        'range': f'A{i+2}:J{i+2}',
        'values': [product.to_sheets_row()]
    })

result = client.batch_update_values(
    spreadsheet_id=spreadsheet_id,
    value_input_data=batch_data
)

print(f"Обновлено строк: {result['totalUpdatedRows']}")
```

## Конфигурация

### Основные настройки

```python
# config/settings.py
settings = Settings()

# Google Sheets API
settings.google_sheets.application_name = "My Price Monitor"
settings.google_sheets.batch_size = 100
settings.google_sheets.request_timeout = 30

# Мониторинг
settings.monitoring.update_interval_hours = 6
settings.monitoring.price_change_threshold_percent = 5.0
settings.monitoring.enable_notifications = True

# Уведомления
settings.notifications.email_enabled = True
settings.notifications.email_recipients = ["admin@company.com"]
settings.notifications.telegram_enabled = False

# Сохранение настроек
settings.save_config()
```

### Переменные окружения

Вы можете использовать переменные окружения для конфигурации:

```bash
export GOOGLE_SHEETS_APPLICATION_NAME="Production Price Monitor"
export MONITORING_UPDATE_INTERVAL_HOURS=4
export NOTIFICATIONS_EMAIL_ENABLED=true
export NOTIFICATIONS_EMAIL_RECIPIENTS="admin@company.com,manager@company.com"
```

## API Reference

### GoogleSheetsClient

Основной класс для работы с Google Sheets API.

```python
class GoogleSheetsClient:
    def __init__(self, auth_helper: AuthHelper, application_name: str = None)
    
    def create_spreadsheet(self, title: str) -> dict
    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict
    def read_values(self, spreadsheet_id: str, range_name: str) -> list
    def update_values(self, spreadsheet_id: str, range_name: str, values: list) -> dict
    def batch_update_values(self, spreadsheet_id: str, value_input_data: list) -> dict
    def batch_get_values(self, spreadsheet_id: str, ranges: list) -> list
```

### Product

Модель продукта для анализа цен.

```python
class Product:
    def __init__(self, id: str, name: str, brand: str, current_price: float, 
                 competitor_prices: list = None)
    
    # Анализ цен
    def get_min_competitor_price(self) -> float
    def get_max_competitor_price(self) -> float
    def get_average_competitor_price(self) -> float
    def get_median_competitor_price(self) -> float
    def get_price_position(self) -> str
    def is_price_competitive(self, threshold_percent: float = 10.0) -> bool
    def get_pricing_recommendations(self) -> dict
    
    # Управление данными
    def add_competitor_price(self, price: float)
    def remove_competitor_price(self, price: float)
    def update_current_price(self, new_price: float)
    
    # Сериализация
    def to_dict(self) -> dict
    def from_dict(cls, data: dict) -> 'Product'
    def to_json(self) -> str
    def from_json(cls, json_str: str) -> 'Product'
    def to_sheets_row(self) -> list
    def get_sheets_headers(cls) -> list
```

### AuthHelper

Помощник для OAuth 2.0 аутентификации.

```python
class AuthHelper:
    def __init__(self, credentials_file: str, token_file: str, scopes: list = None)
    
    def get_credentials(self) -> Credentials
    def save_credentials(self, credentials: Credentials)
    def refresh_credentials(self) -> Credentials
    def revoke_credentials(self)
    def get_sheets_service(self) -> Resource
    def get_drive_service(self) -> Resource
    def test_connection(self) -> bool
```

## Тестирование

Запуск всех тестов:

```bash
cd price_monitoring
python -m pytest tests/ -v
```

Запуск конкретного теста:

```bash
python -m pytest tests/test_google_sheets_client.py -v
```

Запуск с покрытием кода:

```bash
python -m pytest tests/ --cov=. --cov-report=html
```

## Примеры использования

### Анализ конкурентоспособности

```python
# Создание продукта
product = Product(
    id="LAPTOP001",
    name="MacBook Pro 14\"",
    brand="Apple",
    current_price=199990.0,
    competitor_prices=[189990.0, 205000.0, 195000.0, 210000.0]
)

# Получение статистики
print(f"Минимальная цена конкурентов: {product.get_min_competitor_price()}")
print(f"Средняя цена конкурентов: {product.get_average_competitor_price()}")
print(f"Позиция по цене: {product.get_price_position()}")

# Проверка конкурентоспособности
if product.is_price_competitive(threshold_percent=5.0):
    print("Цена конкурентоспособна")
else:
    recommendations = product.get_pricing_recommendations()
    print(f"Рекомендация: {recommendations['action']}")
    print(f"Новая цена: {recommendations['recommended_price']}")
```

### Массовая обработка продуктов

```python
# Загрузка продуктов из Google Sheets
data = client.read_values(spreadsheet_id, 'A2:J100')

products = []
for row in data:
    if len(row) >= 10:  # Проверяем наличие всех колонок
        product = Product(
            id=row[0],
            name=row[1],
            brand=row[2],
            current_price=float(row[3]),
            competitor_prices=json.loads(row[4]) if row[4] else []
        )
        products.append(product)

# Анализ всех продуктов
for product in products:
    recommendations = product.get_pricing_recommendations()
    if recommendations['action'] != 'maintain':
        print(f"{product.name}: {recommendations['action']} -> {recommendations['recommended_price']}")
```

## Лицензия

MIT License

## Поддержка

Для вопросов и предложений создавайте issues в репозитории проекта.