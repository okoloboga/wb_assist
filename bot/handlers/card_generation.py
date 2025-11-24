"""
Card Generation Handler - генерация карточек товаров через GPT.

Кнопка:
- 🎨 Генерация карточки (в меню AI-помощник)
"""

import logging
import os
import re
from typing import Optional, Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp

from api.client import bot_api_client
from core.config import config
from core.states import CardGenerationStates
from keyboards.keyboards import ai_assistant_keyboard
from utils.formatters import (
    safe_send_message,
    handle_telegram_errors,
)
from handlers.registration import register_user

logger = logging.getLogger(__name__)

router = Router()

# URL GPT Service
GPT_SERVICE_URL = getattr(config, "gpt_service_url", None) or os.getenv("GPT_SERVICE_URL", "http://gpt:9000")


# ============================================================================
# Вспомогательные функции
# ============================================================================

def create_card_generation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для режима генерации карточки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_card_generation")]
    ])


# ============================================================================
# Callback start_card_generation - начать генерацию карточки
# ============================================================================

@router.callback_query(F.data == "start_card_generation")
@handle_telegram_errors
async def callback_start_card_generation(callback: CallbackQuery, state: FSMContext):
    """Начать процесс генерации карточки товара."""
    telegram_id = callback.from_user.id
    
    logger.info(f"🎨 User {telegram_id} started card generation")
    
    # Инициализируем данные в FSM
    await state.update_data(
        photo_file_id=None,
        characteristics={},
        target_audience=None,
        selling_points=None,
        semantic_core_text=None, # Добавляем поле для ядра
    )
    
    await state.set_state(CardGenerationStates.waiting_for_photo)
    
    welcome_text = (
        "🎨 <b>Генерация карточки товара</b>\n\n"
        "Я помогу вам создать привлекательную карточку товара для Wildberries!\n\n"
        "📸 <b>Шаг 1:</b> Пришлите фото товара"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=create_card_generation_keyboard()
    )
    await callback.answer()


# ============================================================================
# Обработка фото
# ============================================================================

@router.message(StateFilter(CardGenerationStates.waiting_for_photo), F.photo)
@handle_telegram_errors
async def process_card_photo(message: Message, state: FSMContext):
    """Обработка фото товара."""
    telegram_id = message.from_user.id
    photo = message.photo[-1]  # Берем фото наилучшего качества
    
    logger.info(f"📸 Photo received from user {telegram_id}, file_id: {photo.file_id}")
    
    # Сохраняем file_id в FSM и инициализируем характеристики
    await state.update_data(
        photo_file_id=photo.file_id,
        characteristics={},
        characteristics_step="name"  # Текущий шаг: запрашиваем название
    )
    
    # Переходим к следующему шагу
    await state.set_state(CardGenerationStates.waiting_for_characteristics)
    
    await safe_send_message(
        message,
        "✅ <b>Фото получено!</b>\n\n"
        "📋 <b>Шаг 2:</b> Введите ключевые характеристики:\n\n"
        "• <b>Название товара</b>",
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=create_card_generation_keyboard()
    )


@router.message(StateFilter(CardGenerationStates.waiting_for_photo))
@handle_telegram_errors
async def process_card_photo_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода (не фото)."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, отправьте <b>фотографию</b> товара.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


# ============================================================================
# Обработка характеристик
# ============================================================================

@router.message(StateFilter(CardGenerationStates.waiting_for_characteristics), F.text)
@handle_telegram_errors
async def process_characteristics(message: Message, state: FSMContext):
    """Обработка ключевых характеристик - поочередно запрашиваем каждое поле."""
    telegram_id = message.from_user.id
    text = message.text.strip()
    # Если пришла команда (например, /start) — перезапускаем
    if text.startswith('/'):
        await restart_flow_on_start(message, state)
        return
    
    # Получаем текущие данные
    data = await state.get_data()
    characteristics = data.get("characteristics", {})
    current_step = data.get("characteristics_step", "name")  # name, brand, category
    
    # Сохраняем текущее поле
    if current_step == "name":
        characteristics["name"] = text
        await state.update_data(characteristics=characteristics, characteristics_step="brand")
        
        # Запрашиваем следующее поле - бренд
        await safe_send_message(
            message,
            f"✅ <b>Название сохранено:</b> {text}\n\n"
            f"Введите: • <b>Бренд</b>",
            user_id=telegram_id,
            parse_mode="HTML",
            reply_markup=create_card_generation_keyboard()
        )
    
    elif current_step == "brand":
        characteristics["brand"] = text
        await state.update_data(characteristics=characteristics, characteristics_step="category")
        
        # Запрашиваем последнее поле - категорию
        await safe_send_message(
            message,
            f"✅ <b>Бренд сохранен:</b> {text}\n\n"
            f"Введите: • <b>Категория</b>",
            user_id=telegram_id,
            parse_mode="HTML",
            reply_markup=create_card_generation_keyboard()
        )
    
    elif current_step == "category":
        characteristics["category"] = text
        await state.update_data(characteristics=characteristics)
        
        # Все характеристики собраны, переходим к целевой аудитории
        await state.set_state(CardGenerationStates.waiting_for_audience)
        
        await safe_send_message(
            message,
            f"✅ <b>Характеристики сохранены!</b>\n\n"
            f"📝 Название: {characteristics['name']}\n"
            f"🏷️ Бренд: {characteristics['brand']}\n"
            f"📂 Категория: {characteristics['category']}\n\n"
            f"👥 <b>Шаг 3:</b> Опишите целевую аудиторию (кто покупает этот товар):\n\n"
            f"Пример: \"Женщины 25-40 лет, активные, следящие за модой, ценящие качество и комфорт\"",
            user_id=telegram_id,
            parse_mode="HTML",
            reply_markup=create_card_generation_keyboard()
        )


@router.message(StateFilter(CardGenerationStates.waiting_for_characteristics))
@handle_telegram_errors
async def process_characteristics_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода в состоянии ожидания характеристик (не текст)."""
    telegram_id = message.from_user.id
    
    # Получаем текущий шаг
    data = await state.get_data()
    current_step = data.get("characteristics_step", "name")
    
    field_names = {
        "name": "название товара",
        "brand": "бренд",
        "category": "категорию"
    }
    
    field_name = field_names.get(current_step, "данные")
    
    await safe_send_message(
        message,
        f"⚠️ Пожалуйста, отправьте <b>текстовое сообщение</b> с {field_name}.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


@router.message(
    StateFilter(
        CardGenerationStates.waiting_for_photo,
        CardGenerationStates.waiting_for_characteristics,
        CardGenerationStates.waiting_for_audience,
        CardGenerationStates.waiting_for_selling_points,
        CardGenerationStates.waiting_for_semantic_core,
    ),
    CommandStart()
)
@handle_telegram_errors
async def restart_flow_on_start(message: Message, state: FSMContext):
    """Перезапуск диалога генерации карточек по команде /start в любом состоянии."""
    await state.clear()
    # Передаем обработку стандартному /start потоку
    await register_user(message, state)


# ============================================================================
# Обработка целевой аудитории
# ============================================================================

@router.message(StateFilter(CardGenerationStates.waiting_for_audience), F.text)
@handle_telegram_errors
async def process_target_audience(message: Message, state: FSMContext):
    """Обработка описания целевой аудитории."""
    telegram_id = message.from_user.id
    audience_text = message.text
    # Команда во время шага — перезапуск
    if audience_text.strip().startswith('/'):
        await restart_flow_on_start(message, state)
        return
    
    logger.info(f"👥 Target audience received from user {telegram_id}")
    
    await state.update_data(target_audience=audience_text)
    await state.set_state(CardGenerationStates.waiting_for_selling_points)
    
    await safe_send_message(
        message,
        "✅ <b>Целевая аудитория сохранена!</b>\n\n"
        "⭐ <b>Шаг 4:</b> Опишите ключевые преимущества:\n\n"
        "Пример: \"Премиальное качество материалов, уникальный дизайн, долговечность, "
        "экологичность производства\"",
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=create_card_generation_keyboard()
    )


@router.message(StateFilter(CardGenerationStates.waiting_for_audience))
@handle_telegram_errors
async def process_target_audience_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода в состоянии ожидания целевой аудитории (не текст)."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, отправьте <b>текстовое описание</b> целевой аудитории.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


# ============================================================================
# Обработка selling points
# ============================================================================

@router.message(StateFilter(CardGenerationStates.waiting_for_selling_points), F.text)
@handle_telegram_errors
async def process_selling_points(message: Message, state: FSMContext):
    """Обработка selling points и переход к выбору семантического ядра."""
    telegram_id = message.from_user.id
    selling_points_text = message.text
    if selling_points_text.strip().startswith('/'):
        await restart_flow_on_start(message, state)
        return
    
    logger.info(f"⭐ Selling points received from user {telegram_id}")
    
    await state.update_data(selling_points=selling_points_text)
    await state.set_state(CardGenerationStates.waiting_for_semantic_core)
    
    # Запрашиваем семантическое ядро
    await request_semantic_core(message, state)


@router.message(StateFilter(CardGenerationStates.waiting_for_selling_points))
@handle_telegram_errors
async def process_selling_points_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода в состоянии ожидания selling points (не текст)."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, отправьте <b>текстовое описание</b> уникальных преимуществ товара.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


# ============================================================================
# Выбор семантического ядра
# ============================================================================

async def request_semantic_core(message: Message, state: FSMContext):
    """Запрашивает у пользователя выбор семантического ядра."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚙️ Загружаю список доступных семантических ядер...",
        user_id=telegram_id,
        parse_mode="HTML"
    )
    
    response = await bot_api_client.get_semantic_cores(user_id=telegram_id)
    
    if not response.success or not response.data:
        logger.warning(f"No semantic cores found for user {telegram_id}. Skipping step.")
        await safe_send_message(
            message,
            "⚠️ Не найдено ни одного готового семантического ядра. Пропускаю этот шаг.",
            user_id=telegram_id,
            parse_mode="HTML"
        )
        await generate_card_with_gpt(message, state)
        return

    cores = response.data
    builder = InlineKeyboardBuilder()
    for core in cores:
        button_text = f"'{core['competitor_name']}' - {core['category_name']}"
        builder.button(text=button_text, callback_data=f"select_core_{core['id']}")
    
    builder.button(text="➡️ Пропустить", callback_data="select_core_skip")
    builder.adjust(1)

    await safe_send_message(
        message,
        "💎 <b>Шаг 5:</b> Выберите семантическое ядро для обогащения описания или пропустите этот шаг.",
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("select_core_"))
@handle_telegram_errors
async def process_semantic_core_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора семантического ядра."""
    telegram_id = callback.from_user.id
    selection = callback.data.split("_")[-1]

    if selection == "skip":
        logger.info(f"User {telegram_id} skipped semantic core selection.")
        await state.update_data(semantic_core_text=None)
        await callback.message.edit_text("✅ Шаг пропущен.")
    else:
        core_id = int(selection)
        logger.info(f"User {telegram_id} selected semantic core {core_id}.")
        
        await callback.message.edit_text("⚙️ Загружаю данные ядра...")
        
        response = await bot_api_client.get_semantic_core_detail(core_id=core_id, user_id=telegram_id)
        
        if response.success and response.data:
            core_data = response.data.get("core_data")
            await state.update_data(semantic_core_text=core_data)
            await callback.message.edit_text("✅ Семантическое ядро добавлено!")
        else:
            logger.error(f"Failed to fetch semantic core {core_id} for user {telegram_id}.")
            await state.update_data(semantic_core_text=None)
            await callback.message.edit_text("❌ Не удалось загрузить ядро. Шаг будет пропущен.")

    # Запускаем генерацию
    await generate_card_with_gpt(callback.message, state)
    await callback.answer()


# ============================================================================
# Генерация карточки через GPT
# ============================================================================

async def generate_card_with_gpt(message: Message, state: FSMContext):
    """Отправка данных в GPT сервис для генерации карточки."""
    telegram_id = message.from_user.id
    
    # Получаем все данные из FSM
    data = await state.get_data()
    
    photo_file_id = data.get("photo_file_id")
    characteristics = data.get("characteristics", {})
    target_audience = data.get("target_audience")
    selling_points = data.get("selling_points")
    semantic_core_text = data.get("semantic_core_text") # Получаем ядро
    
    # Проверка обязательных данных
    if not photo_file_id:
        await safe_send_message(
            message,
            "❌ Ошибка: фото не найдено. Начните заново.",
            user_id=telegram_id
        )
        await state.clear()
        return
    
    if not all([characteristics.get("name"), characteristics.get("brand"), characteristics.get("category")]):
        await safe_send_message(
            message,
            "❌ Ошибка: не все характеристики заполнены. Начните заново.",
            user_id=telegram_id
        )
        await state.clear()
        return
    
    # Отправляем индикатор обработки
    await safe_send_message(
        message,
        "⏳ <b>Генерирую карточку товара...</b>\n\n"
        "Это может занять несколько секунд.",
        user_id=telegram_id,
        parse_mode="HTML"
    )
    
    # Формируем запрос к GPT сервису
    endpoint = f"{GPT_SERVICE_URL.rstrip('/')}/v1/card/generate"
    payload = {
        "telegram_id": telegram_id,
        "photo_file_id": photo_file_id,
        "characteristics": characteristics,
        "target_audience": target_audience,
        "selling_points": selling_points,
        "semantic_core_text": semantic_core_text, # Добавляем ядро в payload
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": config.api_secret_key
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=120)  # 2 минуты для генерации
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                success = False
                
                if resp.status == 200:
                    result = await resp.json()
                    card_text = result.get("card", "")
                    
                    # Проверяем, не вернулась ли ошибка в теле успешного ответа
                    if card_text.startswith("ERROR:"):
                        error_msg = card_text.replace("ERROR:", "").strip()
                        if "not available in your region" in error_msg.lower() or "unsupported_country" in error_msg.lower():
                            await safe_send_message(
                                message,
                                "❌ <b>OpenAI API недоступен в вашем регионе</b>\n\n"
                                "🔧 <b>Решение:</b>\n"
                                "Обратитесь к администратору для настройки альтернативного API endpoint.\n\n"
                                "Это может быть прокси-сервер или OpenAI-совместимый провайдер.",
                                user_id=telegram_id,
                                parse_mode="HTML"
                            )
                        else:
                            await safe_send_message(
                                message,
                                f"❌ <b>Ошибка генерации:</b>\n\n{error_msg}",
                                user_id=telegram_id,
                                parse_mode="HTML"
                            )
                    else:
                        await safe_send_message(
                            message,
                            f"✅ <b>Карточка товара сгенерирована!</b>\n\n{card_text}",
                            user_id=telegram_id,
                            parse_mode="HTML"
                        )
                        success = True
                    
                    logger.info(f"✅ Card generated for user {telegram_id}")
                elif resp.status == 403:
                    # Ошибка доступа (региональное ограничение)
                    try:
                        error_data = await resp.json()
                        error_detail = error_data.get("detail", "Ошибка доступа к API")
                    except:
                        error_detail = "OpenAI API недоступен в вашем регионе"
                    
                    await safe_send_message(
                        message,
                        f"❌ <b>{error_detail}</b>",
                        user_id=telegram_id,
                        parse_mode="HTML"
                    )
                    logger.error(f"❌ GPT Service regional restriction error for user {telegram_id}")
                else:
                    error_body = await resp.text()
                    logger.error(f"❌ GPT Service error {resp.status}: {error_body}")
                    
                    await safe_send_message(
                        message,
                        "❌ Произошла ошибка при генерации карточки.\n"
                        "Попробуйте позже или обратитесь к администратору.",
                        user_id=telegram_id
                    )
                
                # Очищаем состояние
                await state.clear()
                
                # Возвращаем в меню только при успехе
                if success:
                    await safe_send_message(
                        message,
                        "🎨 <b>Генерация завершена</b>\n\nВыберите действие:",
                        user_id=telegram_id,
                        parse_mode="HTML",
                        reply_markup=ai_assistant_keyboard()
                    )
                else:
                    # При ошибке просто возвращаем в меню без дополнительного сообщения
                    await safe_send_message(
                        message,
                        "Выберите действие:",
                        user_id=telegram_id,
                        parse_mode="HTML",
                        reply_markup=ai_assistant_keyboard()
                    )
    
    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error calling GPT Service: {e}")
        await safe_send_message(
            message,
            "❌ Не удалось связаться с сервисом генерации.\n"
            "Попробуйте позже.",
            user_id=telegram_id
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in card generation: {e}", exc_info=True)
        await safe_send_message(
            message,
            "❌ Произошла непредвиденная ошибка.\n"
            "Попробуйте позже или обратитесь к администратору.",
            user_id=telegram_id
        )
        await state.clear()


# ============================================================================
# Callback cancel_card_generation - отмена генерации
# ============================================================================

@router.callback_query(F.data == "cancel_card_generation")
@handle_telegram_errors
async def callback_cancel_card_generation(callback: CallbackQuery, state: FSMContext):
    """Отменить процесс генерации карточки."""
    telegram_id = callback.from_user.id
    
    logger.info(f"🔚 User {telegram_id} cancelled card generation")
    
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Генерация карточки отменена."
    )
    
    await safe_send_message(
        callback.message,
        "Вы можете начать генерацию снова в любое время из меню '🤖 AI-помощник'.",
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=ai_assistant_keyboard()
    )
    
    await callback.answer()

