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
        photo_file_id=None,
        prompt=None,
        model=None
    )
    
    await state.set_state(PhotoProcessingStates.waiting_for_photo)
    
    welcome_text = (
        "📸 <b>Обработка фотографии</b>\n\n"
        "Я помогу вам обработать фотографию по вашему описанию!\n\n"
        "📷 <b>Шаг 1:</b> Пришлите фото, которое нужно обработать"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=create_photo_processing_keyboard()
    )
    await callback.answer()


# ============================================================================
# Обработка фото
# ============================================================================

@router.message(StateFilter(PhotoProcessingStates.waiting_for_photo), F.photo)
@handle_telegram_errors
async def process_photo(message: Message, state: FSMContext):
    """Обработка фото от пользователя."""
    telegram_id = message.from_user.id
    photo = message.photo[-1]  # Берем фото наилучшего качества
    
    logger.info(f"📸 Photo received from user {telegram_id}, file_id: {photo.file_id}")
    
    # Сохраняем file_id в FSM
    await state.update_data(photo_file_id=photo.file_id)
    
    # Переходим к следующему шагу
    await state.set_state(PhotoProcessingStates.waiting_for_prompt)
    
    await safe_send_message(
        message,
        "✅ <b>Фото получено!</b>\n\n"
        "📝 <b>Шаг 2:</b> Опишите, что нужно сделать с фотографией\n\n"
        "Например:\n"
        "• \"Сделай фон более ярким\"\n"
        "• \"Добавь эффект размытия\"\n"
        "• \"Измени стиль на акварель\"\n"
        "• \"Улучши качество изображения\"",
        user_id=telegram_id,
        parse_mode="HTML",
        reply_markup=create_photo_processing_keyboard()
    )


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
# Обработка промпта
# ============================================================================

@router.message(StateFilter(PhotoProcessingStates.waiting_for_prompt), F.text)
@handle_telegram_errors
async def process_prompt(message: Message, state: FSMContext):
    """Обработка текстового описания (промпта)."""
    telegram_id = message.from_user.id
    prompt_text = message.text.strip()
    
    # Если пришла команда (например, /start) — перезапускаем
    if prompt_text.startswith('/'):
        await restart_flow_on_start(message, state)
        return
    
    # Валидация промпта
    if len(prompt_text) < 3:
        await safe_send_message(
            message,
            "⚠️ Описание слишком короткое. Пожалуйста, опишите подробнее (минимум 3 символа).",
            user_id=telegram_id,
            parse_mode="HTML"
        )
        return
    
    if len(prompt_text) > 1000:
        await safe_send_message(
            message,
            "⚠️ Описание слишком длинное. Пожалуйста, сократите до 1000 символов.",
            user_id=telegram_id,
            parse_mode="HTML"
        )
        return
    
    logger.info(f"📝 Prompt received from user {telegram_id}: {prompt_text[:50]}...")
    
    # Сохраняем промпт в FSM
    await state.update_data(prompt=prompt_text)
    
    # Переходим к выбору модели
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
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, отправьте <b>текстовое описание</b> того, что нужно сделать с фотографией.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


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
    
    # Сохраняем модель в FSM
    await state.update_data(model=model)
    
    # Запускаем обработку фото
    # Используем callback.message, чтобы бот мог редактировать исходное сообщение
    await process_photo_with_api(callback.message, state)
    await callback.answer()


@router.message(StateFilter(PhotoProcessingStates.waiting_for_model))
@handle_telegram_errors
async def process_model_error(message: Message, state: FSMContext):
    """Обработка некорректного ввода (не кнопка)."""
    telegram_id = message.from_user.id
    
    await safe_send_message(
        message,
        "⚠️ Пожалуйста, выберите модель, используя <b>кнопки</b> выше.",
        user_id=telegram_id,
        parse_mode="HTML"
    )


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
    # Передаем обработку стандартному /start потоку
    await register_user(message, state)


# ============================================================================
# Обработка фото через API
# ============================================================================

async def process_photo_with_api(message: Message, state: FSMContext):
    """Отправка данных в GPT сервис для обработки фото."""
    telegram_id = message.from_user.id
    
    # Получаем все данные из FSM
    data = await state.get_data()
    
    photo_file_id = data.get("photo_file_id")
    prompt = data.get("prompt")
    model = data.get("model")
    
    # Проверка обязательных данных
    if not photo_file_id:
        await safe_send_message(
            message,
            "❌ Ошибка: фото не найдено. Начните заново.",
            user_id=telegram_id
        )
        await state.clear()
        return
    
    if not prompt:
        await safe_send_message(
            message,
            "❌ Ошибка: описание не найдено. Начните заново.",
            user_id=telegram_id
        )
        await state.clear()
        return

    if not model:
        await safe_send_message(
            message,
            "❌ Ошибка: модель не выбрана. Начните заново.",
            user_id=telegram_id
        )
        await state.clear()
        return
    
    # Отправляем индикатор обработки, редактируя предыдущее сообщение
    await message.edit_text(
        "⏳ <b>Обрабатываю фотографию...</b>\n\n"
        "Это может занять несколько секунд.",
        parse_mode="HTML",
        reply_markup=None  # Убираем клавиатуру
    )
    
    # Формируем запрос к GPT сервису
    endpoint = f"{GPT_SERVICE_URL.rstrip('/')}/v1/photo/process"
    payload = {
        "telegram_id": telegram_id,
        "photo_file_id": photo_file_id,
        "prompt": prompt,
        "model": model
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": config.api_secret_key
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)  # 5 минут для обработки
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                success = False
                
                if resp.status == 200:
                    result = await resp.json()
                    
                    if result.get("status") == "success":
                        photo_url = result.get("result", {}).get("photo_url", "")
                        processing_time = result.get("result", {}).get("processing_time", 0)
                        
                        if photo_url:
                            # Проверяем формат фото (base64 или URL)
                            if photo_url.startswith("data:image"):
                                # Это base64, конвертируем в байты
                                import base64
                                import io
                                
                                # Извлекаем base64 данные
                                base64_data = photo_url.split(",")[1] if "," in photo_url else photo_url
                                image_bytes = base64.b64decode(base64_data)
                                
                                # Создаем BufferedInputFile для отправки
                                from aiogram.types import BufferedInputFile
                                photo_file = BufferedInputFile(image_bytes, filename="processed_photo.png")
                                
                                # Отправляем обработанное фото
                                await message.answer_photo(
                                    photo=photo_file,
                                    caption=(
                                        "✅ <b>Фото обработано!</b>\n\n"
                                        f"⏱️ Время обработки: {processing_time:.1f} сек\n\n"
                                        "💾 Результат сохранен в вашей галерее."
                                    ),
                                    parse_mode="HTML"
                                )
                            else:
                                # Это URL, отправляем как есть
                                await message.answer_photo(
                                    photo=photo_url,
                                    caption=(
                                        "✅ <b>Фото обработано!</b>\n\n"
                                        f"⏱️ Время обработки: {processing_time:.1f} сек\n\n"
                                        "💾 Результат сохранен в вашей галерее."
                                    ),
                                    parse_mode="HTML"
                                )
                            success = True
                            logger.info(f"✅ Photo processed for user {telegram_id}")
                        else:
                            await safe_send_message(
                                message,
                                "❌ Не удалось получить обработанное изображение.",
                                user_id=telegram_id
                            )
                    else:
                        # Обработка ошибок из API
                        error_message = result.get("message", "Неизвестная ошибка")
                        error_type = result.get("error_type", "")
                        
                        if error_type == "api_error":
                            await safe_send_message(
                                message,
                                f"❌ <b>Ошибка API:</b>\n\n{error_message}",
                                user_id=telegram_id,
                                parse_mode="HTML"
                            )
                        elif error_type == "timeout":
                            await safe_send_message(
                                message,
                                "❌ Превышено время ожидания. Попробуйте еще раз.",
                                user_id=telegram_id
                            )
                        elif error_type == "validation_error":
                            await safe_send_message(
                                message,
                                f"❌ Некорректные данные: {error_message}",
                                user_id=telegram_id
                            )
                        else:
                            await safe_send_message(
                                message,
                                f"❌ {error_message}",
                                user_id=telegram_id
                            )
                        
                        logger.error(f"❌ Photo processing error for user {telegram_id}: {error_message}")
                
                elif resp.status == 400:
                    await safe_send_message(
                        message,
                        "❌ Некорректные данные. Попробуйте другое фото или описание.",
                        user_id=telegram_id
                    )
                    logger.error(f"❌ Bad request for user {telegram_id}")
                
                elif resp.status == 403:
                    await safe_send_message(
                        message,
                        "❌ Ошибка доступа к сервису. Попробуйте позже.",
                        user_id=telegram_id
                    )
                    logger.error(f"❌ Access denied for user {telegram_id}")
                
                elif resp.status in [500, 503]:
                    await safe_send_message(
                        message,
                        "❌ Сервис временно недоступен. Попробуйте позже.",
                        user_id=telegram_id
                    )
                    logger.error(f"❌ Service unavailable (status {resp.status}) for user {telegram_id}")
                
                else:
                    error_body = await resp.text()
                    logger.error(f"❌ GPT Service error {resp.status}: {error_body}")
                    
                    await safe_send_message(
                        message,
                        "❌ Произошла ошибка при обработке фотографии.\n"
                        "Попробуйте позже или обратитесь к администратору.",
                        user_id=telegram_id
                    )
                
                # Очищаем состояние
                await state.clear()
                
                # Возвращаем в меню
                if success:
                    await safe_send_message(
                        message,
                        "📸 <b>Обработка завершена</b>\n\nВыберите действие:",
                        user_id=telegram_id,
                        parse_mode="HTML",
                        reply_markup=ai_assistant_keyboard()
                    )
                else:
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
            "❌ Не удалось связаться с сервисом обработки.\n"
            "Попробуйте позже.",
            user_id=telegram_id
        )
        await state.clear()
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in photo processing: {e}", exc_info=True)
        await safe_send_message(
            message,
            "❌ Произошла непредвиденная ошибка.\n"
            "Попробуйте позже или обратитесь к администратору.",
            user_id=telegram_id
        )
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
