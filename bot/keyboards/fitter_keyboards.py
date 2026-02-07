"""
Клавиатуры для функционала примерки одежды (Fitter)
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


def get_fitter_main_menu(has_tryon_history: bool = False):
    """Получить клавиатуру главного меню (скопировано из донора)

    Args:
        has_tryon_history: True если у пользователя есть история примерок
    """
    buttons = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"),
            InlineKeyboardButton(text="⭐️ Избранное", callback_data="favorites")
        ],
        [InlineKeyboardButton(text="📐 Мои параметры", callback_data="measurements")],
    ]

    # Добавляем кнопку истории примерок если есть история
    if has_tryon_history:
        buttons.append([InlineKeyboardButton(text="📜 История примерок", callback_data="tryon_history")])

    buttons.append([InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_fitter_mode_selection():
    """Клавиатура выбора режима примерки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👕 Только этот товар", callback_data="fitter:mode:single_item")],
        [InlineKeyboardButton(text="👗 Весь образ с фото", callback_data="fitter:mode:full_outfit")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
    ])


def get_fitter_category_selection():
    """Клавиатура выбора категории одежды"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👕 Верхняя одежда", callback_data="fitter:category:tops")],
        [InlineKeyboardButton(text="👖 Нижняя одежда", callback_data="fitter:category:bottoms")],
        [InlineKeyboardButton(text="👗 Платья", callback_data="fitter:category:dresses")],
        [InlineKeyboardButton(text="👟 Обувь", callback_data="fitter:category:shoes")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="fitter_main")]
    ])


def get_fitter_back_to_main():
    """Кнопка возврата в главное меню примерки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="fitter_main")]
    ])


def get_consent_keyboard():
    """Клавиатура согласия на обработку фото"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="fitter:consent:yes")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="fitter:consent:no")]
    ])


def get_photo_selection_keyboard(photos: list):
    """Клавиатура выбора фото"""
    keyboard = []
    for i, photo in enumerate(photos):
        keyboard.append([
            InlineKeyboardButton(
                text=f"📸 Фото {i+1} ({datetime.fromisoformat(photo['uploaded_at']).strftime('%d.%m.%Y')})",
                callback_data=f"fitter:select_photo:{photo['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="📤 Загрузить новое фото", callback_data="fitter:upload_new")])
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_model_selection_keyboard():
    """Клавиатура выбора модели генерации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Быстрая (~1-2 мин)", callback_data="fitter:model:fast")],
        [InlineKeyboardButton(text="👑 Качественная (~3-4 мин)", callback_data="fitter:model:pro")],
        [InlineKeyboardButton(text="🚀 GPT Image 1.5 (~3-4 мин)", callback_data="fitter:model:gpt-image-1.5")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
    ])


def get_fitter_mode_keyboard():
    """Клавиатура выбора режима примерки (идентично донору)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👕 Только этот товар", callback_data="fitter:mode:single_item")],
        [InlineKeyboardButton(text="👗 Весь образ с фото", callback_data="fitter:mode:full_outfit")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
    ])


def get_fitter_result_keyboard(fitter_id: int, product_id: str, wb_link: str, ozon_url: str = None,
                              source: str = 'catalog', category_id: str = '', index: int = 0):
    """Клавиатура после успешной примерки (идентично донору)"""
    keyboard = []

    # Кнопки магазинов в одну строку если есть обе ссылки
    shop_buttons = []
    if wb_link:
        shop_buttons.append(InlineKeyboardButton(text="Wildberries", url=wb_link))
    if ozon_url:
        shop_buttons.append(InlineKeyboardButton(text="Ozon", url=ozon_url))

    if shop_buttons:
        if len(shop_buttons) == 2:
            keyboard.append(shop_buttons)
        else:
            keyboard.append([shop_buttons[0]])

    # Формируем коллбэк для возврата
    if source == 'catalog':
        back_callback = f"back:product:{product_id}:{category_id}:{index}"
    elif source == 'favorites':
        back_callback = f"back_fav:{product_id}:{index}"
    else:
        # Фоллбэк на старое поведение, если источник неизвестен
        back_callback = f"product:{product_id}"
        
    retry_callback = f"fitter:retry:{source}:{product_id}:{category_id}:{index}"

    keyboard.extend([
        [InlineKeyboardButton(text="💾 Сохранить результат", callback_data=f"fitter:save_result:{fitter_id}")],
        [InlineKeyboardButton(text="🔄 Другое фото", callback_data=retry_callback)],
        [InlineKeyboardButton(text="◀️ К товару", callback_data=back_callback)]
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_my_photos_keyboard():
    """Клавиатура управления фото (идентично донору)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить фото", callback_data="fitter:upload_new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="measurements_menu")]
    ])


def get_photo_manage_keyboard(photo_id: int):
    """Клавиатура управления конкретным фото (идентично донору)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"fitter:delete_photo:{photo_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_photos")]
    ])


def get_history_navigation_keyboard(index: int, total: int, fitter: dict):
    """Клавиатура навигации по истории примерок (идентично донору)"""
    buttons = []
    
    # Кнопки магазинов
    shop_buttons = []
    wb_link = fitter.get('wb_link')
    ozon_url = fitter.get('ozon_url')
    if wb_link:
        shop_buttons.append(InlineKeyboardButton(text="Wildberries", url=wb_link))
    if ozon_url:
        shop_buttons.append(InlineKeyboardButton(text="Ozon", url=ozon_url))
    
    if shop_buttons:
        buttons.append(shop_buttons)

    # Навигация
    nav_row = []
    if index > 0: 
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"fitter_hist:prev:{index}"))
    nav_row.append(InlineKeyboardButton(text=f"({index+1}/{total})", callback_data="noop"))
    if index < total - 1: 
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"fitter_hist:next:{index}"))
    
    if nav_row:
        buttons.append(nav_row)

    # Управление и выход
    fitter_id = fitter["id"]
    buttons.extend([
        [InlineKeyboardButton(text="💾 Скачать", callback_data=f"fitter_hist:download:{fitter_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"fitter_hist:delete:{fitter_id}")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="fitter_main")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)