import sys
from pathlib import Path
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.client import bot_api_client
from core.states import WBConnectionStates, WBCabinetStates
from keyboards.keyboards import wb_menu_keyboard, main_keyboard
from utils.formatters import format_error_message

router = Router()


@router.callback_query(F.data == "settings_api_key")
async def start_wb_connection(callback: CallbackQuery, state: FSMContext):
    """Начать процесс подключения WB кабинета"""
    await state.set_state(WBConnectionStates.waiting_for_api_key)
    
    await callback.message.edit_text(
        "🔑 ПОДКЛЮЧЕНИЕ WB КАБИНЕТА\n\n"
        "Для подключения кабинета Wildberries введите ваш API ключ.\n\n"
        "📋 Как получить API ключ:\n"
        "1. Войдите в личный кабинет WB\n"
        "2. Перейдите в раздел 'Настройки' → 'Доступ к API'\n"
        "3. Создайте новый ключ или используйте существующий\n"
        "4. Скопируйте ключ и отправьте его сюда\n\n"
        "⚠️ Ключ будет сохранен в зашифрованном виде\n"
        "❌ Для отмены отправьте /cancel",
        reply_markup=None
    )
    await callback.answer()


@router.message(WBCabinetStates.waiting_for_api_key)
async def process_initial_api_key(message: Message, state: FSMContext):
    """Обработать введенный API ключ при первичной регистрации"""
    api_key = message.text.strip()
    
    # Проверка на отмену
    if api_key.lower() in ['/cancel', 'отмена', 'cancel']:
        await state.clear()
        await message.answer(
            "❌ Подключение отменено. Без API ключа использование бота невозможно.",
            reply_markup=main_keyboard()
        )
        return
    
    # Базовая валидация ключа
    if len(api_key) < 10:
        await message.answer(
            "❌ API ключ слишком короткий. Пожалуйста, проверьте правильность ввода.\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены:"
        )
        return
    
    # Переходим в состояние валидации
    await state.set_state(WBCabinetStates.validating_key)
    await message.answer("⏳ Проверяю API ключ...")
    
    # Отправляем запрос на сервер для валидации
    response = await bot_api_client.connect_wb_cabinet(
        user_id=message.from_user.id,
        api_key=api_key
    )
    
    if response.success:
        await state.clear()
        
        # Очищаем кэш middleware для этого пользователя
        try:
            from __main__ import api_key_middleware
            api_key_middleware.clear_user_cache(message.from_user.id)
        except ImportError:
            # Если не можем импортировать, пропускаем
            pass
        
        await message.answer(
            response.telegram_text or "✅ Кабинет успешно подключен! Теперь вы можете пользоваться ботом.",
            reply_markup=wb_menu_keyboard()
        )
    else:
        await state.set_state(WBCabinetStates.connection_error)
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка подключения кабинета:\n\n{error_message}\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены:",
            reply_markup=None
        )
        # Возвращаемся к ожиданию ключа
        await state.set_state(WBCabinetStates.waiting_for_api_key)


@router.message(WBConnectionStates.waiting_for_api_key)
async def process_api_key(message: Message, state: FSMContext):
    """Обработать введенный API ключ"""
    api_key = message.text.strip()
    
    # Проверка на отмену
    if api_key.lower() in ['/cancel', 'отмена', 'cancel']:
        await state.clear()
        await message.answer(
            "❌ Подключение отменено",
            reply_markup=main_keyboard()
        )
        return
    
    # Базовая валидация ключа
    if len(api_key) < 10:
        await message.answer(
            "❌ API ключ слишком короткий. Пожалуйста, проверьте правильность ввода.\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены:"
        )
        return
    
    # Переходим в состояние валидации
    await state.set_state(WBConnectionStates.validating_key)
    await message.answer("⏳ Проверяю API ключ...")
    
    # Отправляем запрос на сервер для валидации
    response = await bot_api_client.connect_wb_cabinet(
        user_id=message.from_user.id,
        api_key=api_key
    )
    
    if response.success:
        await state.set_state(WBConnectionStates.connection_success)
        await message.answer(
            response.telegram_text or "✅ Кабинет успешно подключен!",
            reply_markup=wb_menu_keyboard()
        )
        await state.clear()
    else:
        await state.set_state(WBConnectionStates.connection_error)
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка подключения кабинета:\n\n{error_message}\n\n"
            "Попробуйте еще раз или отправьте /cancel для отмены:",
            reply_markup=None
        )
        # Возвращаемся к ожиданию ключа
        await state.set_state(WBConnectionStates.waiting_for_api_key)


@router.message(WBCabinetStates.connection_error)
async def handle_initial_connection_error(message: Message, state: FSMContext):
    """Обработать ошибку подключения при первичной регистрации"""
    await state.set_state(WBCabinetStates.waiting_for_api_key)
    await process_initial_api_key(message, state)


@router.message(WBConnectionStates.connection_error)
async def handle_connection_error(message: Message, state: FSMContext):
    """Обработать ошибку подключения - вернуться к вводу ключа"""
    await state.set_state(WBConnectionStates.waiting_for_api_key)
    await process_api_key(message, state)


@router.callback_query(F.data == "check_cabinet_status")
async def check_cabinet_status(callback: CallbackQuery):
    """Проверить статус подключенных кабинетов"""
    response = await bot_api_client.get_cabinet_status(
        user_id=callback.from_user.id
    )
    
    if response.success:
        await callback.message.edit_text(
            response.telegram_text or "📊 Статус кабинетов получен",
            reply_markup=wb_menu_keyboard()
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка получения статуса:\n\n{error_message}",
            reply_markup=main_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "disconnect_cabinet")
async def disconnect_cabinet(callback: CallbackQuery):
    """Отключить кабинет WB"""
    # TODO: Реализовать отключение кабинета через API
    await callback.message.edit_text(
        "🔌 ОТКЛЮЧЕНИЕ КАБИНЕТА\n\n"
        "⚠️ Функция отключения кабинета будет доступна в следующей версии.\n\n"
        "Для отключения обратитесь к администратору.",
        reply_markup=wb_menu_keyboard()
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_operation(message: Message, state: FSMContext):
    """Отменить текущую операцию"""
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
        await message.answer(
            "❌ Операция отменена",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(
            "ℹ️ Нет активных операций для отмены",
            reply_markup=main_keyboard()
        )