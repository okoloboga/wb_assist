"""
FSM для добавления нового канала
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from core.states import AddChannelStates
from api.client import api_client
from keyboards.keyboards import back_to_main_keyboard, time_digit_keyboard
from utils.validators import parse_channel_link

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления канала"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем наличие кабинетов
        response = await api_client.get_user_cabinets(user_id)
        
        if not response.success or not response.data.get("cabinets"):
            await callback.message.edit_text(
                "❌ У вас нет подключенных кабинетов.\n"
                "Сначала подключите кабинет в основном боте.",
                reply_markup=back_to_main_keyboard()
            )
            await callback.answer()
            return
        
        # Сохраняем данные кабинета в state
        cabinets = response.data.get("cabinets", [])
        await state.update_data(cabinet=cabinets[0])
        
        await callback.message.edit_text(
            "📢 Добавление канала\n\n"
            "Шаг 1/2: Отправьте ссылку на канал или его @username\n\n"
            "Примеры:\n"
            "• @mychannel\n"
            "• https://t.me/mychannel\n\n"
            "❗ Убедитесь, что бот добавлен в канал как администратор с правом отправки сообщений."
        )
        await state.set_state(AddChannelStates.waiting_for_channel)
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in start_add_channel for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.message(AddChannelStates.waiting_for_channel)
async def process_channel_link(message: Message, state: FSMContext):
    """Обработка ссылки/username канала"""
    try:
        # Парсим ссылку/username
        channel_username = parse_channel_link(message.text)
        
        if not channel_username:
            await message.answer(
                "❌ Неверный формат. Отправьте ссылку на канал или @username"
            )
            return
        
        # Валидируем канал через Telegram API
        from aiogram import Bot
        bot = message.bot
        
        try:
            # Пробуем получить информацию о чате
            chat = await bot.get_chat(channel_username)
            
            # Проверяем права бота
            bot_member = await bot.get_chat_member(chat.id, bot.id)
            
            if bot_member.status not in ['administrator', 'creator']:
                await message.answer(
                    "❌ Бот не является администратором в канале.\n\n"
                    "Добавьте бота в канал как администратора с правом отправки сообщений."
                )
                return
            
            # Проверяем право отправки сообщений
            if bot_member.status == 'administrator' and not bot_member.can_post_messages:
                await message.answer(
                    "❌ У бота нет права отправлять сообщения в канале.\n\n"
                    "Предоставьте боту право отправки сообщений в настройках канала."
                )
                return
            
            # Сохраняем данные о канале
            await state.update_data(
                chat_id=chat.id,
                chat_title=chat.title,
                chat_type=chat.type
            )
            
            # Переходим к вводу времени (начинаем с часов)
            await message.answer(
                "Введите время для отправления отчета\n\n"
                "Часы (0-23):",
                reply_markup=time_digit_keyboard("", is_hours=True)
            )
            await state.set_state(AddChannelStates.entering_hours)
            await state.update_data(hours="")
            
        except Exception as e:
            logger.exception(f"Error validating channel '{channel_username}' for user {message.from_user.id}: {e}")
            await message.answer(
                "❌ Не удалось найти канал.\n\n"
                "Убедитесь, что:\n"
                "• Канал существует\n"
                "• Бот добавлен в канал как администратор\n"
                "• Ссылка/username указаны правильно"
            )
        
    except Exception as e:
        logger.exception(f"Error in process_channel_link for user {message.from_user.id}: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")


@router.callback_query(AddChannelStates.entering_hours, F.data.startswith("time_digit:"))
async def process_hours_digit(callback: CallbackQuery, state: FSMContext):
    """Обработка ввода часов"""
    try:
        data = await state.get_data()
        current_hours = data.get("hours", "")
        action = callback.data.split(":")[1]
        
        if action == "delete":
            # Удаление последней цифры
            current_hours = current_hours[:-1] if current_hours else ""
        elif action == "confirm":
            # Подтверждение часов
            if not current_hours:
                await callback.answer("Введите часы", show_alert=True)
                return
            
            hours_int = int(current_hours)
            if hours_int < 0 or hours_int > 23:
                await callback.answer("Часы должны быть от 0 до 23", show_alert=True)
                return
            
            # Переходим к вводу минут
            await state.update_data(hours=current_hours, minutes="")
            # Форматируем отображение часов
            if len(current_hours) == 1 and int(current_hours) > 2:
                hours_display = current_hours
            else:
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
            # Добавление цифры
            digit = action
            
            if len(current_hours) == 0:
                # Первая цифра
                first_digit = int(digit)
                if first_digit > 2:
                    # Если первая цифра 3-9, это уже финальное значение (3-9 часов валидны)
                    current_hours = digit
                else:
                    # Если 0, 1, 2 - можно вводить вторую
                    current_hours = digit
            elif len(current_hours) == 1:
                # Вторая цифра
                new_hours = current_hours + digit
                hours_int = int(new_hours)
                if hours_int > 23:
                    await callback.answer("Часы не могут быть больше 23", show_alert=True)
                    return
                current_hours = new_hours
            else:
                # Уже две цифры, игнорируем
                await callback.answer()
                return
        
        # Обновляем сообщение с текущим значением
        # Если одна цифра и она 3-9, показываем как есть, иначе с ведущим нулем
        if current_hours and len(current_hours) == 1 and int(current_hours) > 2:
            hours_display = current_hours
        else:
            hours_display = current_hours.zfill(2) if current_hours else "00"
        
        try:
            await callback.message.edit_text(
                f"Введите время для отправления отчета\n\n"
                f"Часы (0-23): {hours_display}",
                reply_markup=time_digit_keyboard(current_hours, is_hours=True)
            )
        except TelegramBadRequest as e:
            # Игнорируем ошибку "message is not modified" - сообщение уже в нужном состоянии
            if "message is not modified" in str(e).lower():
                logger.debug(f"Message not modified for user {callback.from_user.id}, ignoring")
            else:
                raise
        
        await state.update_data(hours=current_hours)
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in process_hours_digit for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)


@router.callback_query(AddChannelStates.entering_minutes, F.data.startswith("time_digit:"))
async def process_minutes_digit(callback: CallbackQuery, state: FSMContext):
    """Обработка ввода минут (только круглые значения: 00, 10, 20, 30, 40, 50)"""
    try:
        data = await state.get_data()
        current_minutes = data.get("minutes", "")
        hours = data.get("hours", "0")
        action = callback.data.split(":")[1]
        
        if action == "delete":
            # Удаление значения
            current_minutes = ""
        elif action == "confirm":
            # Подтверждение минут и сохранение канала
            if not current_minutes:
                await callback.answer("Выберите минуты", show_alert=True)
                return
            
            # Проверяем что это валидная цифра (0-5)
            digit = int(current_minutes)
            if digit < 0 or digit > 5:
                await callback.answer("Выберите значение от 0 до 5", show_alert=True)
                return
            
            # Умножаем на 10 для получения минут (0->00, 1->10, 2->20, 3->30, 4->40, 5->50)
            minutes_value = digit * 10
            
            # Формируем время в формате HH:MM
            hours_formatted = hours.zfill(2) if len(hours) == 1 else hours
            time_str = f"{hours_formatted.zfill(2)}:{minutes_value:02d}"
            
            # Сохраняем канал
            await save_channel(callback.from_user.id, state, time_str, callback)
            await callback.answer()
            return
        else:
            # Добавление цифры (только одна цифра 0-5)
            digit = action
            digit_int = int(digit)
            
            if digit_int < 0 or digit_int > 5:
                await callback.answer("Для минут доступны только значения 0-5 (00, 10, 20, 30, 40, 50)", show_alert=True)
                return
            
            # Сохраняем только одну цифру
            current_minutes = digit
        
        # Обновляем отображение
        data = await state.get_data()
        hours = data.get("hours", "0")
        
        # Форматируем отображение часов
        if len(hours) == 1 and int(hours) > 2:
            hours_display = hours
        else:
            hours_display = hours.zfill(2) if hours else "00"
        
        # Форматируем отображение минут (показываем как будет выглядеть финальное значение)
        if current_minutes:
            minutes_value = int(current_minutes) * 10
            minutes_display = f"{minutes_value:02d}"
        else:
            minutes_display = "00"
        
        try:
            await callback.message.edit_text(
                f"Введите время для отправления отчета\n\n"
                f"Часы: {hours_display}\n"
                f"Минуты: {minutes_display} (выберите 0-5)",
                reply_markup=time_digit_keyboard(current_minutes, is_hours=False)
            )
        except TelegramBadRequest as e:
            # Игнорируем ошибку "message is not modified" - сообщение уже в нужном состоянии
            if "message is not modified" in str(e).lower():
                logger.debug(f"Message not modified for user {callback.from_user.id}, ignoring")
            else:
                raise
        
        await state.update_data(minutes=current_minutes)
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in process_minutes_digit for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)


async def save_channel(telegram_id: int, state: FSMContext, time_str: str, message_or_callback):
    """Сохранение настроек канала через API"""
    try:
        data = await state.get_data()
        channel_id = data.get("channel_id")  # Если есть - это обновление времени
        
        if channel_id:
            # Обновление времени существующего канала
            response = await api_client.update_channel(
                channel_id=channel_id,
                telegram_id=telegram_id,
                updates={"report_time": time_str}
            )
            
            if response.success:
                text = (
                    f"✅ Время обновлено!\n\n"
                    f"🕐 Новое время: {time_str} МСК\n\n"
                    f"Сводки будут отправляться в новое время."
                )
            else:
                logger.error(f"Error updating channel time for user {telegram_id}: {response.error} (status: {response.status_code})")
                error_text = "❌ Не удалось обновить время. Попробуйте позже."
                if isinstance(message_or_callback, CallbackQuery):
                    await message_or_callback.message.edit_text(error_text, reply_markup=back_to_main_keyboard())
                else:
                    await message_or_callback.answer(error_text, reply_markup=back_to_main_keyboard())
                return
        else:
            # Создание нового канала
            cabinet = data.get("cabinet")
            chat_id = data.get("chat_id")
            chat_title = data.get("chat_title")
            chat_type = data.get("chat_type")
            
            # Извлекаем ID кабинета (может быть "cabinet_1" или просто число)
            cabinet_id_str = cabinet.get("id", "")
            if isinstance(cabinet_id_str, str) and cabinet_id_str.startswith("cabinet_"):
                # Извлекаем число из строки "cabinet_1"
                cabinet_id = int(cabinet_id_str.replace("cabinet_", ""))
            elif isinstance(cabinet_id_str, int):
                cabinet_id = cabinet_id_str
            else:
                # Пробуем преобразовать в int
                cabinet_id = int(cabinet_id_str)
            
            # Отправляем на сервер (используем telegram_id, сервер сам найдет user_id)
            response = await api_client.create_channel_report(
                telegram_id=telegram_id,
                cabinet_id=cabinet_id,
                chat_id=chat_id,
                chat_title=chat_title,
                chat_type=chat_type,
                report_time=time_str
            )
            
            if response.success:
                text = (
                    f"✅ Готово!\n\n"
                    f"📢 Канал: {chat_title}\n"
                    f"🕐 Время: {time_str} МСК\n\n"
                    f"Ежедневные сводки будут отправляться автоматически."
                )
            else:
                # Логируем детальную ошибку
                logger.error(f"Error saving channel for user {telegram_id}: {response.error} (status: {response.status_code})")
                
                # Показываем абстрактное сообщение пользователю
                error_text = "❌ Не удалось сохранить настройки канала. Попробуйте позже."
                if isinstance(message_or_callback, CallbackQuery):
                    await message_or_callback.message.edit_text(error_text, reply_markup=back_to_main_keyboard())
                else:
                    await message_or_callback.answer(error_text, reply_markup=back_to_main_keyboard())
                return
        
        # Показываем успешное сообщение
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text, reply_markup=back_to_main_keyboard())
        else:
            # Это Message
            await message_or_callback.answer(text, reply_markup=back_to_main_keyboard())
        
        # Очищаем состояние только при успехе
        await state.clear()
        
    except Exception as e:
        # Логируем полную ошибку с traceback
        logger.exception(f"Error in save_channel for user {telegram_id}: {e}")
        
        # Показываем абстрактное сообщение пользователю
        error_text = "❌ Произошла ошибка при сохранении. Попробуйте позже."
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(error_text, reply_markup=back_to_main_keyboard())
        else:
            await message_or_callback.answer(error_text, reply_markup=back_to_main_keyboard())

