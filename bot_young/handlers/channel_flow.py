"""
Логика подключения канала через пересылку сообщения или ссылку
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from core.states import AddChannelStates
from api.client import api_client
from keyboards.keyboards import time_digit_keyboard
from utils.validators import parse_channel_link

router = Router()
logger = logging.getLogger(__name__)


@router.message(AddChannelStates.waiting_for_channel_input, F.forward_date.is_not(None) | F.text)
async def process_channel_link(message: Message, bot: Bot, state: FSMContext):
    """
    Обработка ссылки/username канала или пересланного сообщения.
    Срабатывает только в состоянии waiting_for_channel_input.
    """
    try:
        chat_to_validate = None
        user_id = message.from_user.id

        # 1. Обработка пересланного сообщения
        if message.forward_from_chat and message.forward_from_chat.type == 'channel':
            chat_to_validate = message.forward_from_chat
        # 2. Обработка текстовой ссылки
        elif message.text:
            channel_username = parse_channel_link(message.text)
            if not channel_username:
                await message.answer(
                    "Неверный формат. Отправьте ссылку на публичный канал (@channel), или перешлите сообщение из приватного канала."
                )
                return
            chat_to_validate = channel_username
        else:
            await message.answer("Пожалуйста, перешлите сообщение из канала или отправьте ссылку на него.")
            return

        # Валидируем канал
        chat = await bot.get_chat(chat_to_validate.id if hasattr(chat_to_validate, 'id') else chat_to_validate)

        if chat.type != 'channel':
            await message.answer("Этот способ предназначен только для добавления каналов. Для добавления группы, пожалуйста, воспользуйтесь командой /connect внутри самой группы.")
            return

        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer("Ошибка: бот не является администратором в этом канале.")
            return
        
        if not bot_member.can_post_messages:
            await message.answer("Ошибка: у бота нет права на отправку сообщений в этом канале.")
            return
            
        # Проверяем кабинеты пользователя
        response = await api_client.get_user_cabinets(user_id)
        if not response.success or not response.data.get("cabinets"):
            await message.answer(
                "Не удалось подключить канал.\n\n"
                "Сначала подключите хотя бы один кабинет Wildberries в основном боте."
            )
            return
        cabinets = response.data.get("cabinets", [])

        # Все проверки пройдены, переходим к вводу времени
        await state.set_data({
            "chat_id": chat.id,
            "chat_title": chat.title,
            "chat_type": chat.type,
            "cabinet": cabinets[0]
        })
        await state.set_state(AddChannelStates.entering_hours)
        
        await message.answer(
            f"Отлично! Вы подключаете канал «{chat.title}».\n\n"
            "Теперь укажите время для отправки ежедневного отчета.\n\n"
            "Часы (0-23):",
            reply_markup=time_digit_keyboard("", is_hours=True)
        )

    except Exception as e:
        logger.exception(f"Error in process_channel_link for user {message.from_user.id}: {e}")
        await message.answer(
            "Не удалось найти или проверить канал.\n\n"
            "Убедитесь, что:\n"
            "• Канал существует.\n"
            "• Бот добавлен в канал как администратор с правом отправки сообщений."
        )
