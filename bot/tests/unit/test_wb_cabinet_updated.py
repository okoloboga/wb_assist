"""
Тесты для обновленных обработчиков WB кабинета
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User, Chat, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.wb_cabinet import (
    process_initial_api_key,
    handle_initial_connection_error,
    process_api_key,
    handle_connection_error,
    start_wb_connection,
    check_cabinet_status,
    disconnect_cabinet
)
from api.client import BotAPIResponse
from core.states import WBCabinetStates, WBConnectionStates


class TestWBCabinetUpdated:
    """Тесты для обновленных обработчиков WB кабинета"""
    
    @pytest.fixture
    def mock_message(self):
        """Фикстура для сообщения"""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=123, type="private")
        message = MagicMock(spec=Message)
        message.from_user = user
        message.chat = chat
        message.text = "test_api_key_12345"
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
    def mock_state(self):
        """Фикстура для FSM состояния"""
        state = AsyncMock(spec=FSMContext)
        return state
    
    @pytest.mark.asyncio
    async def test_process_initial_api_key_success(self, mock_message, mock_state):
        """Тест: успешная обработка API ключа при первичной регистрации"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="✅ Кабинет успешно подключен!"
            )
            mock_client.connect_wb_cabinet = AsyncMock(return_value=mock_response)
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_state, 'clear') as mock_clear:
                    with patch.object(mock_message, 'answer') as mock_answer:
                        await process_initial_api_key(mock_message, mock_state)
                        
                        # Проверяем вызовы
                        mock_client.connect_wb_cabinet.assert_called_once_with(
                            user_id=123,
                            api_key="test_api_key_12345"
                        )
                        mock_set_state.assert_called_once_with(WBCabinetStates.validating_key)
                        mock_clear.assert_called_once()
                        mock_answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_initial_api_key_failure(self, mock_message, mock_state):
        """Тест: неуспешная обработка API ключа при первичной регистрации"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="Invalid API key",
                status_code=400
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_message, 'answer') as mock_answer:
                    await process_initial_api_key(mock_message, mock_state)
                    
                    # Проверяем вызовы
                    mock_client.connect_wb_cabinet.assert_called_once()
                    mock_set_state.assert_any_call(WBCabinetStates.connection_error)
                    mock_set_state.assert_any_call(WBCabinetStates.waiting_for_api_key)
                    mock_answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_initial_api_key_cancel(self, mock_message, mock_state):
        """Тест: отмена ввода API ключа при первичной регистрации"""
        mock_message.text = "/cancel"
        
        with patch.object(mock_state, 'clear') as mock_clear:
            with patch.object(mock_message, 'answer') as mock_answer:
                await process_initial_api_key(mock_message, mock_state)
                
                mock_clear.assert_called_once()
                mock_answer.assert_called_once()
                call_args = mock_answer.call_args
                assert "Подключение отменено" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_process_initial_api_key_short(self, mock_message, mock_state):
        """Тест: слишком короткий API ключ при первичной регистрации"""
        mock_message.text = "short"
        
        with patch.object(mock_message, 'answer') as mock_answer:
            await process_initial_api_key(mock_message, mock_state)
            
            mock_answer.assert_called_once()
            call_args = mock_answer.call_args
            assert "API ключ слишком короткий" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_handle_initial_connection_error(self, mock_message, mock_state):
        """Тест: обработка ошибки подключения при первичной регистрации"""
        with patch('handlers.wb_cabinet.process_initial_api_key') as mock_process:
            await handle_initial_connection_error(mock_message, mock_state)
            
            mock_state.set_state.assert_called_once_with(WBCabinetStates.waiting_for_api_key)
            mock_process.assert_called_once_with(mock_message, mock_state)
    
    @pytest.mark.asyncio
    async def test_process_api_key_success(self, mock_message, mock_state):
        """Тест: успешная обработка API ключа в обычном режиме"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="✅ Кабинет успешно подключен!"
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_state, 'clear') as mock_clear:
                    with patch.object(mock_message, 'answer') as mock_answer:
                        await process_api_key(mock_message, mock_state)
                        
                        # Проверяем вызовы
                        mock_client.connect_wb_cabinet.assert_called_once_with(
                            user_id=123,
                            api_key="test_api_key_12345"
                        )
                        mock_set_state.assert_called_once_with(WBConnectionStates.connection_success)
                        mock_clear.assert_called_once()
                        mock_answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_api_key_failure(self, mock_message, mock_state):
        """Тест: неуспешная обработка API ключа в обычном режиме"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="Invalid API key",
                status_code=400
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_message, 'answer') as mock_answer:
                    await process_api_key(mock_message, mock_state)
                    
                    # Проверяем вызовы
                    mock_client.connect_wb_cabinet.assert_called_once()
                    mock_set_state.assert_any_call(WBConnectionStates.connection_error)
                    mock_set_state.assert_any_call(WBConnectionStates.waiting_for_api_key)
                    mock_answer.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_connection_error(self, mock_message, mock_state):
        """Тест: обработка ошибки подключения в обычном режиме"""
        with patch('handlers.wb_cabinet.process_api_key') as mock_process:
            await handle_connection_error(mock_message, mock_state)
            
            mock_state.set_state.assert_called_once_with(WBConnectionStates.waiting_for_api_key)
            mock_process.assert_called_once_with(mock_message, mock_state)
    
    @pytest.mark.asyncio
    async def test_start_wb_connection(self, mock_callback_query, mock_state):
        """Тест: начало процесса подключения WB кабинета"""
        with patch.object(mock_state, 'set_state') as mock_set_state:
            with patch.object(mock_callback_query.message, 'edit_text') as mock_edit:
                await start_wb_connection(mock_callback_query, mock_state)
                
                mock_set_state.assert_called_once_with(WBConnectionStates.waiting_for_api_key)
                mock_edit.assert_called_once()
                mock_callback_query.answer.assert_called_once()
                
                # Проверяем содержимое сообщения
                call_args = mock_edit.call_args
                assert "ПОДКЛЮЧЕНИЕ WB КАБИНЕТА" in call_args[0][0]
                assert "Как получить API ключ" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_check_cabinet_status_success(self, mock_callback_query):
        """Тест: успешная проверка статуса кабинета"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="📊 Статус кабинетов получен"
            )
            mock_client.get_cabinet_status.return_value = mock_response
            
            with patch.object(mock_callback_query.message, 'edit_text') as mock_edit:
                await check_cabinet_status(mock_callback_query)
                
                mock_client.get_cabinet_status.assert_called_once_with(user_id=123)
                mock_edit.assert_called_once()
                mock_callback_query.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_cabinet_status_failure(self, mock_callback_query):
        """Тест: неуспешная проверка статуса кабинета"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=False,
                error="API error",
                status_code=500
            )
            mock_client.get_cabinet_status.return_value = mock_response
            
            with patch.object(mock_callback_query.message, 'edit_text') as mock_edit:
                await check_cabinet_status(mock_callback_query)
                
                mock_client.get_cabinet_status.assert_called_once_with(user_id=123)
                mock_edit.assert_called_once()
                mock_callback_query.answer.assert_called_once()
                
                # Проверяем содержимое сообщения об ошибке
                call_args = mock_edit.call_args
                assert "Ошибка получения статуса" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_disconnect_cabinet(self, mock_callback_query):
        """Тест: отключение кабинета"""
        with patch.object(mock_callback_query.message, 'edit_text') as mock_edit:
            await disconnect_cabinet(mock_callback_query)
            
            mock_edit.assert_called_once()
            mock_callback_query.answer.assert_called_once()
            
            # Проверяем содержимое сообщения
            call_args = mock_edit.call_args
            assert "ОТКЛЮЧЕНИЕ КАБИНЕТА" in call_args[0][0]
            assert "Функция отключения кабинета будет доступна" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_process_initial_api_key_validation_state(self, mock_message, mock_state):
        """Тест: переход в состояние валидации при первичной регистрации"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="✅ Кабинет успешно подключен!"
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_message, 'answer') as mock_answer:
                    await process_initial_api_key(mock_message, mock_state)
                    
                    # Проверяем переход в состояние валидации
                    mock_set_state.assert_any_call(WBCabinetStates.validating_key)
    
    @pytest.mark.asyncio
    async def test_process_api_key_validation_state(self, mock_message, mock_state):
        """Тест: переход в состояние валидации в обычном режиме"""
        with patch('handlers.wb_cabinet.bot_api_client') as mock_client:
            mock_response = BotAPIResponse(
                success=True,
                telegram_text="✅ Кабинет успешно подключен!"
            )
            mock_client.connect_wb_cabinet.return_value = mock_response
            
            with patch.object(mock_state, 'set_state') as mock_set_state:
                with patch.object(mock_message, 'answer') as mock_answer:
                    await process_api_key(mock_message, mock_state)
                    
                    # Проверяем переход в состояние валидации
                    mock_set_state.assert_any_call(WBConnectionStates.validating_key)