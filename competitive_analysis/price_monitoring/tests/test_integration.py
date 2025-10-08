"""
Интеграционные тесты для модуля мониторинга цен.

Тестирует взаимодействие между различными компонентами модуля.
"""

import unittest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Добавляем путь к модулю в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.google_sheets_client import GoogleSheetsClient
from models.product import Product
from utils.auth_helper import AuthHelper
from config.settings import Settings


class TestFullWorkflow(unittest.TestCase):
    """Тесты полного рабочего процесса мониторинга цен."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем тестовые настройки
        self.settings = Settings(config_dir=str(self.config_dir))
        
        # Создаем тестовые продукты
        self.products = [
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
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('core.google_sheets_client.build')
    @patch('utils.auth_helper.pickle')
    @patch('utils.auth_helper.InstalledAppFlow')
    @patch('utils.auth_helper.Credentials')
    def test_complete_price_monitoring_workflow(self, mock_credentials, mock_flow, mock_pickle, mock_build):
        """Тест полного процесса мониторинга цен."""
        
        # Настраиваем моки для аутентификации
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        # Настраиваем мок для Google Sheets API
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Мок для создания таблицы
        mock_service.spreadsheets().create().execute.return_value = {
            'spreadsheetId': 'test_spreadsheet_id',
            'properties': {'title': 'Test Spreadsheet'}
        }
        
        # Мок для получения информации о таблице
        mock_service.spreadsheets().get().execute.return_value = {
            'spreadsheetId': 'test_spreadsheet_id',
            'properties': {'title': 'Test Spreadsheet'},
            'sheets': [{'properties': {'title': 'Sheet1'}}]
        }
        
        # Мок для записи данных
        mock_service.spreadsheets().values().update().execute.return_value = {
            'updatedCells': 10,
            'updatedRows': 2
        }
        
        # Мок для чтения данных
        mock_service.spreadsheets().values().get().execute.return_value = {
            'values': [
                Product.get_sheets_headers(),
                self.products[0].to_sheets_row(),
                self.products[1].to_sheets_row()
            ]
        }
        
        # 1. Инициализация AuthHelper
        auth_helper = AuthHelper(
            credentials_file='credentials.json',
            token_file='token.pickle',
            config_dir=str(self.config_dir)
        )
        
        # 2. Инициализация GoogleSheetsClient
        client = GoogleSheetsClient(credentials_path='config/credentials.json')
        
        # 3. Создание новой таблицы
        spreadsheet_info = client.create_spreadsheet("Мониторинг цен - Тест")
        
        self.assertIsNotNone(spreadsheet_info)
        self.assertEqual(spreadsheet_info['spreadsheetId'], 'test_spreadsheet_id')
        
        # 4. Запись заголовков
        headers = Product.get_sheets_headers()
        client.update_values(
            spreadsheet_id='test_spreadsheet_id',
            range_name='A1:J1',
            values=[headers]
        )
        
        # 5. Запись данных о продуктах
        product_rows = [product.to_sheets_row() for product in self.products]
        client.update_values(
            spreadsheet_id='test_spreadsheet_id',
            range_name='A2:J3',
            values=product_rows
        )
        
        # 6. Чтение данных обратно
        read_data = client.read_values(
            spreadsheet_id='test_spreadsheet_id',
            range_name='A1:J3'
        )
        
        self.assertIsNotNone(read_data)
        self.assertEqual(len(read_data), 3)  # Заголовки + 2 продукта
        
        # 7. Проверка корректности данных
        self.assertEqual(read_data[0], headers)
        self.assertEqual(read_data[1], self.products[0].to_sheets_row())
        self.assertEqual(read_data[2], self.products[1].to_sheets_row())
        
        # Проверяем, что все необходимые методы были вызваны
        mock_service.spreadsheets().create.assert_called_once()
        mock_service.spreadsheets().values().update.assert_called()
        mock_service.spreadsheets().values().get.assert_called_once()
    
    @patch('core.google_sheets_client.build')
    @patch('utils.auth_helper.pickle')
    @patch('utils.auth_helper.InstalledAppFlow')
    @patch('utils.auth_helper.Credentials')
    def test_batch_operations_workflow(self, mock_credentials, mock_flow, mock_pickle, mock_build):
        """Тест пакетных операций с большим количеством продуктов."""
        
        # Настраиваем моки
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Создаем большое количество продуктов для тестирования пакетных операций
        large_product_list = []
        for i in range(150):  # Больше чем batch_size по умолчанию (100)
            product = Product(
                id=f"PROD{i:03d}",
                name=f"Тестовый товар {i}",
                brand="TestBrand",
                article=f"ART{i:03d}",
                sku=f"SKU{i:03d}",
                category="Test Category",
                current_price=1000.0 + i * 10,
                competitor_prices=[950.0 + i * 10, 1050.0 + i * 10]
            )
            large_product_list.append(product)
        
        # Мок для пакетного обновления
        mock_service.spreadsheets().values().batchUpdate().execute.return_value = {
            'totalUpdatedCells': 1500,
            'totalUpdatedRows': 150
        }
        
        # Мок для пакетного чтения
        mock_service.spreadsheets().values().batchGet().execute.return_value = {
            'valueRanges': [
                {
                    'range': 'A1:J50',
                    'values': [product.to_sheets_row() for product in large_product_list[:50]]
                },
                {
                    'range': 'A51:J100',
                    'values': [product.to_sheets_row() for product in large_product_list[50:100]]
                },
                {
                    'range': 'A101:J150',
                    'values': [product.to_sheets_row() for product in large_product_list[100:150]]
                }
            ]
        }
        
        # Инициализация клиента
        auth_helper = AuthHelper(
            credentials_file='credentials.json',
            token_file='token.pickle',
            config_dir=str(self.config_dir)
        )
        client = GoogleSheetsClient(credentials_path='config/credentials.json')
        
        # Подготовка данных для пакетного обновления
        batch_data = []
        for i, product in enumerate(large_product_list):
            batch_data.append({
                'range': f'A{i+2}:J{i+2}',  # Начинаем с A2, так как A1 - заголовки
                'values': [product.to_sheets_row()]
            })
        
        # Выполнение пакетного обновления
        result = client.batch_update_values(
            spreadsheet_id='test_spreadsheet_id',
            value_input_data=batch_data
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['totalUpdatedRows'], 150)
        
        # Выполнение пакетного чтения
        ranges = ['A1:J50', 'A51:J100', 'A101:J150']
        batch_read_result = client.batch_get_values(
            spreadsheet_id='test_spreadsheet_id',
            ranges=ranges
        )
        
        self.assertIsNotNone(batch_read_result)
        self.assertEqual(len(batch_read_result), 3)
        
        # Проверяем, что пакетные методы были вызваны
        mock_service.spreadsheets().values().batchUpdate.assert_called_once()
        mock_service.spreadsheets().values().batchGet.assert_called_once()
    
    def test_product_analysis_workflow(self):
        """Тест процесса анализа продуктов и ценовых рекомендаций."""
        
        # Создаем продукт с различными конкурентными ценами
        product = Product(
            id="ANALYSIS_TEST",
            name="Товар для анализа",
            brand="AnalysisBrand",
            article="ANALYSIS001",
            sku="SKU_ANALYSIS",
            category="Analysis Category",
            current_price=1000.0,
            competitor_prices=[800.0, 900.0, 1100.0, 1200.0, 950.0]
        )
        
        # 1. Анализ позиции по цене
        price_position = product.get_price_position()
        self.assertIn(price_position, ['lowest', 'below_average', 'average', 'above_average', 'highest'])
        
        # 2. Расчет статистики конкурентных цен
        min_price = product.get_min_competitor_price()
        max_price = product.get_max_competitor_price()
        avg_price = product.get_average_competitor_price()
        median_price = product.get_median_competitor_price()
        
        self.assertEqual(min_price, 800.0)
        self.assertEqual(max_price, 1200.0)
        self.assertAlmostEqual(avg_price, 990.0, places=1)
        self.assertEqual(median_price, 950.0)
        
        # 3. Проверка конкурентоспособности
        is_competitive = product.is_price_competitive(threshold_percent=10.0)
        self.assertIsInstance(is_competitive, bool)
        
        # 4. Получение ценовых рекомендаций
        recommendations = product.get_price_recommendations()
        
        self.assertIsInstance(recommendations, dict)
        self.assertIn('action', recommendations)
        self.assertIn('recommended_price', recommendations)
        self.assertIn('reason', recommendations)
        
        # 5. Обновление цены и проверка истории
        old_price = product.current_price
        product.update_price(950.0)
        
        self.assertEqual(product.current_price, 950.0)
        self.assertNotEqual(product.current_price, old_price)
        
        # 6. Добавление новых конкурентных цен
        product.add_competitor_price(920.0)
        self.assertIn(920.0, product.competitor_prices)
        
        # 7. Удаление конкурентной цены
        product.remove_competitor_price(1200.0)
        self.assertNotIn(1200.0, product.competitor_prices)
        
        # 8. Проверка сериализации
        product_dict = product.to_dict()
        restored_product = Product.from_dict(product_dict)
        
        self.assertEqual(product.id, restored_product.id)
        self.assertEqual(product.name, restored_product.name)
        self.assertEqual(product.current_price, restored_product.current_price)
        self.assertEqual(product.competitor_prices, restored_product.competitor_prices)
    
    def test_settings_integration_workflow(self):
        """Тест интеграции настроек с различными компонентами."""
        
        # 1. Создание и сохранение настроек
        settings = Settings(config_dir=str(self.config_dir))
        
        # Изменяем настройки
        settings.monitoring.update_interval_hours = 12
        settings.monitoring.default_price_threshold = 7.5
        settings.notifications.email_enabled = True
        settings.notifications.email_to = ['test@example.com']
        
        # Сохраняем настройки
        settings.save_config()
        
        # 2. Загрузка настроек из файла
        new_settings = Settings(config_dir=str(self.config_dir))
        
        self.assertEqual(new_settings.monitoring.update_interval_hours, 12)
        self.assertEqual(new_settings.monitoring.default_price_threshold, 7.5)
        self.assertEqual(new_settings.notifications.email_enabled, True)
        self.assertEqual(new_settings.notifications.email_to, ['test@example.com'])
        
        # 3. Валидация настроек
        errors = new_settings.validate_config()
        self.assertIsInstance(errors, list)
        
        # 4. Использование настроек в AuthHelper
        auth_helper = AuthHelper(
            credentials_file=str(new_settings.get_credentials_path()),
            token_file=str(new_settings.get_token_path()),
            config_dir=str(self.config_dir)
        )
        
        self.assertEqual(auth_helper.credentials_file, str(new_settings.get_credentials_path()))
        self.assertEqual(auth_helper.token_file, str(new_settings.get_token_path()))
        
        # 5. Использование настроек в GoogleSheetsClient
        with patch('core.google_sheets_client.build'):
            client = GoogleSheetsClient(
                credentials_path=str(new_settings.get_credentials_path())
            )
            
            self.assertIsNotNone(client)
    
    @patch('core.google_sheets_client.build')
    @patch('utils.auth_helper.pickle')
    @patch('utils.auth_helper.InstalledAppFlow')
    @patch('utils.auth_helper.Credentials')
    def test_error_handling_workflow(self, mock_credentials, mock_flow, mock_pickle, mock_build):
        """Тест обработки ошибок в рабочем процессе."""
        
        # Настраиваем моки для имитации ошибок
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_credentials.from_authorized_user_file.return_value = mock_creds
        
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Имитируем ошибку API
        from googleapiclient.errors import HttpError
        mock_response = Mock()
        mock_response.status = 403
        mock_response.reason = 'Forbidden'
        
        mock_service.spreadsheets().create().execute.side_effect = HttpError(
            resp=mock_response, 
            content=b'{"error": {"message": "API quota exceeded"}}'
        )
        
        # Инициализация клиента
        auth_helper = AuthHelper(
            credentials_file='credentials.json',
            token_file='token.pickle',
            config_dir=str(self.config_dir)
        )
        client = GoogleSheetsClient(credentials_path='config/credentials.json')
        
        # Проверяем, что ошибка корректно обрабатывается
        with self.assertRaises(HttpError):
            client.create_spreadsheet("Test Spreadsheet")
        
        # Проверяем обработку ошибок в Product
        product = Product(
            id="ERROR_TEST",
            name="Тест ошибок",
            brand="ErrorBrand",
            article="ERROR001",
            sku="SKU_ERROR",
            category="Error Category",
            current_price=1000.0
        )
        
        # Попытка получить статистику без конкурентных цен
        self.assertIsNone(product.get_min_competitor_price())
        self.assertIsNone(product.get_max_competitor_price())
        self.assertIsNone(product.get_average_competitor_price())
        self.assertIsNone(product.get_median_competitor_price())
        
        # Проверяем обработку некорректных данных
        with self.assertRaises(ValueError):
            Product.from_dict({})  # Пустой словарь
        
        with self.assertRaises(ValueError):
            Product.from_dict({'id': 'TEST'})  # Отсутствуют обязательные поля
    
    def test_performance_workflow(self):
        """Тест производительности с большим объемом данных."""
        
        import time
        
        # Создаем большое количество продуктов
        start_time = time.time()
        
        products = []
        for i in range(1000):
            product = Product(
                id=f"PERF{i:04d}",
                name=f"Товар производительности {i}",
                brand="PerfBrand",
                article=f"PERF{i:04d}",
                sku=f"SKU_PERF{i:04d}",
                category="Performance Category",
                current_price=1000.0 + i,
                competitor_prices=[950.0 + i, 1050.0 + i, 980.0 + i, 1020.0 + i]
            )
            products.append(product)
        
        creation_time = time.time() - start_time
        
        # Проверяем, что создание 1000 продуктов занимает разумное время
        self.assertLess(creation_time, 5.0)  # Менее 5 секунд
        
        # Тестируем массовые операции
        start_time = time.time()
        
        # Массовое преобразование в словари
        product_dicts = [product.to_dict() for product in products]
        
        # Массовое преобразование в строки Google Sheets
        sheets_rows = [product.to_sheets_row() for product in products]
        
        # Массовые расчеты
        recommendations = [product.get_price_recommendations() for product in products]
        
        operations_time = time.time() - start_time
        
        # Проверяем, что массовые операции выполняются за разумное время
        self.assertLess(operations_time, 10.0)  # Менее 10 секунд
        
        # Проверяем корректность результатов
        self.assertEqual(len(product_dicts), 1000)
        self.assertEqual(len(sheets_rows), 1000)
        self.assertEqual(len(recommendations), 1000)
        
        # Проверяем, что все рекомендации содержат необходимые ключи
        for recommendation in recommendations:
            self.assertIn('action', recommendation)
            self.assertIn('recommended_price', recommendation)
            self.assertIn('reason', recommendation)


class TestModuleIntegration(unittest.TestCase):
    """Тесты интеграции между модулями."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Очистка после тестов."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_module_imports(self):
        """Тест корректности импортов между модулями."""
        
        # Проверяем, что все основные классы можно импортировать
        from core.google_sheets_client import GoogleSheetsClient
        from models.product import Product
        from utils.auth_helper import AuthHelper
        from config.settings import Settings, get_settings
        
        # Проверяем, что классы можно инстанцировать
        settings = Settings(config_dir=str(self.config_dir))
        self.assertIsInstance(settings, Settings)
        
        product = Product(
            id="IMPORT_TEST",
            name="Тест импорта",
            brand="ImportBrand",
            article="IMPORT001",
            sku="SKU_IMPORT",
            category="Import Category",
            current_price=1000.0
        )
        self.assertIsInstance(product, Product)
        
        auth_helper = AuthHelper(
            credentials_file=str(self.config_dir / 'credentials.json'),
            token_file=str(self.config_dir / 'token.pickle')
        )
        self.assertIsInstance(auth_helper, AuthHelper)
        
        with patch('core.google_sheets_client.build'):
            client = GoogleSheetsClient(credentials_path='config/credentials.json')
            self.assertIsInstance(client, GoogleSheetsClient)
    
    def test_data_flow_integration(self):
        """Тест потока данных между компонентами."""
        
        # 1. Создаем настройки
        settings = Settings(config_dir=str(self.config_dir))
        
        # 2. Создаем продукт
        product = Product(
            id="FLOW_TEST",
            name="Тест потока данных",
            brand="FlowBrand",
            article="FLOW001",
            sku="SKU_FLOW",
            category="Flow Category",
            current_price=1500.0,
            competitor_prices=[1400.0, 1600.0, 1450.0]
        )
        
        # 3. Преобразуем продукт в формат для Google Sheets
        sheets_row = product.to_sheets_row()
        headers = Product.get_sheets_headers()
        
        # 4. Проверяем соответствие данных
        self.assertEqual(len(sheets_row), len(headers))
        
        # 5. Восстанавливаем продукт из данных Google Sheets
        # Имитируем чтение из Google Sheets
        sheets_data = dict(zip(headers, sheets_row))
        
        restored_product = Product(
            id=sheets_data['ID'],
            name=sheets_data['Название'],
            brand=sheets_data['Бренд'],
            article=sheets_data.get('Артикул', 'DEFAULT_ARTICLE'),
            sku=sheets_data.get('SKU', 'DEFAULT_SKU'),
            category=sheets_data.get('Категория', 'Default Category'),
            current_price=float(sheets_data['Текущая цена']),
            competitor_prices=json.loads(sheets_data.get('Цены конкурентов', '[]')) if sheets_data.get('Цены конкурентов') else []
        )
        
        # 6. Проверяем корректность восстановления
        self.assertEqual(product.id, restored_product.id)
        self.assertEqual(product.name, restored_product.name)
        self.assertEqual(product.brand, restored_product.brand)
        self.assertEqual(product.current_price, restored_product.current_price)
        self.assertEqual(product.competitor_prices, restored_product.competitor_prices)
    
    def test_configuration_propagation(self):
        """Тест распространения конфигурации по компонентам."""
        
        # Создаем настройки с пользовательскими значениями
        settings = Settings(config_dir=str(self.config_dir))
        settings.google_sheets.application_name = "Custom Integration Test"
        settings.google_sheets.batch_size = 50
        settings.google_sheets.request_timeout = 60
        
        # Проверяем, что настройки корректно используются в AuthHelper
        auth_helper = AuthHelper(
            credentials_file=str(settings.get_credentials_path()),
            token_file=str(settings.get_token_path()),
            config_dir=str(self.config_dir)
        )
        

        
        # Проверяем, что настройки корректно используются в GoogleSheetsClient
        with patch('core.google_sheets_client.build'):
            client = GoogleSheetsClient(
                credentials_path=str(settings.get_credentials_path())
            )
            
            self.assertIsNotNone(client)


if __name__ == '__main__':
    # Настраиваем логирование для тестов
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Запускаем тесты
    unittest.main(verbosity=2)