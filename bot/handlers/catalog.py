"""
Обработчики каталога товаров
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from typing import Optional, List
import logging

from keyboards.catalog import (
    get_categories_keyboard,
    get_product_keyboard,
    get_back_to_product_keyboard
)
from api.client import bot_api_client

logger = logging.getLogger(__name__)

router = Router()


def get_valid_photo_url(product: dict) -> Optional[str]:
    """
    Получить валидный URL фото товара с fallback логикой.

    Приоритет:
    1. collage_url
    2. photo_1_url
    3. photo_2_url
    4. photo_3_url
    5. photo_4_url
    6. photo_5_url
    7. photo_6_url

    Returns:
        Валидный URL или None, если все URL пустые
    """
    urls_to_try = [
        product.get('collage_url'),
        product.get('photo_1_url'),
        product.get('photo_2_url'),
        product.get('photo_3_url'),
        product.get('photo_4_url'),
        product.get('photo_5_url'),
        product.get('photo_6_url'),
    ]

    for url in urls_to_try:
        # Проверяем что URL не пустой и не пустая строка
        if url and isinstance(url, str) and url.strip() and url != "":
            return url

    return None


def get_all_valid_photo_urls(product: dict) -> List[str]:
    """
    Получить все валидные URL фотографий товара.

    Returns:
        Список валидных URL
    """
    urls = [
        product.get('photo_1_url'),
        product.get('photo_2_url'),
        product.get('photo_3_url'),
        product.get('photo_4_url'),
        product.get('photo_5_url'),
        product.get('photo_6_url'),
    ]

    return [url for url in urls if url and isinstance(url, str) and url.strip() and url != ""]


async def get_product_photo(product: dict, prefer_collage: bool = True) -> Optional[URLInputFile]:
    """
    Получить фото товара для отправки в Telegram.
    Упрощенная версия без локального кеширования.

    Args:
        product: Словарь с данными товара
        prefer_collage: Предпочитать коллаж (True) или первое фото (False)

    Returns:
        URLInputFile или None
    """
    photo_url = get_valid_photo_url(product)
    if not photo_url:
        logger.warning(f"No valid photo URL for product {product.get('product_id')}")
        return None

    try:
        return URLInputFile(photo_url)
    except Exception as e:
        logger.error(f"Error creating URLInputFile: {e}")
        return None


async def format_product_message(product: dict, user_id: int, current_index: int, total_count: int):
    """Форматировать сообщение карточки товара"""
    measurements = await bot_api_client.get_measurements(user_id)
    size_recommendation = ""

    if measurements:
        recommendation = await bot_api_client.recommend_size(user_id, product['product_id'])
        if recommendation and recommendation.get('success') and recommendation.get('recommended_size'):
            size_recommendation = f"\n\n✅ Рекомендуемый размер: {recommendation['recommended_size']}"
            # Optionally, add alternative size if available
            if recommendation.get('alternative_size'):
                size_recommendation += f" (возможно, подойдет {recommendation['alternative_size']})"
        elif recommendation:
            # Use the message from the recommendation service if it fails
            size_recommendation = f"\n\n⚠️ {recommendation.get('message', 'Не удалось подобрать размер')}"
        else:
            # Fallback if API call fails
            size_recommendation = "\n\n⚠️ Не удалось получить рекомендацию по размеру"
    else:
        size_recommendation = "\n\n📐 Укажи свои параметры, чтобы получить рекомендацию по размеру"

    # Ограничиваем описание (Telegram caption max 1024 символов)
    description = product.get('description', '')
    max_description_length = 600
    if len(description) > max_description_length:
        description = description[:max_description_length].rsplit(' ', 1)[0] + '...'

    message_text = f"""🧥 {product.get('name', 'Без названия')}

{description}

Размеры: {product.get('available_sizes', 'Нет данных')}{size_recommendation}

Товар {current_index + 1} из {total_count}"""

    return message_text


@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    """Показать каталог товаров"""
    categories = await bot_api_client.get_categories()

    if not categories:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет доступных категорий товаров.\n\nПопробуйте зайти позже!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return

    keyboard = get_categories_keyboard(categories)
    await callback.message.edit_text(
        "🛍 Каталог\n\nВыбери категорию:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "catalog_main")
async def show_catalog_main(callback: CallbackQuery):
    """Показать каталог товаров (главное меню)"""
    categories = await bot_api_client.get_categories()

    if not categories:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет доступных категорий товаров.\n\nПопробуйте зайти позже!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return

    keyboard = get_categories_keyboard(categories)
    await callback.message.edit_text(
        "🛍 Каталог\n\nВыбери категорию:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "back:categories")
async def back_to_categories(callback: CallbackQuery):
    """Возврат к списку категорий"""
    categories = await bot_api_client.get_categories()
    keyboard = get_categories_keyboard(categories)
    
    # Удаляем предыдущее сообщение (карточку товара) и отправляем новое
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "🛍 Каталог\n\nВыбери категорию:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category:"))
async def show_category_products(callback: CallbackQuery):
    """Показать товары категории"""
    category_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    products = await bot_api_client.get_products_by_category(category_id)

    if not products:
        await callback.answer("В этой категории пока нет товаров", show_alert=True)
        return

    product = products[0]
    message_text = await format_product_message(product, user_id, 0, len(products))
    
    # Проверяем избранное
    fav_response = await bot_api_client.check_favorite(user_id, product['product_id'])
    is_fav = fav_response.get('is_favorite', False) if fav_response else False

    try:
        await callback.message.delete()
    except:
        pass

    photo = await get_product_photo(product)
    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=message_text,
            reply_markup=get_product_keyboard(
                product, category_id, 0, len(products), is_fav
            ),
        )
    else:
        # Fallback: отправить текстовое сообщение, если нет фото
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_product_keyboard(
                product,
                category_id,
                0,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("nav:"))
async def navigate_products(callback: CallbackQuery):
    """Навигация между товарами"""
    parts = callback.data.split(":")
    category_id = parts[1]
    current_index = int(parts[2])
    action = parts[3]
    user_id = callback.from_user.id

    products = await bot_api_client.get_products_by_category(category_id)
    if not products:
        await callback.answer("Товары не найдены", show_alert=True)
        return

    if action == "next":
        new_index = (current_index + 1) % len(products)
    else:  # prev
        new_index = (current_index - 1 + len(products)) % len(products)

    product = products[new_index]
    message_text = await format_product_message(product, user_id, new_index, len(products))
    
    # Проверяем избранное
    fav_response = await bot_api_client.check_favorite(user_id, product['product_id'])
    is_fav = fav_response.get('is_favorite', False) if fav_response else False

    photo = await get_product_photo(product)
    if not photo:
        await callback.answer("Не удалось загрузить фото товара", show_alert=True)
        return

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=message_text
            ),
            reply_markup=get_product_keyboard(
                product,
                category_id,
                new_index,
                len(products),
                is_fav
            )
        )
    except Exception:
        # Fallback if edit_media fails (e.g., message is too old)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=photo,
            caption=message_text,
            reply_markup=get_product_keyboard(
                product,
                category_id,
                new_index,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("photos:"))
async def show_all_photos(callback: CallbackQuery):
    """Показать все фото товара"""
    parts = callback.data.split(":")
    product_id = parts[1]
    category_id = parts[2]
    index = int(parts[3])

    product = await bot_api_client.get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    photo_urls = get_all_valid_photo_urls(product)
    if not photo_urls:
        await callback.answer("Фотографии товара недоступны", show_alert=True)
        return

    media = [InputMediaPhoto(media=URLInputFile(url)) for url in photo_urls]

    await callback.message.answer_media_group(media=media)
    await callback.message.answer(
        "📸 Все фото товара",
        reply_markup=get_back_to_product_keyboard(product_id, category_id, index)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back:product:"))
async def back_to_product(callback: CallbackQuery):
    """Вернуться к карточке товара"""
    parts = callback.data.split(":")
    product_id = parts[2]
    category_id = parts[3]
    index = int(parts[4])
    user_id = callback.from_user.id

    product = await bot_api_client.get_product_by_id(product_id)
    products = await bot_api_client.get_products_by_category(category_id)

    if not product or not products:
        await callback.answer("Товар или категория не найдены.", show_alert=True)
        return

    message_text = await format_product_message(product, user_id, index, len(products))
    
    # Проверяем избранное
    fav_response = await bot_api_client.check_favorite(user_id, product_id)
    is_fav = fav_response.get('is_favorite', False) if fav_response else False

    await callback.message.delete()

    photo = await get_product_photo(product)
    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=message_text,
            reply_markup=get_product_keyboard(
                product, category_id, index, len(products), is_fav
            ),
        )
    else:
        # Fallback: отправить текстовое сообщение, если нет фото
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_product_keyboard(
                product,
                category_id,
                index,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("tryon:"))
async def start_tryon_from_catalog(callback: CallbackQuery, state: FSMContext):
    """Запуск примерки из каталога"""
    from keyboards.fitter_keyboards import get_fitter_mode_keyboard
    from states.fitter_states import FitterStates

    parts = callback.data.split(":")
    product_id = parts[1]
    category_id = parts[2]
    index = int(parts[3])

    # Получаем информацию о товаре
    product = await bot_api_client.get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Сохраняем контекст в state
    await state.update_data(
        product_id=product_id,
        category_id=category_id,
        index=index,
        source='catalog',
        product=product
    )

    text = f"""👗 <b>Примерка: {product.get('name', 'Товар')}</b>

Выбери режим примерки:

👕 <b>Только этот товар</b>
Примерь только выбранную вещь

👗 <b>Весь образ с фото</b>
Примерь вещь вместе с другой одеждой из фото"""

    # Удаляем сообщение с фото и отправляем новое текстовое
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        text,
        reply_markup=get_fitter_mode_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(FitterStates.choosing_mode)
    await callback.answer()


@router.callback_query(F.data == "close_tryon")
async def close_tryon_message(callback: CallbackQuery):
    """Закрыть сообщение о примерке"""
    await callback.message.delete()
    await callback.answer()