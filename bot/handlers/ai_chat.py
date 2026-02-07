"""
AI Chat Handler - интеграция с AI Chat Service.

Кнопка:
- 💬 AI-чат (в меню AI-помощник)

Команды:
- /ai_limits - проверить лимиты запросов
"""

import logging
import os
from typing import Optional, Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import aiohttp

from core.config import config
from core.states import AIChatStates
from utils.formatters import (
    safe_send_message,
    handle_telegram_errors,
)
from api.client import bot_api_client

logger = logging.getLogger(__name__)

router = Router()

# URL AI Chat Service (в составе gpt_integration)
AI_CHAT_URL = getattr(config, "ai_chat_service_url", None) or os.getenv("AI_CHAT_SERVICE_URL", "http://gpt:9000")


# ============================================================================
# Функции для получения пользовательского контекста
# ============================================================================

async def get_user_context(telegram_id: int) -> Optional[str]:
    """
    Получает контекст пользователя из основной БД для персонализированных ответов.
    
    Включает:
    - Статистику продаж
    - Данные о заказах
    - Аналитику
    
    Returns:
        str: Форматированный контекст для добавления в промпт или None при ошибке
    """
    try:
        logger.info(f"📊 Получение контекста пользователя {telegram_id}")
        
        # Получаем dashboard (основная статистика)
        dashboard_resp = await bot_api_client.get_dashboard(telegram_id)
        
        if not dashboard_resp.success or not dashboard_resp.data:
            logger.warning(f"⚠️ Не удалось получить dashboard для пользователя {telegram_id}")
            return None
        
        dashboard = dashboard_resp.data
        
        # Получаем статистику продаж за 7 дней
        sales_resp = await bot_api_client.get_analytics_sales(
            user_id=telegram_id,
            period="7d"
        )
        
        sales_data = sales_resp.data if sales_resp.success else {}
        
        # Формируем контекст
        context_parts = []
        
        # Основная статистика
        if "orders" in dashboard:
            orders = dashboard["orders"]
            context_parts.append(f"Заказы за 7 дней: {orders.get('total_7d', 0)} шт.")
            context_parts.append(f"Новые заказы: {orders.get('new', 0)} шт.")
        
        if "sales" in dashboard:
            sales = dashboard["sales"]
            revenue_7d = sales.get('revenue_7d', 0)
            context_parts.append(f"Выручка за 7 дней: {revenue_7d:,.0f} ₽")
        
        if "stocks" in dashboard:
            stocks = dashboard["stocks"]
            context_parts.append(f"Товаров на складе: {stocks.get('total_items', 0)} шт.")
            critical = stocks.get('critical_items', 0)
            if critical > 0:
                context_parts.append(f"⚠️ Критичных остатков: {critical}")
        
        if "reviews" in dashboard:
            reviews = dashboard["reviews"]
            avg_rating = reviews.get('average_rating', 0)
            if avg_rating:
                context_parts.append(f"Средний рейтинг: {avg_rating:.1f}⭐")
            negative = reviews.get('negative_count', 0)
            if negative > 0:
                context_parts.append(f"Негативных отзывов: {negative}")
        
        # Статистика продаж
        if sales_data:
            if "top_products" in sales_data:
                top_products = sales_data["top_products"][:3]  # Топ-3
                if top_products:
                    context_parts.append("\nТоп товары по продажам:")
                    for i, product in enumerate(top_products, 1):
                        name = product.get("name", "N/A")[:30]
                        revenue = product.get("revenue", 0)
                        context_parts.append(f"{i}. {name} - {revenue:,.0f} ₽")
        
        if not context_parts:
            return None
        
        # Собираем контекст
        context = "\n".join(context_parts)
        
        logger.info(f"✅ Контекст пользователя {telegram_id} получен: {len(context)} символов")
        
        return context
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения контекста для пользователя {telegram_id}: {e}", exc_info=True)
        return None


# ============================================================================
# Callback ai_chat - начать диалог с AI
# ============================================================================

def create_ai_chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для режима AI чата."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Выйти из чата", callback_data="cancel_ai_chat")],
        [InlineKeyboardButton(text="📊 Мои лимиты", callback_data="check_ai_limits")]
    ])


@router.callback_query(F.data == "ai_chat")
@handle_telegram_errors
async def callback_ai_chat(callback: CallbackQuery, state: FSMContext):
    """
    Начать диалог с AI ассистентом.
    
    Активирует режим чата, где все последующие сообщения
    отправляются в AI Chat Service.
    """
    telegram_id = callback.from_user.id
    
    logger.info(f"🤖 User {telegram_id} started AI chat")
    
    welcome_text = (
        "🤖 <b>AI Ассистент Wildberries</b>\n\n"
        "Я помогу вам с:\n"
        "📊 Анализом продаж и статистики\n"
        "📦 Работой с заказами и остатками\n"
        "⭐ Отзывами и рейтингами\n"
        "💰 Ценообразованием и конкурентами\n"
        "📈 Стратегиями продвижения на WB\n\n"
        "Просто напишите ваш вопрос, и я отвечу!\n\n"
        "🎯 <b>Персонализация:</b>\n"
        "<i>Я вижу статистику ваших продаж и могу давать конкретные советы на основе ваших данных!</i>\n\n"
        "💡 <b>Для глубокого анализа:</b> Используйте кнопку <b>🧠 AI-анализ</b> - детальный отчет с рекомендациями\n"
        "📊 <i>У вас есть 30 запросов в сутки</i>"
    )
    
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=create_ai_chat_keyboard()
    )
    
    # Устанавливаем состояние ожидания сообщения
    await state.set_state(AIChatStates.waiting_for_message)
    await callback.answer()


# ============================================================================
# Callback cancel_ai_chat - выйти из режима чата
# ============================================================================

@router.callback_query(F.data == "cancel_ai_chat", StateFilter(AIChatStates.waiting_for_message))
@handle_telegram_errors
async def callback_cancel_chat(callback: CallbackQuery, state: FSMContext):
    """
    Выйти из режима AI чата.
    """
    telegram_id = callback.from_user.id
    
    logger.info(f"🔚 User {telegram_id} cancelled AI chat")
    
    await state.clear()
    
    # Возвращаемся в меню AI-помощника
    from keyboards.keyboards import ai_assistant_keyboard
    
    await callback.message.edit_text(
        "✅ Чат с AI завершен.\n\nВыберите действие:",
        reply_markup=ai_assistant_keyboard()
    )
    
    # Отправляем отдельное сообщение о завершении диалога
    await safe_send_message(
        callback.message,
        "✅ <b>Диалог завершен</b>\n\n"
        "Спасибо за использование AI ассистента! Если понадобится помощь, "
        "вы всегда можете начать новый диалог.",
        user_id=telegram_id,
        parse_mode="HTML"
    )
    
    await callback.answer()


# ============================================================================
# Обработка текстовых сообщений в режиме AI чата
# ============================================================================

@router.message(StateFilter(AIChatStates.waiting_for_message), F.text)
@handle_telegram_errors
async def process_ai_message(message: Message, state: FSMContext):
    """
    Обработка сообщений пользователя в режиме AI чата.
    
    Отправляет сообщение в AI Chat Service и возвращает ответ.
    """
    telegram_id = message.from_user.id
    user_message = message.text
    
    # Проверка длины сообщения
    if len(user_message) > 4000:
        await safe_send_message(
            message,
            "⚠️ Сообщение слишком длинное (максимум 4000 символов).\n"
            "Пожалуйста, сократите ваш вопрос.",
            user_id=telegram_id
        )
        return
    
    logger.info(f"💬 AI chat message from user {telegram_id}: {len(user_message)} chars")
    
    # Показываем индикатор печати
    await message.bot.send_chat_action(chat_id=telegram_id, action="typing")
    
    # Получаем персонализированный контекст пользователя
    user_context = await get_user_context(telegram_id)
    
    # Отправляем запрос к AI Chat Service
    endpoint = f"{AI_CHAT_URL.rstrip('/')}/v1/chat/send"
    payload = {
        "telegram_id": telegram_id,
        "message": user_message,
        "user_context": user_context  # Добавляем контекст пользователя
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": config.api_secret_key
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # 60 секунд для OpenAI
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                
                # Успешный ответ
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get("response", "")
                    remaining = data.get("remaining_requests", 0)
                    
                    # Формируем ответ с информацией о лимитах
                    full_response = (
                        f"{response_text}\n\n"
                        f"<i>Осталось запросов: {remaining}/30</i>"
                    )
                    
                    await safe_send_message(
                        message,
                        full_response,
                        user_id=telegram_id,
                        parse_mode="HTML"
                    )
                    
                    logger.info(f"✅ AI response sent to user {telegram_id}: {remaining} requests remaining")
                
                # Лимит исчерпан
                elif resp.status == 429:
                    error_data = await resp.json()
                    error_detail = error_data.get("detail", {})
                    
                    if isinstance(error_detail, dict):
                        error_msg = error_detail.get("message", "Лимит запросов исчерпан")
                    else:
                        error_msg = str(error_detail)
                    
                    await safe_send_message(
                        message,
                        f"⛔ {error_msg}\n\n"
                        "💡 Лимит сбрасывается каждый день в полночь.\n"
                        "Попробуйте завтра! 🌅",
                        user_id=telegram_id
                    )
                    
                    # Выходим из режима чата
                    await state.clear()
                    
                    # Отправляем сообщение о завершении диалога
                    await safe_send_message(
                        message,
                        "✅ <b>Диалог завершен</b>\n\n"
                        "Лимит запросов исчерпан. Диалог с AI завершен.\n"
                        "Вы можете начать новый диалог завтра после сброса лимита.",
                        user_id=telegram_id,
                        parse_mode="HTML"
                    )
                    
                    logger.warning(f"⛔ Rate limit exceeded for user {telegram_id}")
                
                # Другие ошибки
                else:
                    body = await resp.text()
                    logger.error(f"❌ AI Chat Service error {resp.status}: {body}")
                    
                    # Пытаемся извлечь детали ошибки из ответа
                    error_detail = "Неизвестная ошибка"
                    try:
                        error_data = await resp.json()
                        if isinstance(error_data, dict):
                            detail = error_data.get("detail", {})
                            if isinstance(detail, dict):
                                error_msg = detail.get("message", detail.get("error", "Неизвестная ошибка"))
                                error_detail = error_msg
                            else:
                                error_detail = str(detail)
                    except Exception:
                        # Если не удалось распарсить JSON, используем текст ответа
                        if body:
                            error_detail = body[:500]  # Ограничиваем длину
                    
                    await safe_send_message(
                        message,
                        f"❌ Произошла ошибка при обращении к AI сервису.\n\n"
                        f"<code>Статус: {resp.status}</code>\n"
                        f"<code>{error_detail[:200]}</code>\n\n"
                        "Попробуйте позже или обратитесь к администратору.",
                        user_id=telegram_id,
                        parse_mode="HTML"
                    )
    
    except aiohttp.ClientError as e:
        logger.error(f"❌ Network error calling AI Chat Service: {e}")
        await safe_send_message(
            message,
            "❌ Не удалось связаться с AI сервисом.\n"
            "Проверьте подключение или попробуйте позже.",
            user_id=telegram_id
        )
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in AI chat: {e}", exc_info=True)
        await safe_send_message(
            message,
            "❌ Произошла непредвиденная ошибка.\n"
            "Попробуйте позже или обратитесь к администратору.",
            user_id=telegram_id
        )


# ============================================================================
# Callback check_ai_limits - проверить лимиты
# ============================================================================

@router.callback_query(F.data == "check_ai_limits")
@handle_telegram_errors
async def callback_ai_limits(callback: CallbackQuery):
    """
    Проверить текущие лимиты AI запросов (через callback).
    """
    await show_ai_limits(callback.from_user.id, callback.message)
    await callback.answer()


# ============================================================================
# Команда /ai_limits - проверить лимиты (оставляем для совместимости)
# ============================================================================

@router.message(Command("ai_limits"))
@handle_telegram_errors
async def cmd_ai_limits(message: Message):
    """
    Проверить текущие лимиты AI запросов (через команду).
    """
    await show_ai_limits(message.from_user.id, message)


async def show_ai_limits(telegram_id: int, target_message: Message):
    """
    Проверить текущие лимиты AI запросов.
    """
    logger.info(f"📊 User {telegram_id} checking AI limits")
    
    # Запрос к AI Chat Service
    endpoint = f"{AI_CHAT_URL.rstrip('/')}/v1/chat/limits/{telegram_id}"
    headers = {
        "X-API-KEY": config.api_secret_key
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(endpoint, headers=headers) as resp:
                
                if resp.status == 200:
                    data = await resp.json()
                    
                    requests_today = data.get("requests_today", 0)
                    requests_remaining = data.get("requests_remaining", 0)
                    daily_limit = data.get("daily_limit", 30)
                    
                    # Прогресс бар
                    filled = int((requests_today / daily_limit) * 10)
                    empty = 10 - filled
                    progress_bar = "█" * filled + "░" * empty
                    
                    limits_text = (
                        "📊 <b>Ваши лимиты AI чата</b>\n\n"
                        f"Использовано: <b>{requests_today}</b> из {daily_limit}\n"
                        f"Осталось: <b>{requests_remaining}</b>\n\n"
                        f"[{progress_bar}] {requests_today}/{daily_limit}\n\n"
                        "💡 Лимит сбрасывается каждый день в полночь"
                    )
                    
                    # Если это callback, редактируем сообщение
                    if hasattr(target_message, 'edit_text'):
                        await target_message.edit_text(
                            limits_text,
                            parse_mode="HTML",
                            reply_markup=create_ai_chat_keyboard()
                        )
                    else:
                        # Если это обычное сообщение
                        await safe_send_message(
                            target_message,
                            limits_text,
                            user_id=telegram_id,
                            parse_mode="HTML"
                        )
                    
                    logger.info(f"✅ Limits sent to user {telegram_id}: {requests_remaining} remaining")
                
                else:
                    body = await resp.text()
                    logger.error(f"❌ Failed to get limits: HTTP {resp.status}: {body}")
                    
                    error_text = "❌ Не удалось получить информацию о лимитах.\nПопробуйте позже."
                    
                    if hasattr(target_message, 'edit_text'):
                        await target_message.edit_text(error_text, reply_markup=create_ai_chat_keyboard())
                    else:
                        await safe_send_message(target_message, error_text, user_id=telegram_id)
    
    except Exception as e:
        logger.error(f"❌ Error getting AI limits: {e}", exc_info=True)
        
        error_text = "❌ Произошла ошибка при получении лимитов.\nПопробуйте позже."
        
        if hasattr(target_message, 'edit_text'):
            await target_message.edit_text(error_text, reply_markup=create_ai_chat_keyboard())
        else:
            await safe_send_message(target_message, error_text, user_id=telegram_id)


# ============================================================================
# Callback ai_fitter - переход к функционалу примерки
# ============================================================================

@router.callback_query(F.data == "ai_fitter")
@handle_telegram_errors
async def ai_fitter_transition(callback: CallbackQuery):
    """Переход к функционалу примерки из AI-помощника."""
    from keyboards.fitter_keyboards import get_fitter_main_menu
    
    # Проверяем есть ли история примерок (заглушка, в реальности нужно проверить через API)
    has_tryon_history = False  # TODO: проверить через bot_api_client.has_tryon_history(callback.from_user.id)
    
    await callback.message.edit_text(
        "👗 <b>Виртуальная примерка одежды</b>\n\n"
        "Загрузите своё фото и фото одежды, которую хотите примерить. "
        "Я создам реалистичное изображение того, как вы будете выглядеть в этой одежде.\n\n"
        "Выберите действие:",
        reply_markup=get_fitter_main_menu(has_tryon_history=has_tryon_history),
        parse_mode="HTML"
    )
    await callback.answer()

