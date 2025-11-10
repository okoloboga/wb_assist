"""
Логика подключения чата через команду /connect в группе
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.filters import Command

from core.states import AddChannelStates
from api.client import api_client
from keyboards.keyboards import time_digit_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("connect"), F.chat.type.in_({"group", "supergroup"}))
async def connect_chat_command(message: Message, bot: Bot, state: FSMContext):
    """
    Обрабатывает команду /connect, отправленную в группе/супергруппе.
    """
    chat = message.chat
    user = message.from_user
    
    if not user:
        await message.answer("Не удалось определить пользователя. Пожалуйста, отправьте команду /connect от своего имени (не анонимно).")
        return

    try:
        # 1. Проверяем права бота
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer("Ошибка: бот не является администратором в этом чате.")
            return

        # 2. Проверяем, есть ли у пользователя кабинеты
        response = await api_client.get_user_cabinets(user.id)
        if not response.success or not response.data.get("cabinets"):
            await bot.send_message(
                user.id,
                f"Не удалось подключить чат «{chat.title}».\n\n"
                "Сначала подключите хотя бы один кабинет Wildberries в основном боте."
            )
            await message.answer(f"@{user.username}, не удалось найти ваши кабинеты. Проверьте личные сообщения от меня.")
            return
        
        cabinets = response.data.get("cabinets", [])

        # 3. Все проверки пройдены. Начинаем FSM для этого пользователя в ЛС.
        user_state_key = StorageKey(bot_id=bot.id, user_id=user.id, chat_id=user.id)
        user_state = FSMContext(storage=state.storage, key=user_state_key)
        
        await user_state.set_data({
            "chat_id": chat.id,
            "chat_title": chat.title,
            "chat_type": chat.type,
            "cabinet": cabinets[0]
        })
        
        await user_state.set_state(AddChannelStates.entering_hours)
        
        await bot.send_message(
            user.id,
            f"Отлично! Вы подключаете чат «{chat.title}».\n\n"
            "Теперь укажите время для отправки ежедневного отчета.\n\n"
            "Часы (0-23):",
            reply_markup=time_digit_keyboard("", is_hours=True)
        )
        
        await message.answer(f"Чат «{chat.title}» готов к подключению!\n\n@{user.username}, я отправил вам личное сообщение для завершения настройки.")

    except Exception as e:
        logger.exception(f"Error in connect_chat_command for user {user.id} in chat {chat.id}: {e}")
        await message.answer("Произошла непредвиденная ошибка при попытке подключения чата.")
