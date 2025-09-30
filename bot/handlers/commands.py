from aiogram import Router, F
from aiogram.types import CallbackQuery, User

from ..keyboards.keyboards import (
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
    "analytics": "wb_menu",
    "stock": "wb_menu",
    "reviews": "wb_menu",
    "prices": "wb_menu",
    "content": "wb_menu",
    "ai_assistant": "wb_menu",
    "settings": "wb_menu",
    "wb_menu": "main"
}

keyboards_map = {
    "main": main_keyboard,
    "wb_menu": wb_menu_keyboard,
    "analytics": analytics_keyboard,
    "stock": stock_keyboard,
    "reviews": reviews_keyboard,
    "prices": prices_keyboard,
    "content": content_keyboard,
    "ai_assistant": ai_assistant_keyboard,
    "settings": settings_keyboard
}

section_titles = {
    "main": "Я — ваш персональный ассистент для работы с кабинетом WildBerries.\n\nПодключите кабинет, чтобы начать.",
    "wb_menu": "✅ Кабинет '{user_name}'\nПоследнее обновление: 5 минут назад\n\nВыберите, с чем хотите поработать:",
    "analytics": "📊 Аналитика\n\nКлючевые показатели за сегодня:\n- Выручка: 123 456 ₽ (+15%)\n- Заказы: 89 шт. (-5%)\n- Конверсия в заказ: 4.2%\n\nЧто вас интересует подробнее?",
    "stock": "📦 Склад\n\nОбщая стоимость остатков: 1 234 567 ₽\nТоваров на исходе (менее 7 дней): 5 шт.\n\nВыберите действие:",
    "reviews": "⭐ Отзывы\n\nУ вас 12 новых отзывов.\nТребуют ответа: 3 критических (1-3⭐)\n\nЧто будем делать?",
    "prices": "💰 Цены и конкуренты\n\nВыгоднее конкурентов: 45 позиций\nДороже конкурентов: 12 позиций\n\nВыберите, что проанализировать:",
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
    text = await get_section_text("wb_menu", callback.from_user)
    await callback.message.edit_text(
        text,
        reply_markup=wb_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    text = (
        "Команды:\n"
        "/sales — продажи\n"
        "/stock — остатки\n"
        "/reviews — отзывы\n"
        "/digest — аналитический дайджест\n\n"
        "Навигация через кнопки в чате."
    )
    await callback.message.edit_text(text, reply_markup=main_keyboard())
    await callback.answer()


@router.callback_query(F.data)
async def menu_callback(callback: CallbackQuery):
    data = callback.data

    if data in keyboards_map:
        text = await get_section_text(data, callback.from_user)
        await callback.message.edit_text(
            text,
            reply_markup=keyboards_map[data]()
        )
        await callback.answer()

    elif data.startswith("back_"):
        target_menu = navigation.get(data.replace("back_", ""), "main")
        text = await get_section_text(target_menu, callback.from_user)
        await callback.message.edit_text(
            text,
            reply_markup=keyboards_map[target_menu]()
        )
        await callback.answer()
