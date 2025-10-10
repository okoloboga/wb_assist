"""
Расширенные unit тесты для Google Sheets API.

Дополняет test_google_sheets_client.py более детальными тестами
для всех аспектов работы с Google Sheets API, включая:
- Детальное тестирование всех методов GoogleSheetsClient
- Тестирование обработки ошибок и исключений
- Моки для внешних API вызовов
- Тестирование retry логики и rate limiting
- Тестирование batch операций
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from pathlib import Path
import tempfile
import json
import time
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.google_sheets_client import GoogleSheetsClient, retry_on_quota_exceeded
from core.exceptions import (
    GoogleSheetsError, AuthenticationError, SpreadsheetNotFoundError,
    SheetNotFoundError, InvalidRangeError, QuotaExceededError,
    RateLimitError, NetworkError
)
from models.product import Product
from models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
from models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType


class TestGoogleSheetsClientDetailed(unittest.TestCase):
    """Детальные тесты для GoogleSheetsClient."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем фиктивный файл credentials.json
        self.credentials_path = self.config_dir / 'credentials.json'
        with open(self.credentials_path, 'w') as f:
            json.dump({
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                }
            }, f)
        
        # Мокаем процесс аутентификации
        with patch('core.google_sheets_client.GoogleSheetsClient._authenticate'):
            self.client = GoogleSheetsClient(
                credentials_path=str(self.credentials_path)
            )
            # Мокаем сервис
            self.client.service = Mock()
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_spreadsheet_with_custom_properties(self):
        """Тест создания таблицы с пользовательскими свойствами."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'custom_spreadsheet_id',
            'properties': {
                'title': 'Custom Spreadsheet',
                'locale': 'ru_RU',
                'timeZone': 'Europe/Moscow'
            },
            'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/custom_spreadsheet_id'
        }
        
        self.client.service.spreadsheets().create().execute.return_value = expected_response
        
        # Вызываем метод
        result = self.client.create_spreadsheet(
            title="Custom Spreadsheet",
            locale="ru_RU",
            time_zone="Europe/Moscow"
        )
        
        # Проверяем результат
        self.assertEqual(result['spreadsheetId'], 'custom_spreadsheet_id')
        self.assertEqual(result['properties']['locale'], 'ru_RU')
        self.assertEqual(result['properties']['timeZone'], 'Europe/Moscow')
        
        # Проверяем вызов API
        self.client.service.spreadsheets().create.assert_called_once()
        call_args = self.client.service.spreadsheets().create.call_args[1]['body']
        self.assertEqual(call_args['properties']['title'], 'Custom Spreadsheet')
        self.assertEqual(call_args['properties']['locale'], 'ru_RU')
        self.assertEqual(call_args['properties']['timeZone'], 'Europe/Moscow')
    
    def test_create_spreadsheet_http_error(self):
        """Тест обработки HTTP ошибки при создании таблицы."""
        # Настраиваем мок для генерации HTTP ошибки
        http_error = HttpError(
            resp=Mock(status=403),
            content=b'{"error": {"message": "Insufficient permissions"}}'
        )
        self.client.service.spreadsheets().create().execute.side_effect = http_error
        
        # Проверяем, что выбрасывается правильное исключение
        with self.assertRaises(GoogleSheetsError) as context:
            self.client.create_spreadsheet("Test Spreadsheet")
        
        self.assertIn("Insufficient permissions", str(context.exception))
    
    def test_get_spreadsheet_info_not_found(self):
        """Тест получения информации о несуществующей таблице."""
        # Настраиваем мок для генерации ошибки 404
        http_error = HttpError(
            resp=Mock(status=404),
            content=b'{"error": {"message": "Requested entity was not found"}}'
        )
        self.client.service.spreadsheets().get().execute.side_effect = http_error
        
        # Проверяем, что выбрасывается правильное исключение
        with self.assertRaises(SpreadsheetNotFoundError):
            self.client.get_spreadsheet_info("nonexistent_id")
    
    def test_read_values_invalid_range(self):
        """Тест чтения значений с некорректным диапазоном."""
        # Настраиваем мок для генерации ошибки 400
        http_error = HttpError(
            resp=Mock(status=400),
            content=b'{"error": {"message": "Invalid range"}}'
        )
        self.client.service.spreadsheets().values().get().execute.side_effect = http_error
        
        # Проверяем, что выбрасывается правильное исключение
        with self.assertRaises(InvalidRangeError):
            self.client.read_values("test_id", "Invalid!Range")
    
    def test_update_values_with_value_input_option(self):
        """Тест обновления значений с различными опциями ввода."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'updatedRows': 2,
            'updatedColumns': 3,
            'updatedCells': 6
        }
        self.client.service.spreadsheets().values().update().execute.return_value = expected_response
        
        # Тестируем с RAW опцией
        values = [['=SUM(A1:A2)', '123', 'text']]
        result = self.client.update_values(
            'test_id', 'Sheet1!A1:C1', values, value_input_option='RAW'
        )
        
        # Проверяем результат
        self.assertEqual(result['updatedCells'], 6)
        
        # Проверяем вызов API
        call_args = self.client.service.spreadsheets().values().update.call_args[1]
        self.assertEqual(call_args['valueInputOption'], 'RAW')
        self.assertEqual(call_args['body']['values'], values)
    
    def test_batch_update_values_large_dataset(self):
        """Тест batch обновления с большим набором данных."""
        # Создаем большой набор данных
        large_data = []
        for i in range(1000):
            large_data.append({
                'range': f'Sheet1!A{i+1}:C{i+1}',
                'values': [[f'Product {i}', f'{100 + i}', f'Category {i % 10}']]
            })
        
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'totalUpdatedRows': 1000,
            'totalUpdatedColumns': 3,
            'totalUpdatedCells': 3000,
            'totalUpdatedSheets': 1
        }
        self.client.service.spreadsheets().values().batchUpdate().execute.return_value = expected_response
        
        # Вызываем метод
        result = self.client.batch_update_values('test_id', large_data)
        
        # Проверяем результат
        self.assertEqual(result['totalUpdatedCells'], 3000)
        
        # Проверяем, что данные были переданы корректно
        call_args = self.client.service.spreadsheets().values().batchUpdate.call_args[1]
        self.assertEqual(len(call_args['body']['data']), 1000)
    
    def test_add_sheet_with_properties(self):
        """Тест добавления листа с пользовательскими свойствами."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'replies': [{
                'addSheet': {
                    'properties': {
                        'sheetId': 123456,
                        'title': 'Custom Sheet',
                        'gridProperties': {
                            'rowCount': 2000,
                            'columnCount': 50
                        },
                        'tabColor': {'red': 1.0, 'green': 0.0, 'blue': 0.0}
                    }
                }
            }]
        }
        self.client.service.spreadsheets().batchUpdate().execute.return_value = expected_response
        
        # Вызываем метод
        result = self.client.add_sheet(
            'test_id',
            'Custom Sheet',
            row_count=2000,
            column_count=50,
            tab_color={'red': 1.0, 'green': 0.0, 'blue': 0.0}
        )
        
        # Проверяем результат
        sheet_props = result['replies'][0]['addSheet']['properties']
        self.assertEqual(sheet_props['title'], 'Custom Sheet')
        self.assertEqual(sheet_props['gridProperties']['rowCount'], 2000)
        self.assertEqual(sheet_props['tabColor']['red'], 1.0)
    
    def test_delete_sheet_success(self):
        """Тест удаления листа."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'replies': [{}]
        }
        self.client.service.spreadsheets().batchUpdate().execute.return_value = expected_response
        
        # Вызываем метод
        result = self.client.delete_sheet('test_id', 123456)
        
        # Проверяем результат
        self.assertEqual(result['spreadsheetId'], 'test_id')
        
        # Проверяем вызов API
        call_args = self.client.service.spreadsheets().batchUpdate.call_args[1]
        delete_request = call_args['body']['requests'][0]['deleteSheet']
        self.assertEqual(delete_request['sheetId'], 123456)
    
    def test_clear_values_success(self):
        """Тест очистки значений в диапазоне."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'clearedRange': 'Sheet1!A1:Z1000'
        }
        self.client.service.spreadsheets().values().clear().execute.return_value = expected_response
        
        # Вызываем метод
        result = self.client.clear_values('test_id', 'Sheet1!A1:Z1000')
        
        # Проверяем результат
        self.assertEqual(result['clearedRange'], 'Sheet1!A1:Z1000')
        
        # Проверяем вызов API
        self.client.service.spreadsheets().values().clear.assert_called_once_with(
            spreadsheetId='test_id',
            range='Sheet1!A1:Z1000'
        )


class TestRetryDecorator(unittest.TestCase):
    """Тесты для декоратора retry_on_quota_exceeded."""
    
    def test_retry_on_quota_exceeded_success_first_try(self):
        """Тест успешного выполнения с первой попытки."""
        @retry_on_quota_exceeded(max_retries=3, base_delay=0.1)
        def test_function():
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
    
    def test_retry_on_quota_exceeded_success_after_retries(self):
        """Тест успешного выполнения после нескольких попыток."""
        call_count = 0
        
        @retry_on_quota_exceeded(max_retries=3, base_delay=0.1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Имитируем quota exceeded ошибку
                http_error = HttpError(
                    resp=Mock(status=429),
                    content=b'{"error": {"message": "Quota exceeded"}}'
                )
                raise http_error
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_retry_on_quota_exceeded_max_retries_exceeded(self):
        """Тест превышения максимального количества попыток."""
        @retry_on_quota_exceeded(max_retries=2, base_delay=0.1)
        def test_function():
            # Всегда генерируем quota exceeded ошибку
            http_error = HttpError(
                resp=Mock(status=429),
                content=b'{"error": {"message": "Quota exceeded"}}'
            )
            raise http_error
        
        with self.assertRaises(QuotaExceededError):
            test_function()
    
    def test_retry_on_quota_exceeded_non_retryable_error(self):
        """Тест с ошибкой, которая не подлежит повтору."""
        @retry_on_quota_exceeded(max_retries=3, base_delay=0.1)
        def test_function():
            # Генерируем ошибку, которая не подлежит повтору
            http_error = HttpError(
                resp=Mock(status=404),
                content=b'{"error": {"message": "Not found"}}'
            )
            raise http_error
        
        with self.assertRaises(HttpError):
            test_function()


class TestGoogleSheetsErrorHandling(unittest.TestCase):
    """Тесты для обработки ошибок Google Sheets API."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        with patch('core.google_sheets_client.GoogleSheetsClient._authenticate'):
            self.client = GoogleSheetsClient()
            self.client.service = Mock()
    
    def test_handle_authentication_error(self):
        """Тест обработки ошибки аутентификации."""
        http_error = HttpError(
            resp=Mock(status=401),
            content=b'{"error": {"message": "Invalid credentials"}}'
        )
        self.client.service.spreadsheets().create().execute.side_effect = http_error
        
        with self.assertRaises(AuthenticationError):
            self.client.create_spreadsheet("Test")
    
    def test_handle_rate_limit_error(self):
        """Тест обработки ошибки превышения лимита запросов."""
        http_error = HttpError(
            resp=Mock(status=429),
            content=b'{"error": {"message": "Rate limit exceeded"}}'
        )
        self.client.service.spreadsheets().create().execute.side_effect = http_error
        
        with self.assertRaises(RateLimitError):
            self.client.create_spreadsheet("Test")
    
    def test_handle_network_error(self):
        """Тест обработки сетевой ошибки."""
        self.client.service.spreadsheets().create().execute.side_effect = ConnectionError("Network error")
        
        with self.assertRaises(NetworkError):
            self.client.create_spreadsheet("Test")
    
    def test_handle_generic_google_sheets_error(self):
        """Тест обработки общей ошибки Google Sheets."""
        http_error = HttpError(
            resp=Mock(status=500),
            content=b'{"error": {"message": "Internal server error"}}'
        )
        self.client.service.spreadsheets().create().execute.side_effect = http_error
        
        with self.assertRaises(GoogleSheetsError):
            self.client.create_spreadsheet("Test")


class TestGoogleSheetsDataOperations(unittest.TestCase):
    """Тесты для операций с данными в Google Sheets."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        with patch('core.google_sheets_client.GoogleSheetsClient._authenticate'):
            self.client = GoogleSheetsClient()
            self.client.service = Mock()
        
        # Создаем тестовые данные
        self.test_products = [
            Product(
                id="PROD001",
                name="Тестовый товар 1",
                brand="TestBrand",
                article="ART001",
                sku="SKU001",
                category="Test Category",
                current_price=1000.0,
                competitor_prices=[950.0, 1050.0, 980.0]
            ),
            Product(
                id="PROD002",
                name="Тестовый товар 2",
                brand="TestBrand",
                article="ART002",
                sku="SKU002",
                category="Test Category",
                current_price=2000.0,
                competitor_prices=[1900.0, 2100.0, 1950.0]
            )
        ]
    
    def test_write_products_to_sheet(self):
        """Тест записи товаров в таблицу."""
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'updatedRows': 3,  # Заголовок + 2 товара
            'updatedColumns': 10,
            'updatedCells': 30
        }
        self.client.service.spreadsheets().values().update().execute.return_value = expected_response
        
        # Подготавливаем данные для записи
        headers = Product.get_sheets_headers()
        data = [headers]
        for product in self.test_products:
            data.append(product.to_sheets_row())
        
        # Вызываем метод
        result = self.client.update_values('test_id', 'Products!A1:J3', data)
        
        # Проверяем результат
        self.assertEqual(result['updatedRows'], 3)
        
        # Проверяем, что данные были переданы корректно
        call_args = self.client.service.spreadsheets().values().update.call_args[1]
        self.assertEqual(len(call_args['body']['values']), 3)  # Заголовок + 2 товара
        self.assertEqual(call_args['body']['values'][0], headers)
    
    def test_read_products_from_sheet(self):
        """Тест чтения товаров из таблицы."""
        # Настраиваем мок для возврата данных
        headers = Product.get_sheets_headers()
        product_data = []
        for product in self.test_products:
            product_data.append(product.to_sheets_row())
        
        mock_response = {
            'values': [headers] + product_data
        }
        self.client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        # Вызываем метод
        result = self.client.read_values('test_id', 'Products!A1:J3')
        
        # Проверяем результат
        self.assertEqual(len(result), 3)  # Заголовок + 2 товара
        self.assertEqual(result[0], headers)
        self.assertEqual(result[1], self.test_products[0].to_sheets_row())
        self.assertEqual(result[2], self.test_products[1].to_sheets_row())
    
    def test_batch_write_price_history(self):
        """Тест batch записи истории цен."""
        # Создаем историю цен
        price_history = PriceHistory(product_id="PROD001")
        for i in range(10):
            entry = PriceHistoryEntry(
                timestamp=datetime.now() - timedelta(days=i),
                price=1000.0 + i * 10,
                source=PriceSource.MANUAL,
                change_type=PriceChangeType.INCREASE if i % 2 == 0 else PriceChangeType.DECREASE
            )
            price_history.add_entry(entry)
        
        # Настраиваем мок
        expected_response = {
            'spreadsheetId': 'test_id',
            'totalUpdatedRows': 11,  # Заголовок + 10 записей
            'totalUpdatedColumns': 5,
            'totalUpdatedCells': 55
        }
        self.client.service.spreadsheets().values().batchUpdate().execute.return_value = expected_response
        
        # Подготавливаем данные для batch записи
        batch_data = []
        headers = ['Timestamp', 'Price', 'Source', 'Change Type', 'Notes']
        batch_data.append({
            'range': 'PriceHistory!A1:E1',
            'values': [headers]
        })
        
        for i, entry in enumerate(price_history.entries):
            batch_data.append({
                'range': f'PriceHistory!A{i+2}:E{i+2}',
                'values': [[
                    entry.timestamp.isoformat(),
                    entry.price,
                    entry.source.value,
                    entry.change_type.value,
                    entry.notes or ''
                ]]
            })
        
        # Вызываем метод
        result = self.client.batch_update_values('test_id', batch_data)
        
        # Проверяем результат
        self.assertEqual(result['totalUpdatedRows'], 11)
        
        # Проверяем, что данные были переданы корректно
        call_args = self.client.service.spreadsheets().values().batchUpdate.call_args[1]
        self.assertEqual(len(call_args['body']['data']), 11)  # Заголовок + 10 записей


class TestGoogleSheetsMocks(unittest.TestCase):
    """Тесты с моками для внешних API."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.patcher_build = patch('core.google_sheets_client.build')
        self.patcher_flow = patch('core.google_sheets_client.InstalledAppFlow')
        self.patcher_creds = patch('core.google_sheets_client.Credentials')
        
        self.mock_build = self.patcher_build.start()
        self.mock_flow = self.patcher_flow.start()
        self.mock_creds = self.patcher_creds.start()
        
        # Настраиваем моки
        self.mock_service = Mock()
        self.mock_build.return_value = self.mock_service
        
        self.mock_credentials = Mock()
        self.mock_credentials.valid = True
        self.mock_credentials.expired = False
        self.mock_creds.from_authorized_user_file.return_value = self.mock_credentials
        
        # Создаем клиент
        self.client = GoogleSheetsClient()
    
    def tearDown(self):
        """Очистка после тестов."""
        self.patcher_build.stop()
        self.patcher_flow.stop()
        self.patcher_creds.stop()
    
    def test_full_api_workflow_with_mocks(self):
        """Тест полного workflow с моками API."""
        # 1. Создание таблицы
        create_response = {
            'spreadsheetId': 'test_spreadsheet_id',
            'properties': {'title': 'Test Spreadsheet'},
            'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_spreadsheet_id'
        }
        self.mock_service.spreadsheets().create().execute.return_value = create_response
        
        spreadsheet = self.client.create_spreadsheet("Test Spreadsheet")
        self.assertEqual(spreadsheet['spreadsheetId'], 'test_spreadsheet_id')
        
        # 2. Добавление листа
        add_sheet_response = {
            'spreadsheetId': 'test_spreadsheet_id',
            'replies': [{
                'addSheet': {
                    'properties': {
                        'sheetId': 123456,
                        'title': 'Products'
                    }
                }
            }]
        }
        self.mock_service.spreadsheets().batchUpdate().execute.return_value = add_sheet_response
        
        sheet = self.client.add_sheet('test_spreadsheet_id', 'Products')
        self.assertEqual(sheet['replies'][0]['addSheet']['properties']['title'], 'Products')
        
        # 3. Запись данных
        update_response = {
            'spreadsheetId': 'test_spreadsheet_id',
            'updatedRows': 2,
            'updatedColumns': 3,
            'updatedCells': 6
        }
        self.mock_service.spreadsheets().values().update().execute.return_value = update_response
        
        data = [['Product', 'Price', 'Category'], ['Test Product', '100', 'Test']]
        result = self.client.update_values('test_spreadsheet_id', 'Products!A1:C2', data)
        self.assertEqual(result['updatedCells'], 6)
        
        # 4. Чтение данных
        read_response = {
            'values': [['Product', 'Price', 'Category'], ['Test Product', '100', 'Test']]
        }
        self.mock_service.spreadsheets().values().get().execute.return_value = read_response
        
        values = self.client.read_values('test_spreadsheet_id', 'Products!A1:C2')
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0], ['Product', 'Price', 'Category'])
        
        # Проверяем, что все API вызовы были сделаны
        self.mock_service.spreadsheets().create.assert_called_once()
        self.mock_service.spreadsheets().batchUpdate.assert_called_once()
        self.mock_service.spreadsheets().values().update.assert_called_once()
        self.mock_service.spreadsheets().values().get.assert_called_once()


if __name__ == '__main__':
    # Настраиваем логирование для тестов
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Запускаем тесты
    unittest.main(verbosity=2)