"""
Моки для внешних API для unit тестирования.
Этот модуль содержит моки для Google Sheets API, Wildberries API и других внешних сервисов.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import time


class MockGoogleSheetsService:
    """Мок для Google Sheets API сервиса."""
    
    def __init__(self):
        self.spreadsheets_data = {}
        self.call_count = 0
        self.should_fail = False
        self.fail_after_calls = None
        
    def spreadsheets(self):
        """Возвращает мок для spreadsheets ресурса."""
        return MockSpreadsheetsResource(self)
    
    def reset(self):
        """Сброс состояния мока."""
        self.spreadsheets_data = {}
        self.call_count = 0
        self.should_fail = False
        self.fail_after_calls = None


class MockSpreadsheetsResource:
    """Мок для spreadsheets ресурса Google Sheets API."""
    
    def __init__(self, service):
        self.service = service
        
    def create(self, body):
        """Мок создания таблицы."""
        self.service.call_count += 1
        
        if self.service.should_fail or (
            self.service.fail_after_calls and 
            self.service.call_count > self.service.fail_after_calls
        ):
            raise Exception("Google Sheets API Error")
        
        spreadsheet_id = f"mock_sheet_{len(self.service.spreadsheets_data)}"
        
        spreadsheet_data = {
            'spreadsheetId': spreadsheet_id,
            'properties': {
                'title': body.get('properties', {}).get('title', 'Untitled'),
            },
            'sheets': [
                {
                    'properties': {
                        'sheetId': 0,
                        'title': 'Sheet1',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 26
                        }
                    }
                }
            ]
        }
        
        self.service.spreadsheets_data[spreadsheet_id] = spreadsheet_data
        
        return MockExecuteRequest(spreadsheet_data)
    
    def get(self, spreadsheetId, ranges=None, includeGridData=False):
        """Мок получения данных таблицы."""
        self.service.call_count += 1
        
        if self.service.should_fail:
            raise Exception("Google Sheets API Error")
        
        if spreadsheetId not in self.service.spreadsheets_data:
            raise Exception(f"Spreadsheet {spreadsheetId} not found")
        
        return MockExecuteRequest(self.service.spreadsheets_data[spreadsheetId])
    
    def values(self):
        """Возвращает мок для values ресурса."""
        return MockValuesResource(self.service)


class MockValuesResource:
    """Мок для values ресурса Google Sheets API."""
    
    def __init__(self, service):
        self.service = service
        self.values_data = {}
    
    def get(self, spreadsheetId, range):
        """Мок получения значений из диапазона."""
        self.service.call_count += 1
        
        if self.service.should_fail:
            raise Exception("Google Sheets API Error")
        
        key = f"{spreadsheetId}:{range}"
        values = self.values_data.get(key, [])
        
        return MockExecuteRequest({
            'range': range,
            'majorDimension': 'ROWS',
            'values': values
        })
    
    def update(self, spreadsheetId, range, valueInputOption, body):
        """Мок обновления значений в диапазоне."""
        self.service.call_count += 1
        
        if self.service.should_fail:
            raise Exception("Google Sheets API Error")
        
        key = f"{spreadsheetId}:{range}"
        self.values_data[key] = body.get('values', [])
        
        return MockExecuteRequest({
            'spreadsheetId': spreadsheetId,
            'updatedRange': range,
            'updatedRows': len(body.get('values', [])),
            'updatedColumns': len(body.get('values', [[]])[0]) if body.get('values') else 0,
            'updatedCells': len(body.get('values', [])) * len(body.get('values', [[]])[0]) if body.get('values') else 0
        })
    
    def append(self, spreadsheetId, range, valueInputOption, body):
        """Мок добавления значений в диапазон."""
        self.service.call_count += 1
        
        if self.service.should_fail:
            raise Exception("Google Sheets API Error")
        
        key = f"{spreadsheetId}:{range}"
        if key not in self.values_data:
            self.values_data[key] = []
        
        self.values_data[key].extend(body.get('values', []))
        
        return MockExecuteRequest({
            'spreadsheetId': spreadsheetId,
            'tableRange': range,
            'updates': {
                'updatedRange': range,
                'updatedRows': len(body.get('values', [])),
                'updatedColumns': len(body.get('values', [[]])[0]) if body.get('values') else 0,
                'updatedCells': len(body.get('values', [])) * len(body.get('values', [[]])[0]) if body.get('values') else 0
            }
        })
    
    def batchUpdate(self, spreadsheetId, body):
        """Мок пакетного обновления значений."""
        self.service.call_count += 1
        
        if self.service.should_fail:
            raise Exception("Google Sheets API Error")
        
        responses = []
        for request in body.get('valueInputOption', []):
            # Обрабатываем каждый запрос в пакете
            responses.append({
                'updatedRange': request.get('range', ''),
                'updatedRows': 1,
                'updatedColumns': 1,
                'updatedCells': 1
            })
        
        return MockExecuteRequest({
            'spreadsheetId': spreadsheetId,
            'totalUpdatedRows': len(responses),
            'totalUpdatedColumns': len(responses),
            'totalUpdatedCells': len(responses),
            'responses': responses
        })


class MockExecuteRequest:
    """Мок для execute() запроса."""
    
    def __init__(self, response_data):
        self.response_data = response_data
    
    def execute(self):
        """Выполнение запроса."""
        return self.response_data


class MockWildberriesAPI:
    """Мок для Wildberries API."""
    
    def __init__(self):
        self.products_data = {}
        self.call_count = 0
        self.should_fail = False
        self.response_delay = 0
        self.rate_limit_calls = None
        self.rate_limit_reset_time = None
        
    def get_product_info(self, article: str) -> Dict[str, Any]:
        """Мок получения информации о товаре."""
        self.call_count += 1
        
        if self.response_delay > 0:
            time.sleep(self.response_delay)
        
        if self.should_fail:
            raise Exception("Wildberries API Error")
        
        if self.rate_limit_calls and self.call_count > self.rate_limit_calls:
            if not self.rate_limit_reset_time or datetime.now() < self.rate_limit_reset_time:
                raise Exception("Rate limit exceeded")
        
        if article in self.products_data:
            return self.products_data[article]
        
        # Возвращаем мок данные для неизвестного товара
        return {
            'id': f'wb_{article}',
            'name': f'Тестовый товар {article}',
            'brand': 'TestBrand',
            'article': article,
            'price': 1000.0,
            'sale_price': 900.0,
            'rating': 4.5,
            'reviews_count': 150,
            'in_stock': True,
            'category': 'Electronics',
            'images': [f'https://example.com/image_{article}.jpg'],
            'description': f'Описание товара {article}',
            'characteristics': {
                'color': 'Черный',
                'size': 'M',
                'material': 'Пластик'
            },
            'seller': {
                'name': 'TestSeller',
                'rating': 4.8
            },
            'updated_at': datetime.now().isoformat()
        }
    
    def search_products(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Мок поиска товаров."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Wildberries API Error")
        
        # Возвращаем мок результаты поиска
        results = []
        for i in range(min(limit, 10)):  # Максимум 10 результатов для тестов
            results.append({
                'id': f'wb_search_{i}',
                'name': f'{query} товар {i}',
                'brand': f'Brand{i}',
                'article': f'ART{i:03d}',
                'price': 1000.0 + i * 100,
                'sale_price': 900.0 + i * 100,
                'rating': 4.0 + (i % 5) * 0.2,
                'reviews_count': 100 + i * 10,
                'in_stock': i % 3 != 0,  # Некоторые товары не в наличии
                'category': 'Electronics',
                'images': [f'https://example.com/search_image_{i}.jpg']
            })
        
        return results
    
    def get_competitor_prices(self, article: str) -> List[Dict[str, Any]]:
        """Мок получения цен конкурентов."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Wildberries API Error")
        
        # Возвращаем мок цены конкурентов
        competitors = []
        for i in range(3):  # 3 конкурента
            competitors.append({
                'seller_id': f'competitor_{i}',
                'seller_name': f'Конкурент {i}',
                'price': 950.0 + i * 50,
                'sale_price': 900.0 + i * 50,
                'in_stock': True,
                'rating': 4.0 + i * 0.3,
                'reviews_count': 50 + i * 25
            })
        
        return competitors
    
    def add_product_data(self, article: str, data: Dict[str, Any]):
        """Добавление тестовых данных для товара."""
        self.products_data[article] = data
    
    def reset(self):
        """Сброс состояния мока."""
        self.products_data = {}
        self.call_count = 0
        self.should_fail = False
        self.response_delay = 0
        self.rate_limit_calls = None
        self.rate_limit_reset_time = None


class MockHttpResponse:
    """Мок для HTTP ответа."""
    
    def __init__(self, status_code: int = 200, json_data: Dict = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = {}
    
    def json(self):
        """Возвращает JSON данные."""
        if self._json_data:
            return self._json_data
        raise ValueError("No JSON object could be decoded")
    
    def raise_for_status(self):
        """Проверка статуса ответа."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


class MockRequestsSession:
    """Мок для requests.Session."""
    
    def __init__(self):
        self.responses = {}
        self.call_count = 0
        self.should_fail = False
        self.default_response = MockHttpResponse()
    
    def get(self, url, **kwargs):
        """Мок GET запроса."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Network Error")
        
        if url in self.responses:
            return self.responses[url]
        
        return self.default_response
    
    def post(self, url, **kwargs):
        """Мок POST запроса."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Network Error")
        
        if url in self.responses:
            return self.responses[url]
        
        return self.default_response
    
    def add_response(self, url: str, response: MockHttpResponse):
        """Добавление мок ответа для URL."""
        self.responses[url] = response
    
    def reset(self):
        """Сброс состояния мока."""
        self.responses = {}
        self.call_count = 0
        self.should_fail = False


class MockFileSystem:
    """Мок для файловой системы."""
    
    def __init__(self):
        self.files = {}
        self.directories = set()
    
    def exists(self, path: str) -> bool:
        """Проверка существования файла/директории."""
        return path in self.files or path in self.directories
    
    def read_file(self, path: str) -> str:
        """Чтение файла."""
        if path not in self.files:
            raise FileNotFoundError(f"File {path} not found")
        return self.files[path]
    
    def write_file(self, path: str, content: str):
        """Запись файла."""
        self.files[path] = content
    
    def create_directory(self, path: str):
        """Создание директории."""
        self.directories.add(path)
    
    def list_directory(self, path: str) -> List[str]:
        """Список файлов в директории."""
        if path not in self.directories:
            raise FileNotFoundError(f"Directory {path} not found")
        
        # Возвращаем файлы, которые начинаются с пути директории
        files = []
        for file_path in self.files:
            if file_path.startswith(path):
                relative_path = file_path[len(path):].lstrip('/')
                if '/' not in relative_path:  # Только файлы в этой директории
                    files.append(relative_path)
        
        return files
    
    def reset(self):
        """Сброс состояния мока."""
        self.files = {}
        self.directories = set()


# Глобальные экземпляры моков для использования в тестах
mock_google_sheets_service = MockGoogleSheetsService()
mock_wildberries_api = MockWildberriesAPI()
mock_requests_session = MockRequestsSession()
mock_file_system = MockFileSystem()


def reset_all_mocks():
    """Сброс всех моков."""
    mock_google_sheets_service.reset()
    mock_wildberries_api.reset()
    mock_requests_session.reset()
    mock_file_system.reset()


# Декораторы для патчинга в тестах
def patch_google_sheets_service(func):
    """Декоратор для патчинга Google Sheets сервиса."""
    return patch('utils.auth_helper.build', return_value=mock_google_sheets_service)(func)


def patch_wildberries_api(func):
    """Декоратор для патчинга Wildberries API."""
    return patch('utils.wildberries_api.WildberriesAPI', return_value=mock_wildberries_api)(func)


def patch_requests_session(func):
    """Декоратор для патчинга requests.Session."""
    return patch('requests.Session', return_value=mock_requests_session)(func)


def patch_file_operations(func):
    """Декоратор для патчинга файловых операций."""
    def wrapper(*args, **kwargs):
        with patch('os.path.exists', side_effect=mock_file_system.exists), \
             patch('builtins.open', mock_file_system.read_file), \
             patch('os.makedirs', mock_file_system.create_directory), \
             patch('os.listdir', mock_file_system.list_directory):
            return func(*args, **kwargs)
    return wrapper


class TestMocks(unittest.TestCase):
    """Тесты для проверки работы моков."""
    
    def setUp(self):
        """Настройка тестов."""
        reset_all_mocks()
    
    def test_google_sheets_mock(self):
        """Тест мока Google Sheets API."""
        # Создание таблицы
        create_body = {
            'properties': {
                'title': 'Test Spreadsheet'
            }
        }
        
        result = mock_google_sheets_service.spreadsheets().create(create_body).execute()
        
        self.assertIn('spreadsheetId', result)
        self.assertEqual(result['properties']['title'], 'Test Spreadsheet')
        self.assertEqual(mock_google_sheets_service.call_count, 1)
        
        # Получение данных таблицы
        spreadsheet_id = result['spreadsheetId']
        get_result = mock_google_sheets_service.spreadsheets().get(spreadsheet_id).execute()
        
        self.assertEqual(get_result['spreadsheetId'], spreadsheet_id)
        self.assertEqual(mock_google_sheets_service.call_count, 2)
        
        # Работа с values
        values_resource = mock_google_sheets_service.spreadsheets().values()
        
        # Обновление значений
        update_body = {
            'values': [['Header1', 'Header2'], ['Value1', 'Value2']]
        }
        
        update_result = values_resource.update(
            spreadsheet_id, 'A1:B2', 'RAW', update_body
        ).execute()
        
        self.assertEqual(update_result['updatedRows'], 2)
        self.assertEqual(update_result['updatedColumns'], 2)
        
        # Получение значений
        get_values_result = values_resource.get(spreadsheet_id, 'A1:B2').execute()
        
        self.assertEqual(get_values_result['values'], update_body['values'])
    
    def test_google_sheets_mock_errors(self):
        """Тест обработки ошибок в моке Google Sheets API."""
        # Включаем режим ошибок
        mock_google_sheets_service.should_fail = True
        
        with self.assertRaises(Exception):
            mock_google_sheets_service.spreadsheets().create({}).execute()
        
        # Ошибка после определенного количества вызовов
        mock_google_sheets_service.should_fail = False
        mock_google_sheets_service.fail_after_calls = 2
        
        # Первые два вызова должны пройти успешно
        mock_google_sheets_service.spreadsheets().create({}).execute()
        mock_google_sheets_service.spreadsheets().create({}).execute()
        
        # Третий вызов должен вызвать ошибку
        with self.assertRaises(Exception):
            mock_google_sheets_service.spreadsheets().create({}).execute()
    
    def test_wildberries_api_mock(self):
        """Тест мока Wildberries API."""
        # Получение информации о товаре
        product_info = mock_wildberries_api.get_product_info('TEST001')
        
        self.assertEqual(product_info['article'], 'TEST001')
        self.assertIn('name', product_info)
        self.assertIn('price', product_info)
        self.assertEqual(mock_wildberries_api.call_count, 1)
        
        # Поиск товаров
        search_results = mock_wildberries_api.search_products('тест', limit=5)
        
        self.assertEqual(len(search_results), 5)
        self.assertEqual(mock_wildberries_api.call_count, 2)
        
        for result in search_results:
            self.assertIn('тест', result['name'])
        
        # Получение цен конкурентов
        competitor_prices = mock_wildberries_api.get_competitor_prices('TEST001')
        
        self.assertEqual(len(competitor_prices), 3)
        self.assertEqual(mock_wildberries_api.call_count, 3)
        
        for competitor in competitor_prices:
            self.assertIn('seller_name', competitor)
            self.assertIn('price', competitor)
    
    def test_wildberries_api_mock_custom_data(self):
        """Тест мока Wildberries API с пользовательскими данными."""
        # Добавляем пользовательские данные
        custom_data = {
            'id': 'custom_001',
            'name': 'Пользовательский товар',
            'price': 1500.0,
            'brand': 'CustomBrand'
        }
        
        mock_wildberries_api.add_product_data('CUSTOM001', custom_data)
        
        # Получаем данные
        result = mock_wildberries_api.get_product_info('CUSTOM001')
        
        self.assertEqual(result['name'], 'Пользовательский товар')
        self.assertEqual(result['price'], 1500.0)
        self.assertEqual(result['brand'], 'CustomBrand')
    
    def test_wildberries_api_mock_errors(self):
        """Тест обработки ошибок в моке Wildberries API."""
        # Включаем режим ошибок
        mock_wildberries_api.should_fail = True
        
        with self.assertRaises(Exception):
            mock_wildberries_api.get_product_info('TEST001')
        
        # Тест rate limiting
        mock_wildberries_api.should_fail = False
        mock_wildberries_api.rate_limit_calls = 2
        mock_wildberries_api.rate_limit_reset_time = datetime.now() + timedelta(seconds=1)
        
        # Первые два вызова должны пройти успешно
        mock_wildberries_api.get_product_info('TEST001')
        mock_wildberries_api.get_product_info('TEST002')
        
        # Третий вызов должен вызвать ошибку rate limit
        with self.assertRaises(Exception) as context:
            mock_wildberries_api.get_product_info('TEST003')
        
        self.assertIn("Rate limit", str(context.exception))
    
    def test_requests_session_mock(self):
        """Тест мока requests.Session."""
        # Добавляем мок ответ
        mock_response = MockHttpResponse(
            status_code=200,
            json_data={'status': 'success', 'data': 'test'}
        )
        
        mock_requests_session.add_response('https://api.example.com/test', mock_response)
        
        # Выполняем запрос
        response = mock_requests_session.get('https://api.example.com/test')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(mock_requests_session.call_count, 1)
        
        # Тест POST запроса
        post_response = mock_requests_session.post('https://api.example.com/create')
        self.assertEqual(post_response.status_code, 200)  # Дефолтный ответ
        self.assertEqual(mock_requests_session.call_count, 2)
    
    def test_requests_session_mock_errors(self):
        """Тест обработки ошибок в моке requests.Session."""
        # Включаем режим ошибок
        mock_requests_session.should_fail = True
        
        with self.assertRaises(Exception):
            mock_requests_session.get('https://api.example.com/test')
        
        # Тест HTTP ошибки
        mock_requests_session.should_fail = False
        error_response = MockHttpResponse(status_code=404)
        mock_requests_session.add_response('https://api.example.com/notfound', error_response)
        
        response = mock_requests_session.get('https://api.example.com/notfound')
        self.assertEqual(response.status_code, 404)
        
        with self.assertRaises(Exception):
            response.raise_for_status()
    
    def test_file_system_mock(self):
        """Тест мока файловой системы."""
        # Создание директории
        mock_file_system.create_directory('/test/dir')
        self.assertTrue(mock_file_system.exists('/test/dir'))
        
        # Запись файла
        mock_file_system.write_file('/test/dir/file.txt', 'test content')
        self.assertTrue(mock_file_system.exists('/test/dir/file.txt'))
        
        # Чтение файла
        content = mock_file_system.read_file('/test/dir/file.txt')
        self.assertEqual(content, 'test content')
        
        # Список файлов в директории
        files = mock_file_system.list_directory('/test/dir')
        self.assertIn('file.txt', files)
        
        # Ошибка при чтении несуществующего файла
        with self.assertRaises(FileNotFoundError):
            mock_file_system.read_file('/nonexistent/file.txt')


if __name__ == '__main__':
    unittest.main(verbosity=2)