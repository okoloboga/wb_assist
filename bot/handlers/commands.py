import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, User, InlineKeyboardMarkup, InlineKeyboardButton, Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.formatters import safe_edit_message, safe_send_message, handle_telegram_errors

logger = logging.getLogger(__name__)

from keyboards.keyboards import (
    main_keyboard,
    wb_menu_keyboard,
    analytics_keyboard,
    stock_keyboard,
    reviews_keyboard,
    prices_keyboard,
    content_keyboard,
    ai_assistant_keyboard,
    settings_keyboard
)

router = Router()

# Навигация кнопки "назад"
navigation = {
    "orders": "wb_menu",
    "analytics": "wb_menu",
    "stock": "wb_menu",
    "reviews": "wb_menu",
    "prices": "wb_menu",
    "notifications": "wb_menu",
    "content": "wb_menu",
    "ai_assistant": "wb_menu",
    "settings": "wb_menu",
    "wb_menu": "main"
}

keyboards_map = {
    "main": main_keyboard,
    "wb_menu": wb_menu_keyboard,
    "prices": prices_keyboard,
    "content": content_keyboard,
    "ai_assistant": ai_assistant_keyboard,
    "settings": settings_keyboard
}

section_titles = {
    "main": "Я — ваш персональный ассистент для работы с кабинетом WildBerries.\n\nПодключите кабинет, чтобы начать.",
    "wb_menu": "✅ Кабинет '{user_name}'\nПоследнее обновление: 5 минут назад\n\nВыберите, с чем хотите поработать:",
    "orders": "🛒 Заказы\n\nПросмотр последних заказов и детальных отчетов.\n\nЗагружаю данные...",
    "analytics": "📊 Аналитика\n\nКлючевые показатели за сегодня:\n- Выручка: 123 456 ₽ (+15%)\n- Заказы: 89 шт. (-5%)\n- Конверсия в заказ: 4.2%\n\nЧто вас интересует подробнее?",
    "stock": "📦 Склад\n\nОбщая стоимость остатков: 1 234 567 ₽\nТоваров на исходе (менее 7 дней): 5 шт.\n\nВыберите действие:",
    "reviews": "⭐ Отзывы\n\nУ вас 12 новых отзывов.\nТребуют ответа: 3 критических (1-3⭐)\n\nЧто будем делать?",
    "prices": "💰 Цены и конкуренты\n\nВыгоднее конкурентов: 45 позиций\nДороже конкурентов: 12 позиций\n\nВыберите, что проанализировать:",
    "notifications": "🔔 Уведомления\n\nReal-time уведомления о новых заказах, остатках и отзывах.\n\nЗагружаю настройки...",
    "content": "🎨 Контент-студия\n\nЗдесь мы можем создать продающие тексты и изображения для ваших карточек товаров. Начнем творить?",
    "ai_assistant": "🤖 AI-ассистент\n\nЯ готов проанализировать ваши данные, найти точки роста или ответить на любой вопрос о вашем бизнесе. Просто спросите. Например: 'Какие 5 товаров принесли больше всего прибыли за месяц?'",
    "settings": "⚙️ Настройки\n\nУправление подключениями, доступами и уведомлениями."
}


async def get_section_text(menu_name: str, user: User) -> str:
    """
    Возвращает текст для указанного раздела меню, форматируя его при необходимости.
    """
    text_template = section_titles.get(menu_name, "")

    if 'user_name' in text_template:
        user_name = f"{user.first_name} {user.last_name or ''}".strip()
        return text_template.format(user_name=user_name)
    
    return text_template


@router.callback_query(F.data == "connect_wb")
async def connect_wb_callback(callback: CallbackQuery):
    # Проверяем, есть ли уже подключенный кабинет
    from api.client import bot_api_client
    
    response = await bot_api_client.get_cabinet_status(
        user_id=callback.from_user.id
    )
    
    if response.success and response.data:
        # Кабинет уже подключен, показываем дашборд в главном меню
        dashboard_response = await bot_api_client.get_dashboard(
            user_id=callback.from_user.id
        )
        
        if dashboard_response.success:
            # Показываем данные дашборда с кнопками меню
            await safe_edit_message(
                callback=callback,
                text=dashboard_response.telegram_text or "📊 Дашборд загружен",
                reply_markup=wb_menu_keyboard(),
                user_id=callback.from_user.id
            )
        else:
            # Если дашборд не загрузился, показываем обычное меню
            text = await get_section_text("wb_menu", callback.from_user)
            await safe_edit_message(
                callback=callback,
                text=text,
                reply_markup=wb_menu_keyboard(),
                user_id=callback.from_user.id
            )
    else:
        # Кабинет не подключен, показываем меню подключения
        await callback.message.edit_text(
            "🔑 ПОДКЛЮЧЕНИЕ WB КАБИНЕТА\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.\n\n"
            "Выберите действие:",
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


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    # Проверяем, есть ли подключенный кабинет
    from api.client import bot_api_client
    
    response = await bot_api_client.get_cabinet_status(
        user_id=callback.from_user.id
    )
    
    if response.success and response.data:
        # Кабинет подключен - показываем дашборд
        dashboard_response = await bot_api_client.get_dashboard(
            user_id=callback.from_user.id
        )
        
        if dashboard_response.success:
            await safe_edit_message(
                callback=callback,
                text=dashboard_response.telegram_text or "📊 Дашборд загружен",
                reply_markup=wb_menu_keyboard(),
                user_id=callback.from_user.id
            )
        else:
            await safe_edit_message(
                callback=callback,
                text="✅ Кабинет подключен\n\nВыберите действие:",
                reply_markup=wb_menu_keyboard(),
                user_id=callback.from_user.id
            )
    else:
        # Кабинет не подключен - показываем меню подключения
        text = (
            "🔑 ПОДКЛЮЧЕНИЕ WB КАБИНЕТА\n\n"
            "Для работы с ботом необходимо подключить кабинет Wildberries.\n\n"
            "Выберите действие:"
        )
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔑 Подключить кабинет",
                    callback_data="settings_api_key"
                )],
                [InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )]
            ]),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Прямой обработчик для кнопки 'Назад в меню' - показывает дашборд"""
    logger.info(f"🔍 DEBUG: Обработка main_menu для пользователя {callback.from_user.id}")
    
    from api.client import bot_api_client
    
    dashboard_response = await bot_api_client.get_dashboard(
        user_id=callback.from_user.id
    )
    
    if dashboard_response.success:
        await safe_edit_message(
            callback=callback,
            text=dashboard_response.telegram_text or "📊 Дашборд загружен",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    else:
        await safe_edit_message(
            callback=callback,
            text="✅ Кабинет подключен\n\nВыберите действие:",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data == "wb_menu")
async def wb_menu_callback(callback: CallbackQuery):
    """Обработчик для кнопки 'Назад к меню' - показывает дашборд"""
    logger.info(f"🔍 DEBUG: Обработка wb_menu для пользователя {callback.from_user.id}")
    
    from api.client import bot_api_client
    
    dashboard_response = await bot_api_client.get_dashboard(
        user_id=callback.from_user.id
    )
    
    if dashboard_response.success:
        await safe_edit_message(
            callback=callback,
            text=dashboard_response.telegram_text or "📊 Дашборд загружен",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    else:
        await safe_edit_message(
            callback=callback,
            text="✅ Кабинет подключен\n\nВыберите действие:",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data == "export_sheets")
@handle_telegram_errors
async def handle_export_sheets_button(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки экспорта в Google Sheets"""
    user_id = callback.from_user.id
    logger.info(f"🔍 DEBUG: Получен callback для export_sheets от пользователя {user_id}")
    await export_to_sheets_from_callback(callback.message, user_id, state)
    await callback.answer()


@router.callback_query(F.data.in_(["prices", "content", "ai_assistant", "settings"]))
async def menu_callback(callback: CallbackQuery):
    data = callback.data

    if data in keyboards_map:
        text = await get_section_text(data, callback.from_user)
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=keyboards_map[data](),
            user_id=callback.from_user.id
        )
        await callback.answer()
        
    elif data.startswith("back_"):
        target_menu = navigation.get(data.replace("back_", ""), "main")
        logger.info(f"🔍 DEBUG: Обработка back_ для {data}, target_menu: {target_menu}")
        
        if data == "back_wb_menu" or target_menu == "wb_menu":
            # Возвращаемся в главное меню - показываем дашборд
            from api.client import bot_api_client
            
            dashboard_response = await bot_api_client.get_dashboard(
                user_id=callback.from_user.id
            )
            
            if dashboard_response.success:
                await safe_edit_message(
                    callback=callback,
                    text=dashboard_response.telegram_text or "📊 Дашборд загружен",
                    reply_markup=wb_menu_keyboard(),
                    user_id=callback.from_user.id
                )
            else:
                text = await get_section_text(target_menu, callback.from_user)
                await safe_edit_message(
                    callback=callback,
                    text=text,
                    reply_markup=keyboards_map[target_menu](),
                    user_id=callback.from_user.id
                )
        else:
            text = await get_section_text(target_menu, callback.from_user)
            await safe_edit_message(
                callback=callback,
                text=text,
                reply_markup=keyboards_map[target_menu](),
                user_id=callback.from_user.id
            )
        await callback.answer()


# Команда /webhook перенесена в handlers/webhook.py


async def export_to_sheets_from_callback(message: Message, user_id: int, state: FSMContext):
    """Экспорт данных в Google Sheets из callback"""
    logger.info(f"🔍 DEBUG: Запуск экспорта для пользователя {user_id} (из callback)")
    
    try:
        from api.client import bot_api_client
        
        logger.info(f"🔍 DEBUG: Вызываем get_dashboard с user_id={user_id}")
        # Получаем информацию о кабинетах пользователя
        dashboard_response = await bot_api_client.get_dashboard(user_id=user_id)
        logger.info(f"🔍 DEBUG: get_dashboard вернул success={dashboard_response.success}")
        logger.info(f"🔍 DEBUG: dashboard_response.data = {dashboard_response.data}")
        
        if not dashboard_response.success or not dashboard_response.data or not dashboard_response.data.get('dashboard'):
            await safe_send_message(
                message=message,
                text="❌ У вас нет активных кабинетов WB. Сначала добавьте кабинет через команду /start",
                user_id=user_id
            )
            return
        
        # У пользователя только один кабинет - создаем экспорт
        # Получаем ID кабинета из API
        cabinet_status_response = await bot_api_client.get_cabinet_status(user_id=user_id)
        if not cabinet_status_response.success:
            await safe_send_message(
                message=message,
                text="❌ Ошибка получения ID кабинета. Попробуйте позже.",
                user_id=user_id
            )
            return
        
        # Получаем информацию о кабинете из dashboard
        dashboard_data = dashboard_response.data.get('dashboard', {})
        
        # Извлекаем числовой ID кабинета из строки "cabinet_1" -> 1
        cabinet_id_str = cabinet_status_response.data.get('cabinets', [{}])[0].get('id', 'cabinet_1')
        cabinet_id = int(cabinet_id_str.replace('cabinet_', '')) if cabinet_id_str.startswith('cabinet_') else 1
        
        cabinet = type('Cabinet', (), {
            'id': cabinet_id,  # Числовой ID из API
            'name': dashboard_data.get('cabinet_name', 'Неизвестный кабинет')
        })()
        
        await create_export_for_cabinet(message, cabinet, user_id, state)
            
    except Exception as e:
        logger.error(f"Ошибка в export_to_sheets_from_callback: {e}")
        await safe_send_message(
            message=message,
            text="❌ Произошла ошибка при создании экспорта. Попробуйте позже.",
            user_id=user_id
        )


@router.message(Command("export_sheets"))
@handle_telegram_errors
async def export_to_sheets(message: Message, state: FSMContext):
    """Команда экспорта данных в Google Sheets"""
    user_id = message.from_user.id
    logger.info(f"🔍 DEBUG: Запуск экспорта для пользователя {user_id}")
    
    try:
        from api.client import bot_api_client
        
        logger.info(f"🔍 DEBUG: Вызываем get_dashboard с user_id={user_id}")
        # Получаем информацию о кабинетах пользователя
        dashboard_response = await bot_api_client.get_dashboard(user_id=user_id)
        logger.info(f"🔍 DEBUG: get_dashboard вернул success={dashboard_response.success}")
        logger.info(f"🔍 DEBUG: dashboard_response.data = {dashboard_response.data}")
        
        if not dashboard_response.success or not dashboard_response.data or not dashboard_response.data.get('dashboard'):
            await safe_send_message(
                message=message,
                text="❌ У вас нет активных кабинетов WB. Сначала добавьте кабинет через команду /start",
                user_id=user_id
            )
            return
        
        # У пользователя только один кабинет - создаем экспорт
        # Получаем ID кабинета из API
        cabinet_status_response = await bot_api_client.get_cabinet_status(user_id=user_id)
        if not cabinet_status_response.success:
            await safe_send_message(
                message=message,
                text="❌ Ошибка получения ID кабинета. Попробуйте позже.",
                user_id=user_id
            )
            return
        
        # Получаем информацию о кабинете из dashboard
        dashboard_data = dashboard_response.data.get('dashboard', {})
        
        # Извлекаем числовой ID кабинета из строки "cabinet_1" -> 1
        cabinet_id_str = cabinet_status_response.data.get('cabinets', [{}])[0].get('id', 'cabinet_1')
        cabinet_id = int(cabinet_id_str.replace('cabinet_', '')) if cabinet_id_str.startswith('cabinet_') else 1
        
        cabinet = type('Cabinet', (), {
            'id': cabinet_id,  # Числовой ID из API
            'name': dashboard_data.get('cabinet_name', 'Неизвестный кабинет')
        })()
        
        await create_export_for_cabinet(message, cabinet, user_id, state)
            
    except Exception as e:
        logger.error(f"Ошибка в команде export_sheets: {e}")
        await safe_send_message(
            message=message,
            text="❌ Произошла ошибка при создании экспорта. Попробуйте позже.",
            user_id=user_id
        )


async def create_export_for_cabinet(message: Message, cabinet, user_id: int, state: FSMContext = None):
    """Настраивает экспорт для конкретного кабинета"""
    try:
        import os
        
        # Получаем ID шаблона из переменных окружения
        template_id = os.getenv('GOOGLE_TEMPLATE_SPREADSHEET_ID')
        if not template_id:
            await safe_send_message(
                message=message,
                text="❌ Шаблон Google Sheets не настроен. Обратитесь к администратору.",
                user_id=user_id
            )
            return
        template_url = f"https://docs.google.com/spreadsheets/d/{template_id}/copy"

        # 1) Проверяем, привязана ли таблица
        from api.client import bot_api_client
        existing_sheet = await bot_api_client.get_cabinet_spreadsheet(cabinet.id)
        
        if existing_sheet.success and existing_sheet.data and existing_sheet.data.get("spreadsheet_id"):
            sheet_url = existing_sheet.data.get("spreadsheet_url")
            text = (
                f"📊 Экспорт в Google Sheets\n\n"
                f"🔗 Текущая таблица: {sheet_url}\n\n"
                f"ℹ️ Данные обновляются автоматически по расписанию.\n"
                f"Вы можете обновить вручную или заменить таблицу."
            )
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить сейчас", callback_data=f"manual_export_update_{cabinet.id}")],
                [InlineKeyboardButton(text="♻️ Сменить таблицу", callback_data=f"change_spreadsheet_{cabinet.id}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_wb_menu")]
            ])
            await safe_send_message(message=message, text=text, reply_markup=kb, user_id=user_id)
            return
        
        # 2) Если таблица не привязана — поведение как раньше (инструкция + ожидание URL)
        if state:
            await state.update_data(cabinet_id=cabinet.id)
            from core.states import ExportStates
            await state.set_state(ExportStates.waiting_for_spreadsheet_url)

        text = f"""📊 Экспорт в Google Sheets

📋 Инструкция:

1️⃣ Откройте ссылку и скопируйте таблицу:
{template_url}

2️⃣ Дайте доступ боту:
   • Нажмите "Настроить доступ"
   • Добавьте: wb-assist-sheets@wb-assist.iam.gserviceaccount.com
   • Дайте права "Редактор"

3️⃣ Отправьте мне ссылку на вашу скопированную таблицу

✨ После этого данные будут обновляться автоматически!

💡 Поддержка: @wb_assist_bot"""
        
        await safe_send_message(message=message, text=text, user_id=user_id)
        
    except Exception as e:
        logger.error(f"Ошибка настройки экспорта для кабинета {cabinet.id}: {e}")
        await safe_send_message(
            message=message,
            text="❌ Произошла ошибка. Попробуйте позже.",
            user_id=user_id
        )


async def show_cabinet_selection(message: Message, cabinets, user_id: int):
    """Показывает выбор кабинета для экспорта"""
    from keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for cabinet in cabinets:
        cabinet_name = cabinet.name or f"Кабинет {cabinet.id}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📊 {cabinet_name}",
                callback_data=f"export_cabinet_{cabinet.id}"
            )
        ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_export")
    ])
    
    await safe_send_message(
        message=message,
        text="📊 **Выберите кабинет для экспорта в Google Sheets:**",
        reply_markup=keyboard,
        user_id=user_id
    )


@router.callback_query(F.data.startswith("export_cabinet_"))
@handle_telegram_errors
async def handle_cabinet_export_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора кабинета для экспорта"""
    try:
        cabinet_id = int(callback.data.replace("export_cabinet_", ""))
        user_id = callback.from_user.id
        
        from api.client import bot_api_client
        
        # Получаем информацию о кабинете
        dashboard_response = await bot_api_client.get_dashboard(user_id=user_id)
        cabinet = None
        
        if dashboard_response.success and dashboard_response.cabinets:
            cabinet = next((c for c in dashboard_response.cabinets if c.id == cabinet_id), None)
        
        if not cabinet:
            await callback.answer("❌ Кабинет не найден", show_alert=True)
            return
        
        await callback.answer()
        await create_export_for_cabinet(callback.message, cabinet, user_id, state)
        
    except Exception as e:
        logger.error(f"Ошибка обработки выбора кабинета: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_export")
@handle_telegram_errors
async def handle_cancel_export(callback: CallbackQuery, state: FSMContext):
    """Отмена экспорта"""
    await callback.answer("❌ Экспорт отменен")
    await state.clear()
    await safe_edit_message(
        callback=callback,
        text="❌ Экспорт отменен",
        user_id=callback.from_user.id
    )


@router.callback_query(F.data.startswith("change_spreadsheet_"))
@handle_telegram_errors
async def handle_change_spreadsheet(callback: CallbackQuery, state: FSMContext):
    """Включает режим смены таблицы и показывает инструкцию"""
    try:
        import os
        from core.states import ExportStates
        
        cabinet_id = int(callback.data.replace("change_spreadsheet_", ""))
        template_id = os.getenv('GOOGLE_TEMPLATE_SPREADSHEET_ID')
        template_url = f"https://docs.google.com/spreadsheets/d/{template_id}/copy" if template_id else None
        
        await state.update_data(cabinet_id=cabinet_id)
        await state.set_state(ExportStates.waiting_for_spreadsheet_url)
        
        text = (
            "🔄 Смена таблицы экспорта.\n\n"
            "📋 Инструкция:\n\n"
            f"1️⃣ Откройте ссылку и скопируйте таблицу:\n{template_url}\n\n"
            "2️⃣ Дайте доступ боту:\n"
            "   • Нажмите \"Настроить доступ\"\n"
            "   • Добавьте: wb-assist-sheets@wb-assist.iam.gserviceaccount.com\n"
            "   • Дайте права \"Редактор\"\n\n"
            "3️⃣ Отправьте мне ссылку на вашу скопированную таблицу"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_export")]
        ])
        
        # Отправляем фото с текстом как подписью
        try:
            photo1_path = Path(__file__).parent.parent / "assets" / "1.png"
            photo1 = FSInputFile(photo1_path)
            
            # Удаляем предыдущее сообщение и отправляем фото
            await callback.message.delete()
            
            # Отправляем фото с текстом как подписью
            await callback.message.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=photo1,
                caption=text,
                reply_markup=kb
            )
                
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            # Фолбэк - отправляем обычное сообщение
            await safe_send_message(
                message=callback.message,
                text=text,
                reply_markup=kb,
                user_id=callback.from_user.id
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка смены таблицы: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.message(F.text.startswith("http"))
@handle_telegram_errors
async def check_export_state(message: Message, state: FSMContext):
    """Проверяет состояние для экспорта при получении ссылки"""
    from core.states import ExportStates
    
    # Проверяем, что это ссылка на Google Sheets
    if 'docs.google.com/spreadsheets' not in message.text:
        return  # Не обрабатываем, пропускаем другим handlers
    
    current_state = await state.get_state()
    
    logger.info(f"🔍 Received Google Sheets URL. Current state: {current_state}")
    
    if current_state == ExportStates.waiting_for_spreadsheet_url:
        logger.info(f"✅ State matches, processing spreadsheet URL")
        await process_spreadsheet_url(message, state)
    else:
        # Состояние не совпадает - возможно пользователь просто отправил ссылку
        # Пытаемся найти кабинет пользователя и использовать его
        logger.info(f"⚠️ State does not match. Trying to find cabinet automatically")
        await process_spreadsheet_url_auto(message, state)


# Функция для обработки ссылки
async def process_spreadsheet_url(message: Message, state: FSMContext):
    """Обрабатывает ссылку на Google Sheets от пользователя"""
    user_id = message.from_user.id
    spreadsheet_url = message.text.strip()
    
    logger.info(f"🔍 Processing spreadsheet URL: {spreadsheet_url[:50]}...")
    
    try:
        from api.client import bot_api_client
        from core.states import ExportStates
        
        # Получаем cabinet_id из состояния
        data = await state.get_data()
        cabinet_id = data.get('cabinet_id')
        
        if not cabinet_id:
            await safe_send_message(
                message=message,
                text="❌ Ошибка: не найден ID кабинета. Попробуйте еще раз.",
                user_id=user_id
            )
            await state.clear()
            return
        
        # Проверяем, что это похоже на URL Google Sheets
        if 'docs.google.com/spreadsheets' not in spreadsheet_url:
            await safe_send_message(
                message=message,
                text="❌ Неверный формат ссылки. Отправьте корректную ссылку на Google Sheets таблицу.",
                user_id=user_id
            )
            return
        
        # Сохраняем spreadsheet_id через API
        response = await bot_api_client.set_cabinet_spreadsheet(
            cabinet_id=cabinet_id,
            spreadsheet_url=spreadsheet_url
        )
        
        if response.success:
            # Очищаем состояние
            await state.clear()
            
            # Отправляем успешное сообщение
            text = """✅ Таблица успешно привязана!

📊 Ваши данные будут обновляться автоматически.

🔄 Хотите обновить таблицу прямо сейчас?"""
            
            from keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Обновить сейчас",
                    callback_data=f"manual_export_update_{cabinet_id}"
                )],
                [InlineKeyboardButton(
                    text="❌ Пропустить",
                    callback_data="cancel_export"
                )]
            ])
            
            await safe_send_message(
                message=message,
                text=text,
                reply_markup=keyboard,
                user_id=user_id
            )
        else:
            await safe_send_message(
                message=message,
                text=f"❌ Ошибка привязки таблицы: {response.error}\n\nПопробуйте еще раз или проверьте, что вы дали доступ боту.",
                user_id=user_id
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки ссылки на таблицу: {e}")
        await safe_send_message(
            message=message,
            text="❌ Произошла ошибка. Попробуйте позже.",
            user_id=user_id
        )
        await state.clear()


@router.callback_query(F.data.startswith("manual_export_update_"))
@handle_telegram_errors
async def handle_manual_export_update(callback: CallbackQuery):
    """Обработка ручного обновления таблицы"""
    try:
        from api.client import bot_api_client
        
        cabinet_id = int(callback.data.replace("manual_export_update_", ""))
        user_id = callback.from_user.id
        
        # Показываем сообщение о запуске обновления
        await callback.answer("⏳ Обновляю таблицу...", show_alert=False)
        
        await safe_edit_message(
            callback=callback,
            text="⏳ Обновление таблицы...\nЭто может занять несколько секунд.",
            user_id=user_id
        )
        
        # Запускаем обновление
        response = await bot_api_client.update_cabinet_spreadsheet(cabinet_id)
        
        if response.success:
            text = (
                "✅ Таблица успешно обновлена!\n\n"
                "Данные обновлены и готовы к использованию.\n\n"
                "ℹ️ Для отображения изображений - разрешите доступ третьим сторонам. "
                "Третья сторона - Wildberries, откуда таблица получает фото товара"
            )
            
            # Отправляем фото с текстом
            try:
                photo3_path = Path(__file__).parent.parent / "assets" / "3.png"
                photo3 = FSInputFile(photo3_path)
                
                # Удаляем предыдущее сообщение и отправляем фото с текстом
                await callback.message.delete()
                await callback.message.bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=photo3,
                    caption=text
                )
            except Exception as e:
                logger.error(f"Ошибка отправки фото: {e}")
                # Фолбэк - отправляем обычное сообщение
                await safe_edit_message(
                    callback=callback,
                    text=text,
                    user_id=user_id
                )
        else:
            await safe_edit_message(
                callback=callback,
                text=f"❌ Ошибка обновления таблицы: {response.error}",
                user_id=user_id
            )
            
    except Exception as e:
        logger.error(f"Ошибка ручного обновления таблицы: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def process_spreadsheet_url_auto(message: Message, state: FSMContext):
    """Автоматическая обработка ссылки без состояния"""
    user_id = message.from_user.id
    spreadsheet_url = message.text.strip()
    
    logger.info(f"🔍 Auto-processing spreadsheet URL for user {user_id}")
    
    try:
        from api.client import bot_api_client
        
        # Пытаемся получить кабинеты пользователя
        cabinets_response = await bot_api_client.get_user_cabinets(user_id)
        
        if not cabinets_response.success or not cabinets_response.data:
            await safe_send_message(
                message=message,
                text="❌ У вас нет подключенных кабинетов. Сначала подключите кабинет через /start",
                user_id=user_id
            )
            return
        
        cabinets = cabinets_response.data if isinstance(cabinets_response.data, list) else []
        
        if not cabinets:
            await safe_send_message(
                message=message,
                text="❌ У вас нет подключенных кабинетов",
                user_id=user_id
            )
            return
        
        # Берем первый кабинет
        cabinet_id = cabinets[0].get('id') if isinstance(cabinets[0], dict) else cabinets[0].id
        
        logger.info(f"📊 Using cabinet {cabinet_id} for auto-processing")
        
        # Сохраняем spreadsheet_id через API
        response = await bot_api_client.set_cabinet_spreadsheet(
            cabinet_id=cabinet_id,
            spreadsheet_url=spreadsheet_url
        )
        
        if response.success:
            # Отправляем успешное сообщение
            text = f"""✅ Таблица успешно привязана к кабинету!

📊 Ваши данные будут обновляться автоматически.

🔄 Хотите обновить таблицу прямо сейчас?"""
            
            from keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Обновить сейчас",
                    callback_data=f"manual_export_update_{cabinet_id}"
                )],
                [InlineKeyboardButton(
                    text="❌ Пропустить",
                    callback_data="cancel_export"
                )]
            ])
            
            await safe_send_message(
                message=message,
                text=text,
                reply_markup=keyboard,
                user_id=user_id
            )
        else:
            await safe_send_message(
                message=message,
                text=f"❌ Ошибка привязки таблицы: {response.error}\n\nУбедитесь, что вы дали доступ боту.",
                user_id=user_id
            )
            
    except Exception as e:
        logger.error(f"Ошибка автоматической обработки ссылки: {e}")
        await safe_send_message(
            message=message,
            text="❌ Произошла ошибка. Попробуйте позже.",
            user_id=user_id
    )
