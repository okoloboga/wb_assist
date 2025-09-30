from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключить кабинет WB", callback_data="connect_wb")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])


def wb_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Аналитика", callback_data="analytics"),
            InlineKeyboardButton(text="📦 Склад", callback_data="stock")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews"),
            InlineKeyboardButton(text="💰 Цены, конкуренты", callback_data="prices")
        ],
        [
            InlineKeyboardButton(text="🎨 Контент", callback_data="content"),
            InlineKeyboardButton(text="🤖 AI-помощник", callback_data="ai_assistant")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ])


def analytics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Продажи", callback_data="sales_period"),
            InlineKeyboardButton(text="📈 Выкупы", callback_data="dynamics")
        ],
        [
            InlineKeyboardButton(text="💸 Конверсия", callback_data="avg_check"),
            InlineKeyboardButton(text="📤 Выгрузка в Google", callback_data="export_sales")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_analytics")]
    ])


def stock_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Остатки", callback_data="stock_list"),
            InlineKeyboardButton(text="⏳ Прогноз остатков", callback_data="stock_forecast")
        ],
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="stock_notify"),
            InlineKeyboardButton(text="📤 Выгрузка в Google", callback_data="export_stock")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_stock")]
    ])


def reviews_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆕 Новые отзывы", callback_data="new_reviews"),
            InlineKeyboardButton(text="🚨 Критические 1–3⭐", callback_data="critical_reviews")
        ],
        [
            InlineKeyboardButton(text="🤖 Автоответы 4–5⭐", callback_data="auto_answers"),
            InlineKeyboardButton(text="📤 Выгрузка в Google Sheets", callback_data="export_reviews")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_reviews")]
    ])


def prices_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💲 Мои цены", callback_data="my_prices"),
            InlineKeyboardButton(text="⚖️ Цены конкурентов", callback_data="competitor_prices")
        ],
        [
            InlineKeyboardButton(text="📊 История", callback_data="price_history"),
            InlineKeyboardButton(text="📤 Выгрузка в Google Sheets", callback_data="export_prices")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_prices")]
    ])


def content_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Текст карточек", callback_data="generate_text"),
            InlineKeyboardButton(text="🖼 Изображения", callback_data="generate_images")
        ],
        [InlineKeyboardButton(text="📂 Архив", callback_data="content_archive")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_content")]
    ])


def ai_assistant_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Примеры запросов", callback_data="ai_examples")],
        [InlineKeyboardButton(text="📤 Выгрузка анализа в Google Sheets", callback_data="ai_export_gs")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_ai_assistant")]
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключение WB-кабинета (API-ключ)", callback_data="settings_api_key")],
        [InlineKeyboardButton(text="👥 Доступы (добавить/удалить пользователя по TelegramID)", callback_data="settings_access")],
        [InlineKeyboardButton(text="🔔 Уведомления (вкл/выкл, частота)", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="🌐 Интеграции (Google Sheets, Docs)", callback_data="settings_integrations")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_settings")]
    ])
