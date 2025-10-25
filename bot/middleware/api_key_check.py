"""
Middleware для проверки наличия WB API ключа у пользователя
"""
import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        
        # Пропускаем команды GPT-чата (/gpt, /exit)
        if isinstance(event, Message) and event.text and event.text.startswith(('/gpt', '/exit')):
            logger.info(f"🔍 API_KEY_CHECK: Пропускаем проверку - команда GPT {event.text} для пользователя {user_id}")
            return await handler(event, data)
        
        # Пропускаем callback кнопки подключения кабинета
        if isinstance(event, CallbackQuery) and event.data in ['settings_api_key', 'connect_wb']:
            logger.info(f"🔍 API_KEY_CHECK: Пропускаем проверку - пользователь {user_id} нажимает кнопку подключения кабинета")
            return await handler(event, data)
        
        # Пропускаем кнопки AI-помощника (AI-чат не требует WB кабинета)
        if isinstance(event, CallbackQuery) and event.data in ['ai_assistant', 'ai_chat', 'ai_examples', 'ai_export_gs']:
            logger.info(f"🔍 API_KEY_CHECK: Пропускаем проверку - AI callback '{event.data}' для пользователя {user_id}")
            return await handler(event, data)
        
        # Пропускаем если пользователь уже проверен в этой сессии
        if user_id in self._checked_users:
            return await handler(event, data)
        
        # Пропускаем ввод API ключа (не команды, не callback)
        if isinstance(event, Message) and event.text and not event.text.startswith('/'):
            # Проверяем, не в состоянии ли ввода API ключа
            from aiogram.fsm.context import FSMContext
            state = data.get('state')
            if state:
                current_state = await state.get_state()
                if current_state and ('api_key' in str(current_state) or 'waiting_for_api_key' in str(current_state) or 'gpt_chat' in str(current_state)):
                    logger.info(f"🔍 API_KEY_CHECK: Пропускаем проверку - пользователь {user_id} в состоянии: {current_state}")
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
            logger.info(f"🔍 API_KEY_CHECK: Проверяем API ключ для пользователя {user_id}")
            response = await bot_api_client.get_cabinet_status(user_id)
            
            logger.info(f"🔍 API_KEY_CHECK: Ответ от API: success={response.success}, status_code={response.status_code}")
            if response.data:
                logger.info(f"🔍 API_KEY_CHECK: Данные ответа: {response.data}")
            
            if not response.success:
                logger.warning(f"Ошибка проверки API ключа для пользователя {user_id}: {response.error}")
                return False
            
            # Проверяем, есть ли подключенные кабинеты
            cabinets = response.data.get('cabinets', []) if response.data else []
            logger.info(f"🔍 API_KEY_CHECK: Найдено кабинетов: {len(cabinets)}")
            result = len(cabinets) > 0
            logger.info(f"🔍 API_KEY_CHECK: Результат проверки: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при проверке API ключа для пользователя {user_id}: {e}")
            return False
    
    async def _suggest_cabinet_connection(self, event: Message | CallbackQuery, user_id: int):
        """Предлагает пользователю подключить кабинет вместо блокировки"""
        from aiogram.exceptions import TelegramBadRequest
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        message_text = (
            "🔑 **ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА**\n\n"
            "Для использования бота необходимо подключить ваш WB кабинет.\n"
            "Нажмите кнопку ниже для подключения:\n\n"
            "💡 **Как получить API ключ:**\n"
            "1. Зайдите в личный кабинет WB\n"
            "2. Перейдите в раздел 'Настройки' → 'Доступ к API'\n"
            "3. Создайте новый токен доступа\n"
            "4. Скопируйте и отправьте его боту\n\n"
            "⚠️ **Важно:** API ключ должен быть действительным и иметь права на чтение данных."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔑 Подключить кабинет",
                callback_data="settings_api_key"
            )],
            [InlineKeyboardButton(
                text="ℹ️ Помощь",
                callback_data="help"
            )]
        ])
        
        if isinstance(event, Message):
            await event.answer(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        elif isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await event.answer()
            except TelegramBadRequest:
                # Если не можем отредактировать, отправляем новое сообщение
                await event.message.answer(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await event.answer()

    async def _block_user_access(self, event: Message | CallbackQuery, user_id: int):
        """Блокирует доступ пользователя и требует ввод API ключа"""
        from aiogram.exceptions import TelegramBadRequest
        
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
            try:
                await event.message.edit_text(
                    message_text,
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown"
                )
            except TelegramBadRequest:
                # Если сообщение не изменилось, отправляем новое
                await event.message.answer(
                    message_text,
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown"
                )
            await event.answer()
    
    def clear_user_cache(self, user_id: int):
        """Очищает кэш для пользователя (вызывается после успешного подключения API)"""
        self._checked_users.discard(user_id)