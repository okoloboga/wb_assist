"""
Тесты для APIKeyCheckMiddleware
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat
from aiogram.fsm.context import FSMContext

from middleware.api_key_check import APIKeyCheckMiddleware
from api.client import BotAPIResponse


class TestAPIKeyCheckMiddleware:
    """Тесты для middleware проверки API ключа"""
    
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
        message.text = "/start"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_callback_query(self):
        """Фикстура для callback query"""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "test"
        message.edit_text = AsyncMock()
        
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.from_user = user
        callback_query.message = message
        callback_query.answer = AsyncMock()
        return callback_query
    
    @pytest.fixture
    def mock_handler(self):
        """Фикстура для обработчика"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_start_command_bypassed(self, middleware, mock_message, mock_handler):
        """Тест: команда /start пропускается без проверки"""
        with patch.object(middleware, '_check_api_key', return_value=False):
            result = await middleware(mock_handler, mock_message, {})
            
            # /start команда должна быть пропущена
            mock_handler.assert_called_once_with(mock_message, {})
    
    @pytest.mark.asyncio
    async def test_user_with_api_key_allowed(self, middleware, mock_message, mock_handler):
        """Тест: пользователь с API ключом получает доступ"""
        # Изменяем текст сообщения (не /start)
        mock_message.text = "test message"
        
        with patch.object(middleware, '_check_api_key', return_value=True):
            result = await middleware(mock_handler, mock_message, {})
            
            mock_handler.assert_called_once_with(mock_message, {})
            assert 123 in middleware._checked_users
    
    @pytest.mark.asyncio
    async def test_user_without_api_key_blocked(self, middleware, mock_message, mock_handler):
        """Тест: пользователь без API ключа блокируется"""
        # Изменяем текст сообщения (не /start)
        mock_message.text = "test message"
        
        with patch.object(middleware, '_check_api_key', return_value=False):
            with patch.object(middleware, '_block_user_access') as mock_block:
                result = await middleware(mock_handler, mock_message, {})
                
                # Обработчик не должен быть вызван
                mock_handler.assert_not_called()
                # Должна быть вызвана блокировка
                mock_block.assert_called_once_with(mock_message, 123)
    
    @pytest.mark.asyncio
    async def test_cached_user_bypassed(self, middleware, mock_message, mock_handler):
        """Тест: кэшированный пользователь пропускается"""
        # Добавляем пользователя в кэш
        middleware._checked_users.add(123)
        
        with patch.object(middleware, '_check_api_key') as mock_check:
            result = await middleware(mock_handler, mock_message, {})
            
            # Проверка API ключа не должна вызываться
            mock_check.assert_not_called()
            mock_handler.assert_called_once_with(mock_message, {})
    
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
    
    @pytest.mark.asyncio
    async def test_block_user_access_message(self, middleware, mock_message):
        """Тест: блокировка доступа для сообщения"""
        with patch.object(mock_message, 'answer') as mock_answer:
            await middleware._block_user_access(mock_message, 123)
            
            mock_answer.assert_called_once()
            call_args = mock_answer.call_args
            assert "ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА" in call_args[0][0]
            assert call_args[1]['parse_mode'] == "Markdown"
    
    @pytest.mark.asyncio
    async def test_block_user_access_callback(self, middleware, mock_callback_query):
        """Тест: блокировка доступа для callback query"""
        with patch.object(mock_callback_query.message, 'edit_text') as mock_edit:
            with patch.object(mock_callback_query, 'answer') as mock_answer:
                await middleware._block_user_access(mock_callback_query, 123)
                
                mock_edit.assert_called_once()
                mock_answer.assert_called_once()
                call_args = mock_edit.call_args
                assert "ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА" in call_args[0][0]
    
    def test_clear_user_cache(self, middleware):
        """Тест: очистка кэша пользователя"""
        # Добавляем пользователя в кэш
        middleware._checked_users.add(123)
        assert 123 in middleware._checked_users
        
        # Очищаем кэш
        middleware.clear_user_cache(123)
        assert 123 not in middleware._checked_users
    
    def test_clear_user_cache_nonexistent(self, middleware):
        """Тест: очистка кэша несуществующего пользователя"""
        # Пытаемся очистить кэш несуществующего пользователя
        middleware.clear_user_cache(999)
        # Не должно быть ошибки
        assert 999 not in middleware._checked_users