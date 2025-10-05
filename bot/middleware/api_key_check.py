"""
Middleware для проверки наличия WB API ключа у пользователя
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from api.client import bot_api_client
from keyboards.keyboards import main_keyboard
from core.states import WBCabinetStates

logger = logging.getLogger(__name__)


class APIKeyCheckMiddleware(BaseMiddleware):
    """Middleware для проверки наличия WB API ключа"""
    
    def __init__(self):
        super().__init__()
        self._checked_users = set()  # Кэш проверенных пользователей
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Проверяет наличие API ключа перед обработкой сообщения"""
        
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)
        
        # Пропускаем команду /start - она обрабатывается отдельно
        if isinstance(event, Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        # Пропускаем если пользователь уже проверен в этой сессии
        if user_id in self._checked_users:
            return await handler(event, data)
        
        # Проверяем наличие API ключа
        has_api_key = await self._check_api_key(user_id)
        
        if not has_api_key:
            # Блокируем доступ и требуем ввод API ключа
            await self._block_user_access(event, user_id)
            return
        
        # Добавляем пользователя в кэш проверенных
        self._checked_users.add(user_id)
        
        return await handler(event, data)
    
    async def _check_api_key(self, user_id: int) -> bool:
        """Проверяет наличие API ключа у пользователя"""
        try:
            response = await bot_api_client.get_cabinet_status(user_id)
            
            if not response.success:
                logger.warning(f"Ошибка проверки API ключа для пользователя {user_id}: {response.error}")
                return False
            
            # Проверяем, есть ли подключенные кабинеты
            cabinets = response.data.get('cabinets', []) if response.data else []
            return len(cabinets) > 0
            
        except Exception as e:
            logger.error(f"Ошибка при проверке API ключа для пользователя {user_id}: {e}")
            return False
    
    async def _block_user_access(self, event: Message | CallbackQuery, user_id: int):
        """Блокирует доступ пользователя и требует ввод API ключа"""
        message_text = (
            "🔑 **ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА**\n\n"
            "Для использования бота необходимо подключить ваш WB кабинет.\n"
            "Пожалуйста, введите ваш API ключ от Wildberries:\n\n"
            "💡 **Как получить API ключ:**\n"
            "1. Зайдите в личный кабинет WB\n"
            "2. Перейдите в раздел 'Настройки' → 'Доступ к API'\n"
            "3. Создайте новый токен доступа\n"
            "4. Скопируйте и отправьте его боту\n\n"
            "⚠️ **Важно:** API ключ должен быть действительным и иметь права на чтение данных."
        )
        
        if isinstance(event, Message):
            await event.answer(
                message_text,
                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
        elif isinstance(event, CallbackQuery):
            await event.message.edit_text(
                message_text,
                reply_markup=main_keyboard(),
                parse_mode="Markdown"
            )
            await event.answer()
    
    def clear_user_cache(self, user_id: int):
        """Очищает кэш для пользователя (вызывается после успешного подключения API)"""
        self._checked_users.discard(user_id)