import sys
import logging
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, User, InlineKeyboardMarkup, InlineKeyboardButton, Message
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
