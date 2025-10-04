import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from app.features.wb_api.client import WBAPIClient
from app.features.wb_api.models import WBCabinet


class TestWBAPIClient:
    """Тесты WB API Client"""

    def test_client_initialization(self):
        """Тест инициализации клиента"""
        cabinet = WBCabinet(
            id=1,
            api_key="test-api-key",
            cabinet_name="Test Cabinet"
        )
        
        client = WBAPIClient(cabinet)
        
        assert client.cabinet == cabinet
        assert client.api_key == "test-api-key"
        assert client.base_urls == {
            "marketplace": "https://marketplace-api.wildberries.ru",
            "statistics": "https://statistics-api.wildberries.ru",
            "content": "https://content-api.wildberries.ru",
            "feedbacks": "https://feedbacks-api.wildberries.ru",
            "common": "https://common-api.wildberries.ru"
        }

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self):
        """Тест успешной валидации API ключа"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"warehouseId": 658434, "name": "Коледино"}]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await client.validate_api_key()
            
            assert result is True
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self):
        """Тест неудачной валидации API ключа"""
        cabinet = WBCabinet(api_key="invalid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await client.validate_api_key()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_warehouses_success(self):
        """Тест успешного получения складов"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "warehouseId": 658434,
                "name": "Коледино",
                "address": "Московская область, г. Коледино"
            }
        ]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            warehouses = await client.get_warehouses()
            
            assert len(warehouses) == 1
            assert warehouses[0]["warehouseId"] == 658434
            assert warehouses[0]["name"] == "Коледино"

    @pytest.mark.asyncio
    async def test_get_products_success(self):
        """Тест успешного получения товаров"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "cards": [
                {
                    "nmId": 525760326,
                    "vendorCode": "ART001",
                    "brand": "Test Brand",
                    "title": "Test Product",
                    "sizes": [{"name": "M"}, {"name": "L"}],
                    "characteristics": [{"name": "Цвет", "value": "зеленый"}]
                }
            ]
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            products = await client.get_products()
            
            assert len(products) == 1
            assert products[0]["nmId"] == 525760326
            assert products[0]["vendorCode"] == "ART001"

    @pytest.mark.asyncio
    async def test_get_orders_success(self):
        """Тест успешного получения заказов"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-10-04T12:00:00Z",
                "lastChangeDate": "2024-10-04T12:30:00Z",
                "nmId": 525760326,
                "supplierArticle": "ART001",
                "totalPrice": 1500.0,
                "discountPercent": 10,
                "finishedPrice": 1350.0,
                "isCancel": False,
                "isRealization": True
            }
        ]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            orders = await client.get_orders(
                date_from="2024-01-01",
                date_to="2024-12-31"
            )
            
            assert len(orders) == 1
            assert orders[0]["nmId"] == 525760326
            assert orders[0]["totalPrice"] == 1500.0

    @pytest.mark.asyncio
    async def test_get_stocks_success(self):
        """Тест успешного получения остатков"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "lastChangeDate": "2024-10-04T10:00:00Z",
                "nmId": 525760326,
                "supplierArticle": "ART001",
                "quantity": 50,
                "warehouseName": "Коледино",
                "price": 1500.0,
                "discount": 10.0
            }
        ]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            stocks = await client.get_stocks(
                date_from="2024-01-01",
                date_to="2024-12-31"
            )
            
            assert len(stocks) == 1
            assert stocks[0]["nmId"] == 525760326
            assert stocks[0]["quantity"] == 50

    @pytest.mark.asyncio
    async def test_get_reviews_success(self):
        """Тест успешного получения отзывов"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "countUnanswered": 5,
                "countArchive": 100,
                "feedbacks": [
                    {
                        "id": "rev123",
                        "text": "Отличный товар!",
                        "productValuation": 5,
                        "isAnswered": False,
                        "createdDate": "2024-10-04T15:00:00Z"
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            reviews = await client.get_reviews()
            
            assert reviews["data"]["countUnanswered"] == 5
            assert len(reviews["data"]["feedbacks"]) == 1
            assert reviews["data"]["feedbacks"][0]["id"] == "rev123"

    @pytest.mark.asyncio
    async def test_get_questions_success(self):
        """Тест успешного получения вопросов"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "countUnanswered": 3,
                "countArchive": 50,
                "questions": [
                    {
                        "id": "q123",
                        "text": "Какой размер выбрать?",
                        "isAnswered": False,
                        "createdDate": "2024-10-04T16:00:00Z"
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            questions = await client.get_questions()
            
            assert questions["data"]["countUnanswered"] == 3
            assert len(questions["data"]["questions"]) == 1
            assert questions["data"]["questions"][0]["id"] == "q123"

    @pytest.mark.asyncio
    async def test_get_sales_success(self):
        """Тест успешного получения продаж"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-10-04T14:00:00Z",
                "lastChangeDate": "2024-10-04T14:30:00Z",
                "nmId": 525760326,
                "supplierArticle": "ART001",
                "totalPrice": 1350.0,
                "quantity": 1,
                "subject": "Пиджак",
                "brand": "Test Brand"
            }
        ]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            sales = await client.get_sales(
                date_from="2024-01-01T00:00:00",
                flag=0
            )
            
            assert len(sales) == 1
            assert sales[0]["nmId"] == 525760326
            assert sales[0]["totalPrice"] == 1350.0

    @pytest.mark.asyncio
    async def test_get_commissions_success(self):
        """Тест успешного получения комиссий"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "category": "Одежда",
                    "commission": 15.0,
                    "minCommission": 10.0,
                    "maxCommission": 20.0
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            commissions = await client.get_commissions()
            
            assert len(commissions["data"]) == 1
            assert commissions["data"][0]["category"] == "Одежда"
            assert commissions["data"][0]["commission"] == 15.0

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Тест обработки ошибок API"""
        cabinet = WBCabinet(api_key="invalid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception) as exc_info:
                await client.get_warehouses()
            
            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Тест механизма повторных попыток"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        # Первый вызов - ошибка, второй - успех
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [{"warehouseId": 658434}]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_response_error, mock_response_success]
            
            warehouses = await client.get_warehouses()
            
            assert len(warehouses) == 1
            assert mock_get.call_count == 2

    def test_rate_limit_handling(self):
        """Тест обработки rate limits"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        # Проверяем что клиент правильно обрабатывает разные типы rate limits
        assert client.rate_limits["orders"]["requests_per_minute"] == 300
        assert client.rate_limits["stocks"]["requests_per_minute"] == 100
        assert client.rate_limits["products"]["requests_per_minute"] == 10

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Тест параллельных запросов"""
        cabinet = WBCabinet(api_key="valid-key")
        client = WBAPIClient(cabinet)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"warehouseId": 658434}]
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            # Выполняем несколько запросов параллельно
            tasks = [
                client.get_warehouses(),
                client.get_warehouses(),
                client.get_warehouses()
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(len(result) == 1 for result in results)
            assert mock_get.call_count == 3