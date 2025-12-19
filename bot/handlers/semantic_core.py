"""
Обработчики для работы с агрегированным семантическим ядром в разделе AI-помощника.

Вход через кнопку:
- 💎 Семантическое ядро (callback_data="semantic_core_menu")
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.client import bot_api_client
from utils.formatters import (
    handle_telegram_errors,
    format_error_message,
    safe_edit_message,
    split_telegram_message,
)

router = Router()


@router.callback_query(F.data == "semantic_core_menu")
@handle_telegram_errors
async def show_semantic_core_categories(callback: CallbackQuery):
    """
    Показать список категорий для агрегированного семантического ядра
    (по всем конкурентам кабинета).
    """
    user_id = callback.from_user.id

    response = await bot_api_client.get_semantic_core_categories(user_id=user_id)

    if not response.success:
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=(
                "❌ Ошибка загрузки категорий для семантического ядра:\n\n"
                f"{error_message}"
            ),
            reply_markup=None,
            user_id=user_id,
        )
        await callback.answer()
        return

    categories = (response.data or {}).get("categories") if response.data else None

    if not categories:
        await safe_edit_message(
            callback=callback,
            text=(
                "⚠️ Не найдено категорий товаров по вашим конкурентам.\n\n"
                "Убедитесь, что добавлены конкуренты и по ним есть товары с заполненными категориями."
            ),
            reply_markup=None,
            user_id=user_id,
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for idx, category in enumerate(categories):
        builder.button(
            text=category,
            callback_data=f"semantic_core_category:{idx}",
        )

    # Кнопка "Назад" в AI-помощник
    builder.button(text="🔙 Назад", callback_data="ai_assistant")
    builder.adjust(1)

    await safe_edit_message(
        callback=callback,
        text="🗂️ Выберите категорию для анализа семантического ядра (по всем конкурентам):",
        reply_markup=builder.as_markup(),
        user_id=user_id,
    )

    await callback.answer()


@router.callback_query(F.data.startswith("semantic_core_category:"))
@handle_telegram_errors
async def start_cabinet_semantic_core_generation(callback: CallbackQuery):
    """
    Запустить генерацию агрегированного семантического ядра
    для выбранной категории по всем конкурентам кабинета.
    """
    user_id = callback.from_user.id

    try:
        _, index_str = callback.data.split(":", maxsplit=1)
        category_index = int(index_str)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка: неверные параметры категории", show_alert=True)
        return

    # Повторно запрашиваем категории, чтобы получить имя по индексу
    response = await bot_api_client.get_semantic_core_categories(user_id=user_id)

    if not response.success or not response.data or not response.data.get("categories"):
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=(
                "❌ Ошибка: не удалось получить категории для запуска анализа.\n\n"
                f"{error_message}"
            ),
            reply_markup=None,
            user_id=user_id,
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

    generate_response = await bot_api_client.generate_cabinet_semantic_core(
        category_name=category_name,
        user_id=user_id,
    )

    if generate_response.success and generate_response.data.get("status") == "accepted":
        text = (
            f"✅ Генерация семантического ядра по всем конкурентам для категории "
            f"'{category_name}' запущена.\n\n"
            "Это может занять несколько минут. Я пришлю результат, как только он будет готов."
        )
        await safe_edit_message(
            callback=callback,
            text=text,
            reply_markup=None,
            user_id=user_id,
        )
    elif generate_response.success and generate_response.data.get("status") == "already_exists":
        semantic_core = generate_response.data.get("semantic_core") or {}
        header = (
            f"💎 Семантическое ядро по всем конкурентам для категории "
            f"'{semantic_core.get('category_name')}' уже было сгенерировано.\n\n"
        )
        core_text = semantic_core.get("core_data") or "Данные семантического ядра отсутствуют."

        full_text = header + core_text
        parts = split_telegram_message(full_text)

        # Удаляем исходное сообщение с кнопками
        await callback.message.delete()

        for part in parts:
            await callback.message.answer(part, parse_mode="Markdown")
    else:
        error_message = format_error_message(generate_response.error, generate_response.status_code)
        await safe_edit_message(
            callback=callback,
            text=(
                "❌ Ошибка запуска генерации семантического ядра:\n\n"
                f"{error_message}"
            ),
            reply_markup=None,
            user_id=user_id,
        )

    await callback.answer()


