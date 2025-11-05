from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, Any, Optional
from utils.formatters import format_currency


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключить кабинет WB", callback_data="connect_wb")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])


def wb_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Заказы", callback_data="orders"),
            InlineKeyboardButton(text="📦 Склад", callback_data="stock")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews"),
            InlineKeyboardButton(text="📈 Аналитика", callback_data="analytics")
        ],
        [
            InlineKeyboardButton(text="💰 Цены", callback_data="prices"),
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")
        ],
        [
            InlineKeyboardButton(text="🎨 Контент", callback_data="content"),
            InlineKeyboardButton(text="🤖 AI-помощник", callback_data="ai_assistant")
        ],
        [
            InlineKeyboardButton(text="📊 Экспорт в Google Sheets", callback_data="export_sheets")
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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def stock_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 Уведомления", callback_data="stock_notify"),
            InlineKeyboardButton(text="📤 Выгрузка в Google", callback_data="export_stock")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def content_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Текст карточек", callback_data="generate_text"),
            InlineKeyboardButton(text="🖼 Изображения", callback_data="generate_images")
        ],
        [InlineKeyboardButton(text="📂 Архив", callback_data="content_archive")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def ai_assistant_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 AI-анализ", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="💬 AI-чат", callback_data="ai_chat")],
        [InlineKeyboardButton(text="🎨 Генерация карточки", callback_data="start_card_generation")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Подключение WB-кабинета (API-ключ)", callback_data="settings_api_key")],
        [InlineKeyboardButton(text="👥 Доступы (добавить/удалить пользователя по TelegramID)", callback_data="settings_access")],
        [InlineKeyboardButton(text="🌐 Интеграции (Google Sheets, Docs)", callback_data="settings_integrations")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


# Динамические клавиатуры для обработчиков

def create_orders_keyboard(orders: list, offset: int = 0, has_more: bool = False) -> InlineKeyboardMarkup:
    """Создать клавиатуру для списка заказов"""
    buttons = []
    
    # Кнопки для каждого заказа
    for order in orders:  # Показываем все заказы (до 10)
        # Форматируем дату и время
        order_date = order.get('date', '')
        if order_date:
            # Простое форматирование: 2025-10-24T11:41:25+03:00 -> 2025-10-24 11:41
            if 'T' in order_date and '+03:00' in order_date:
                # МСК время: простое обрезание
                formatted_date = order_date.replace('T', ' ').split('+')[0][:16]  # 2025-10-24 11:41
            else:
                # UTC время или другой формат: используем как есть
                formatted_date = order_date[:16] if len(order_date) > 16 else order_date
        else:
            formatted_date = "N/A"
        
        order_text = f"{formatted_date} | {format_currency(order.get('amount', 0))}"
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
        callback_data="main_menu"
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
            text="🔙 Назад к меню",
            callback_data="main_menu"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_reviews_keyboard(has_more: bool = False, offset: int = 0, rating_threshold: Optional[int] = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру для отзывов с фильтрацией по рейтингу"""
    buttons = []
    
    # Кнопка фильтрации по рейтингу (аналогично уведомлениям)
    def review_filter_text(threshold: Optional[int]) -> str:
        """Форматирование фильтра отзывов"""
        if threshold is None:
            return "⭐ Все отзывы (≤5★)"
        else:
            stars = "⭐" * threshold
            return f"{stars} (≤{threshold}★)"
    
    # Для кнопки фильтра: если None (все отзывы), то передаем 5 в callback_data
    # чтобы цикл был: 1→2→3→4→5→1 (5 = все отзывы)
    filter_callback_value = rating_threshold if rating_threshold is not None else 5
    buttons.append([InlineKeyboardButton(
        text=f"🔍 Фильтр: {review_filter_text(rating_threshold)}",
        callback_data=f"reviews_filter_toggle_{filter_callback_value}"
    )])
    
    # Навигационные кнопки
    if offset > 0 or has_more:
        nav_buttons = []
        threshold_str = str(rating_threshold) if rating_threshold is not None else "all"
        if offset > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"reviews_page_{max(0, offset-10)}_{threshold_str}"
            ))
        
        if has_more:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"reviews_page_{offset+10}_{threshold_str}"
            ))
        
        if nav_buttons:
            buttons.append(nav_buttons)
    
    # Кнопки действий
    buttons.extend([
        [InlineKeyboardButton(
            text="🤖 Автоответы",
            callback_data="auto_answers"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="main_menu"
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
            callback_data="main_menu"
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
            callback_data="main_menu"
        )]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_cabinet_removal_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру для действий после удаления кабинета"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔗 Подключить новый кабинет",
                callback_data="settings_api_key"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Мои кабинеты",
                callback_data="cabinet_status"
            ),
            InlineKeyboardButton(
                text="❓ Помощь",
                callback_data="help"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Главное меню",
                callback_data="main_menu"
            )
        ]
    ])


def create_notification_keyboard(settings: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Создать клавиатуру для настроек уведомлений на основе серверных флагов"""
    def flag_text(enabled: bool) -> str:
        return "✅ Вкл" if enabled else "❌ Выкл"
    
    def review_threshold_text(threshold: int) -> str:
        """Форматирование порога отзывов"""
        if threshold == 0:
            return "❌ Выкл"
        else:
            stars = "⭐" * threshold
            return f"{stars} (≤{threshold}★)"

    new_orders = settings.get("new_orders_enabled", True)
    buyouts = settings.get("order_buyouts_enabled", True)
    cancellations = settings.get("order_cancellations_enabled", True)
    returns = settings.get("order_returns_enabled", True)
    negative_reviews = settings.get("negative_reviews_enabled", True)
    review_threshold = settings.get("review_rating_threshold", 3)
    critical_stocks = settings.get("critical_stocks_enabled", True)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔔 Новые заказы: {flag_text(new_orders)}",
            callback_data="toggle_notif_new_orders"
        )],
        [InlineKeyboardButton(
            text=f"💰 Выкупы: {flag_text(buyouts)}",
            callback_data="toggle_notif_buyouts"
        )],
        [InlineKeyboardButton(
            text=f"↩️ Отмены: {flag_text(cancellations)}",
            callback_data="toggle_notif_cancellations"
        )],
        [InlineKeyboardButton(
            text=f"🔴 Возвраты: {flag_text(returns)}",
            callback_data="toggle_notif_returns"
        )],
        [InlineKeyboardButton(
            text=f"⭐ Отзывы: {review_threshold_text(review_threshold)}",
            callback_data="toggle_notif_negative_reviews"
        )],
        [InlineKeyboardButton(
            text=f"⚠️ Критичные остатки: {flag_text(critical_stocks)}",
            callback_data="toggle_notif_critical_stocks"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад к меню",
            callback_data="wb_menu"
        )]
    ])
