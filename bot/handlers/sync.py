import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from api.client import bot_api_client
from core.states import SyncStates
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_sync_keyboard
from utils.formatters import format_error_message, format_relative_time

router = Router()


# Обработчик sync убран, так как кнопка удалена из меню


@router.callback_query(F.data == "start_sync")
async def start_manual_sync(callback: CallbackQuery, state: FSMContext):
    """Запустить ручную синхронизацию"""
    await state.set_state(SyncStates.waiting_for_confirmation)
    
    await callback.message.edit_text(
        "🔄 РУЧНАЯ СИНХРОНИЗАЦИЯ\n\n"
        "⚠️ Синхронизация может занять 30-60 секунд.\n"
        "В это время данные могут быть недоступны.\n\n"
        "Продолжить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Да, запустить",
                callback_data="confirm_sync"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_sync"
            )]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_sync")
async def confirm_sync(callback: CallbackQuery, state: FSMContext):
    """Подтвердить запуск синхронизации"""
    await state.set_state(SyncStates.sync_in_progress)
    
    await callback.message.edit_text("⏳ Запускаю синхронизацию...")
    
    response = await bot_api_client.start_sync(
        user_id=callback.from_user.id
    )
    
    if response.success and response.data:
        sync_id = response.data.get("sync_id")
        await state.update_data(sync_id=sync_id)
        
        await callback.message.edit_text(
            response.telegram_text or "🔄 Синхронизация запущена",
            reply_markup=create_sync_keyboard(sync_id=sync_id)
        )
        
        # Переходим в состояние ожидания завершения
        await state.set_state(SyncStates.sync_in_progress)
    else:
        await state.set_state(SyncStates.sync_error)
        error_message = format_error_message(response.error, response.status_code)
        
        await callback.message.edit_text(
            f"❌ Ошибка запуска синхронизации:\n\n{error_message}",
            reply_markup=create_sync_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_sync")
async def cancel_sync(callback: CallbackQuery, state: FSMContext):
    """Отменить синхронизацию"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Синхронизация отменена",
        reply_markup=create_sync_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "sync_status")
async def show_sync_status(callback: CallbackQuery):
    """Показать статус синхронизации"""
    response = await bot_api_client.get_sync_status(
        user_id=callback.from_user.id
    )
    
    if response.success and response.data:
        last_sync = response.data.get("last_sync")
        status = response.data.get("status")
        duration = response.data.get("duration_seconds", 0)
        updates = response.data.get("updates", {})
        
        # Формируем дополнительную информацию
        text = response.telegram_text or "🔄 Статус синхронизации"
        
        if last_sync:
            text += f"\n\n⏰ Последняя синхронизация: {format_relative_time(last_sync)}"
        
        if status:
            status_emoji = "✅" if status == "completed" else "⏳" if status == "in_progress" else "❌"
            text += f"\n📊 Статус: {status_emoji} {status.title()}"
        
        if duration > 0:
            text += f"\n⏱️ Длительность: {duration} сек"
        
        if updates:
            text += "\n\n📈 Обновлено:"
            for key, value in updates.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        text += f"\n• {key.title()}: {sub_value}"
                else:
                    text += f"\n• {key.title()}: {value}"
        
        keyboard = create_sync_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка получения статуса:\n\n{error_message}",
            reply_markup=create_sync_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("sync_status_"))
async def check_sync_status(callback: CallbackQuery, state: FSMContext):
    """Проверить статус конкретной синхронизации"""
    sync_id = callback.data.split("_")[-1]
    
    response = await bot_api_client.get_sync_status(
        user_id=callback.from_user.id
    )
    
    if response.success and response.data:
        status = response.data.get("status")
        
        if status == "completed":
            await state.set_state(SyncStates.sync_completed)
            await callback.message.edit_text(
                "✅ Синхронизация завершена успешно!",
                reply_markup=create_sync_keyboard()
            )
        elif status == "in_progress":
            await callback.message.edit_text(
                "⏳ Синхронизация все еще выполняется...\n\n"
                "Попробуйте обновить статус через несколько секунд.",
                reply_markup=create_sync_keyboard(sync_id=sync_id)
            )
        else:
            await state.set_state(SyncStates.sync_error)
            await callback.message.edit_text(
                f"❌ Синхронизация завершилась с ошибкой\n\n"
                f"Статус: {status}",
                reply_markup=create_sync_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка проверки статуса:\n\n{error_message}",
            reply_markup=create_sync_keyboard()
        )
    
    await callback.answer()


@router.message(Command("sync"))
async def cmd_sync(message: Message, state: FSMContext):
    """Команда /sync"""
    await state.set_state(SyncStates.waiting_for_confirmation)
    
    await message.answer(
        "🔄 РУЧНАЯ СИНХРОНИЗАЦИЯ\n\n"
        "⚠️ Синхронизация может занять 30-60 секунд.\n"
        "В это время данные могут быть недоступны.\n\n"
        "Продолжить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Да, запустить",
                callback_data="confirm_sync"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_sync"
            )]
        ])
    )


@router.message(Command("sync_status"))
async def cmd_sync_status(message: Message):
    """Команда /sync_status"""
    response = await bot_api_client.get_sync_status(
        user_id=message.from_user.id
    )
    
    if response.success and response.data:
        await message.answer(
            response.telegram_text or "🔄 Статус синхронизации",
            reply_markup=create_sync_keyboard()
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка получения статуса:\n\n{error_message}",
            reply_markup=main_keyboard()
        )