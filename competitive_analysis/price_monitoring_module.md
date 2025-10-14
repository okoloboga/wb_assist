# Модуль "Цены и конкуренты" - Техническая спецификация

## 📊 Обзор модуля

Модуль предназначен для мониторинга цен конкурентов и анализа рекламных ставок на маркетплейсах. Включает автоматизированное отслеживание изменений цен, уведомления и детальную аналитику через Google Sheets.

## 🎯 Основные функции

### 1. Мониторинг цен конкурентов

#### 1.1 Ручной ввод товаров для отслеживания
- **Ввод по бренду**: поиск всех товаров определенного бренда
- **Ввод по артикулу**: точное отслеживание конкретного товара
- **Массовый импорт**: загрузка списка товаров из файла
- **Категорийный поиск**: мониторинг по категориям товаров

#### 1.2 Система уведомлений
- **Мгновенные уведомления**: при изменении цены более чем на заданный процент
- **Ежедневные сводки**: общий отчет по всем отслеживаемым товарам
- **Еженедельная аналитика**: тренды и рекомендации
- **Критические алерты**: резкие изменения цен конкурентов

#### 1.3 Сравнение с собственными ценами
- **Автоматическое сопоставление**: поиск аналогичных товаров в ассортименте
- **Анализ конкурентоспособности**: позиционирование по цене
- **Рекомендации по ценообразованию**: оптимальные цены для максимизации прибыли
- **История изменений**: отслеживание динамики цен во времени

### 2. Реклама (MVP)

#### 2.1 Проверка ставок по ключевым словам
- **Анализ топ-позиций**: стоимость первых 3-5 позиций по запросу
- **Сезонная динамика**: изменение ставок в зависимости от времени
- **Конкурентный анализ**: кто занимает топовые позиции
- **ROI калькулятор**: расчет эффективности рекламных вложений

#### 2.2 Будущие возможности
- **Тепловая карта**: визуализация эффективности ключевых слов
- **Расширенный контроль бюджета**: автоматическое управление ставками
- **A/B тестирование**: сравнение эффективности разных стратегий
- **Прогнозирование**: предсказание оптимальных ставок

## 🔧 Техническая реализация

### Google Sheets API Integration

#### Этап 1: Изучение Google Sheets API документации

**Ключевые разделы для изучения:**
- **Basic Concepts**: понимание структуры API
- **Authentication**: методы аутентификации
- **Spreadsheets API**: основные операции с таблицами
- **Batch Operations**: массовые операции для оптимизации
- **Quotas and Limits**: ограничения и лимиты API

**Полезные ресурсы:**
https://developers.google.com/sheets/api/guides/concepts 
https://developers.google.com/sheets/api/reference/rest 
https://developers.google.com/sheets/api/samples

**Основные методы API для изучения:**
- `spreadsheets.create()` - создание новых таблиц
- `spreadsheets.values.get()` - чтение данных
- `spreadsheets.values.update()` - обновление данных
- `spreadsheets.values.batchUpdate()` - массовые обновления
- `spreadsheets.batchUpdate()` - форматирование и структура

#### Этап 2: Настройка OAuth 2.0 credentials в Google Cloud Console

**Пошаговая настройка:**

1. **Создание проекта в Google Cloud Console**
   ```
   1. Перейти на https://console.cloud.google.com/
   2. Создать новый проект или выбрать существующий
   3. Записать Project ID для дальнейшего использования
   Project ID: wbassist
   Project number: 222649115405
   ```

2. **Включение Google Sheets API**
   ```
   1. Перейти в "APIs & Services" > "Library"
   2. Найти "Google Sheets API"
   3. Нажать "Enable"
   4. Повторить для "Google Drive API" (для доступа к файлам)
   ```

3. **Создание OAuth 2.0 credentials**
   ```
   1. Перейти в "APIs & Services" > "Credentials"
   2. Нажать "Create Credentials" > "OAuth client ID"
   3. Выбрать "Desktop application" или "Web application"
   4. Настроить authorized redirect URIs
   5. Скачать JSON файл с credentials
   ```

4. **Настройка Consent Screen**
   ```
   1. Перейти в "OAuth consent screen"
   2. Выбрать "External" для тестирования
   3. Заполнить обязательные поля
   4. Добавить scopes: 
      - https://www.googleapis.com/auth/spreadsheets
      - https://www.googleapis.com/auth/drive.file
   ```

**Структура credentials.json:**
```json
{
  "installed": {
    "client_id": "your-client-id",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your-client-secret",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
  }
}
```

#### Этап 3: Создание базовой структуры модуля

**Архитектура модуля:**
price_monitoring/
├── config/
│   ├── credentials.json          # OAuth credentials
│   ├── token.json               # Сохраненные токены
│   └── settings.py              # Настройки модуля
├── core/
│   ├── init .py
│   ├── google_sheets_client.py  # Клиент для работы с Google Sheets
│   ├── price_monitor.py         # Основная логика мониторинга
│   ├── competitor_analyzer.py   # Анализ конкурентов
│   └── notification_service.py  # Сервис уведомлений
├── models/
│   ├── init .py
│   ├── product.py              # Модель товара
│   ├── price_history.py        # История цен
│   └── competitor.py           # Модель конкурента
├── utils/
│   ├── init .py
│   ├── auth_helper.py          # Помощник аутентификации
│   ├── data_formatter.py       # Форматирование данных
│   └── validators.py           # Валидация входных данных
├── templates/
│   ├── price_report_template.py # Шаблон отчета по ценам
│   └── competitor_analysis_template.py # Шаблон анализа конкурентов
└── tests/
├── test_google_sheets.py   # Тесты Google Sheets
├── test_price_monitor.py   # Тесты мониторинга
└── test_integration.py     # Интеграционные тесты


**Базовый класс Google Sheets Client:**

```python
# core/google_sheets_client.py
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleSheetsClient:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self, credentials_path='config/credentials.json'):
        self.credentials_path = credentials_path
        self.token_path = 'config/token.json'
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Аутентификация с Google API"""
        creds = None
        
        # Загрузка существующих токенов
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )
        
        # Если токены недействительны, запрос новых
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Сохранение токенов
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('sheets', 'v4', credentials=creds)
    
    def create_spreadsheet(self, title):
        """Создание новой таблицы"""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            
            result = self.service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            return result.get('spreadsheetId')
        
        except HttpError as error:
            print(f'Ошибка создания таблицы: {error}')
            return None
    
    def read_values(self, spreadsheet_id, range_name):
        """Чтение данных из таблицы"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
        
        except HttpError as error:
            print(f'Ошибка чтения данных: {error}')
            return []
    
    def update_values(self, spreadsheet_id, range_name, values):
        """Обновление данных в таблице"""
        try:
            body = {
                'values': values
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return result.get('updatedCells', 0)
        
        except HttpError as error:
            print(f'Ошибка обновления данных: {error}')
            return 0
```

**Модель товара:**

```python
# models/product.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Product:
    """Модель товара для мониторинга"""
    id: str
    name: str
    brand: str
    article: str
    category: str
    current_price: float
    competitor_prices: List[float]
    last_updated: datetime
    tracking_enabled: bool = True
    price_threshold: float = 5.0  # Процент изменения для уведомления
    
    def __post_init__(self):
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated)
    
    @property
    def min_competitor_price(self) -> Optional[float]:
        """Минимальная цена среди конкурентов"""
        return min(self.competitor_prices) if self.competitor_prices else None
    
    @property
    def max_competitor_price(self) -> Optional[float]:
        """Максимальная цена среди конкурентов"""
        return max(self.competitor_prices) if self.competitor_prices else None
    
    @property
    def avg_competitor_price(self) -> Optional[float]:
        """Средняя цена среди конкурентов"""
        if not self.competitor_prices:
            return None
        return sum(self.competitor_prices) / len(self.competitor_prices)
    
    def price_position(self) -> str:
        """Позиция по цене относительно конкурентов"""
        if not self.competitor_prices:
            return "Нет данных о конкурентах"
        
        min_price = self.min_competitor_price
        max_price = self.max_competitor_price
        
        if self.current_price < min_price:
            return "Самая низкая цена"
        elif self.current_price > max_price:
            return "Самая высокая цена"
        else:
            return "Средняя позиция"
```

#### Этап 4: Проверка подключения простыми тестами

**Базовые тесты подключения:**

```python
# tests/test_google_sheets.py
import unittest
from core.google_sheets_client import GoogleSheetsClient

class TestGoogleSheetsConnection(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестов"""
        self.client = GoogleSheetsClient()
        self.test_spreadsheet_id = None
    
    def test_authentication(self):
        """Тест аутентификации"""
        self.assertIsNotNone(self.client.service)
        print("✅ Аутентификация прошла успешно")
    
    def test_create_spreadsheet(self):
        """Тест создания таблицы"""
        title = "Тест мониторинга цен"
        spreadsheet_id = self.client.create_spreadsheet(title)
        
        self.assertIsNotNone(spreadsheet_id)
        self.test_spreadsheet_id = spreadsheet_id
        print(f"✅ Таблица создана: {spreadsheet_id}")
    
    def test_write_and_read_data(self):
        """Тест записи и чтения данных"""
        if not self.test_spreadsheet_id:
            self.test_create_spreadsheet()
        
        # Тестовые данные
        test_data = [
            ['Товар', 'Цена', 'Конкурент 1', 'Конкурент 2'],
            ['iPhone 14', '80000', '79000', '81000'],
            ['Samsung Galaxy', '70000', '69000', '71000']
        ]
        
        # Запись данных
        updated_cells = self.client.update_values(
            self.test_spreadsheet_id,
            'A1:D3',
            test_data
        )
        
        self.assertGreater(updated_cells, 0)
        print(f"✅ Записано ячеек: {updated_cells}")
        
        # Чтение данных
        read_data = self.client.read_values(
            self.test_spreadsheet_id,
            'A1:D3'
        )
        
        self.assertEqual(len(read_data), 3)
        self.assertEqual(read_data[0][0], 'Товар')
        print("✅ Данные прочитаны успешно")
    
    def tearDown(self):
        """Очистка после тестов"""
        if self.test_spreadsheet_id:
            print(f"🗑️ Тестовая таблица: {self.test_spreadsheet_id}")

if __name__ == '__main__':
    unittest.main()
```

**Интеграционный тест:**

```python
# tests/test_integration.py
import unittest
from datetime import datetime
from core.google_sheets_client import GoogleSheetsClient
from models.product import Product

class TestPriceMonitoringIntegration(unittest.TestCase):
    
    def setUp(self):
        """Настройка интеграционных тестов"""
        self.client = GoogleSheetsClient()
        self.spreadsheet_id = self.client.create_spreadsheet(
            "Интеграционный тест мониторинга цен"
        )
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        
        # 1. Создание тестового товара
        product = Product(
            id="test_001",
            name="Тестовый товар",
            brand="TestBrand",
            article="TB001",
            category="Электроника",
            current_price=1000.0,
            competitor_prices=[950.0, 1050.0, 980.0],
            last_updated=datetime.now()
        )
        
        # 2. Подготовка данных для Google Sheets
        headers = [
            'ID', 'Название', 'Бренд', 'Артикул', 'Категория',
            'Наша цена', 'Мин. цена конкурентов', 'Макс. цена конкурентов',
            'Средняя цена конкурентов', 'Позиция', 'Обновлено'
        ]
        
        data = [
            product.id,
            product.name,
            product.brand,
            product.article,
            product.category,
            product.current_price,
            product.min_competitor_price,
            product.max_competitor_price,
            round(product.avg_competitor_price, 2),
            product.price_position(),
            product.last_updated.strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        # 3. Запись в Google Sheets
        sheet_data = [headers, data]
        updated_cells = self.client.update_values(
            self.spreadsheet_id,
            'A1:K2',
            sheet_data
        )
        
        self.assertGreater(updated_cells, 0)
        
        # 4. Проверка записанных данных
        read_data = self.client.read_values(
            self.spreadsheet_id,
            'A1:K2'
        )
        
        self.assertEqual(len(read_data), 2)
        self.assertEqual(read_data[1][1], product.name)
        self.assertEqual(float(read_data[1][5]), product.current_price)
        
        print("✅ Интеграционный тест прошел успешно")
        print(f"📊 Таблица доступна: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")

if __name__ == '__main__':
    unittest.main()
```

## 📋 План реализации

### Фаза 1: Базовая настройка (1-2 недели)
- [ ] Изучение Google Sheets API документации
- [ ] Настройка OAuth 2.0 credentials
- [ ] Создание базовой структуры проекта
- [ ] Реализация GoogleSheetsClient
- [ ] Написание и прогон базовых тестов

### Фаза 2: Мониторинг цен (2-3 недели)
- [ ] Реализация парсинга цен с Wildberries
- [ ] Создание системы уведомлений
- [ ] Интеграция с Telegram Bot
- [ ] Автоматическое обновление данных в Google Sheets
- [ ] Тестирование на реальных данных

### Фаза 3: Анализ конкурентов (2-3 недели)
- [ ] Алгоритмы сравнения цен
- [ ] Рекомендательная система
- [ ] Визуализация данных в Google Sheets
- [ ] Исторические отчеты
- [ ] A/B тестирование функций

### Фаза 4: Реклама MVP (1-2 недели)
- [ ] Интеграция с рекламными API
- [ ] Мониторинг ставок по ключевым словам
- [ ] Базовая аналитика эффективности
- [ ] Отчеты по рекламным расходам

## 🔍 Метрики и KPI

### Технические метрики
- **Время отклика API**: < 2 секунд для базовых операций
- **Точность данных**: > 95% корректных цен
- **Доступность сервиса**: > 99.5% uptime
- **Лимиты API**: оптимизация под квоты Google Sheets API

### Бизнес-метрики
- **Количество отслеживаемых товаров**: цель 1000+ товаров на пользователя
- **Частота обновления**: каждые 4-6 часов
- **Точность уведомлений**: < 1% ложных срабатываний
- **Экономия времени**: 80% автоматизации рутинных задач

## 🚀 Запуск и тестирование

### Быстрый старт
```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd price-monitoring

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Настройка credentials
# Поместить credentials.json в папку config/

# 4. Запуск тестов
python -m pytest tests/ -v

# 5. Запуск основного модуля
python main.py
```

### Проверочный список
- [ ] Google Cloud Console проект создан
- [ ] APIs включены (Sheets + Drive)
- [ ] OAuth credentials настроены
- [ ] credentials.json загружен
- [ ] Тесты проходят успешно
- [ ] Тестовая таблица создается
- [ ] Данные записываются и читаются корректно

Этот модуль станет основой для мониторинга цен и анализа конкурентов с полной интеграцией в Google Sheets для удобной работы с данными.


## Этап 3: Создание базовой структуры модуля
### 3.1 Создание директорий и базовой структуры проекта
Подэтап 3.1.1: Создание основных директорий

- Создать корневую папку price_monitoring/
- Создать поддиректории: config/ , core/ , models/ , utils/ , templates/ , tests/
- Добавить файлы __init__.py в каждую Python-директорию
- Создать файл requirements.txt с зависимостями
Подэтап 3.1.2: Настройка конфигурации

- Создать config/settings.py с основными настройками модуля
- Подготовить место для config/credentials.json (OAuth credentials)
- Создать config/token.json для хранения токенов аутентификации
- Настроить переменные окружения и конфигурационные константы
### 3.2 Реализация базового Google Sheets клиента
Подэтап 3.2.1: Создание класса GoogleSheetsClient

- Реализовать core/google_sheets_client.py
- Добавить методы аутентификации ( _authenticate() )
- Реализовать базовые CRUD операции:
  - create_spreadsheet() - создание таблиц
  - read_values() - чтение данных
  - update_values() - обновление данных
  - batch_update() - массовые операции
Подэтап 3.2.2: Обработка ошибок и исключений

- Добавить обработку HttpError от Google API
- Реализовать retry-логику для сетевых запросов
- Создать кастомные исключения для модуля
- Добавить логирование операций
### 3.3 Создание моделей данных
Подэтап 3.3.1: Модель Product

- Создать models/product.py с классом Product
- Реализовать свойства для анализа цен:
  - min_competitor_price
  - max_competitor_price
  - avg_competitor_price
  - price_position()
- Добавить валидацию данных и сериализацию
Подэтап 3.3.2: Модели для истории и конкурентов

- Создать models/price_history.py для отслеживания изменений цен
- Создать models/competitor.py для данных о конкурентах
- Реализовать связи между моделями
- Добавить методы для работы с временными рядами
### 3.4 Вспомогательные утилиты
Подэтап 3.4.1: Помощник аутентификации

- Создать utils/auth_helper.py
- Реализовать функции для работы с OAuth токенами
- Добавить проверку валидности credentials
- Создать функции для обновления токенов
Подэтап 3.4.2: Форматирование и валидация данных

- Создать utils/data_formatter.py для форматирования данных под Google Sheets
- Создать utils/validators.py для валидации входных данных
- Реализовать конвертеры типов данных
- Добавить функции для очистки и нормализации данных
### 3.5 Шаблоны отчетов
Подэтап 3.5.1: Шаблон отчета по ценам

- Создать templates/price_report_template.py
- Определить структуру таблицы для мониторинга цен
- Реализовать форматирование заголовков и данных
- Добавить условное форматирование (цветовые индикаторы)
Подэтап 3.5.2: Шаблон анализа конкурентов

- Создать templates/competitor_analysis_template.py
- Определить структуру для сравнительного анализа
- Реализовать расчет метрик и KPI
- Добавить графики и визуализацию данных
### 3.6 Основная логика мониторинга
Подэтап 3.6.1: Класс PriceMonitor

- Создать core/price_monitor.py с основной логикой
- Реализовать методы для добавления товаров в мониторинг
- Создать функции обновления цен
- Добавить логику сравнения с пороговыми значениями
Подэтап 3.6.2: Анализатор конкурентов

- Создать core/competitor_analyzer.py
- Реализовать алгоритмы сравнения цен
- Добавить функции для поиска аналогичных товаров
- Создать рекомендательную систему для ценообразования
### 3.7 Сервис уведомлений
Подэтап 3.7.1: Базовый NotificationService

- Создать core/notification_service.py
- Реализовать интерфейс для отправки уведомлений
- Добавить поддержку различных каналов (Telegram, email)
- Создать шаблоны сообщений
Подэтап 3.7.2: Интеграция с Telegram Bot

- Добавить методы для отправки в Telegram
- Реализовать форматирование сообщений
- Создать функции для отправки графиков и таблиц
- Добавить настройки частоты уведомлений
### 3.8 Тестирование базовой структуры
Подэтап 3.8.1: Unit тесты

- Создать tests/test_google_sheets.py для тестирования API
- Создать tests/test_models.py для тестирования моделей
- Добавить тесты для утилит и валидаторов
- Реализовать моки для внешних API
Подэтап 3.8.2: Интеграционные тесты

- Создать tests/test_integration.py
- Протестировать полный workflow от создания товара до записи в Google Sheets
- Добавить тесты для различных сценариев использования
- Создать тестовые данные и фикстуры