"""
Обработчики для работы с конкурентами
"""

import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from keyboards.keyboards import (
    wb_menu_keyboard,
    main_keyboard,
    create_competitors_list_keyboard, # New import
    create_semantic_core_categories_keyboard,
    create_existing_semantic_core_keyboard
)
from utils.formatters import format_error_message, safe_edit_message, safe_send_message, handle_telegram_errors, split_telegram_message
from api.client import bot_api_client

router = Router()


def validate_competitor_url(url: str) -> bool:
    """Валидация URL конкурента"""
    pattern = r'https?://(www\.)?wildberries\.ru/(brands|seller)/[\w\-]+'
    return bool(re.match(pattern, url))


def create_competitor_products_keyboard(
    products: list,
    competitor_id: int,
    offset: int = 0,
    has_more: bool = False
) -> InlineKeyboardMarkup:
    """Создать клавиатуру для списка товаров конкурента"""
    buttons = []
    
    # Кнопки для каждого товара
    for product in products:
        name = product.get('name') or 'Без названия'
        price = product.get('current_price')
        if price:
            text = f"{name[:40]}"
        else:
            text = name[:50]
        # Включаем ID конкурента в callback для возврата
        callback_data = f"competitor_product_{competitor_id}_{product.get('id')}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
    
    # Навигационные кнопки
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"competitor_products_page_{competitor_id}_{offset - 10}"
        ))
    
    if has_more:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=f"competitor_products_page_{competitor_id}_{offset + 10}"
        ))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    # Кнопка "Семантическое ядро"
    buttons.append([InlineKeyboardButton(
        text="💎 Семантическое ядро",
        callback_data=f"competitor_semantic_core_{competitor_id}"
    )])

    # Кнопка "Удалить конкурента"
    buttons.append([InlineKeyboardButton(
        text="🗑️ Удалить конкурента",
        callback_data=f"delete_competitor_confirm_{competitor_id}"
    )])
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="competitors"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "competitors")
@handle_telegram_errors
async def show_competitors_menu(callback: CallbackQuery):
    """Показать меню конкурентов с пагинацией"""
    user_id = callback.from_user.id
    
    response = await bot_api_client.get_competitors(
        user_id=user_id,
        offset=0,
        limit=10
    )
    
    if response.success and response.data:
        competitors = response.data.get("competitors", [])
        pagination = response.data.get("pagination", {})
        
        keyboard = create_competitors_list_keyboard(
            competitors_data=competitors,
            offset=0,
            limit=10,
            total=pagination.get("total", 0),
            has_more=pagination.get("has_more", False)
        )
        
        text = response.telegram_text or "📊 Конкуренты"
        
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=keyboard,
            user_id=user_id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки конкурентов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard(),
            user_id=user_id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("competitors_page_"))
@handle_telegram_errors
async def show_competitors_page(callback: CallbackQuery):
    """Показать страницу конкурентов"""
    try:
        offset = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        offset = 0
    
    user_id = callback.from_user.id
    
    response = await bot_api_client.get_competitors(
        user_id=user_id,
        offset=offset,
        limit=10
    )
    
    if response.success and response.data:
        competitors = response.data.get("competitors", [])
        pagination = response.data.get("pagination", {})
        
        keyboard = create_competitors_list_keyboard(
            competitors_data=competitors,
            offset=offset,
            limit=10,
            total=pagination.get("total", 0),
            has_more=pagination.get("has_more", False)
        )
        
        text = response.telegram_text or "📊 Конкуренты"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки конкурентов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "add_competitor")
@handle_telegram_errors
async def add_competitor_prompt(callback: CallbackQuery):
    """Показать подсказку для добавления конкурента"""
    text = (
        "➕ ДОБАВЛЕНИЕ КОНКУРЕНТОВ\n\n"
        "Отправьте ссылку на страницу бренда или селлера Wildberries.\n\n"
        "Можно добавить несколько конкурентов сразу (до 10):\n"
        "• Каждую ссылку с новой строки\n"
        "• Максимум 10 ссылок за раз\n\n"
        "Примеры:\n"
        "• https://www.wildberries.ru/brands/310770244-meromi\n"
        "• https://www.wildberries.ru/seller/123456\n\n"
        "Скрапинг запустится автоматически.\n\nРезультаты появятся после завершения."
    )
    
    await safe_edit_message(
        callback=callback,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="competitors")]
        ]),
        user_id=callback.from_user.id
    )
    await callback.answer()


@router.message(F.text.startswith("https://www.wildberries.ru/"))
@handle_telegram_errors
async def handle_competitor_url(message: Message):
    """Обработка ссылки или списка ссылок конкурентов от пользователя"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Разбиваем текст на строки и фильтруем только валидные ссылки
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    urls = [line for line in lines if line.startswith("https://www.wildberries.ru/")]
    
    if not urls:
        await safe_send_message(
            message=message,
            text=(
                "❌ Неверный формат ссылки.\n\n"
                "Отправьте ссылку на страницу бренда или селлера Wildberries:\n"
                "• https://www.wildberries.ru/brands/...\n"
                "• https://www.wildberries.ru/seller/...\n\n"
                "Можно отправить несколько ссылок (до 10), каждую с новой строки."
            ),
            user_id=user_id
        )
        return
    
    # Проверяем лимит (максимум 10 ссылок)
    if len(urls) > 10:
        await safe_send_message(
            message=message,
            text=(
                f"❌ Слишком много ссылок ({len(urls)}).\n\n"
                "Можно добавить максимум 10 конкурентов за раз.\n"
                "Отправьте не более 10 ссылок, каждую с новой строки."
            ),
            user_id=user_id
        )
        return
    
    # Валидируем каждую ссылку
    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        if validate_competitor_url(url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)
    
    if invalid_urls:
        invalid_text = "\n".join(invalid_urls[:5])  # Показываем максимум 5
        if len(invalid_urls) > 5:
            invalid_text += f"\n... и еще {len(invalid_urls) - 5} ссылок"
        
        await safe_send_message(
            message=message,
            text=(
                f"❌ Найдены неверные ссылки ({len(invalid_urls)}):\n\n"
                f"{invalid_text}\n\n"
                "Отправьте ссылки на страницы брендов или селлеров Wildberries:\n"
                "• https://www.wildberries.ru/brands/...\n"
                "• https://www.wildberries.ru/seller/..."
            ),
            user_id=user_id
        )
        return
    
    if not valid_urls:
        await safe_send_message(
            message=message,
            text=(
                "❌ Не найдено валидных ссылок.\n\n"
                "Отправьте ссылки на страницы брендов или селлеров Wildberries:\n"
                "• https://www.wildberries.ru/brands/...\n"
                "• https://www.wildberries.ru/seller/..."
            ),
            user_id=user_id
        )
        return
    
    # Добавляем конкурентов
    success_count = 0
    error_count = 0
    error_messages = []
    
    for url in valid_urls:
        response = await bot_api_client.add_competitor(
            user_id=user_id,
            competitor_url=url
        )
        
        if response.success:
            success_count += 1
        else:
            error_count += 1
            error_msg = format_error_message(response.error, response.status_code)
            error_messages.append(f"• {url[:50]}... - {error_msg}")
    
    # Формируем итоговое сообщение
    if success_count > 0 and error_count == 0:
        # Все успешно
        text = (
            f"✅ Добавлено конкурентов: {success_count}\n\n"
            "Скрапинг запустится автоматически.\n\n"
            "Результаты появятся после завершения."
        )
    elif success_count > 0 and error_count > 0:
        # Частичный успех
        text = (
            f"✅ Добавлено: {success_count}\n"
            f"❌ Ошибок: {error_count}\n\n"
        )
        if error_messages:
            text += "Ошибки:\n" + "\n".join(error_messages[:5])
            if len(error_messages) > 5:
                text += f"\n... и еще {len(error_messages) - 5} ошибок"
    else:
        # Все ошибки
        text = (
            f"❌ Не удалось добавить конкурентов ({error_count})\n\n"
        )
        if error_messages:
            text += "Ошибки:\n" + "\n".join(error_messages[:5])
            if len(error_messages) > 5:
                text += f"\n... и еще {len(error_messages) - 5} ошибок"
    
    await safe_send_message(
        message=message,
        text=text,
        user_id=user_id
    )


@router.callback_query(F.data.startswith("select_competitor_"))
@handle_telegram_errors
async def select_competitor(callback: CallbackQuery):
    """Показать меню для выбранного конкурента"""
    try:
        competitor_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный ID конкурента", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    response = await bot_api_client.get_competitor_products(
        competitor_id=competitor_id,
        user_id=user_id,
        offset=0,
        limit=10
    )
    
    if response.success and response.data:
        products = response.data.get("products", [])
        pagination = response.data.get("pagination", {})
        
        keyboard = create_competitor_products_keyboard(
            products=products,
            competitor_id=competitor_id,
            offset=0,
            has_more=pagination.get("has_more", False)
        )
        
        text = response.telegram_text or "🛍️ Товары конкурента"
        
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=keyboard,
            user_id=user_id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки товаров:\n\n{error_message}",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("competitor_product_"))
@handle_telegram_errors
async def show_competitor_product_detail(callback: CallbackQuery):
    """Показать детальную информацию о товаре конкурента"""
    try:
        parts = callback.data.split("_")
        competitor_id = int(parts[2])
        product_id = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный ID товара", show_alert=True)
        return

    user_id = callback.from_user.id

    # Получаем детали товара
    response = await bot_api_client.get_competitor_product_detail(
        product_id=product_id,
        user_id=user_id
    )

    if response.success and response.data and response.data.get("product"):
        text = response.data.get("telegram_text") or "📦 Детали товара"
        
        # Клавиатура с кнопкой "Назад" к списку товаров конкурента
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к товарам", callback_data=f"select_competitor_{competitor_id}")]
        ])
        
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=keyboard,
            user_id=user_id,
            parse_mode="Markdown",
            disable_web_page_preview=False # Включаем превью для ссылки на товар
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        # Клавиатура для возврата к списку товаров
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к товарам", callback_data=f"select_competitor_{competitor_id}")]
        ])
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки товара:\n\n{error_message}",
            reply_markup=keyboard,
            user_id=user_id
        )

    await callback.answer()





@router.callback_query(F.data.startswith("competitor_products_page_"))
@handle_telegram_errors
async def show_competitor_products_page(callback: CallbackQuery):
    """Показать страницу товаров конкурента"""
    try:
        parts = callback.data.split("_")
        competitor_id = int(parts[3])
        offset = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверные параметры", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    response = await bot_api_client.get_competitor_products(
        competitor_id=competitor_id,
        user_id=user_id,
        offset=offset,
        limit=10
    )
    
    if response.success and response.data:
        products = response.data.get("products", [])
        pagination = response.data.get("pagination", {})
        
        keyboard = create_competitor_products_keyboard(
            products=products,
            competitor_id=competitor_id,
            offset=offset,
            has_more=pagination.get("has_more", False)
        )
        
        text = response.telegram_text or "🛍️ Товары конкурента"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(F.data.startswith("competitor_semantic_core_"))
@handle_telegram_errors
async def show_semantic_core_categories(callback: CallbackQuery):
    """Показать категории для выбора семантического ядра"""
    try:
        competitor_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный ID конкурента", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    response = await bot_api_client.get_competitor_categories(
        competitor_id=competitor_id,
        user_id=user_id
    )
    
    if response.success and response.data and response.data.get("categories"):
        categories = response.data.get("categories")
        
        keyboard = create_semantic_core_categories_keyboard(competitor_id, categories)
        
        text = "🗂️ Выберите категорию для анализа семантического ядра:"
        
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=keyboard,
            user_id=user_id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки категорий:\n\n{error_message}",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_competitor_confirm_"))
@handle_telegram_errors
async def delete_competitor_confirm(callback: CallbackQuery):
    """Показать подтверждение удаления конкурента"""
    try:
        competitor_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный ID конкурента", show_alert=True)
        return

    text = "❓ Вы уверены, что хотите удалить этого конкурента и все его товары?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_competitor_do_{competitor_id}"),
            InlineKeyboardButton(text="🚫 Отмена", callback_data=f"select_competitor_{competitor_id}") # Changed callback
        ]
    ])
    
    await safe_edit_message(
        callback=callback,
        text=text,
        reply_markup=keyboard,
        user_id=callback.from_user.id
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_semantic_core_category:"))
@handle_telegram_errors
async def start_semantic_core_generation(callback: CallbackQuery):
    """Запустить генерацию семантического ядра для выбранной категории"""
    try:
        parts = callback.data.split(":")
        competitor_id = int(parts[1])
        category_index = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверные параметры категории", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    # Получаем категории еще раз, чтобы получить имя по индексу
    response = await bot_api_client.get_competitor_categories(
        competitor_id=competitor_id,
        user_id=user_id
    )
    
    if not response.success or not response.data or not response.data.get("categories"):
        await safe_edit_message(
            callback=callback,
            text="❌ Ошибка: не удалось получить категории для запуска анализа.",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
        await callback.answer()
        return
        
    categories = response.data.get("categories")
    
    try:
        category_name = categories[category_index]
    except IndexError:
        await callback.answer("❌ Ошибка: неверный индекс категории", show_alert=True)
        return

    await callback.answer("💎 Запускаю анализ семантического ядра...", show_alert=False)
    
    response = await bot_api_client.generate_semantic_core(
        competitor_id=competitor_id,
        category_name=category_name,
        user_id=user_id
    )
    
    if response.success and response.data.get("status") == "accepted":
        text = (
            f"✅ Генерация семантического ядра для категории '{category_name}' запущена.\n\n"
            "Это может занять несколько минут. Я пришлю результат, как только он будет готов."
        )
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    elif response.success and response.data.get("status") == "already_exists":
        semantic_core = response.data.get("semantic_core")
        text = (
            f"💎 **Семантическое ядро для категории '{semantic_core.get('category_name')}'**\n\n"
            f"Конкурент: {semantic_core.get('competitor_name')}\n"
            f"Дата создания: {semantic_core.get('created_at')}\n\n"
            f"{semantic_core.get('core_data')}"
        )
        keyboard = create_existing_semantic_core_keyboard(competitor_id, category_index)
        
        # Разбиваем сообщение на части, если оно слишком длинное
        message_parts = split_telegram_message(text)
        
        # Удаляем исходное сообщение с кнопками
        await callback.message.delete()

        for i, part in enumerate(message_parts):
            if i == len(message_parts) - 1:
                # Последняя часть с клавиатурой
                await callback.message.answer(
                    text=part,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer(
                    text=part,
                    parse_mode="Markdown"
                )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка запуска генерации семантического ядра:\n\n{error_message}",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("regenerate_semantic_core:"))
@handle_telegram_errors
async def regenerate_semantic_core(callback: CallbackQuery):
    """Перезапустить генерацию семантического ядра для выбранной категории"""
    try:
        parts = callback.data.split(":")
        competitor_id = int(parts[1])
        category_index = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверные параметры для перезапуска", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    # Получаем категории еще раз, чтобы получить имя по индексу
    response = await bot_api_client.get_competitor_categories(
        competitor_id=competitor_id,
        user_id=user_id
    )
    
    if not response.success or not response.data or not response.data.get("categories"):
        await safe_edit_message(
            callback=callback,
            text="❌ Ошибка: не удалось получить категории для перезапуска анализа.",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
        await callback.answer()
        return
        
    categories = response.data.get("categories")
    
    try:
        category_name = categories[category_index]
    except IndexError:
        await callback.answer("❌ Ошибка: неверный индекс категории", show_alert=True)
        return

    await callback.answer("💎 Перезапускаю анализ семантического ядра...", show_alert=False)
    
    response = await bot_api_client.generate_semantic_core(
        competitor_id=competitor_id,
        category_name=category_name,
        user_id=user_id,
        force=True  # Принудительный перезапуск
    )
    
    if response.success and response.data.get("status") == "accepted":
        text = (
            f"✅ Перезапуск генерации семантического ядра для категории '{category_name}' выполнен.\n\n"
            "Это может занять несколько минут. Я пришлю результат, как только он будет готов."
        )
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка перезапуска генерации семантического ядра:\n\n{error_message}",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("delete_competitor_do_"))
@handle_telegram_errors
async def delete_competitor_do(callback: CallbackQuery):
    """Выполнить удаление конкурента"""
    try:
        competitor_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверный ID конкурента", show_alert=True)
        return

    user_id = callback.from_user.id
    
    # Показываем уведомление об удалении
    await callback.answer("🗑️ Удаление конкурента...", show_alert=False)

    # Вызываем API для удаления
    response = await bot_api_client.delete_competitor(
        competitor_id=competitor_id,
        user_id=user_id
    )

    if response.success:
        # Показываем обновленный список конкурентов
        await callback.message.answer("✅ Конкурент успешно удален.")
        # Вызываем хендлер для отображения основного меню конкурентов
        await show_competitors_menu(callback)
    else:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка удаления:\n\n{error_message}",
            reply_markup=create_competitors_list_keyboard([], 0, 10, 0, False), # Пустая клавиатура
            user_id=user_id
        )
        await callback.answer()
