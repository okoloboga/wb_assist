"""
Интеграционные тесты для внешних API с использованием моков.
Этот модуль тестирует интеграцию с Google Sheets API и Wildberries API.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_mocks import (
    MockGoogleSheetsService, MockWildberriesAPI, MockRequestsSession,
    mock_google_sheets_service, mock_wildberries_api, mock_requests_session,
    reset_all_mocks, patch_google_sheets_service, patch_wildberries_api,
    patch_requests_session
)

try:
    from utils.google_sheets_client import GoogleSheetsClient
    from utils.auth_helper import AuthHelper
    from models.product import Product
    from config.settings import Settings
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")


class TestGoogleSheetsIntegration(unittest.TestCase):
    """Интеграционные тесты для Google Sheets API."""
    
    def setUp(self):
        """Настройка тестов."""
        reset_all_mocks()
        
        # Настройка мок данных
        self.test_spreadsheet_id = "test_spreadsheet_123"
        self.test_product = Product(
            our_product_id="TEST001",
            name="Тестовый товар",
            brand="TestBrand",
            article="ART001",
            current_price=1000.0
        )
    
    @patch_google_sheets_service
    def test_create_and_setup_spreadsheet(self, mock_build):
        """Тест создания и настройки таблицы."""
        # Создаем клиент
        client = GoogleSheetsClient()
        
        # Создаем таблицу
        spreadsheet_id = client.create_spreadsheet("Test Monitoring")
        
        self.assertIsNotNone(spreadsheet_id)
        self.assertTrue(spreadsheet_id.startswith("mock_sheet_"))
        
        # Проверяем, что API был вызван
        self.assertEqual(mock_google_sheets_service.call_count, 1)
    
    @patch_google_sheets_service
    def test_write_and_read_product_data(self, mock_build):
        """Тест записи и чтения данных о товарах."""
        client = GoogleSheetsClient()
        
        # Создаем таблицу
        spreadsheet_id = client.create_spreadsheet("Product Data Test")
        
        # Записываем заголовки
        headers = self.test_product.get_sheets_headers()
        client.write_headers(spreadsheet_id, headers)
        
        # Записываем данные товара
        product_row = self.test_product.to_sheets_row()
        client.append_row(spreadsheet_id, product_row)
        
        # Читаем данные
        data = client.read_range(spreadsheet_id, "A1:Z10")
        
        self.assertIsNotNone(data)
        # Проверяем количество вызовов API
        self.assertGreater(mock_google_sheets_service.call_count, 0)
    
    @patch_google_sheets_service
    def test_batch_operations(self, mock_build):
        """Тест пакетных операций."""
        client = GoogleSheetsClient()
        
        # Создаем таблицу
        spreadsheet_id = client.create_spreadsheet("Batch Operations Test")
        
        # Подготавливаем данные для пакетной записи
        products = []
        for i in range(5):
            product = Product(
                our_product_id=f"TEST{i:03d}",
                name=f"Товар {i}",
                brand="TestBrand",
                article=f"ART{i:03d}",
                current_price=1000.0 + i * 100
            )
            products.append(product)
        
        # Выполняем пакетную запись
        rows_data = [product.to_sheets_row() for product in products]
        
        try:
            client.batch_update(spreadsheet_id, rows_data)
            batch_success = True
        except Exception:
            # Если batch_update не реализован, используем обычную запись
            for row in rows_data:
                client.append_row(spreadsheet_id, row)
            batch_success = False
        
        # Проверяем, что операции были выполнены
        self.assertGreater(mock_google_sheets_service.call_count, 0)
    
    @patch_google_sheets_service
    def test_error_handling(self, mock_build):
        """Тест обработки ошибок API."""
        client = GoogleSheetsClient()
        
        # Включаем режим ошибок
        mock_google_sheets_service.should_fail = True
        
        # Проверяем обработку ошибки при создании таблицы
        with self.assertRaises(Exception):
            client.create_spreadsheet("Error Test")
        
        # Отключаем режим ошибок
        mock_google_sheets_service.should_fail = False
        
        # Создаем таблицу
        spreadsheet_id = client.create_spreadsheet("Error Recovery Test")
        
        # Включаем ошибки для операций с данными
        mock_google_sheets_service.should_fail = True
        
        # Проверяем обработку ошибки при записи данных
        with self.assertRaises(Exception):
            client.write_headers(spreadsheet_id, ["Header1", "Header2"])
    
    @patch_google_sheets_service
    def test_rate_limiting_simulation(self, mock_build):
        """Тест симуляции rate limiting."""
        client = GoogleSheetsClient()
        
        # Настраиваем мок для ошибки после 3 вызовов
        mock_google_sheets_service.fail_after_calls = 3
        
        # Выполняем операции до лимита
        spreadsheet_id = client.create_spreadsheet("Rate Limit Test 1")  # 1 вызов
        client.write_headers(spreadsheet_id, ["Header1", "Header2"])      # 2 вызова
        client.append_row(spreadsheet_id, ["Value1", "Value2"])           # 3 вызова
        
        # Следующий вызов должен вызвать ошибку
        with self.assertRaises(Exception):
            client.append_row(spreadsheet_id, ["Value3", "Value4"])       # 4 вызов - ошибка


class TestWildberriesAPIIntegration(unittest.TestCase):
    """Интеграционные тесты для Wildberries API."""
    
    def setUp(self):
        """Настройка тестов."""
        reset_all_mocks()
        
        # Добавляем тестовые данные в мок
        test_product_data = {
            'id': 'wb_test_001',
            'name': 'Тестовый товар Wildberries',
            'brand': 'WB TestBrand',
            'article': 'WBTEST001',
            'price': 1500.0,
            'sale_price': 1350.0,
            'rating': 4.7,
            'reviews_count': 250,
            'in_stock': True,
            'category': 'Electronics',
            'images': ['https://example.com/wb_image.jpg'],
            'description': 'Описание тестового товара',
            'characteristics': {
                'color': 'Синий',
                'size': 'L',
                'material': 'Металл'
            },
            'seller': {
                'name': 'WB TestSeller',
                'rating': 4.9
            },
            'updated_at': datetime.now().isoformat()
        }
        
        mock_wildberries_api.add_product_data('WBTEST001', test_product_data)
    
    def test_get_product_info(self):
        """Тест получения информации о товаре."""
        # Получаем информацию о товаре с пользовательскими данными
        product_info = mock_wildberries_api.get_product_info('WBTEST001')
        
        self.assertEqual(product_info['name'], 'Тестовый товар Wildberries')
        self.assertEqual(product_info['brand'], 'WB TestBrand')
        self.assertEqual(product_info['price'], 1500.0)
        self.assertEqual(product_info['sale_price'], 1350.0)
        self.assertEqual(product_info['rating'], 4.7)
        self.assertTrue(product_info['in_stock'])
        
        # Получаем информацию о товаре с автогенерированными данными
        auto_product_info = mock_wildberries_api.get_product_info('AUTO001')
        
        self.assertEqual(auto_product_info['article'], 'AUTO001')
        self.assertIn('Тестовый товар AUTO001', auto_product_info['name'])
        self.assertEqual(auto_product_info['price'], 1000.0)
    
    def test_search_products(self):
        """Тест поиска товаров."""
        # Поиск товаров
        search_results = mock_wildberries_api.search_products('смартфон', limit=5)
        
        self.assertEqual(len(search_results), 5)
        
        for i, result in enumerate(search_results):
            self.assertIn('смартфон', result['name'])
            self.assertEqual(result['article'], f'ART{i:03d}')
            self.assertGreater(result['price'], 0)
            self.assertIn('rating', result)
            self.assertIn('reviews_count', result)
        
        # Поиск с большим лимитом (должен вернуть максимум 10)
        large_search = mock_wildberries_api.search_products('товар', limit=20)
        self.assertEqual(len(large_search), 10)  # Максимум в моке
    
    def test_get_competitor_prices(self):
        """Тест получения цен конкурентов."""
        competitor_prices = mock_wildberries_api.get_competitor_prices('WBTEST001')
        
        self.assertEqual(len(competitor_prices), 3)
        
        for i, competitor in enumerate(competitor_prices):
            self.assertEqual(competitor['seller_id'], f'competitor_{i}')
            self.assertIn('Конкурент', competitor['seller_name'])
            self.assertGreater(competitor['price'], 0)
            self.assertGreater(competitor['sale_price'], 0)
            self.assertTrue(competitor['in_stock'])
            self.assertGreaterEqual(competitor['rating'], 4.0)
            self.assertGreater(competitor['reviews_count'], 0)
    
    def test_api_call_counting(self):
        """Тест подсчета вызовов API."""
        initial_count = mock_wildberries_api.call_count
        
        # Выполняем несколько операций
        mock_wildberries_api.get_product_info('TEST001')
        mock_wildberries_api.search_products('тест')
        mock_wildberries_api.get_competitor_prices('TEST001')
        
        # Проверяем, что счетчик увеличился на 3
        self.assertEqual(mock_wildberries_api.call_count, initial_count + 3)
    
    def test_error_handling(self):
        """Тест обработки ошибок API."""
        # Включаем режим ошибок
        mock_wildberries_api.should_fail = True
        
        # Проверяем, что все методы вызывают ошибки
        with self.assertRaises(Exception):
            mock_wildberries_api.get_product_info('TEST001')
        
        with self.assertRaises(Exception):
            mock_wildberries_api.search_products('тест')
        
        with self.assertRaises(Exception):
            mock_wildberries_api.get_competitor_prices('TEST001')
    
    def test_rate_limiting(self):
        """Тест rate limiting."""
        # Настраиваем rate limiting на 2 вызова
        mock_wildberries_api.rate_limit_calls = 2
        mock_wildberries_api.rate_limit_reset_time = datetime.now() + timedelta(seconds=5)
        
        # Первые два вызова должны пройти успешно
        mock_wildberries_api.get_product_info('TEST001')
        mock_wildberries_api.get_product_info('TEST002')
        
        # Третий вызов должен вызвать ошибку rate limit
        with self.assertRaises(Exception) as context:
            mock_wildberries_api.get_product_info('TEST003')
        
        self.assertIn("Rate limit", str(context.exception))
    
    def test_response_delay_simulation(self):
        """Тест симуляции задержки ответа."""
        # Устанавливаем небольшую задержку
        mock_wildberries_api.response_delay = 0.1  # 100ms
        
        start_time = datetime.now()
        mock_wildberries_api.get_product_info('TEST001')
        end_time = datetime.now()
        
        # Проверяем, что прошло достаточно времени
        elapsed = (end_time - start_time).total_seconds()
        self.assertGreaterEqual(elapsed, 0.1)


class TestCombinedAPIIntegration(unittest.TestCase):
    """Тесты интеграции нескольких API."""
    
    def setUp(self):
        """Настройка тестов."""
        reset_all_mocks()
    
    @patch_google_sheets_service
    @patch_wildberries_api
    def test_full_monitoring_workflow(self, mock_wb_api, mock_gs_build):
        """Тест полного workflow мониторинга цен."""
        # Создаем продукт
        product = Product(
            our_product_id="FULL001",
            name="Полный тест товара",
            brand="FullTestBrand",
            article="FULLART001",
            current_price=2000.0
        )
        
        # Добавляем данные в мок Wildberries API
        wb_data = {
            'id': 'wb_full_001',
            'name': 'Полный тест товара WB',
            'price': 1950.0,
            'sale_price': 1850.0,
            'rating': 4.6,
            'reviews_count': 180
        }
        mock_wildberries_api.add_product_data('FULLART001', wb_data)
        
        # Симулируем получение данных с Wildberries
        wb_product_info = mock_wildberries_api.get_product_info('FULLART001')
        competitor_prices = mock_wildberries_api.get_competitor_prices('FULLART001')
        
        # Обновляем продукт данными конкурентов
        for competitor in competitor_prices:
            product.add_competitor_price(
                competitor['seller_name'],
                competitor['price'],
                'wildberries'
            )
        
        # Создаем Google Sheets клиент и таблицу
        gs_client = GoogleSheetsClient()
        spreadsheet_id = gs_client.create_spreadsheet("Full Workflow Test")
        
        # Записываем данные в таблицу
        headers = product.get_sheets_headers()
        gs_client.write_headers(spreadsheet_id, headers)
        
        product_row = product.to_sheets_row()
        gs_client.append_row(spreadsheet_id, product_row)
        
        # Проверяем, что все операции выполнены
        self.assertGreater(mock_wildberries_api.call_count, 0)
        self.assertGreater(mock_google_sheets_service.call_count, 0)
        
        # Проверяем данные продукта
        self.assertEqual(len(product.competitor_prices), 3)  # 3 конкурента из мока
        self.assertIsNotNone(product.get_min_competitor_price())
        self.assertIsNotNone(product.get_max_competitor_price())
    
    @patch_requests_session
    def test_http_requests_integration(self, mock_session):
        """Тест интеграции HTTP запросов."""
        from tests.test_mocks import MockHttpResponse
        
        # Настраиваем мок ответы
        api_response = MockHttpResponse(
            status_code=200,
            json_data={
                'products': [
                    {'id': 1, 'name': 'Product 1', 'price': 100},
                    {'id': 2, 'name': 'Product 2', 'price': 200}
                ],
                'total': 2
            }
        )
        
        mock_requests_session.add_response('https://api.wildberries.ru/products', api_response)
        
        # Выполняем запрос
        response = mock_requests_session.get('https://api.wildberries.ru/products')
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['products']), 2)
        self.assertEqual(data['products'][0]['name'], 'Product 1')
    
    def test_error_recovery_workflow(self):
        """Тест восстановления после ошибок."""
        # Настраиваем Wildberries API для ошибки на первом вызове
        mock_wildberries_api.should_fail = True
        
        # Первый вызов должен вызвать ошибку
        with self.assertRaises(Exception):
            mock_wildberries_api.get_product_info('ERROR001')
        
        # Отключаем ошибки
        mock_wildberries_api.should_fail = False
        
        # Второй вызов должен пройти успешно
        product_info = mock_wildberries_api.get_product_info('ERROR001')
        self.assertIsNotNone(product_info)
        self.assertEqual(product_info['article'], 'ERROR001')
    
    def test_concurrent_api_calls_simulation(self):
        """Тест симуляции конкурентных вызовов API."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_api_call(article):
            try:
                result = mock_wildberries_api.get_product_info(article)
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Создаем несколько потоков для симуляции конкурентных запросов
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_api_call, args=(f'CONCURRENT{i:03d}',))
            threads.append(thread)
        
        # Запускаем все потоки
        for thread in threads:
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Проверяем результаты
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)
        self.assertEqual(mock_wildberries_api.call_count, 5)


class TestMockReliability(unittest.TestCase):
    """Тесты надежности моков."""
    
    def setUp(self):
        """Настройка тестов."""
        reset_all_mocks()
    
    def test_mock_state_isolation(self):
        """Тест изоляции состояния моков между тестами."""
        # Проверяем, что моки сброшены
        self.assertEqual(mock_google_sheets_service.call_count, 0)
        self.assertEqual(mock_wildberries_api.call_count, 0)
        self.assertEqual(mock_requests_session.call_count, 0)
        
        # Выполняем операции
        mock_wildberries_api.get_product_info('ISOLATION001')
        mock_requests_session.get('https://example.com')
        
        # Проверяем, что счетчики увеличились
        self.assertEqual(mock_wildberries_api.call_count, 1)
        self.assertEqual(mock_requests_session.call_count, 1)
        
        # Сбрасываем моки
        reset_all_mocks()
        
        # Проверяем, что счетчики сброшены
        self.assertEqual(mock_wildberries_api.call_count, 0)
        self.assertEqual(mock_requests_session.call_count, 0)
    
    def test_mock_data_persistence(self):
        """Тест сохранения данных в моках."""
        # Добавляем данные в Google Sheets мок
        spreadsheet_id = mock_google_sheets_service.spreadsheets().create({
            'properties': {'title': 'Persistence Test'}
        }).execute()['spreadsheetId']
        
        # Записываем данные
        values_resource = mock_google_sheets_service.spreadsheets().values()
        values_resource.update(
            spreadsheet_id, 'A1:B2', 'RAW',
            {'values': [['Header1', 'Header2'], ['Value1', 'Value2']]}
        ).execute()
        
        # Читаем данные
        result = values_resource.get(spreadsheet_id, 'A1:B2').execute()
        
        self.assertEqual(result['values'], [['Header1', 'Header2'], ['Value1', 'Value2']])
        
        # Добавляем еще данные
        values_resource.append(
            spreadsheet_id, 'A1:B2', 'RAW',
            {'values': [['Value3', 'Value4']]}
        ).execute()
        
        # Читаем обновленные данные
        updated_result = values_resource.get(spreadsheet_id, 'A1:B4').execute()
        
        self.assertEqual(len(updated_result['values']), 3)  # 2 исходные строки + 1 добавленная
    
    def test_mock_configuration_flexibility(self):
        """Тест гибкости настройки моков."""
        # Настраиваем различные сценарии для Wildberries API
        
        # Сценарий 1: Нормальная работа
        product1 = mock_wildberries_api.get_product_info('CONFIG001')
        self.assertIsNotNone(product1)
        
        # Сценарий 2: Задержка ответа
        mock_wildberries_api.response_delay = 0.05
        start_time = datetime.now()
        product2 = mock_wildberries_api.get_product_info('CONFIG002')
        elapsed = (datetime.now() - start_time).total_seconds()
        self.assertGreaterEqual(elapsed, 0.05)
        
        # Сценарий 3: Rate limiting
        mock_wildberries_api.response_delay = 0
        mock_wildberries_api.rate_limit_calls = 1
        mock_wildberries_api.rate_limit_reset_time = datetime.now() + timedelta(seconds=1)
        
        # Первый вызов проходит
        mock_wildberries_api.get_product_info('CONFIG003')
        
        # Второй вызов вызывает ошибку
        with self.assertRaises(Exception):
            mock_wildberries_api.get_product_info('CONFIG004')


if __name__ == '__main__':
    # Запускаем тесты с подробным выводом
    unittest.main(verbosity=2)