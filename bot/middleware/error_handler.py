import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from core.config import config
from utils.formatters import format_error_message
from keyboards.keyboards import main_keyboard

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramAPIError as e:
            logger.error(f"Telegram API Error: {e}")
            await self._handle_telegram_error(event, e)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await self._handle_general_error(event, e)
    
    async def _handle_telegram_error(self, event: TelegramObject, error: TelegramAPIError):
        """Обработать ошибку Telegram API"""
        if isinstance(event, Message):
            try:
                await event.answer(
                    "❌ Произошла ошибка при отправке сообщения.\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    reply_markup=main_keyboard()
                )
            except:
                pass  # Не можем отправить ответ
        elif isinstance(event, CallbackQuery):
            try:
                await event.answer(
                    "❌ Произошла ошибка при обработке запроса",
                    show_alert=True
                )
            except:
                pass  # Не можем отправить ответ
    
    async def _handle_general_error(self, event: TelegramObject, error: Exception):
        """Обработать общую ошибку"""
        error_message = self._get_user_friendly_error(error)
        
        if isinstance(event, Message):
            try:
                await event.answer(
                    f"❌ Произошла непредвиденная ошибка:\n\n{error_message}\n\n"
                    "Попробуйте позже или обратитесь к администратору.",
                    reply_markup=main_keyboard()
                )
            except:
                pass  # Не можем отправить ответ
        elif isinstance(event, CallbackQuery):
            try:
                await event.answer(
                    f"❌ Ошибка: {error_message}",
                    show_alert=True
                )
            except:
                pass  # Не можем отправить ответ
    
    def _get_user_friendly_error(self, error: Exception) -> str:
        """Получить понятное пользователю сообщение об ошибке"""
        error_type = type(error).__name__
        
        if "ConnectionError" in error_type or "TimeoutError" in error_type:
            return "Проблемы с подключением к серверу. Попробуйте позже."
        elif "ValidationError" in error_type:
            return "Некорректные данные. Проверьте введенную информацию."
        elif "PermissionError" in error_type:
            return "Недостаточно прав для выполнения операции."
        elif "FileNotFoundError" in error_type:
            return "Файл не найден. Обратитесь к администратору."
        else:
            if config.debug:
                return f"{error_type}: {str(error)}"
            else:
                return "Внутренняя ошибка системы. Попробуйте позже."


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящие события
        if isinstance(event, Message):
            logger.info(
                f"Message from {event.from_user.id} (@{event.from_user.username}): "
                f"{event.text[:100] if event.text else 'No text'}"
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                f"Callback from {event.from_user.id} (@{event.from_user.username}): "
                f"{event.data}"
            )
        
        try:
            result = await handler(event, data)
            logger.debug(f"Handler completed successfully for {type(event).__name__}")
            return result
        except Exception as e:
            logger.error(f"Handler failed for {type(event).__name__}: {e}")
            raise


class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты запросов"""
    
    def __init__(self):
        self.user_requests = {}  # В реальном приложении использовать Redis
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if user_id:
            # Простая проверка частоты запросов (1 запрос в секунду)
            import time
            current_time = time.time()
            
            if user_id in self.user_requests:
                last_request = self.user_requests[user_id]
                if current_time - last_request < 1.0:  # 1 секунда
                    if isinstance(event, Message):
                        await event.answer(
                            "⏳ Слишком частые запросы. Подождите секунду.",
                            reply_markup=main_keyboard()
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            "⏳ Слишком частые запросы. Подождите секунду.",
                            show_alert=True
                        )
                    return
            
            self.user_requests[user_id] = current_time
        
        return await handler(event, data)