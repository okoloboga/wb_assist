import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import aiohttp

from api.client import BotAPIClient, BotAPIResponse


class TestBotAPIClient:
    """Тесты для BotAPIClient"""
    
    @pytest.fixture
    def client(self):
        """Фикстура клиента API"""
        with patch.dict('os.environ', {'API_SECRET_KEY': 'test_secret'}):
            return BotAPIClient()
    
    @pytest.mark.asyncio
    async def test_get_dashboard_success(self, client):
        """Тест успешного получения дашборда"""
        mock_response_data = {
            "success": True,
            "data": {"cabinet_name": "Test Cabinet"},
            "telegram_text": "Test dashboard"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response_data)
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            response = await client.get_dashboard(user_id=12345)
            
            assert response.success is True
            assert response.data == {"cabinet_name": "Test Cabinet"}
            assert response.telegram_text == "Test dashboard"
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_dashboard_error(self, client):
        """Тест ошибки получения дашборда"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 500
            mock_resp.json = AsyncMock(return_value={"error": "Server error"})
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            response = await client.get_dashboard(user_id=12345)
            
            assert response.success is False
            assert response.status_code == 500
            assert response.error == "Server error"
    
    @pytest.mark.asyncio
    async def test_get_recent_orders_with_params(self, client):
        """Тест получения заказов с параметрами"""
        mock_response_data = {
            "success": True,
            "data": {"orders": []},
            "telegram_text": "Test orders"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response_data)
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            response = await client.get_recent_orders(
                user_id=12345,
                limit=5,
                offset=10
            )
            
            assert response.success is True
            # Проверяем, что параметры переданы
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]['params'] == {"limit": 5, "offset": 10}
    
    @pytest.mark.asyncio
    async def test_connect_wb_cabinet(self, client):
        """Тест подключения WB кабинета"""
        mock_response_data = {
            "success": True,
            "data": {"cabinet_id": "test_cabinet"},
            "telegram_text": "Cabinet connected"
        }
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response_data)
            mock_request.return_value.__aenter__.return_value = mock_resp
            
            response = await client.connect_wb_cabinet(
                user_id=12345,
                api_key="test_api_key"
            )
            
            assert response.success is True
            # Проверяем, что API ключ передан в JSON
            call_args = mock_request.call_args
            assert call_args[1]['json'] == {"api_key": "test_api_key"}
    
    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        """Тест ошибки соединения"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            # Используем простое исключение для имитации ошибки соединения
            mock_request.side_effect = Exception("Connection failed")
            
            response = await client.get_dashboard(user_id=12345)
            
            assert response.success is False
            assert response.error == "Internal client error"
            assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Тест ошибки таймаута"""
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.side_effect = asyncio.TimeoutError("Request timeout")
            
            response = await client.get_dashboard(user_id=12345)
            
            assert response.success is False
            assert response.error == "Request timeout"
            assert response.status_code == 408


class TestBotAPIResponse:
    """Тесты для BotAPIResponse"""
    
    def test_response_creation(self):
        """Тест создания ответа"""
        response = BotAPIResponse(
            success=True,
            data={"test": "data"},
            telegram_text="Test text",
            error=None,
            status_code=200
        )
        
        assert response.success is True
        assert response.data == {"test": "data"}
        assert response.telegram_text == "Test text"
        assert response.error is None
        assert response.status_code == 200
    
    def test_response_defaults(self):
        """Тест значений по умолчанию"""
        response = BotAPIResponse(success=False)
        
        assert response.success is False
        assert response.data is None
        assert response.telegram_text is None
        assert response.error is None
        assert response.status_code == 200