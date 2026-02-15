"""
Handler для настроек пользователя и выбора AI модели
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from bot.api.client import BotAPIClient
from bot.keyboards.keyboards import get_settings_keyboard, get_ai_model_selection_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_model_display_name(model_id: str) -> str:
    """Получить читаемое название модели"""
    names = {
        "gpt-5.1": "GPT-5.1 (OpenAI)",
        "claude-sonnet-4.5": "Claude Sonnet 4.5 (Anthropic)"
    }
    return names.get(model_id, model_id)


def get_model_description(model_id: str) -> str:
    """Получить описание модели"""
    descriptions = {
        "gpt-5.1": "Новейшая модель GPT-5.1 от OpenAI с улучшенными возможностями рассуждения",
        "claude-sonnet-4.5": "Продвинутая модель Claude Sonnet 4.5 с глубоким пониманием контекста"
    }
    return descriptions.get(model_id, "")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings - открыть настройки"""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел настроек:",
        reply_markup=get_settings_keyboard()
    )


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показать меню настроек"""
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел настроек:",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "settings_ai_model")
async def show_ai_model_selection(callback: CallbackQuery):
    """Показать выбор AI модели"""
    logger.info(f"🤖 Получен callback settings_ai_model от пользователя {callback.from_user.id}")
    
    try:
        client = BotAPIClient()
        
        logger.info(f"📡 Запрашиваем настройки пользователя {callback.from_user.id}")
        # Получаем текущие настройки пользователя
        settings = await client.get_user_settings(callback.from_user.id)
        current_model = settings.get("preferred_ai_model", "gpt-5.1")
        logger.info(f"✅ Текущая модель пользователя: {current_model}")
        
        logger.info(f"📡 Запрашиваем список доступных моделей")
        # Получаем список доступных моделей
        models_data = await client.get_available_ai_models()
        logger.info(f"✅ Получено моделей: {len(models_data.get('models', []))}")
        
        text = (
            "🤖 Выбор AI модели\n\n"
            f"Текущая модель: {get_model_display_name(current_model)}\n\n"
            "Доступные модели:\n\n"
        )
        
        # Если список моделей пустой, добавляем вручную
        if not models_data.get("models"):
            text += "• GPT-5.1 (OpenAI)\n"
            text += "  Новейшая модель GPT-5.1 от OpenAI с улучшенными возможностями рассуждения\n\n"
            text += "• Claude Sonnet 4.5 (Anthropic)\n"
            text += "  Продвинутая модель Claude Sonnet 4.5 с глубоким пониманием контекста\n\n"
        else:
            for model in models_data["models"]:
                text += f"• {model['name']}\n"
                text += f"  {model['description']}\n\n"
        
        text += (
            "Выбранная модель будет использоваться для:\n"
            "• AI-ассистента\n"
            "• Аналитики продаж\n"
            "• Генерации контента\n\n"
            "Выберите модель:"
        )
        
        logger.info(f"📤 Отправляем сообщение пользователю {callback.from_user.id}")
        await callback.message.edit_text(
            text,
            reply_markup=get_ai_model_selection_keyboard(current_model),
            parse_mode=None  # Отключаем HTML парсинг
        )
        await callback.answer()
        logger.info(f"✅ Сообщение отправлено пользователю {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка показа выбора AI модели: {e}", exc_info=True)
        await callback.answer(
            "❌ Ошибка загрузки настроек",
            show_alert=True
        )


@router.callback_query(F.data.startswith("ai_model_"))
async def select_ai_model(callback: CallbackQuery):
    """Выбрать AI модель"""
    try:
        model_id = callback.data.replace("ai_model_", "")
        client = BotAPIClient()
        
        # Обновляем настройки пользователя
        await client.update_user_settings(
            telegram_id=callback.from_user.id,
            preferred_ai_model=model_id
        )
        
        model_name = get_model_display_name(model_id)
        
        await callback.answer(
            f"✅ Модель {model_name} выбрана!",
            show_alert=True
        )
        
        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=get_ai_model_selection_keyboard(model_id)
        )
        
        logger.info(
            f"Пользователь {callback.from_user.id} выбрал модель {model_id}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка выбора AI модели: {e}")
        await callback.answer(
            "❌ Ошибка обновления настроек",
            show_alert=True
        )
