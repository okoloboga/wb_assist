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