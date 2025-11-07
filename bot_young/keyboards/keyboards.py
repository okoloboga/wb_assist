"""
Inline клавиатуры для bot_young
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import config


def main_menu_keyboard(has_cabinets: bool = True) -> InlineKeyboardMarkup:
    """Главное меню бота"""
    if not has_cabinets:
        # Нет кабинетов - только ссылка на основного бота
        buttons = []
        
        if config.main_bot_username:
            main_bot_url = f"https://t.me/{config.main_bot_username}"
            buttons.append([InlineKeyboardButton(text="🔗 Подключить кабинет", url=main_bot_url)])
        
        buttons.append([InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")])
    else:
        # Есть кабинеты - полное меню
        buttons = [
            [InlineKeyboardButton(text="📢 Мои каналы", callback_data="my_channels")],
            [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channels_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Список каналов пользователя"""
    buttons = []
    
    for channel in channels:
        status_emoji = "✅" if channel.get("is_active") else "⏸"
        chat_title = channel.get("chat_title", "Канал")
        time = channel.get("report_time", "09:00")
        
        button_text = f"{status_emoji} {chat_title} ({time})"
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"channel_detail:{channel['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")
    ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def channel_detail_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """Меню управления отдельным каналом"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Изменить время", callback_data=f"change_time:{channel_id}")],
        [InlineKeyboardButton(text="🗑 Удалить канал", callback_data=f"delete_channel:{channel_id}")],
        [InlineKeyboardButton(text="◀️ К списку каналов", callback_data="my_channels")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_selection_keyboard() -> InlineKeyboardMarkup:
    """Выбор времени отправки сводки"""
    buttons = [
        # Утро
        [
            InlineKeyboardButton(text="06:00", callback_data="time:06:00"),
            InlineKeyboardButton(text="07:00", callback_data="time:07:00"),
            InlineKeyboardButton(text="08:00", callback_data="time:08:00"),
            InlineKeyboardButton(text="09:00", callback_data="time:09:00"),
        ],
        # День
        [
            InlineKeyboardButton(text="12:00", callback_data="time:12:00"),
            InlineKeyboardButton(text="13:00", callback_data="time:13:00"),
            InlineKeyboardButton(text="14:00", callback_data="time:14:00"),
            InlineKeyboardButton(text="15:00", callback_data="time:15:00"),
        ],
        # Вечер
        [
            InlineKeyboardButton(text="18:00", callback_data="time:18:00"),
            InlineKeyboardButton(text="19:00", callback_data="time:19:00"),
            InlineKeyboardButton(text="20:00", callback_data="time:20:00"),
            InlineKeyboardButton(text="21:00", callback_data="time:21:00"),
        ],
        # Свое время
        [InlineKeyboardButton(text="⚙️ Свое время", callback_data="time:custom")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    buttons = [
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_main")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_digit_keyboard(current_value: str = "", is_hours: bool = True) -> InlineKeyboardMarkup:
    """
    Цифровая клавиатура для ввода времени
    
    Args:
        current_value: Текущее значение (например, "09" для часов или "3" для минут)
        is_hours: True если вводим часы, False если минуты
    """
    buttons = []
    
    if is_hours:
        # Для часов - полная клавиатура 0-9
        # Первая строка: 1, 2, 3
        buttons.append([
            InlineKeyboardButton(text="1", callback_data=f"time_digit:1"),
            InlineKeyboardButton(text="2", callback_data=f"time_digit:2"),
            InlineKeyboardButton(text="3", callback_data=f"time_digit:3"),
        ])
        
        # Вторая строка: 4, 5, 6
        buttons.append([
            InlineKeyboardButton(text="4", callback_data=f"time_digit:4"),
            InlineKeyboardButton(text="5", callback_data=f"time_digit:5"),
            InlineKeyboardButton(text="6", callback_data=f"time_digit:6"),
        ])
        
        # Третья строка: 7, 8, 9
        buttons.append([
            InlineKeyboardButton(text="7", callback_data=f"time_digit:7"),
            InlineKeyboardButton(text="8", callback_data=f"time_digit:8"),
            InlineKeyboardButton(text="9", callback_data=f"time_digit:9"),
        ])
        
        # Четвертая строка: 0, удаление, подтверждение
        action_buttons = [
            InlineKeyboardButton(text="0", callback_data=f"time_digit:0"),
            InlineKeyboardButton(text="⌫", callback_data="time_digit:delete"),
        ]
        
        # Кнопка подтверждения (только если есть значение)
        if current_value:
            action_buttons.append(
                InlineKeyboardButton(text="✅", callback_data="time_digit:confirm")
            )
        
        buttons.append(action_buttons)
    else:
        # Для минут - только 0, 1, 2, 3, 4, 5 (для 00, 10, 20, 30, 40, 50)
        # Первая строка: 0, 1, 2
        buttons.append([
            InlineKeyboardButton(text="0 (00)", callback_data=f"time_digit:0"),
            InlineKeyboardButton(text="1 (10)", callback_data=f"time_digit:1"),
            InlineKeyboardButton(text="2 (20)", callback_data=f"time_digit:2"),
        ])
        
        # Вторая строка: 3, 4, 5
        buttons.append([
            InlineKeyboardButton(text="3 (30)", callback_data=f"time_digit:3"),
            InlineKeyboardButton(text="4 (40)", callback_data=f"time_digit:4"),
            InlineKeyboardButton(text="5 (50)", callback_data=f"time_digit:5"),
        ])
        
        # Третья строка: удаление, подтверждение
        action_buttons = [
            InlineKeyboardButton(text="⌫", callback_data="time_digit:delete"),
        ]
        
        # Кнопка подтверждения (только если есть значение)
        if current_value:
            action_buttons.append(
                InlineKeyboardButton(text="✅", callback_data="time_digit:confirm")
            )
        
        buttons.append(action_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

