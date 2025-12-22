"""
Content Handler - генерация контента для карточек товаров.

Кнопки в разделе "🎨 Контент":
- ✍️ Текст карточек (generate_text)
- 🖼 Изображения (generate_images)
"""

import logging
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

from core.config import config
from keyboards.keyboards import content_keyboard
from utils.formatters import (
    safe_edit_message,
    handle_telegram_errors,
)

logger = logging.getLogger(__name__)

router = Router()

# URL GPT Service
GPT_SERVICE_URL = getattr(config, "gpt_service_url", None) or os.getenv("GPT_SERVICE_URL", "http://gpt:9000")


# ============================================================================
# Callback generate_text - генерация текста карточек
# ============================================================================

@router.callback_query(F.data == "generate_text")
@handle_telegram_errors
async def callback_generate_text(callback: CallbackQuery):
    """Обработчик кнопки '✍️ Текст карточек'."""
    telegram_id = callback.from_user.id
    
    logger.info(f"✍️ User {telegram_id} clicked 'generate_text' button")
    
    text = (
        "✍️ <b>Генерация текста карточек</b>\n\n"
        "Я помогу вам создать продающие тексты для карточек товаров:\n"
        "• Названия товаров\n"
        "• Описания и характеристики\n"
        "• Буллеты (ключевые особенности)\n\n"
        "📝 <b>Отправьте мне:</b>\n"
        "1. Название товара\n"
        "2. Основные характеристики\n"
        "3. Целевая аудитория (опционально)\n\n"
        "Или просто опишите товар, и я создам для него текст карточки!"
    )
    
    await safe_edit_message(
        callback=callback,
        text=text,
        reply_markup=content_keyboard(),
        user_id=telegram_id
    )
    await callback.answer()


# ============================================================================
# Callback generate_images - генерация изображений
# ============================================================================

@router.callback_query(F.data == "generate_images")
@handle_telegram_errors
async def callback_generate_images(callback: CallbackQuery):
    """Обработчик кнопки '🖼 Изображения'."""
    telegram_id = callback.from_user.id
    
    logger.info(f"🖼 User {telegram_id} clicked 'generate_images' button")
    
    text = (
        "🖼 <b>Генерация изображений</b>\n\n"
        "Я могу создать для вас изображения для карточек товаров:\n"
        "• Lifestyle-съёмка (товар на модели в обстановке)\n"
        "• Инфографика без текста\n"
        "• Обработка существующих фото\n\n"
        "📸 <b>Отправьте мне:</b>\n"
        "1. Фото товара (или несколько)\n"
        "2. Описание желаемого результата\n\n"
        "Или используйте кнопку <b>📸 Обработка фото</b> в разделе AI-помощник для более продвинутой обработки."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Обработка фото", callback_data="start_photo_processing")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="content")]
    ])
    
    await safe_edit_message(
        callback=callback,
        text=text,
        reply_markup=keyboard,
        user_id=telegram_id
    )
    await callback.answer()


