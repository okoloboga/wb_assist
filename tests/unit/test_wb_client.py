import pytest
import requests
from unittest.mock import Mock, patch
from wb_api.client import WildberriesAPI

class TestWildberriesAPI:
    """Тесты клиента Wildberries API"""
    
    def test_client_initialization(self):
        """Тест инициализации клиента"""
        # 🔴 Тест упадет - класс не существует
        client = WildberriesAPI()
        assert client.api_key is not None
        assert client.base_url == "https://statistics-api.wildberries.ru/api/v1/supplier"
    
    @pytest.mark.asyncio
    async def test_get_orders_success(self):
        """Тест успешного получения заказов"""
        # 🔴 Мокаем API ответ
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [{"nmId": 123456789, "totalPrice": 1500.0}]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            orders = client.get_orders()
            
            # Проверяем что запрос был сделан
            mock_get.assert_called_once()
            assert len(orders) == 1
            assert orders[0]["nmId"] == 123456789
    
    def test_get_orders_with_date_filter(self):
        """Тест получения заказов с фильтром по дате"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            client.get_orders(date_from="2023-10-01")
            
            # Проверяем параметры запроса
            call_args = mock_get.call_args
            params = call_args[1]['params']  # kwargs
            assert params['dateFrom'] == "2023-10-01"
    
    def test_get_orders_api_error(self):
        """Тест обработки ошибки API"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            client = WildberriesAPI()
            orders = client.get_orders()
            
            # Должен вернуть пустой список при ошибке
            assert orders == []
    
    def test_get_stocks_success(self):
        """Тест получения остатков"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [
                {"nmId": 123456789, "quantity": 50, "warehouseName": "Москва"}
            ]
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            stocks = client.get_stocks()
            
            assert len(stocks) == 1
            assert stocks[0]["quantity"] == 50
    
    def test_get_sales_success(self):
        """Тест получения продаж"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [
                {"nmId": 123456789, "totalPrice": 1350.0, "quantity": 1}
            ]
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            sales = client.get_sales()
            
            assert len(sales) == 1
            assert sales[0]["totalPrice"] == 1350.0

    def test_get_prices_success(self):
        """Тест успешного получения цен товаров"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "nmId": 123456789,
                    "price": 1500,
                    "discount": 10,
                    "promoCode": 5
                },
                {
                    "nmId": 987654321,
                    "price": 2000,
                    "discount": 15,
                    "promoCode": 0
                }
            ]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            prices = client.get_prices()
            
            # Проверяем что запрос был сделан к правильному URL
            mock_get.assert_called_once_with(
                "https://discounts-prices-api.wildberries.ru/api/v1/list/goods/filter",
                headers=client.headers,
                timeout=30
            )
            
            # Проверяем результат
            assert len(prices) == 2
            assert prices[0]["nmId"] == 123456789
            assert prices[0]["price"] == 1500
            assert prices[1]["discount"] == 15

    def test_get_prices_api_error(self):
        """Тест обработки ошибки API при получении цен"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            client = WildberriesAPI()
            prices = client.get_prices()
            
            # Должен вернуть пустой список при ошибке
            assert prices == []

    def test_get_prices_empty_response(self):
        """Тест обработки пустого ответа от API цен"""
        with patch('wb_api.client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = None
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            client = WildberriesAPI()
            prices = client.get_prices()
            
            # Должен вернуть пустой список при None ответе
            assert prices == []