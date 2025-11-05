import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from api.client import bot_api_client
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_reviews_keyboard
from utils.formatters import format_error_message, format_rating

router = Router()


@router.callback_query(F.data == "reviews")
async def show_reviews_menu(callback: CallbackQuery):
    """Показать меню отзывов с реальными данными"""
    # По умолчанию показываем все отзывы (rating_threshold=None)
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=0,
        rating_threshold=None
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        statistics = reviews_data.get("statistics", {})
        rating_threshold = statistics.get("rating_threshold")
        
        if new_reviews or unanswered_questions:
            keyboard = create_reviews_keyboard(
                has_more=len(new_reviews) + len(unanswered_questions) >= 10,
                offset=0,
                rating_threshold=rating_threshold
            )
            
            await callback.message.edit_text(
                response.telegram_text or "⭐ Отзывы и вопросы",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "✅ Новых отзывов и вопросов нет!\n\n"
                "Все отзывы обработаны.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "new_reviews")
async def show_new_reviews(callback: CallbackQuery):
    """Показать новые отзывы"""
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        statistics = reviews_data.get("statistics", {})
        
        if new_reviews or unanswered_questions:
            keyboard = create_reviews_keyboard(
                has_more=len(new_reviews) + len(unanswered_questions) >= 10,
                offset=0
            )
            
            await callback.message.edit_text(
                response.telegram_text or "⭐ Новые отзывы и вопросы",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                "✅ Новых отзывов и вопросов нет!\n\n"
                "Все отзывы обработаны.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "critical_reviews")
async def show_critical_reviews(callback: CallbackQuery):
    """Показать критические отзывы (1-3 звезды)"""
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        statistics = reviews_data.get("statistics", {})
        
        # Фильтруем критические отзывы
        critical_reviews = [r for r in new_reviews if r.get("rating", 5) <= 3]
        
        if critical_reviews:
            # Формируем текст для критических отзывов
            text = "🚨 КРИТИЧЕСКИЕ ОТЗЫВЫ (1-3⭐)\n\n"
            
            for review in critical_reviews[:5]:  # Показываем максимум 5
                rating = review.get("rating", 0)
                product_name = review.get("product_name", "Неизвестный товар")
                review_text = review.get("text", "")
                time_ago = review.get("time_ago", "")
                
                text += f"{format_rating(rating)} {product_name}\n"
                text += f"💬 \"{review_text[:100]}{'...' if len(review_text) > 100 else ''}\"\n"
                text += f"⏰ {time_ago}\n\n"
            
            if len(critical_reviews) > 5:
                text += f"... и еще {len(critical_reviews) - 5} отзывов\n\n"
            
            text += f"📊 Всего критических: {statistics.get('attention_needed', 0)}"
            
            keyboard = create_reviews_keyboard()
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(
                "✅ Критических отзывов нет!\n\n"
                "Все отзывы имеют рейтинг 4-5 звезд.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("reviews_page_"))
async def show_reviews_page(callback: CallbackQuery):
    """Показать страницу отзывов с сохранением фильтра"""
    try:
        # Парсим callback_data: reviews_page_{offset}_{rating_threshold}
        parts = callback.data.split("_")
        offset = int(parts[2]) if len(parts) > 2 else 0
        
        # Парсим rating_threshold (последняя часть после offset)
        rating_threshold = None
        if len(parts) > 3:
            threshold_str = parts[3]
            if threshold_str != "all":
                try:
                    rating_threshold = int(threshold_str)
                except ValueError:
                    rating_threshold = None
    except (ValueError, IndexError):
        offset = 0
        rating_threshold = None
    
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=offset,
        rating_threshold=rating_threshold
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        statistics = reviews_data.get("statistics", {})
        current_threshold = statistics.get("rating_threshold")
        
        keyboard = create_reviews_keyboard(
            has_more=len(new_reviews) + len(unanswered_questions) >= 10,
            offset=offset,
            rating_threshold=current_threshold
        )
        
        await callback.message.edit_text(
            response.telegram_text or "⭐ Отзывы и вопросы",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("reviews_filter_toggle_"))
async def toggle_reviews_filter(callback: CallbackQuery):
    """Циклически переключать фильтр отзывов: 1 → 2 → 3 → 4 → 5 → 1"""
    # Парсим текущий threshold из callback_data
    try:
        current_threshold_str = callback.data.split("_")[-1]
        current_threshold = int(current_threshold_str) if current_threshold_str.isdigit() else 5
    except (ValueError, IndexError):
        current_threshold = 5  # По умолчанию 5 (все отзывы)
    
    # Циклическое переключение: 1 → 2 → 3 → 4 → 5 (все) → 1 (без варианта "Выкл")
    if current_threshold >= 5:
        next_threshold = 1
    else:
        next_threshold = current_threshold + 1
    
    # Для API: если next_threshold=5, передаем None (все отзывы)
    # Для клавиатуры: используем 5 для callback_data (цикл), но показываем "Все отзывы"
    api_threshold = None if next_threshold == 5 else next_threshold
    
    # Получаем отзывы с новым фильтром
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=0,
        rating_threshold=api_threshold
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        statistics = reviews_data.get("statistics", {})
        
        # Формируем текст для callback answer
        if next_threshold == 5:
            callback_text = "✅ Фильтр: Все отзывы (≤5★)"
        else:
            stars = "⭐" * next_threshold
            callback_text = f"✅ Фильтр: {stars} (≤{next_threshold}★)"
        
        # Для клавиатуры используем None если next_threshold=5 (все отзывы)
        keyboard_threshold = None if next_threshold == 5 else next_threshold
        keyboard = create_reviews_keyboard(
            has_more=len(new_reviews) + len(unanswered_questions) >= 10,
            offset=0,
            rating_threshold=keyboard_threshold
        )
        
        await callback.message.edit_text(
            response.telegram_text or "⭐ Отзывы и вопросы",
            reply_markup=keyboard
        )
        await callback.answer(callback_text)
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "auto_answers")
async def show_auto_answers(callback: CallbackQuery):
    """Показать настройки автоответов"""
    # TODO: Реализовать автоответы через API
    await callback.message.edit_text(
        "🤖 АВТООТВЕТЫ\n\n"
        "⚠️ Функция автоответов будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр новых отзывов и вопросов.",
        reply_markup=create_reviews_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "export_reviews")
async def export_reviews_to_google(callback: CallbackQuery):
    """Экспорт отзывов в Google Sheets"""
    # TODO: Реализовать экспорт в Google Sheets
    await callback.message.edit_text(
        "📤 ЭКСПОРТ В GOOGLE SHEETS\n\n"
        "⚠️ Функция экспорта в Google Sheets будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр новых отзывов и вопросов.",
        reply_markup=create_reviews_keyboard()
    )
    await callback.answer()


@router.message(Command("reviews"))
async def cmd_reviews(message: Message):
    """Команда /reviews"""
    response = await bot_api_client.get_reviews_summary(
        user_id=message.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        
        if new_reviews or unanswered_questions:
            keyboard = create_reviews_keyboard(
                has_more=len(new_reviews) + len(unanswered_questions) >= 10,
                offset=0
            )
            
            await message.answer(
                response.telegram_text or "⭐ Новые отзывы и вопросы",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "✅ Новых отзывов и вопросов нет!\n\n"
                "Все отзывы обработаны.",
                reply_markup=wb_menu_keyboard()
            )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка загрузки отзывов:\n\n{error_message}",
            reply_markup=main_keyboard()
        )