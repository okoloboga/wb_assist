"""
Photo Processing Handler - обработка фотографий через нейронную сеть.

Кнопка:
- 📸 Обработка фото (в меню AI-помощник)
"""

import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
import aiohttp
from typing import List

from core.config import config
from core.states import PhotoProcessingStates
from keyboards.keyboards import ai_assistant_keyboard, create_photo_processing_keyboard, create_photo_model_selection_keyboard
from utils.formatters import (
    safe_send_message,
    handle_telegram_errors,
)
from handlers.registration import register_user

logger = logging.getLogger(__name__)

router = Router()

# URL GPT Service
GPT_SERVICE_URL = getattr(config, "gpt_service_url", None) or os.getenv("GPT_SERVICE_URL", "http://gpt:9000")
MAX_PHOTOS = 3


# ============================================================================
# Callback start_photo_processing - начать обработку фото
# ============================================================================

@router.callback_query(F.data == "start_photo_processing")
@handle_telegram_errors
async def callback_start_photo_processing(callback: CallbackQuery, state: FSMContext):
    """Начать процесс обработки фотографии."""
    telegram_id = callback.from_user.id
    
    logger.info(f"📸 User {telegram_id} started photo processing")
    
    # Инициализируем данные в FSM
    await state.update_data(
        photo_file_ids=[],
        prompt=None,
        model=None
    )
    
    await state.set_state(PhotoProcessingStates.waiting_for_photo)
    
    welcome_text = (
        "📸 <b>Обработка фотографии</b>\n\n"
        "Я помогу вам обработать фотографию по вашему описанию!\n\n"
        f"📷 <b>Шаг 1:</b> Пришлите от 1 до {MAX_PHOTOS} фотографий <b>по одной</b>, которые нужно обработать. "
        "Когда закончите, нажмите 'Готово'."
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=create_photo_processing_keyboard()
    )
    await callback.answer()


# ============================================================================
# Обработка фото (по одному)
# ============================================================================

async def add_photos_to_state(message: Message, state: FSMContext, new_photos: List[str]):
    """Добавляет ID фотографий в состояние FSM."""
    telegram_id = message.from_user.id
    data = await state.get_data()
    photo_ids = data.get("photo_file_ids", [])
    
    added_count = 0
    for photo_id in new_photos:
        if len(photo_ids) < MAX_PHOTOS:
            photo_ids.append(photo_id)
            added_count += 1
        else:
            break
            
    await state.update_data(photo_file_ids=photo_ids)
    
    current_count = len(photo_ids)
    
    if added_count > 0:
        photo_noun = "фотография" if added_count == 1 else "фотографии"
        feedback_text = f"✅ {added_count} {photo_noun} добавлено. Всего загружено: {current_count}/{MAX_PHOTOS}.\n\n"
        if current_count < MAX_PHOTOS:
            feedback_text += "Можете отправить еще или нажмите 'Готово'."
        else:
            feedback_text += "Достигнут лимит. Нажмите 'Готово', чтобы продолжить."
    else:
        feedback_text = f"⚠️ Вы уже загрузили максимальное количество фото ({MAX_PHOTOS}). Нажмите 'Готово'."

    await safe_send_message(
        message,
        feedback_text,
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=create_photo_processing_keyboard(photo_count=current_count)
    )

@router.message(StateFilter(PhotoProcessingStates.waiting_for_photo), F.photo)
@handle_telegram_errors
async def process_photo(message: Message, state: FSMContext):
    """Обработка одиночного фото от пользователя."""
    photo_id = message.photo[-1].file_id
    logger.info(f"📸 Single photo received from user {message.from_user.id}, file_id: {photo_id}")
    await add_photos_to_state(message, state, [photo_id])


@router.message(StateFilter(PhotoProcessingStates.waiting_for_photo))
@handle_telegram_errors
async def process_photo_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода (не фото)."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, отправьте <b>фотографию</b>.",
        user_id=telegram_id,
        parse_mode="HTML"
    )

# ============================================================================
# Завершение загрузки фото
# ============================================================================

@router.callback_query(StateFilter(PhotoProcessingStates.waiting_for_photo), F.data == "finish_photo_upload")
@handle_telegram_errors
async def finish_photo_upload(callback: CallbackQuery, state: FSMContext):
    """Переход к следующему шагу после добавления фото."""
    data = await state.get_data()
    if not data.get("photo_file_ids"):
        await callback.answer("⚠️ Вы не добавили ни одной фотографии.", show_alert=True)
        return

    await state.set_state(PhotoProcessingStates.waiting_for_prompt)
    
    prompt_text = (
        "✅ <b>Фото получены!</b>\n\n"
        "📝 <b>Шаг 2:</b> Теперь опишите, что нужно сделать с фотографиями\n\n"
        "Например:\n"
        "• \"Сделай фон более ярким на всех фото\"\n"
        "• \"Объедини эти фото в коллаж\"\n"
        "• \"Замени фон на первой фотографии на пляж\""
    )
    
    await callback.message.edit_text(
        prompt_text,
        parse_mode="HTML",
        reply_markup=create_photo_processing_keyboard() # Клавиатура с кнопкой "Отмена"
    )
    await callback.answer()


# ============================================================================
# Обработка промпта
# ============================================================================

@router.message(StateFilter(PhotoProcessingStates.waiting_for_prompt), F.text)
@handle_telegram_errors
async def process_prompt(message: Message, state: FSMContext):
    """Обработка текстового описания (промпта)."""
    telegram_id = message.from_user.id
    prompt_text = message.text.strip()
    
    if prompt_text.startswith('/'):
        await restart_flow_on_start(message, state)
        return
    
    if len(prompt_text) < 3:
        await safe_send_message(message, "⚠️ Описание слишком короткое (минимум 3 символа).", user_id=telegram_id)
        return
    
    if len(prompt_text) > 1000:
        await safe_send_message(message, "⚠️ Описание слишком длинное (максимум 1000 символов).", user_id=telegram_id)
        return
    
    logger.info(f"📝 Prompt received from user {telegram_id}: {prompt_text[:50]}...")
    
    await state.update_data(prompt=prompt_text)
    await state.set_state(PhotoProcessingStates.waiting_for_model)
    
    model_selection_text = (
        "✅ <b>Описание принято!</b>\n\n"
        "🤖 <b>Шаг 3:</b> Выберите модель для обработки\n\n"
        "• <b>Nano Banana:</b> дешевле и быстрее\n"
        "• <b>Nano Banana 2:</b> дороже, медленнее, но качественнее"
    )
    
    await safe_send_message(
        message,
        model_selection_text,
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=create_photo_model_selection_keyboard()
    )


@router.message(StateFilter(PhotoProcessingStates.waiting_for_prompt))
@handle_telegram_errors
async def process_prompt_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода в состоянии ожидания промпта (не текст)."""
    await safe_send_message(message, "⚠️ Пожалуйста, отправьте <b>текстовое описание</b>.", user_id=message.from_user.id, parse_mode="HTML")


# ============================================================================
# Обработка выбора модели
# ============================================================================

@router.callback_query(StateFilter(PhotoProcessingStates.waiting_for_model), F.data.startswith("select_model:"))
@handle_telegram_errors
async def process_model_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора модели."""
    telegram_id = callback.from_user.id
    model = callback.data.split(":")[1]
    
    logger.info(f"🤖 Model selected by user {telegram_id}: {model}")
    
    await state.update_data(model=model)
    await process_photo_with_api(callback.message, state)
    await callback.answer()


@router.message(StateFilter(PhotoProcessingStates.waiting_for_model))
@handle_telegram_errors
async def process_model_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода (не кнопка)."""
    await safe_send_message(message, "⚠️ Пожалуйста, выберите модель, используя <b>кнопки</b>.", user_id=message.from_user.id, parse_mode="HTML")


# ============================================================================
# Обработка команды /start во время процесса
# ============================================================================

@router.message(
    StateFilter(
        PhotoProcessingStates.waiting_for_photo,
        PhotoProcessingStates.waiting_for_prompt,
        PhotoProcessingStates.waiting_for_model,
    ),
    CommandStart()
)
@handle_telegram_errors
async def restart_flow_on_start(message: Message, state: FSMContext):
    """Перезапуск диалога обработки фото по команде /start в любом состоянии."""
    await state.clear()
    await register_user(message, state)


# ============================================================================
# Обработка фото через API
# ============================================================================

async def process_photo_with_api(message: Message, state: FSMContext):
    """Отправка данных в GPT сервис для обработки фото."""
    telegram_id = message.from_user.id
    data = await state.get_data()
    
    photo_file_ids = data.get("photo_file_ids")
    prompt = data.get("prompt")
    model = data.get("model")
    
    if not photo_file_ids:
        await safe_send_message(message, "❌ Ошибка: фото не найдены. Начните заново.", user_id=telegram_id)
        await state.clear()
        return
    
    if not prompt:
        await safe_send_message(message, "❌ Ошибка: описание не найдено. Начните заново.", user_id=telegram_id)
        await state.clear()
        return

    if not model:
        await safe_send_message(message, "❌ Ошибка: модель не выбрана. Начните заново.", user_id=telegram_id)
        await state.clear()
        return
    
    await message.edit_text(
        "⏳ <b>Обрабатываю фотографии...</b>\n\nЭто может занять некоторое время.",
        parse_mode="HTML",
        reply_markup=None
    )
    
    endpoint = f"{GPT_SERVICE_URL.rstrip('/')}/v1/photo/process"
    payload = {
        "telegram_id": telegram_id,
        "photo_file_ids": photo_file_ids,
        "prompt": prompt,
        "model": model
    }
    headers = {"Content-Type": "application/json", "X-API-KEY": config.api_secret_key}
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                success = False
                
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("status") == "success":
                        photo_url = result.get("result", {}).get("photo_url", "")
                        processing_time = result.get("result", {}).get("processing_time", 0)
                        
                        if photo_url:
                            if photo_url.startswith("data:image"):
                                import base64
                                from aiogram.types import BufferedInputFile
                                base64_data = photo_url.split(",")[1]
                                image_bytes = base64.b64decode(base64_data)
                                photo_file = BufferedInputFile(image_bytes, filename="processed_photo.png")
                                await message.answer_photo(
                                    photo=photo_file,
                                    caption=f"✅ <b>Фото обработано!</b>\n\n⏱️ Время: {processing_time:.1f} сек",
                                    parse_mode="HTML"
                                )
                            else:
                                await message.answer_photo(
                                    photo=photo_url,
                                    caption=f"✅ <b>Фото обработано!</b>\n\n⏱️ Время: {processing_time:.1f} сек",
                                    parse_mode="HTML"
                                )
                            success = True
                            logger.info(f"✅ Photo processed for user {telegram_id}")
                        else:
                            await safe_send_message(message, "❌ Не удалось получить обработанное изображение.", user_id=telegram_id)
                    else:
                        error_message = result.get("message", "Неизвестная ошибка")
                        logger.error(f"❌ Photo processing error for user {telegram_id}: {error_message}")
                        await safe_send_message(message, f"❌ {error_message}", user_id=telegram_id)
                
                else:
                    error_body = await resp.text()
                    logger.error(f"❌ GPT Service error {resp.status}: {error_body}")
                    await safe_send_message(message, "❌ Ошибка при обработке. Попробуйте позже.", user_id=telegram_id)
                
                await state.clear()
                
                final_message = "📸 <b>Обработка завершена.</b>" if success else "Выберите действие:"
                await safe_send_message(
                    message,
                    final_message,
                    user_id=telegram_id,
                    parse_mode="HTML",
                    reply_markup=ai_assistant_keyboard()
                )
    
    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error calling GPT Service: {e}")
        await safe_send_message(message, "❌ Не удалось связаться с сервисом обработки.", user_id=telegram_id)
        await state.clear()
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in photo processing: {e}", exc_info=True)
        await safe_send_message(message, "❌ Произошла непредвиденная ошибка.", user_id=telegram_id)
        await state.clear()


# ============================================================================
# Callback cancel_photo_processing - отмена обработки
# ============================================================================

@router.callback_query(F.data == "cancel_photo_processing")
@handle_telegram_errors
async def callback_cancel_photo_processing(callback: CallbackQuery, state: FSMContext):
    """Отменить процесс обработки фотографии."""
    telegram_id = callback.from_user.id
    
    logger.info(f"🔚 User {telegram_id} cancelled photo processing")
    
    await state.clear()
    
    await callback.message.edit_text(
        "✅ Обработка фото отменена.\n\nВыберите действие:",
        reply_markup=ai_assistant_keyboard()
    )
    
    await callback.answer()
