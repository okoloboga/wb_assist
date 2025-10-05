"""
Упрощенные тесты для проверки API ключа
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery

from middleware.api_key_check import APIKeyCheckMiddleware
from api.client import BotAPIResponse


class TestAPIKeySimple:
    """Упрощенные тесты для проверки API ключа"""
    
    @pytest.fixture
    def middleware(self):
        """Фикстура для middleware"""
        return APIKeyCheckMiddleware()
    
    @pytest.fixture
    def mock_message(self):
        """Фикстура для сообщения"""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "test message"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_handler(self):
        """Фикстура для обработчика"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_start_command_bypassed(self, middleware, mock_message, mock_handler):
        """Тест: команда /start пропускается без проверки"""
        mock_message.text = "/start"
        
        with patch.object(middleware, '_check_api_key', return_value=False):
            result = await middleware(mock_handler, mock_message, {})
            
            # /start команда должна быть пропущена
            mock_handler.assert_called_once_with(mock_message, {})
    
    @pytest.mark.asyncio
    async def test_user_with_api_key_allowed(self, middleware, mock_message, mock_handler):
        """Тест: пользователь с API ключом получает доступ"""
        mock_message.text = "test message"
        
        with patch.object(middleware, '_check_api_key', return_value=True):
            result = await middleware(mock_handler, mock_message, {})
            
            mock_handler.assert_called_once_with(mock_message, {})
            assert 123 in middleware._checked_users
    
    @pytest.mark.asyncio
    async def test_user_without_api_key_blocked(self, middleware, mock_message, mock_handler):
        """Тест: пользователь без API ключа блокируется"""
        mock_message.text = "test message"
        
        with patch.object(middleware, '_check_api_key', return_value=False):
            with patch.object(middleware, '_block_user_access') as mock_block:
                result = await middleware(mock_handler, mock_message, {})
                
                # Обработчик не должен быть вызван
                mock_handler.assert_not_called()
                # Должна быть вызвана блокировка
                mock_block.assert_called_once_with(mock_message, 123)
    
    @pytest.mark.asyncio
    async def test_check_api_key_success(self, middleware):
        """Тест: успешная проверка API ключа"""
        with patch('middleware.api_key_check.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                data={'cabinets': [{'id': 'cabinet_1'}]}
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await middleware._check_api_key(123)
            
            assert result is True
            mock_client.get_cabinet_status.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_check_api_key_no_cabinets(self, middleware):
        """Тест: проверка API ключа без кабинетов"""
        with patch('middleware.api_key_check.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                data={'cabinets': []}
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await middleware._check_api_key(123)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_api_key_failure(self, middleware):
        """Тест: неуспешная проверка API ключа"""
        with patch('middleware.api_key_check.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="API error"
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await middleware._check_api_key(123)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_api_key_exception(self, middleware):
        """Тест: исключение при проверке API ключа"""
        with patch('middleware.api_key_check.bot_api_client') as mock_client:
            mock_client.get_cabinet_status = AsyncMock(side_effect=Exception("Network error"))
            
            result = await middleware._check_api_key(123)
            
            assert result is False
    
    def test_clear_user_cache(self, middleware):
        """Тест: очистка кэша пользователя"""
        # Добавляем пользователя в кэш
        middleware._checked_users.add(123)
        assert 123 in middleware._checked_users
        
        # Очищаем кэш
        middleware.clear_user_cache(123)
        assert 123 not in middleware._checked_users