"""
Управление каналами - просмотр, редактирование, удаление
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from api.client import api_client
from keyboards.keyboards import channels_list_keyboard, channel_detail_keyboard, back_to_main_keyboard, time_digit_keyboard
from core.states import AddChannelStates

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "my_channels")
async def show_channels_list(callback: CallbackQuery):
    """Показать список каналов пользователя"""
    try:
        user_id = callback.from_user.id
        
        response = await api_client.get_user_channels(user_id)
        
        if not response.success:
            await callback.message.edit_text(
                "❌ Ошибка при получении списка каналов",
                reply_markup=back_to_main_keyboard()
            )
            return
        
        channels = response.data.get("channels", []) if response.data else []
        
        if not channels:
            await callback.message.edit_text(
                "У вас пока нет настроенных каналов.\n\n"
                "Нажмите 'Добавить канал' чтобы настроить первый канал.",
                reply_markup=back_to_main_keyboard()
            )
        else:
            text = "📢 Ваши каналы:\n\n"
            await callback.message.edit_text(
                text,
                reply_markup=channels_list_keyboard(channels)
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in show_channels_list for user {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при загрузке каналов. Попробуйте позже.",
            reply_markup=back_to_main_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data.startswith("channel_detail:"))
async def show_channel_detail(callback: CallbackQuery, bot):
    """Показать детальную информацию о канале"""
    try:
        channel_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        # Получаем детали канала через API
        response = await api_client.get_channel_detail(channel_id, user_id)
        
        if not response.success:
            logger.error(f"Error getting channel detail: {response.error}")
            await callback.answer("❌ Ошибка при загрузке информации о канале", show_alert=True)
            return
        
        channel_data = response.data
        
        # Получаем информацию о канале через Telegram API для получения username
        chat_id = channel_data.get("chat_id")
        chat_title = channel_data.get("chat_title", "Канал")
        report_time = channel_data.get("report_time", "09:00")
        timezone = channel_data.get("timezone", "Europe/Moscow")
        
        # Пытаемся получить username канала
        channel_link = f"ID: {chat_id}"
        try:
            chat = await bot.get_chat(chat_id)
            if chat.username:
                channel_link = f"@{chat.username}"
            elif chat.invite_link:
                channel_link = chat.invite_link
            else:
                channel_link = chat.title or f"ID: {chat_id}"
        except Exception as e:
            logger.debug(f"Could not get chat info: {e}")
            # Используем chat_title из БД
            channel_link = chat_title
        
        # Формируем сообщение
        # Определяем название timezone для отображения
        timezone_display = "МСК" if timezone == "Europe/Moscow" else timezone
        
        text = (
            f"📢 Управление каналом\n\n"
            f"📍 Канал: {channel_link}\n"
            f"🕐 Время отправки: {report_time} {timezone_display}\n"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=channel_detail_keyboard(channel_id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in show_channel_detail for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("change_time:"))
async def change_time(callback: CallbackQuery, state: FSMContext):
    """Изменить время отправки для канала"""
    try:
        channel_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        # Сохраняем channel_id в state для последующего обновления
        await state.update_data(channel_id=channel_id)
        
        # Переходим к вводу времени (начинаем с часов)
        await callback.message.edit_text(
            "Введите время для отправления отчета\n\n"
            "Часы (0-23):",
            reply_markup=time_digit_keyboard("", is_hours=True)
        )
        await state.set_state(AddChannelStates.entering_hours)
        await state.update_data(hours="")
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error in change_time for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("delete_channel:"))
async def delete_channel(callback: CallbackQuery):
    """Удалить канал"""
    try:
        channel_id = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        
        response = await api_client.delete_channel(channel_id, user_id)
        
        if response.success:
            await callback.answer("✅ Канал удален", show_alert=True)
            # Возвращаем к списку каналов
            await show_channels_list(callback)
        else:
            logger.error(f"Error deleting channel {channel_id} for user {user_id}: {response.error} (status: {response.status_code})")
            await callback.answer("❌ Не удалось удалить канал. Попробуйте позже.", show_alert=True)
        
    except Exception as e:
        logger.exception(f"Error in delete_channel for user {callback.from_user.id}: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    from keyboards.keyboards import main_menu_keyboard
    
    await callback.message.edit_text(
        "🤖 Привет! Это бот для ежедневных отчетов.\n\n"
        "📊 Я автоматически отправляю сводки по вашему кабинету Wildberries в Telegram каналы и чаты.\n\n"
        "✨ Что я умею:\n"
        "• Отправлять ежедневные отчеты о продажах\n"
        "• Работать с несколькими каналами\n"
        "• Настраивать удобное время отправки\n\n"
        "Добавьте канал, установите время — и получайте актуальные данные каждый день! 🚀",
        reply_markup=main_menu_keyboard(has_cabinets=True)
    )
    await callback.answer()

