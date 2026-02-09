"""
Обработчики AI-примерки одежды (Fitter)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError
import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from PIL import Image
import io
import base64

from keyboards.keyboards import main_keyboard
from states.fitter_states import FitterStates
from api.client import bot_api_client
from gpt_integration.fitter import validate_photo, generate_tryon

router = Router()
logger = logging.getLogger(__name__)


async def safe_edit_message(message_or_callback, text: str, max_retries: int = 3):
    """
    Безопасное редактирование сообщения с обработкой сетевых ошибок.
    
    Args:
        message_or_callback: Message или CallbackQuery объект
        text: Текст для отправки
        max_retries: Максимальное количество попыток
    """
    if hasattr(message_or_callback, 'edit_text'):
        msg = message_or_callback
    elif hasattr(message_or_callback, 'message'):
        msg = message_or_callback.message
    else:
        logger.warning("Cannot determine message object for safe_edit_message")
        return
    
    for attempt in range(max_retries):
        try:
            await msg.edit_text(text)
            return
        except (TelegramNetworkError, TelegramAPIError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error editing message (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(1)  # Небольшая задержка перед повтором
            else:
                logger.error(f"Failed to edit message after {max_retries} attempts: {e}")
                # Пробуем отправить новое сообщение вместо редактирования
                try:
                    if hasattr(msg, 'answer'):
                        await msg.answer(text)
                    elif hasattr(message_or_callback, 'message') and hasattr(message_or_callback.message, 'answer'):
                        await message_or_callback.message.answer(text)
                except Exception as e2:
                    logger.error(f"Failed to send new message as fallback: {e2}")
        except Exception as e:
            logger.error(f"Unexpected error editing message: {e}", exc_info=True)
            break

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "storage"))
USER_PHOTOS_PATH = STORAGE_PATH / "user_photos"
FITTER_RESULTS_PATH = STORAGE_PATH / "fitter_results"


# === Вспомогательные функции ===

async def download_telegram_file(bot, file_id: str, save_path: str) -> bool:
    """Скачать файл из Telegram"""
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, save_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return False


def compress_image(image_path: str, max_size_mb: int = 10):
    """Сжать изображение если оно больше max_size_mb"""
    if not os.path.exists(image_path): return
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        return

    try:
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        quality = 85
        while quality > 20:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            if len(output.getvalue()) / (1024 * 1024) <= max_size_mb:
                with open(image_path, 'wb') as f:
                    f.write(output.getvalue())
                logger.info(f"Compressed image to quality {quality}")
                return
            quality -= 10
        logger.warning("Could not compress image enough")
    except Exception as e:
        logger.error(f"Failed to compress image: {e}")


async def get_telegram_file_url(bot, file_id: str) -> str:
    """Получить публичный URL файла из Telegram"""
    try:
        file = await bot.get_file(file_id)
        token = bot.token
        return f"https://api.telegram.org/file/bot{token}/{file.file_path}"
    except Exception as e:
        logger.error(f"Failed to get file URL: {e}")
        return None


# === Клавиатуры ===

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
    """Клавиатура выбора режима примерки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👕 Только этот товар", callback_data="fitter:mode:single_item")],
        [InlineKeyboardButton(text="👗 Весь образ с фото", callback_data="fitter:mode:full_outfit")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
    ])


def get_fitter_result_keyboard(fitter_id: int, product_id: str, wb_link: str, ozon_url: str = None):
    """Клавиатура после успешной примерки"""
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

    keyboard.extend([
        [InlineKeyboardButton(text="💾 Сохранить результат", callback_data=f"fitter:save_result:{fitter_id}")],
        [InlineKeyboardButton(text="🔄 Другое фото", callback_data=f"fitter:retry:{product_id}")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_my_photos_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить фото", callback_data="fitter:upload_new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])


def get_photo_manage_keyboard(photo_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"fitter:delete_photo:{photo_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_photos")]
    ])


# === Главное меню примерки ===

@router.callback_query(F.data == "fitter_main")
async def fitter_main_menu(callback: CallbackQuery):
    """Главное меню примерки"""
    await callback.message.edit_text(
        "👗 <b>Виртуальная примерка одежды</b>\n\n"
        "Загрузите своё фото и фото одежды, которую хотите примерить. "
        "Я создам реалистичное изображение того, как вы будете выглядеть в этой одежде.\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📸 Мои фото", callback_data="my_photos")],
            [InlineKeyboardButton(text="📜 История примерок", callback_data="fitter_history")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# === Согласие на обработку фото ===

@router.callback_query(F.data == "fitter:consent:yes", FitterStates.waiting_consent)
async def consent_given(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FitterStates.waiting_photo)
    await callback.message.edit_text(
        "Чтобы примерить одежду, загрузи свое фото!\n\n"
        "Требования:\n"
        "📸 Фото минимум по пояс\n"
        "💡 Хорошее освещение\n\n"
        "Загрузи фото прямо в чат!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]])
    )
    await callback.answer()


@router.callback_query(F.data == "fitter:consent:no", FitterStates.waiting_consent)
async def consent_declined(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Хорошо, примерка отменена. Ты всегда можешь вернуться к ней позже!")
    await callback.answer()


# === Загрузка фото ===

@router.callback_query(F.data == "fitter:upload_new")
async def request_photo_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FitterStates.waiting_photo)
    await callback.message.answer(
        "Загрузи свое фото:\n\n"
        "Требования:\n"
        "📸 Фото минимум по пояс\n"
        "💡 Хорошее освещение\n\n"
        "Отправь фото прямо в чат!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]])
    )
    await callback.answer()


@router.message(FitterStates.waiting_photo, F.photo)
async def photo_received(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    photo = message.photo[-1]  # Берем самое большое фото
    status_msg = await message.answer("Проверяем фото... 🔍")
    
    try:
        user_dir = USER_PHOTOS_PATH / str(tg_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = user_dir / f"photo_{timestamp}.jpg"
        
        if not await download_telegram_file(message.bot, photo.file_id, str(file_path)):
            await status_msg.edit_text("❌ Не удалось скачать фото. Попробуй еще раз")
            return
            
        compress_image(str(file_path), max_size_mb=10)
        file_url = await get_telegram_file_url(message.bot, photo.file_id)
        
        if not file_url:
            await status_msg.edit_text("❌ Ошибка обработки фото")
            return
            
        validation_result = await validate_photo(file_url)
        if not validation_result.get("valid"):
            reason = validation_result.get("description", "Фото не подходит для примерки")
            await status_msg.edit_text(
                f"❌ {reason}\n\nПопробуй загрузить другое фото",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Загрузить другое фото", callback_data="fitter:upload_new")],
                    [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
                ])
            )
            if file_path.exists(): 
                file_path.unlink()
            return

        # Здесь должна быть логика сохранения фото через API
        # upload_result = await bot_api_client.upload_photo(tg_id, photo.file_id, str(file_path), True)
        # Пока заглушка:
        upload_result = {"success": True, "photo": {"id": 1}}
        
        if not upload_result or not upload_result.get("success"):
            await status_msg.edit_text("❌ Ошибка сохранения фото")
            return

        photo_id = upload_result["photo"]["id"]
        await state.update_data(photo_id=photo_id)
        await status_msg.edit_text("✅ Отлично! Фото принято")
        
        data = await state.get_data()
        if data.get("product_id"):
            # Переходим к выбору модели
            await state.set_state(FitterStates.selecting_model)
            await message.answer("Отлично! Теперь выбери модель для генерации:", reply_markup=get_model_selection_keyboard())
        else:
            await message.answer("Фото сохранено! Теперь можешь примерять одежду 👗")
            await state.clear()
            
    except Exception as e:
        logger.error(f"Failed to process photo: {e}", exc_info=True)
        await status_msg.edit_text("❌ Ошибка обработки фото. Попробуй еще раз")


@router.message(FitterStates.waiting_photo, ~F.photo)
async def invalid_photo_received(message: Message):
    await message.answer(
        "Это не похоже на фото. Пожалуйста, отправь изображение или отмени операцию.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]])
    )


# === Общие хэндлеры ===

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    # Проверяем есть ли история примерок (заглушка)
    has_tryon_history = False
    
    await callback.message.edit_text(
        "👗 <b>Виртуальная примерка одежды</b>\n\n"
        "Загрузите своё фото и фото одежды, которую хотите примерить. "
        "Я создам реалистичное изображение того, как вы будете выглядеть в этой одежде.\n\n"
        "Выберите действие:",
        reply_markup=get_fitter_main_menu(has_tryon_history=has_tryon_history),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "tryon_history")
async def show_tryon_history(callback: CallbackQuery):
    """Показать историю примерок (заглушка)"""
    await callback.message.edit_text(
        "📜 <b>История примерок</b>\n\n"
        "У вас пока нет примерок. Попробуйте примерить что-нибудь!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_fitter")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустой callback для счетчика пагинации"""
    await callback.answer()


# === Выбор режима примерки ===

@router.callback_query(F.data == "fitter:mode:single_item")
async def choose_single_item_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор режима: только этот товар"""
    from keyboards.fitter_keyboards import get_model_selection_keyboard

    await state.update_data(tryon_mode='single_item')

    text = """⚡️ <b>Выбери модель генерации</b>

⚡️ <b>Быстрая</b> (~1-2 мин)
Быстрый результат, хорошее качество

👑 <b>Качественная</b> (~3-4 мин)
Высокое качество, более реалистичный результат

🚀 <b>GPT Image 1.5</b> (~3-4 мин)
Новейшая модель, максимальная детализация"""

    await callback.message.edit_text(
        text,
        reply_markup=get_model_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(FitterStates.choosing_model)
    await callback.answer()


@router.callback_query(F.data == "fitter:mode:full_outfit")
async def choose_full_outfit_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор режима: весь образ"""
    from keyboards.fitter_keyboards import get_model_selection_keyboard

    await state.update_data(tryon_mode='full_outfit')

    text = """⚡️ <b>Выбери модель генерации</b>

⚡️ <b>Быстрая</b> (~1-2 мин)
Быстрый результат, хорошее качество

👑 <b>Качественная</b> (~3-4 мин)
Высокое качество, более реалистичный результат

🚀 <b>GPT Image 1.5</b> (~3-4 мин)
Новейшая модель, максимальная детализация"""

    await callback.message.edit_text(
        text,
        reply_markup=get_model_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(FitterStates.choosing_model)
    await callback.answer()


# === Выбор модели генерации ===

@router.callback_query(F.data.startswith("fitter:model:"))
async def choose_model(callback: CallbackQuery, state: FSMContext):
    """Выбор модели генерации"""
    model = callback.data.split(":")[-1]
    await state.update_data(model=model)

    model_names = {
        'fast': 'Быстрая',
        'pro': 'Качественная',
        'gpt-image-1.5': 'GPT Image 1.5'
    }

    text = f"""📸 <b>Загрузи свое фото</b>

Модель: {model_names.get(model, model)}

<b>Требования к фото:</b>
• Человек должен быть виден в полный рост или по пояс
• Хорошее освещение
• Четкое изображение

Отправь фото в чат 👇"""

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(FitterStates.waiting_for_user_photo)
    await callback.answer()


# === Обработка фото пользователя ===

@router.message(FitterStates.waiting_for_user_photo, F.photo)
async def process_user_photo_for_tryon(message: Message, state: FSMContext):
    """Обработка фото пользователя для примерки"""
    from keyboards.fitter_keyboards import get_fitter_result_keyboard

    status_msg = await message.answer("⏳ Обрабатываем фото...")

    try:
        # Получаем данные из state
        data = await state.get_data()
        product = data.get('product')
        model = data.get('model', 'fast')
        tryon_mode = data.get('tryon_mode', 'single_item')
        category_id = data.get('category_id', '')
        index = data.get('index', 0)
        source = data.get('source', 'catalog')

        if not product:
            await status_msg.edit_text("❌ Ошибка: товар не найден")
            return

        # Получаем URL фото пользователя
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        user_photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        # Валидация фото
        await status_msg.edit_text("🔍 Проверяем фото...")
        validation_result = await validate_photo(user_photo_url)

        if not validation_result.get("valid"):
            reason = validation_result.get("description", "Фото не подходит для примерки")
            await status_msg.edit_text(
                f"❌ {reason}\n\nПопробуй загрузить другое фото",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Загрузить другое", callback_data=f"fitter:retry:{source}:{product['product_id']}:{category_id}:{index}")],
                    [InlineKeyboardButton(text="◀️ К товару", callback_data=f"back:product:{product['product_id']}:{category_id}:{index}")]
                ])
            )
            return

        # Получаем фото товара
        garment_url = product.get('photo_1_url') or product.get('collage_url')
        if not garment_url:
            await status_msg.edit_text("❌ У товара нет фото для примерки")
            return

        # Генерация примерки
        await status_msg.edit_text(f"✨ Создаем примерку... Это займет ~{model == 'fast' and '1-2' or '3-4'} минуты")

        result = await generate_tryon(
            user_photo_url=user_photo_url,
            garment_url=garment_url,
            mode=tryon_mode,
            model=model
        )

        if result.get('success') and result.get('image_url'):
            # Отправляем результат
            await message.answer_photo(
                photo=result['image_url'],
                caption=f"✨ <b>Примерка готова!</b>\n\n{product.get('name', 'Товар')}",
                reply_markup=get_fitter_result_keyboard(
                    fitter_id=result.get('fitter_id', 0),
                    product_id=product['product_id'],
                    wb_link=product.get('wb_link', ''),
                    ozon_url=product.get('ozon_url'),
                    source=source,
                    category_id=category_id,
                    index=index
                ),
                parse_mode="HTML"
            )
            await status_msg.delete()
        else:
            error_msg = result.get('error', {}).get('message', 'Не удалось создать примерку')
            await status_msg.edit_text(
                f"❌ {error_msg}\n\nПопробуй еще раз или выбери другое фото",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"fitter:retry:{source}:{product['product_id']}:{category_id}:{index}")],
                    [InlineKeyboardButton(text="◀️ К товару", callback_data=f"back:product:{product['product_id']}:{category_id}:{index}")]
                ])
            )

    except Exception as e:
        logger.error(f"Error processing tryon: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Произошла ошибка при создании примерки\n\nПопробуй еще раз",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
            ])
        )
    finally:
        await state.clear()


@router.message(FitterStates.waiting_for_user_photo, ~F.photo)
async def invalid_photo_for_tryon(message: Message):
    """Неверный формат - ожидается фото"""
    await message.answer(
        "❌ Пожалуйста, отправь фото (не файл, не документ)\n\nИли отмени операцию",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="fitter:cancel")]
        ])
    )


# === Повтор примерки ===

@router.callback_query(F.data.startswith("fitter:retry:"))
async def retry_tryon(callback: CallbackQuery, state: FSMContext):
    """Повторить примерку с другим фото"""
    from keyboards.fitter_keyboards import get_model_selection_keyboard

    parts = callback.data.split(":")
    source = parts[2]
    product_id = parts[3]
    category_id = parts[4] if len(parts) > 4 else ''
    index = int(parts[5]) if len(parts) > 5 else 0

    # Получаем товар
    product = await bot_api_client.get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    # Сохраняем контекст
    await state.update_data(
        product_id=product_id,
        category_id=category_id,
        index=index,
        source=source,
        product=product
    )

    text = """⚡️ <b>Выбери модель генерации</b>

⚡️ <b>Быстрая</b> (~1-2 мин)
Быстрый результат, хорошее качество

👑 <b>Качественная</b> (~3-4 мин)
Высокое качество, более реалистичный результат

🚀 <b>GPT Image 1.5</b> (~3-4 мин)
Новейшая модель, максимальная детализация"""

    await callback.message.edit_text(
        text,
        reply_markup=get_model_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(FitterStates.choosing_model)
    await callback.answer()


# === Отмена ===

@router.callback_query(F.data == "fitter:cancel")
async def cancel_fitter(callback: CallbackQuery, state: FSMContext):
    """Отмена примерки"""
    await state.clear()
    await callback.message.edit_text(
        "Примерка отменена. Вы в главном меню.",
        reply_markup=main_keyboard()
    )
    await callback.answer()