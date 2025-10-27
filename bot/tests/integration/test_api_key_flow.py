"""
Интеграционные тесты для полного flow проверки API ключа
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery
from aiogram.fsm.context import FSMContext

from middleware.api_key_check import APIKeyCheckMiddleware
from handlers.registration import register_user
from handlers.wb_cabinet import process_initial_api_key
from api.client import BotAPIResponse
from core.states import WBCabinetStates


class TestAPIKeyFlow:
    """Интеграционные тесты для полного flow с API ключом"""
    
    @pytest.fixture
    def mock_user_with_api_key(self):
        """Фикстура пользователя с API ключом"""
        return User(
            id=12345,
            is_bot=False,
            first_name="Test",
            last_name="User",
            username="testuser",
            language_code="ru"
        )
    
    @pytest.fixture
    def mock_user_without_api_key(self):
        """Фикстура пользователя без API ключа"""
        return User(
            id=54321,
            is_bot=False,
            first_name="New",
            last_name="User",
            username="newuser",
            language_code="ru"
        )
    
    @pytest.fixture
    def mock_chat(self):
        """Фикстура чата"""
        return Chat(id=12345, type="private")
    
    @pytest.fixture
    def mock_message_with_api_key(self, mock_user_with_api_key, mock_chat):
        """Фикстура сообщения от пользователя с API ключом"""
        message = MagicMock(spec=Message)
        message.from_user = mock_user_with_api_key
        message.chat = mock_chat
        message.text = "test message"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_message_without_api_key(self, mock_user_without_api_key, mock_chat):
        """Фикстура сообщения от пользователя без API ключа"""
        message = MagicMock(spec=Message)
        message.from_user = mock_user_without_api_key
        message.chat = mock_chat
        message.text = "test message"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_start_message(self, mock_user_without_api_key, mock_chat):
        """Фикстура сообщения /start"""
        message = MagicMock(spec=Message)
        message.from_user = mock_user_without_api_key
        message.chat = mock_chat
        message.text = "/start"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_api_key_message(self, mock_user_without_api_key, mock_chat):
        """Фикстура сообщения с API ключом"""
        message = MagicMock(spec=Message)
        message.from_user = mock_user_without_api_key
        message.chat = mock_chat
        message.text = "test_api_key_12345"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_state(self):
        """Фикстура FSM состояния"""
        state = AsyncMock(spec=FSMContext)
        return state
    
    @pytest.fixture
    def middleware(self):
        """Фикстура middleware"""
        return APIKeyCheckMiddleware()
    
    @pytest.fixture
    def mock_handler(self):
        """Фикстура обработчика"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_full_flow_new_user_without_api_key(self, mock_start_message, mock_api_key_message, mock_state, middleware, mock_handler):
        """Тест: полный flow для нового пользователя без API ключа"""
        
        # 1. Пользователь отправляет /start
        with patch('handlers.registration.register_user_on_server', return_value=(201, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=False) as mock_check:
                with patch('handlers.registration._require_api_key') as mock_require:
                    await register_user(mock_start_message, mock_state)
                    
                    # Проверяем, что пользователь зарегистрирован
                    mock_register.assert_called_once()
                    # Проверяем, что API ключ не найден
                    mock_check.assert_called_once_with(54321)
                    # Проверяем, что требуется ввод API ключа
                    mock_require.assert_called_once()
        
        # 2. Middleware блокирует обычные сообщения
        with patch.object(middleware, '_check_api_key', return_value=False):
            with patch.object(middleware, '_block_user_access') as mock_block:
                mock_start_message.text = "test message"
                await middleware(mock_handler, mock_start_message, {})
                
                # Обработчик не должен быть вызван
                mock_handler.assert_not_called()
                # Должна быть вызвана блокировка
                mock_block.assert_called_once()
        
        # 3. Пользователь вводит API ключ
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="✅ Кабинет успешно подключен!"
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_state, 'clear') as mock_clear:
                    await process_initial_api_key(mock_api_key_message, mock_state)
                    
                    # Проверяем подключение кабинета
                    mock_client.connect_wb_cabinet.assert_called_once_with(
                        user_id=54321,
                        api_key="test_api_key_12345"
                    )
                    # Проверяем очистку состояния
                    mock_clear.assert_called_once()
        
        # 4. После подключения middleware пропускает запросы
        with patch.object(middleware, '_check_api_key', return_value=True):
            await middleware(mock_handler, mock_start_message, {})
            
            # Теперь обработчик должен быть вызван
            mock_handler.assert_called_once_with(mock_start_message, {})
    
    @pytest.mark.asyncio
    async def test_full_flow_existing_user_with_api_key(self, mock_message_with_api_key, mock_state, middleware, mock_handler):
        """Тест: полный flow для существующего пользователя с API ключом"""
        
        # 1. Пользователь отправляет /start
        with patch('handlers.registration.register_user_on_server', return_value=(200, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=True) as mock_check:
                with patch.object(mock_message_with_api_key, 'answer') as mock_answer:
                    await register_user(mock_message_with_api_key, mock_state)
                    
                    # Проверяем, что пользователь найден
                    mock_register.assert_called_once()
                    # Проверяем, что API ключ найден
                    mock_check.assert_called_once_with(12345)
                    # Проверяем приветствие
                    mock_answer.assert_called_once()
        
        # 2. Middleware пропускает запросы
        with patch.object(middleware, '_check_api_key', return_value=True):
            await middleware(mock_handler, mock_message_with_api_key, {})
            
            # Обработчик должен быть вызван
            mock_handler.assert_called_once_with(mock_message_with_api_key, {})
    
    @pytest.mark.asyncio
    async def test_middleware_caching(self, mock_message_with_api_key, middleware, mock_handler):
        """Тест: кэширование в middleware"""
        
        # Первый запрос - проверяем API ключ
        with patch.object(middleware, '_check_api_key', return_value=True) as mock_check:
            await middleware(mock_handler, mock_message_with_api_key, {})
            
            # Проверка должна быть вызвана
            mock_check.assert_called_once_with(12345)
            # Пользователь должен быть добавлен в кэш
            assert 12345 in middleware._checked_users
        
        # Второй запрос - проверка не должна вызываться
        with patch.object(middleware, '_check_api_key') as mock_check:
            await middleware(mock_handler, mock_message_with_api_key, {})
            
            # Проверка не должна быть вызвана
            mock_check.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_api_key_validation_failure(self, mock_api_key_message, mock_state):
        """Тест: неуспешная валидация API ключа"""
        
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="Invalid API key",
                status_code=400
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_api_key_message, 'answer') as mock_answer:
                    await process_initial_api_key(mock_api_key_message, mock_state)
                    
                    # Проверяем, что состояние переходит в ошибку
                    mock_set_state.assert_any_call(WBCabinetStates.connection_error)
                    # Проверяем, что состояние возвращается к ожиданию ключа
                    mock_set_state.assert_any_call(WBCabinetStates.waiting_for_api_key)
                    # Проверяем отправку сообщения об ошибке
                    mock_answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_short_api_key_rejection(self, mock_state):
        """Тест: отклонение слишком короткого API ключа"""
        
        mock_message = MagicMock(spec=Message)
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.text = "short"
        mock_message.answer = AsyncMock()
        
        with patch.object(mock_message, 'answer') as mock_answer:
            await process_initial_api_key(mock_message, mock_state)
            
            # Проверяем отправку сообщения об ошибке
            mock_answer.assert_called_once()
            call_args = mock_answer.call_args
            assert "API ключ слишком короткий" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_cancel_api_key_input(self, mock_state):
        """Тест: отмена ввода API ключа"""
        
        mock_message = MagicMock(spec=Message)
        mock_message.from_user = MagicMock()
        mock_message.from_user.id = 12345
        mock_message.text = "/cancel"
        mock_message.answer = AsyncMock()
        
        with patch.object(mock_state, 'clear') as mock_clear:
            with patch.object(mock_message, 'answer') as mock_answer:
                await process_initial_api_key(mock_message, mock_state)
                
                # Проверяем очистку состояния
                mock_clear.assert_called_once()
                # Проверяем отправку сообщения об отмене
                mock_answer.assert_called_once()
                call_args = mock_answer.call_args
                assert "Подключение отменено" in call_args[0][0]