
"""
Инструкция по добавлению нового чата
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from core.states import AddChannelStates
from keyboards.keyboards import back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    """Инструкция по добавлению нового чата"""
    try:
        await state.clear()
        
        await callback.message.edit_text(
            "Выберите, что вы хотите подключить:\n\n"
            "1. ДЛЯ ГРУППЫ:\n"
            "   - Добавьте бота в вашу группу как администратора.\n"
            "   - Напишите в группе команду /connect.\n\n"
            "2. ДЛЯ КАНАЛА:\n"
            "   - Добавьте бота в ваш канал как администратора.\n"
            "   - Перешлите сюда любое сообщение из канала или отправьте на него ссылку (@channelname).\n\n"
            "Ожидаю ссылку или пересланное сообщение для подключения КАНАЛА...",
            reply_markup=back_to_main_keyboard()
        )
        # Сразу переводим в состояние ожидания для канала
        await state.set_state(AddChannelStates.waiting_for_channel_input)
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in start_add_channel for user {callback.from_user.id}: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)



