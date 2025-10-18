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
    """Показать страницу отзывов"""
    try:
        offset = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        offset = 0
    
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=offset
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        
        keyboard = create_reviews_keyboard(
            has_more=len(new_reviews) + len(unanswered_questions) >= 10,
            offset=offset
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


@router.callback_query(F.data == "refresh_reviews")
async def refresh_reviews(callback: CallbackQuery):
    """Обновить данные об отзывах"""
    await callback.message.edit_text("⏳ Обновляю данные об отзывах...")
    
    response = await bot_api_client.get_reviews_summary(
        user_id=callback.from_user.id,
        limit=10,
        offset=0
    )
    
    if response.success and response.data:
        reviews_data = response.data.get("reviews", {})
        new_reviews = reviews_data.get("new_reviews", [])
        unanswered_questions = reviews_data.get("unanswered_questions", [])
        
        keyboard = create_reviews_keyboard(
            has_more=len(new_reviews) + len(unanswered_questions) >= 10,
            offset=0
        )
        
        await callback.message.edit_text(
            response.telegram_text or "⭐ Отзывы обновлены",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка обновления отзывов:\n\n{error_message}",
            reply_markup=wb_menu_keyboard()
        )
    
    await callback.answer("✅ Данные обновлены")


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