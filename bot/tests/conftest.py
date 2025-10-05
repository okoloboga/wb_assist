import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram import Bot, Dispatcher
from aiogram.types import User, Chat, Message, CallbackQuery, Update

from core.config import BotConfig


@pytest.fixture
def bot_config():
    """Фикстура конфигурации бота"""
    return BotConfig(
        bot_token="test_token",
        server_host="http://test-server:8000",
        api_secret_key="test_secret",
        debug=True
    )


@pytest.fixture
def mock_bot():
    """Фикстура мок-бота"""
    bot = AsyncMock(spec=Bot)
    bot.token = "test_token"
    return bot


@pytest.fixture
def mock_dp():
    """Фикстура мок-диспетчера"""
    return AsyncMock(spec=Dispatcher)


@pytest.fixture
def mock_user():
    """Фикстура мок-пользователя"""
    return User(
        id=12345,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser",
        language_code="ru"
    )


@pytest.fixture
def mock_chat():
    """Фикстура мок-чата"""
    return Chat(
        id=12345,
        type="private"
    )


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Фикстура мок-сообщения"""
    message = MagicMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "Test message"
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user, mock_chat):
    """Фикстура мок-callback запроса"""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.message = MagicMock(spec=Message)
    callback.message.chat = mock_chat
    callback.message.edit_text = AsyncMock()
    callback.data = "test_callback"
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_update(mock_message):
    """Фикстура мок-обновления"""
    update = MagicMock(spec=Update)
    update.message = mock_message
    update.callback_query = None
    return update


@pytest.fixture
def event_loop():
    """Фикстура event loop для асинхронных тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_api_response():
    """Фикстура мок-ответа API"""
    def _create_response(success=True, data=None, telegram_text=None, error=None, status_code=200):
        from api.client import BotAPIResponse
        return BotAPIResponse(
            success=success,
            data=data or {},
            telegram_text=telegram_text or "Test response",
            error=error,
            status_code=status_code
        )
    return _create_response


@pytest.fixture
def mock_fsm_context():
    """Фикстура мок-FSM контекста"""
    context = AsyncMock()
    context.set_state = AsyncMock()
    context.clear = AsyncMock()
    context.get_state = AsyncMock(return_value=None)
    return context


@pytest.fixture
def mock_user_with_api_key():
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
def mock_user_without_api_key():
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
def mock_cabinet_status_response():
    """Фикстура ответа статуса кабинета"""
    def _create_cabinet_response(has_cabinets=True):
        from api.client import BotAPIResponse
        if has_cabinets:
            data = {
                "cabinets": [
                    {
                        "id": "cabinet_123",
                        "name": "Test Cabinet",
                        "status": "active"
                    }
                ]
            }
        else:
            data = {"cabinets": []}
        
        return BotAPIResponse(
            success=True,
            data=data,
            telegram_text="Cabinet status response"
        )
    return _create_cabinet_response


@pytest.fixture
def mock_connect_cabinet_response():
    """Фикстура ответа подключения кабинета"""
    def _create_connect_response(success=True):
        from api.client import BotAPIResponse
        if success:
            return BotAPIResponse(
                success=True,
                data={
                    "cabinet_id": "cabinet_123",
                    "cabinet_name": "Test Cabinet",
                    "status": "connected"
                },
                telegram_text="✅ Кабинет успешно подключен!"
            )
        else:
            return BotAPIResponse(
                success=False,
                error="Invalid API key",
                status_code=400,
                telegram_text="❌ Ошибка подключения кабинета"
            )
    return _create_connect_response