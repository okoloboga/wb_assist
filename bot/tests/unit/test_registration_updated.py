"""
Тесты для обновленной логики регистрации с проверкой API ключа
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat
from aiogram.fsm.context import FSMContext

from handlers.registration import register_user, _check_user_api_key, _require_api_key
from api.client import BotAPIResponse
from core.states import WBCabinetStates


class TestRegistrationUpdated:
    """Тесты для обновленной логики регистрации"""
    
    @pytest.fixture
    def mock_message(self):
        """Фикстура для сообщения"""
        user = User(id=123, is_bot=False, first_name="Test", username="testuser")
        chat = Chat(id=123, type="private")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "/start"
        message.answer = AsyncMock()
        return message
    
    @pytest.fixture
    def mock_state(self):
        """Фикстура для FSM состояния"""
        state = AsyncMock(spec=FSMContext)
        return state
    
    @pytest.mark.asyncio
    async def test_register_user_success_with_api_key(self, mock_message, mock_state):
        """Тест: успешная регистрация пользователя с API ключом"""
        with patch('handlers.registration.register_user_on_server', return_value=(200, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=True) as mock_check:
                with patch.object(mock_message, 'answer') as mock_answer:
                    await register_user(mock_message, mock_state)
                    
                    # Проверяем вызовы
                    mock_register.assert_called_once()
                    mock_check.assert_called_once_with(123)
                    mock_answer.assert_called_once()
                    
                    # Проверяем содержимое ответа
                    call_args = mock_answer.call_args
                    assert "Добро пожаловать обратно!" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_register_user_success_without_api_key(self, mock_message, mock_state):
        """Тест: регистрация пользователя без API ключа"""
        with patch('handlers.registration.register_user_on_server', return_value=(201, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=False) as mock_check:
                with patch('handlers.registration._require_api_key') as mock_require:
                    await register_user(mock_message, mock_state)
                    
                    # Проверяем вызовы
                    mock_register.assert_called_once()
                    mock_check.assert_called_once_with(123)
                    mock_require.assert_called_once_with(mock_message, "Test", mock_state)
    
    @pytest.mark.asyncio
    async def test_register_user_server_error_503(self, mock_message, mock_state):
        """Тест: ошибка сервера 503 при регистрации"""
        with patch('handlers.registration.register_user_on_server', return_value=(503, {})) as mock_register:
            with patch.object(mock_message, 'answer') as mock_answer:
                await register_user(mock_message, mock_state)
                
                mock_answer.assert_called_once()
                call_args = mock_answer.call_args
                assert "Не удалось связаться с сервером" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_register_user_server_error_other(self, mock_message, mock_state):
        """Тест: другая ошибка сервера при регистрации"""
        with patch('handlers.registration.register_user_on_server', return_value=(500, {})) as mock_register:
            with patch.object(mock_message, 'answer') as mock_answer:
                await register_user(mock_message, mock_state)
                
                mock_answer.assert_called_once()
                call_args = mock_answer.call_args
                assert "Произошла непредвиденная ошибка" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_check_user_api_key_success(self):
        """Тест: успешная проверка API ключа пользователя"""
        with patch('handlers.registration.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                data={'cabinets': [{'id': 'cabinet_1'}]}
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await _check_user_api_key(123)
            
            assert result is True
            mock_client.get_cabinet_status.assert_called_once_with(123)
    
    @pytest.mark.asyncio
    async def test_check_user_api_key_no_cabinets(self):
        """Тест: проверка API ключа без кабинетов"""
        with patch('handlers.registration.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                data={'cabinets': []}
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await _check_user_api_key(123)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_api_key_failure(self):
        """Тест: неуспешная проверка API ключа"""
        with patch('handlers.registration.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="API error"
            )
            mock_client.get_cabinet_status = AsyncMock(return_value=mock_response)
            
            result = await _check_user_api_key(123)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_api_key_exception(self):
        """Тест: исключение при проверке API ключа"""
        with patch('handlers.registration.bot_api_client') as mock_client:
            mock_client.get_cabinet_status = AsyncMock(side_effect=Exception("Network error"))
            
            result = await _check_user_api_key(123)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_require_api_key(self, mock_message, mock_state):
        """Тест: требование ввода API ключа"""
        with patch.object(mock_state, 'set_state') as mock_set_state:
            with patch.object(mock_message, 'answer') as mock_answer:
                await _require_api_key(mock_message, "Test", mock_state)
                
                # Проверяем установку состояния
                mock_set_state.assert_called_once_with(WBCabinetStates.waiting_for_api_key)
                
                # Проверяем отправку сообщения
                mock_answer.assert_called_once()
                call_args = mock_answer.call_args
                assert "ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА" in call_args[0][0]
                assert "Как получить API ключ" in call_args[0][0]
                assert call_args[1]['parse_mode'] == "Markdown"
    
    @pytest.mark.asyncio
    async def test_register_user_payload_structure(self, mock_message, mock_state):
        """Тест: структура payload для регистрации"""
        with patch('handlers.registration.register_user_on_server', return_value=(200, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=True):
                with patch.object(mock_message, 'answer'):
                    await register_user(mock_message, mock_state)
                    
                    # Проверяем структуру payload
                    call_args = mock_register.call_args[0][0]
                    assert call_args['telegram_id'] == 123
                    assert call_args['username'] == "testuser"
                    assert call_args['first_name'] == "Test"
                    assert call_args['last_name'] == ""
    
    @pytest.mark.asyncio
    async def test_register_user_missing_last_name(self, mock_message, mock_state):
        """Тест: регистрация без фамилии"""
        # Убираем last_name из пользователя
        mock_message.from_user.last_name = None
        
        with patch('handlers.registration.register_user_on_server', return_value=(200, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=True):
                with patch.object(mock_message, 'answer'):
                    await register_user(mock_message, mock_state)
                    
                    # Проверяем, что last_name установлен в пустую строку
                    call_args = mock_register.call_args[0][0]
                    assert call_args['last_name'] == ""
    
    @pytest.mark.asyncio
    async def test_register_user_missing_username(self, mock_message, mock_state):
        """Тест: регистрация без username"""
        # Убираем username из пользователя
        mock_message.from_user.username = None
        
        with patch('handlers.registration.register_user_on_server', return_value=(200, {})) as mock_register:
            with patch('handlers.registration._check_user_api_key', return_value=True):
                with patch.object(mock_message, 'answer'):
                    await register_user(mock_message, mock_state)
                    
                    # Проверяем, что username установлен в пустую строку
                    call_args = mock_register.call_args[0][0]
                    assert call_args['username'] == ""