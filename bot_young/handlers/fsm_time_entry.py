"""
Общие хендлеры для FSM ввода времени
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from core.states import AddChannelStates
from api.client import api_client
from keyboards.keyboards import time_digit_keyboard, back_to_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(AddChannelStates.entering_hours, F.data.startswith("time_digit:"))
async def process_hours_digit(callback: CallbackQuery, state: FSMContext):
    """Обработка ввода часов"""
    try:
        data = await state.get_data()
        current_hours = data.get("hours", "")
        action = callback.data.split(":")[1]
        
        if action == "delete":
            current_hours = current_hours[:-1] if current_hours else ""
        elif action == "confirm":
            if not current_hours:
                await callback.answer("Введите часы", show_alert=True)
                return
            
            hours_int = int(current_hours)
            if not (0 <= hours_int <= 23):
                await callback.answer("Часы должны быть от 0 до 23", show_alert=True)
                return
            
            await state.update_data(hours=current_hours, minutes="")
            hours_display = current_hours.zfill(2)
            
            await callback.message.edit_text(
                f"Введите время для отправления отчета\n\n"
                f"Часы: {hours_display}\n"
                f"Минуты (0-59):",
                reply_markup=time_digit_keyboard("", is_hours=False)
            )
            await state.set_state(AddChannelStates.entering_minutes)
            await callback.answer()
            return
        else:
            digit = action
            if len(current_hours) >= 2:
                await callback.answer()
                return
            
            new_hours = current_hours + digit
            if int(new_hours) > 23:
                await callback.answer("Часы не могут быть больше 23", show_alert=True)
                return
            current_hours = new_hours
        
        await state.update_data(hours=current_hours)
        hours_display = current_hours.zfill(2) if current_hours else "00"
        
        try:
            await callback.message.edit_text(
                f"Введите время для отправления отчета\n\n"
                f"Часы (0-23): {hours_display}",
                reply_markup=time_digit_keyboard(current_hours, is_hours=True)
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in process_hours_digit for user {callback.from_user.id}: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)


@router.callback_query(AddChannelStates.entering_minutes, F.data.startswith("time_digit:"))
async def process_minutes_digit(callback: CallbackQuery, state: FSMContext):
    """Обработка ввода минут (00, 10, 20, 30, 40, 50)"""
    try:
        data = await state.get_data()
        hours = data.get("hours", "0").zfill(2)
        action = callback.data.split(":")[1]
        
        if action == "confirm":
            current_minutes = data.get("minutes")
            if not current_minutes:
                await callback.answer("Выберите минуты", show_alert=True)
                return
            
            minutes_value = int(current_minutes) * 10
            time_str = f"{hours}:{minutes_value:02d}"
            
            await save_channel(callback.from_user.id, state, time_str, callback)
            await callback.answer()
            return
        
        if action == "delete":
            current_minutes = ""
        else:
            digit = action
            if not ('0' <= digit <= '5'):
                await callback.answer("Для минут доступны только значения 0-5", show_alert=True)
                return
            current_minutes = digit
            
        await state.update_data(minutes=current_minutes)
        minutes_display = f"{int(current_minutes) * 10:02d}" if current_minutes else "00"
        
        try:
            await callback.message.edit_text(
                f"Введите время для отправления отчета\n\n"
                f"Часы: {hours}\n"
                f"Минуты: {minutes_display} (выберите 0-5)",
                reply_markup=time_digit_keyboard(current_minutes, is_hours=False)
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in process_minutes_digit for user {callback.from_user.id}: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)


async def save_channel(telegram_id: int, state: FSMContext, time_str: str, message_or_callback):
    """Сохранение настроек канала через API"""
    try:
        data = await state.get_data()
        cabinet = data.get("cabinet")
        chat_id = data.get("chat_id")
        chat_title = data.get("chat_title")
        chat_type = data.get("chat_type")
        
        cabinet_id_str = cabinet.get("id", "")
        cabinet_id = int(str(cabinet_id_str).replace("cabinet_", ""))

        response = await api_client.create_channel_report(
            telegram_id=telegram_id,
            cabinet_id=cabinet_id,
            chat_id=chat_id,
            chat_title=chat_title,
            chat_type=chat_type,
            report_time=time_str
        )
        
        text_to_show = ""
        if response.success:
            text_to_show = (
                f"Готово!\n\n"
                f"Чат: {chat_title}\n"
                f"Время отчетов: {time_str} МСК\n\n"
                f"Ежедневные сводки будут отправляться автоматически."
            )
        else:
            logger.error(f"Error saving channel for user {telegram_id}: {response.error} (status: {response.status_code})")
            if response.status_code == 409: # Conflict
                 text_to_show = f"Этот чат уже был добавлен ранее."
            else:
                 text_to_show = "Не удалось сохранить настройки чата. Попробуйте позже."

        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text_to_show, reply_markup=back_to_main_keyboard())
        else: # CallbackQuery
            await message_or_callback.message.edit_text(text_to_show, reply_markup=back_to_main_keyboard())
        
        await state.clear()
        
    except Exception as e:
        logger.exception(f"Error in save_channel for user {telegram_id}: {e}")
        error_text = "Произошла критическая ошибка при сохранении. Попробуйте позже."
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(error_text, reply_markup=back_to_main_keyboard())
        else:
            await message_or_callback.message.edit_text(error_text, reply_markup=back_to_main_keyboard())
