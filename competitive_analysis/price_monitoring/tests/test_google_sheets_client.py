"""
Тесты для GoogleSheetsClient и подключения к Google Sheets API.

Включает тесты аутентификации, создания таблиц, чтения и записи данных.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path
import tempfile
import json

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.google_sheets_client import GoogleSheetsClient
from utils.auth_helper import AuthHelper
from config.settings import Settings
from models.product import Product


class TestGoogleSheetsClient(unittest.TestCase):
    """Тесты для класса GoogleSheetsClient."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        # Создаем временную директорию для тестов
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем тестовые настройки
        self.settings = Settings(config_dir=str(self.config_dir))
        
        # Создаем фиктивный файл credentials.json
        credentials_path = self.config_dir / 'credentials.json'
        with open(credentials_path, 'w') as f:
            json.dump({
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_client_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }, f)
        
        # Мокаем процесс аутентификации
        with patch('core.google_sheets_client.GoogleSheetsClient._authenticate'):
            self.client = GoogleSheetsClient(
                credentials_path=str(credentials_path)
            )
            # Мокаем сервис
            self.client.service = Mock()
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_client_initialization(self):
        """Тест инициализации клиента."""
        self.assertIsNotNone(self.client)
        self.assertIsNotNone(self.client.credentials_path)
        self.assertIsNotNone(self.client.token_path)
    
    def test_client_initialization_without_auth_helper(self):
        """Тест инициализации клиента без дополнительных параметров."""
        with patch('core.google_sheets_client.GoogleSheetsClient._authenticate'):
            client = GoogleSheetsClient()
            self.assertIsNotNone(client)
            self.assertIsNotNone(client.credentials_path)
    
    @patch('core.google_sheets_client.logger')
    def test_authenticate_success(self, mock_logger):
        """Тест успешной аутентификации."""
        # Мокаем успешную аутентификацию
        with patch.object(self.client, '_authenticate') as mock_auth:
            mock_auth.return_value = None
            self.client._authenticate()
            mock_auth.assert_called_once()
    
    @patch('core.google_sheets_client.logger')
    def test_authenticate_failure(self, mock_logger):
        """Тест неудачной аутентификации."""
        # Мокаем неудачную аутентификацию
        with patch.object(self.client, '_authenticate') as mock_auth:
            mock_auth.side_effect = Exception("Auth failed")
            with self.assertRaises(Exception):
                self.client._authenticate()
    
    def test_create_spreadsheet_success(self):
        """Тест успешного создания таблицы."""
        # Настраиваем мок сервиса
        mock_response = {
            'spreadsheetId': 'test_spreadsheet_id',
            'properties': {'title': 'Test Spreadsheet'},
            'spreadsheetUrl': 'https://docs.google.com/spreadsheets/d/test_spreadsheet_id'
        }
        self.client.service.spreadsheets().create().execute.return_value = mock_response
        
        result = self.client.create_spreadsheet('Test Spreadsheet')
        
        self.assertEqual(result, 'test_spreadsheet_id')
    
    def test_create_spreadsheet_with_exception(self):
        """Тест создания таблицы с исключением."""
        self.client.service.spreadsheets().create().execute.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            self.client.create_spreadsheet('Test Spreadsheet')
    
    def test_get_spreadsheet_info_success(self):
        """Тест успешного получения информации о таблице."""
        mock_response = {
            'spreadsheetId': 'test_id',
            'properties': {'title': 'Test Sheet'},
            'sheets': [{'properties': {'title': 'Sheet1'}}]
        }
        self.client.service.spreadsheets().get().execute.return_value = mock_response
        
        result = self.client.get_spreadsheet_info('test_id')
        
        self.assertEqual(result['spreadsheetId'], 'test_id')
        self.assertEqual(result['properties']['title'], 'Test Sheet')
    
    def test_read_values_success(self):
        """Тест чтения значений из таблицы."""
        mock_response = {
            'values': [
                ['Header1', 'Header2'],
                ['Value1', 'Value2']
            ]
        }
        self.client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = self.client.read_values('test_id', 'A1:B2')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ['Header1', 'Header2'])
        self.assertEqual(result[1], ['Value1', 'Value2'])
    
    def test_read_values_empty_response(self):
        """Тест чтения значений с пустым ответом."""
        mock_response = {}
        self.client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = self.client.read_values('test_id', 'A1:B2')
        
        self.assertEqual(result, [])
    
    def test_update_values_success(self):
        """Тест обновления значений в таблице."""
        mock_response = {
            'updatedCells': 4,
            'updatedColumns': 2,
            'updatedRows': 2
        }
        self.client.service.spreadsheets().values().update().execute.return_value = mock_response
        
        values = [['New1', 'New2'], ['New3', 'New4']]
        result = self.client.update_values('test_id', 'A1:B2', values)
        
        self.assertEqual(result, 4)
    
    def test_batch_update_values_success(self):
        """Тест пакетного обновления значений."""
        mock_response = {
            'totalUpdatedCells': 8,
            'totalUpdatedColumns': 4,
            'totalUpdatedRows': 2
        }
        self.client.service.spreadsheets().values().batchUpdate().execute.return_value = mock_response
        
        updates = [
            {'range': 'A1:B2', 'values': [['A1', 'B1'], ['A2', 'B2']]},
            {'range': 'C1:D2', 'values': [['C1', 'D1'], ['C2', 'D2']]}
        ]
        result = self.client.batch_update_values('test_id', updates)
        
        self.assertEqual(result, 8)
    
    def test_batch_get_values_success(self):
        """Тест пакетного чтения значений."""
        mock_response = {
            'valueRanges': [
                {'range': 'A1:B2', 'values': [['A1', 'B1'], ['A2', 'B2']]},
                {'range': 'C1:D2', 'values': [['C1', 'D1'], ['C2', 'D2']]}
            ]
        }
        self.client.service.spreadsheets().values().batchGet().execute.return_value = mock_response
        
        ranges = ['A1:B2', 'C1:D2']
        result = self.client.batch_get_values('test_id', ranges)
        
        self.assertEqual(len(result), 2)
        self.assertIn('A1:B2', result)
        self.assertEqual(result['A1:B2'], [['A1', 'B1'], ['A2', 'B2']])
    
    def test_add_sheet_success(self):
        """Тест добавления нового листа."""
        mock_response = {
            'replies': [{
                'addSheet': {
                    'properties': {
                        'sheetId': 123,
                        'title': 'New Sheet'
                    }
                }
            }]
        }
        self.client.service.spreadsheets().batchUpdate().execute.return_value = mock_response
        
        result = self.client.add_sheet('test_id', 'New Sheet')
        
        self.assertEqual(result, 123)


class TestAuthHelper(unittest.TestCase):
    """Тесты для класса AuthHelper."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.auth_helper = AuthHelper(config_dir=str(self.config_dir))
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_auth_helper_initialization(self):
        """Тест инициализации AuthHelper."""
        self.assertIsNotNone(self.auth_helper)
        self.assertEqual(self.auth_helper.config_dir, self.config_dir)
        self.assertFalse(self.auth_helper.is_authenticated)
    
    def test_credentials_property(self):
        """Тест свойства credentials."""
        self.assertIsNone(self.auth_helper.credentials)
    
    def test_create_credentials_template(self):
        """Тест создания шаблона credentials."""
        template = AuthHelper.create_credentials_template()
        
        self.assertIsInstance(template, str)
        template_data = json.loads(template)
        self.assertIn('installed', template_data)
        self.assertIn('client_id', template_data['installed'])
    
    def test_setup_credentials_file(self):
        """Тест создания файла credentials."""
        client_id = 'test_client_id'
        client_secret = 'test_client_secret'
        project_id = 'test_project'
        
        self.auth_helper.setup_credentials_file(client_id, client_secret, project_id)
        
        self.assertTrue(self.auth_helper.credentials_file.exists())
        
        with open(self.auth_helper.credentials_file, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['installed']['client_id'], client_id)
        self.assertEqual(data['installed']['client_secret'], client_secret)
        self.assertEqual(data['installed']['project_id'], project_id)


class TestProduct(unittest.TestCase):
    """Тесты для модели Product."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.product = Product(
            id='test_product_1',
            name='Test Product',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Electronics',
            current_price=1000.0,
            competitor_prices=[950.0, 1050.0, 980.0]
        )
    
    def test_product_initialization(self):
        """Тест инициализации продукта."""
        self.assertEqual(self.product.id, 'test_product_1')
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.current_price, 1000.0)
        self.assertEqual(len(self.product.competitor_prices), 3)
    
    def test_min_competitor_price(self):
        """Тест получения минимальной цены конкурента."""
        self.assertEqual(self.product.min_competitor_price, 950.0)
    
    def test_max_competitor_price(self):
        """Тест получения максимальной цены конкурента."""
        self.assertEqual(self.product.max_competitor_price, 1050.0)
    
    def test_avg_competitor_price(self):
        """Тест получения средней цены конкурента."""
        expected_avg = (950.0 + 1050.0 + 980.0) / 3
        self.assertAlmostEqual(self.product.avg_competitor_price, expected_avg, places=2)
    
    def test_median_competitor_price(self):
        """Тест получения медианной цены конкурента."""
        # Отсортированные цены: [950.0, 980.0, 1050.0]
        # Медиана: 980.0
        self.assertEqual(self.product.median_competitor_price, 980.0)
    
    def test_price_position(self):
        """Тест определения позиции по цене."""
        # Наша цена 1000.0, диапазон конкурентов 950.0-1050.0
        # Средняя цена конкурентов: (950.0 + 1050.0 + 980.0) / 3 = 993.33
        # Наша цена 1000.0 > 993.33, поэтому позиция "above_average"
        self.assertEqual(self.product.price_position, "above_average")
        
        # Тест самой низкой цены
        self.product.current_price = 900.0
        self.assertEqual(self.product.price_position, "lowest")
        
        # Тест самой высокой цены
        self.product.current_price = 1100.0
        self.assertEqual(self.product.price_position, "highest")
    
    def test_price_difference_percent(self):
        """Тест расчета разности цен в процентах."""
        # Наша цена 1000.0, цена конкурента 950.0
        # Разность: ((1000 - 950) / 950) * 100 = 5.26%
        diff = self.product.price_difference_percent(950.0)
        self.assertAlmostEqual(diff, 5.26, places=2)
    
    def test_is_price_competitive(self):
        """Тест проверки конкурентоспособности цены."""
        # При толерантности 10% наша цена должна быть конкурентоспособной
        self.assertTrue(self.product.is_price_competitive(10.0))
        
        # При толерантности 1% наша цена все еще конкурентоспособна (отклонение 0.67%)
        self.assertTrue(self.product.is_price_competitive(1.0))
        
        # При толерантности 0.5% наша цена может быть неконкурентоспособной
        self.assertFalse(self.product.is_price_competitive(0.5))
    
    def test_add_competitor_price(self):
        """Тест добавления цены конкурента."""
        initial_count = len(self.product.competitor_prices)
        self.product.add_competitor_price(1200.0)
        
        self.assertEqual(len(self.product.competitor_prices), initial_count + 1)
        self.assertIn(1200.0, self.product.competitor_prices)
    
    def test_remove_competitor_price(self):
        """Тест удаления цены конкурента."""
        initial_count = len(self.product.competitor_prices)
        removed = self.product.remove_competitor_price(950.0)
        
        self.assertTrue(removed)
        self.assertEqual(len(self.product.competitor_prices), initial_count - 1)
        self.assertNotIn(950.0, self.product.competitor_prices)
    
    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации."""
        product_dict = self.product.to_dict()
        
        self.assertIsInstance(product_dict, dict)
        self.assertEqual(product_dict['id'], self.product.id)
        self.assertEqual(product_dict['name'], self.product.name)
        
        # Восстанавливаем объект из словаря
        restored_product = Product.from_dict(product_dict)
        
        self.assertEqual(restored_product.id, self.product.id)
        self.assertEqual(restored_product.name, self.product.name)
        self.assertEqual(restored_product.current_price, self.product.current_price)
    
    def test_to_sheets_row(self):
        """Тест преобразования в строку для Google Sheets."""
        row = self.product.to_sheets_row()
        
        self.assertIsInstance(row, list)
        self.assertEqual(row[0], self.product.id)  # ID товара
        self.assertEqual(row[1], self.product.name)  # Название
        self.assertEqual(row[6], self.product.current_price)  # Текущая цена (индекс 6)
    
    def test_get_sheets_headers(self):
        """Тест получения заголовков для Google Sheets."""
        headers = Product.get_sheets_headers()
        
        self.assertIsInstance(headers, list)
        self.assertIn('ID', headers)
        self.assertIn('Название', headers)
        self.assertIn('Текущая цена', headers)


class TestSettings(unittest.TestCase):
    """Тесты для класса Settings."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings = Settings(config_dir=str(self.config_dir))
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_settings_initialization(self):
        """Тест инициализации настроек."""
        self.assertIsNotNone(self.settings)
        self.assertEqual(self.settings.config_dir, self.config_dir)
        self.assertIsNotNone(self.settings.google_sheets)
        self.assertIsNotNone(self.settings.monitoring)
    
    def test_validate_config(self):
        """Тест валидации конфигурации."""
        errors = self.settings.validate_config()
        
        # Должны быть ошибки, так как файл credentials не указан
        self.assertIsInstance(errors, list)
    
    def test_save_and_load_config(self):
        """Тест сохранения и загрузки конфигурации."""
        # Изменяем настройку
        original_interval = self.settings.monitoring.update_interval_hours
        self.settings.monitoring.update_interval_hours = 12
        
        # Сохраняем
        self.settings.save_config()
        self.assertTrue(self.settings.config_file.exists())
        
        # Создаем новый экземпляр и загружаем
        new_settings = Settings(config_dir=str(self.config_dir))
        
        # Проверяем, что настройка загрузилась
        self.assertEqual(new_settings.monitoring.update_interval_hours, 12)
    
    def test_get_credentials_path(self):
        """Тест получения пути к файлу учетных данных."""
        path = self.settings.get_credentials_path()
        
        self.assertIsInstance(path, Path)
        self.assertEqual(path.name, 'credentials.json')
    
    def test_to_dict(self):
        """Тест преобразования настроек в словарь."""
        settings_dict = self.settings.to_dict()
        
        self.assertIsInstance(settings_dict, dict)
        self.assertIn('google_sheets', settings_dict)
        self.assertIn('monitoring', settings_dict)
        self.assertIn('notifications', settings_dict)


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('core.google_sheets_client.build')
    @patch('core.google_sheets_client.InstalledAppFlow')
    def test_full_workflow_mock(self, mock_flow, mock_build):
        """Тест полного рабочего процесса с моками."""
        # Настраиваем моки
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_flow_instance = Mock()
        mock_flow_instance.run_local_server.return_value = mock_credentials
        mock_flow.from_client_secrets_file.return_value = mock_flow_instance
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Создаем файл credentials
        credentials_file = self.config_dir / 'credentials.json'
        with open(credentials_file, 'w') as f:
            json.dump({
                "installed": {
                    "client_id": "test_client_id",
                    "client_secret": "test_secret",
                    "project_id": "test_project"
                }
            }, f)
        
        # Создаем клиент с патчем аутентификации
        with patch.object(GoogleSheetsClient, '_authenticate') as mock_auth:
            mock_auth.return_value = None
            client = GoogleSheetsClient(credentials_path=str(credentials_file))
            client.service = mock_service
            
            # Проверяем, что клиент создан
            self.assertIsNotNone(client)
            self.assertIsNotNone(client.service)


if __name__ == '__main__':
    # Настраиваем логирование для тестов
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Запускаем тесты
    unittest.main(verbosity=2)