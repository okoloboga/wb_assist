from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключить кабинет WB", callback_data="connect_wb")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])


def wb_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Дашборд", callback_data="dashboard"),
            InlineKeyboardButton(text="🛒 Заказы", callback_data="orders")
        ],
        [
            InlineKeyboardButton(text="📦 Склад", callback_data="stock"),
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews")
        ],
        [
            InlineKeyboardButton(text="📈 Аналитика", callback_data="analytics"),
            InlineKeyboardButton(text="💰 Цены", callback_data="prices")
        ],
        [
            InlineKeyboardButton(text="🔄 Синхронизация", callback_data="sync"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")
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


# Динамические клавиатуры для обработчиков

def create_orders_keyboard(orders: list, offset: int = 0, has_more: bool = False) -> InlineKeyboardMarkup:
    """Создать клавиатуру для списка заказов"""
    buttons = []
    
    # Кнопки для каждого заказа
    for order in orders[:5]:  # Показываем максимум 5 заказов
        order_text = f"#{order.get('id', 'N/A')} | {order.get('amount', 0):,}₽"
        callback_data = f"order_details_{order.get('id', 'N/A')}"
        buttons.append([InlineKeyboardButton(
            text=order_text,
            callback_data=callback_data
        )])
    
    # Навигационные кнопки
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"orders_page_{max(0, offset-10)}"
        ))
    
    if has_more:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"orders_page_{offset+10}"
        ))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Кнопка возврата
    buttons.append([InlineKeyboardButton(
        text="🔙 Назад к меню",
        callback_data="back_analytics"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_stocks_keyboard(has_more: bool = False, offset: int = 0) -> InlineKeyboardMarkup:
    """Создать клавиатуру для остатков"""
    buttons = []
    
    # Навигационные кнопки
    if offset > 0 or has_more:
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"stocks_page_{max(0, offset-20)}"
            ))
        
        if has_more:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"stocks_page_{offset+20}"
            ))
        
        if nav_buttons:
            buttons.append(nav_buttons)
    
    # Кнопки действий
    buttons.extend([
        [InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="refresh_stocks"
        )],
        [InlineKeyboardButton(
            text="📊 Прогноз остатков",
            callback_data="stock_forecast"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="back_stock"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_reviews_keyboard(has_more: bool = False, offset: int = 0) -> InlineKeyboardMarkup:
    """Создать клавиатуру для отзывов"""
    buttons = []
    
    # Навигационные кнопки
    if offset > 0 or has_more:
        nav_buttons = []
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"reviews_page_{max(0, offset-10)}"
            ))
        
        if has_more:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"reviews_page_{offset+10}"
            ))
        
        if nav_buttons:
            buttons.append(nav_buttons)
    
    # Кнопки действий
    buttons.extend([
        [InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="refresh_reviews"
        )],
        [InlineKeyboardButton(
            text="🤖 Автоответы",
            callback_data="auto_answers"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="back_reviews"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_analytics_keyboard(period: str = "7d") -> InlineKeyboardMarkup:
    """Создать клавиатуру для аналитики"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📅 7 дней" if period != "7d" else "✅ 7 дней",
                callback_data="analytics_period_7d"
            ),
            InlineKeyboardButton(
                text="📅 30 дней" if period != "30d" else "✅ 30 дней",
                callback_data="analytics_period_30d"
            ),
            InlineKeyboardButton(
                text="📅 90 дней" if period != "90d" else "✅ 90 дней",
                callback_data="analytics_period_90d"
            )
        ],
        [InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="refresh_analytics"
        )],
        [InlineKeyboardButton(
            text="📊 Динамика",
            callback_data="dynamics"
        )],
        [InlineKeyboardButton(
            text="💰 Конверсия",
            callback_data="avg_check"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="back_analytics"
        )]
    ])


def create_sync_keyboard(sync_id: str = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру для синхронизации"""
    buttons = []
    
    if sync_id:
        buttons.append([InlineKeyboardButton(
            text="🔄 Обновить статус",
            callback_data=f"sync_status_{sync_id}"
        )])
    
    buttons.extend([
        [InlineKeyboardButton(
            text="🔄 Запустить синхронизацию",
            callback_data="start_sync"
        )],
        [InlineKeyboardButton(
            text="📊 Статус синхронизации",
            callback_data="sync_status"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="back_analytics"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_notification_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру для настроек уведомлений"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔔 Новые заказы",
            callback_data="toggle_orders_notifications"
        )],
        [InlineKeyboardButton(
            text="⚠️ Критичные остатки",
            callback_data="toggle_stocks_notifications"
        )],
        [InlineKeyboardButton(
            text="⭐ Новые отзывы",
            callback_data="toggle_reviews_notifications"
        )],
        [InlineKeyboardButton(
            text="🔄 Синхронизация",
            callback_data="toggle_sync_notifications"
        )],
        [InlineKeyboardButton(
            text="🧪 Тестовое уведомление",
            callback_data="test_notification"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к настройкам",
            callback_data="back_settings"
        )]
    ])
