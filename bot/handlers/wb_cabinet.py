import sys
from pathlib import Path
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
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
    """Показать текущий API ключ и предложить замену"""
    user_id = callback.from_user.id
    
    # Получаем статус кабинета
    cabinet_status = await bot_api_client.get_cabinet_status(user_id=user_id)
    
    if cabinet_status.success and cabinet_status.data:
        cabinets = cabinet_status.data.get("cabinets", [])
        if cabinets:
            # Показываем текущий API ключ
            cabinet = cabinets[0]  # Берем первый кабинет
            api_key = cabinet.get("api_key", "")
            cabinet_name = cabinet.get("name", "Неизвестный кабинет")
            status = cabinet.get("status", "unknown")
            connected_at = cabinet.get("connected_at", "")
            
            # Маскируем API ключ для безопасности
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key[:4] + "..."
            
            await callback.message.edit_text(
                f"🔑 УПРАВЛЕНИЕ WB КАБИНЕТОМ\n\n"
                f"🏢 **Текущий кабинет:** {cabinet_name}\n"
                f"🔑 **API ключ:** `{masked_key}`\n"
                f"📊 **Статус:** {status}\n"
                f"📅 **Подключен:** {connected_at}\n\n"
                f"🔄 **ЗАМЕНИТЬ API КЛЮЧ:**\n"
                f"Если вы хотите изменить API ключ, просто отправьте новый ключ в чат.\n"
                f"Старый ключ будет автоматически удален.\n\n"
                f"📋 **Как получить новый API ключ:**\n"
                f"1. Войдите в личный кабинет WB\n"
                f"2. Перейдите в раздел 'Настройки' → 'Доступ к API'\n"
                f"3. Создайте новый ключ\n"
                f"4. Скопируйте и отправьте его сюда\n\n"
                f"⚠️ **Внимание:** При замене ключа старый будет удален!\n"
                f"❌ Для отмены отправьте /cancel",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="settings"
                    )]
                ]),
                parse_mode="Markdown"
            )
        else:
            # Нет кабинета - показываем инструкцию по подключению
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
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="settings"
                    )]
                ])
            )
    else:
        # Ошибка получения статуса
        await callback.message.edit_text(
            "❌ Ошибка получения информации о кабинете\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Назад к настройкам",
                    callback_data="settings"
                )]
            ])
        )
    
    await callback.answer()
    
    # Устанавливаем состояние для замены API ключа
    await state.set_state(WBConnectionStates.waiting_for_api_key)


@router.message(WBCabinetStates.waiting_for_api_key)
async def process_api_key_replacement(message: Message, state: FSMContext):
    """Обработать введенный API ключ (новый или заменяющий)"""
    api_key = message.text.strip()
    
    # Проверка на отмену
    if api_key.lower() in ['/cancel', 'отмена', 'cancel']:
        await state.clear()
        await message.answer(
            "❌ Операция отменена.\n\n"
            "Вы можете попробовать снова позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Управление API ключом",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="🔙 Назад к настройкам",
                    callback_data="settings"
                )]
            ])
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
    
    # Отправляем запрос на сервер для валидации/замены
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
        
        # Проверяем, это новая регистрация или замена API ключа
        # Проверяем по telegram_text или по данным ответа
        telegram_text = response.telegram_text or ""
        is_replacement = (
            "обновлен" in telegram_text.lower() or 
            "заменен" in telegram_text.lower() or
            "замен" in telegram_text.lower()
        )
        
        if is_replacement:
            # Это замена API ключа - показываем сообщение об успехе
            await message.answer(
                response.telegram_text or "✅ API ключ успешно обновлен!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔙 Назад к настройкам",
                        callback_data="settings"
                    )],
                    [InlineKeyboardButton(
                        text="📊 Главное меню",
                        callback_data="main_menu"
                    )]
                ])
            )
        else:
            # Это новая регистрация - показываем сообщение о синхронизации
            await message.answer(
                response.telegram_text or "✅ КАБИНЕТ ПОДКЛЮЧЕН!\n\n🔄 Запускаю первичную синхронизацию данных...\n⏳ Это может занять 3-5 минут. Пожалуйста, подождите.\n📊 Загружаю товары, заказы, остатки и отзывы...",
                reply_markup=None
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
            "❌ Подключение отменено\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Подключить кабинет",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )]
            ])
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
        
        # Запускаем первичную синхронизацию
        await message.answer(
            "🔄 Запускаю первичную синхронизацию данных...\n"
            "⏳ Это может занять 3-5 минут. Пожалуйста, подождите.\n"
            "📊 Загружаю товары, заказы, остатки и отзывы...",
            reply_markup=None
        )
        
        # Запускаем первичную синхронизацию с увеличенным таймаутом
        sync_response = await bot_api_client.start_initial_sync(
            user_id=message.from_user.id
        )
        
        if sync_response.success:
            await message.answer(
                "✅ Кабинет успешно подключен!\n"
                "🔄 Первичная синхронизация завершена.\n"
                "📊 Все данные загружены и готовы к использованию!\n\n"
                "Теперь вы можете пользоваться ботом!",
                reply_markup=wb_menu_keyboard()
            )
        elif sync_response.status_code == 408:  # Timeout
            await message.answer(
                "✅ Кабинет успешно подключен!\n"
                "⏳ Синхронизация занимает больше времени, чем ожидалось.\n"
                "📊 Данные будут загружены в фоновом режиме.\n\n"
                "Теперь вы можете пользоваться ботом!",
                reply_markup=wb_menu_keyboard()
            )
        else:
            await message.answer(
                "✅ Кабинет успешно подключен!\n"
                "⚠️ Синхронизация будет запущена автоматически позже.\n\n"
                "Теперь вы можете пользоваться ботом!",
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
    await process_api_key_replacement(message, state)


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
            f"❌ Ошибка получения статуса:\n\n{error_message}\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Подключить кабинет",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )]
            ])
        )
    
    await callback.answer()


@router.callback_query(F.data == "cabinet_status")
async def cabinet_status_callback(callback: CallbackQuery):
    """Показать статус кабинетов (алиас для check_cabinet_status)"""
    await check_cabinet_status(callback)


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
            "❌ Операция отменена\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Подключить кабинет",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )]
            ])
        )
    else:
        await message.answer(
            "ℹ️ Нет активных операций для отмены\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Подключить кабинет",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )]
            ])
        )