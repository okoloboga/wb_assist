"""
Клавиатуры для раздела параметров
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="measurements:cancel"
        )]
    ])


def get_measurements_menu_keyboard():
    """Клавиатура главного меню параметров"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Добавить/изменить параметры",
            callback_data="measurements:edit_menu"
        )],
        [InlineKeyboardButton(
            text="📸 Мои фото",
            callback_data="my_photos"
        )],
        [InlineKeyboardButton(
            text="◀️ В главное меню",
            callback_data="main_menu"
        )]
    ])


from typing import Optional, Dict

def get_edit_measurements_keyboard(measurements: Optional[Dict] = None) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора параметра для редактирования.
    Динамически добавляет текущие значения пользователя к кнопкам.
    """
    if measurements is None:
        measurements = {}

    # Словарь с текстами кнопок и соответствующими ключами параметров
    button_definitions = {
        'russian_size': "📏 Российский размер",
        'shoulder_length': "👔 Длина плеч",
        'back_width': "👔 Ширина спины",
        'sleeve_length': "👕 Длина рукава",
        'back_length': "👕 Длина по спинке",
        'chest': "👚 Обхват груди",
        'waist': "👖 Обхват талии",
        'hips': "🍑 Обхват бедер",
        'pants_length': "👖 Длина брюк",
        'waist_girth': "⚡ Обхват в поясе",
        'rise_height': "📐 Высота посадки",
        'back_rise_height': "📐 Посадка сзади",
    }

    def get_button_text(param_key: str) -> str:
        """Формирует текст для кнопки, добавляя значение, если оно есть"""
        base_text = button_definitions[param_key]
        value = measurements.get(param_key)
        if value is not None and value != '':
            return f"{base_text}: {value}"
        return base_text

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_button_text('russian_size'),
                callback_data="measurements:edit:russian_size"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('shoulder_length'),
                callback_data="measurements:edit:shoulder_length"
            ),
            InlineKeyboardButton(
                text=get_button_text('back_width'),
                callback_data="measurements:edit:back_width"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('sleeve_length'),
                callback_data="measurements:edit:sleeve_length"
            ),
            InlineKeyboardButton(
                text=get_button_text('back_length'),
                callback_data="measurements:edit:back_length"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('chest'),
                callback_data="measurements:edit:chest"
            ),
            InlineKeyboardButton(
                text=get_button_text('waist'),
                callback_data="measurements:edit:waist"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('hips'),
                callback_data="measurements:edit:hips"
            ),
            InlineKeyboardButton(
                text=get_button_text('pants_length'),
                callback_data="measurements:edit:pants_length"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('waist_girth'),
                callback_data="measurements:edit:waist_girth"
            ),
        ],
        [
            InlineKeyboardButton(
                text=get_button_text('rise_height'),
                callback_data="measurements:edit:rise_height"
            ),
            InlineKeyboardButton(
                text=get_button_text('back_rise_height'),
                callback_data="measurements:edit:back_rise_height"
            )
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="measurements")]
    ])


def get_go_to_catalog_keyboard():
    """Клавиатура с кнопкой перехода в каталог"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Перейти в каталог",
            callback_data="back:categories"
        )]
    ])