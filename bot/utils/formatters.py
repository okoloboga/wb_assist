from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import re
from functools import wraps
import inspect
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


def format_error_message(error: Optional[str], status_code: int) -> str:
    """Форматировать сообщение об ошибке для пользователя"""
    if not error:
        error = "Неизвестная ошибка"
    
    # Специальные сообщения для разных статус кодов
    if status_code == 503:
        return "🔧 Сервер временно недоступен. Попробуйте позже."
    elif status_code == 404:
        return "❌ Ресурс не найден. Проверьте правильность запроса."
    elif status_code == 400:
        return f"❌ Некорректный запрос: {error}"
    elif status_code == 401:
        return "🔐 Ошибка авторизации. Проверьте API ключ."
    elif status_code == 403:
        return "🚫 Доступ запрещен. У вас нет прав для выполнения этой операции."
    elif status_code == 408:
        return "⏰ Превышено время ожидания. Попробуйте позже."
    elif status_code == 409:
        return f"⚠️ {error}" # Возвращаем сообщение от сервера напрямую
    elif status_code == 429:
        return "🚦 Слишком много запросов. Подождите немного."
    elif status_code >= 500:
        return "🔧 Внутренняя ошибка сервера. Попробуйте позже."
    else:
        return f"❌ Ошибка: {error}"


def format_currency(amount: float) -> str:
    """Форматировать валюту"""
    return f"{amount:,.0f}₽".replace(",", " ")


def format_percentage(value: float) -> str:
    """Форматировать процент"""
    return f"{value:+.1f}%"


def format_datetime(dt_string: str) -> str:
    """Форматировать дату и время"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return dt_string


def format_relative_time(dt_string: str) -> str:
    """Форматировать относительное время"""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"
    except:
        return dt_string


def format_stocks_summary(stocks: Dict[str, int]) -> str:
    """Форматировать сводку по остаткам"""
    if not stocks:
        return "Нет данных"
    
    formatted = []
    for size, quantity in stocks.items():
        if quantity == 0:
            formatted.append(f"{size}(0)")
        elif quantity < 5:
            formatted.append(f"{size}({quantity})⚠️")
        else:
            formatted.append(f"{size}({quantity})")
    
    return " ".join(formatted)


def format_order_summary(order: Dict[str, Any]) -> str:
    """Форматировать краткую сводку заказа"""
    return (
        f"🧾 #{order.get('id', 'N/A')} | "
        f"{format_relative_time(order.get('date', ''))} | "
        f"{format_currency(order.get('amount', 0))}"
    )


def format_product_summary(product: Dict[str, Any]) -> str:
    """Форматировать краткую сводку товара"""
    return (
        f"📦 {product.get('name', 'N/A')} | "
        f"{product.get('brand', 'N/A')} | "
        f"{format_currency(product.get('price', 0))}"
    )


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def format_rating(rating: float) -> str:
    """Форматировать рейтинг звездочками"""
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = "⭐" * full_stars
    if half_star:
        stars += "✨"
    stars += "☆" * empty_stars
    
    return f"{stars} {rating:.1f}/5"


async def safe_edit_message(
    callback: CallbackQuery, 
    text: str, 
    reply_markup=None,
    user_id: int = None,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: Optional[bool] = None
) -> bool:
    """
    Безопасно редактировать сообщение с обработкой TelegramBadRequest
    
    Returns:
        bool: True если сообщение было отредактировано, False если не изменилось
    """
    try:
        # Проверяем, изменилось ли содержимое (безопасно обрабатываем отсутствие атрибутов у mock)
        current_text = getattr(callback.message, "text", None)
        current_markup = getattr(callback.message, "reply_markup", None)
        if (current_text == text and 
            current_markup == reply_markup):
            await callback.answer()
            return False
        
        # Редактируем сообщение
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        return True
        
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        
        if "message is not modified" in error_msg:
            await callback.answer()
            return False
        elif "message to edit not found" in error_msg:
            logger.warning(f"⚠️ Сообщение для редактирования не найдено для пользователя {user_id or callback.from_user.id}")
            await callback.answer()
            return False
        else:
            logger.error(f"❌ Telegram API error for user {user_id or callback.from_user.id}: {e}")
            await callback.answer()
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error for user {user_id or callback.from_user.id}: {e}")
        await callback.answer()
        return False


async def safe_send_message(
    message: Message,
    text: str,
    reply_markup=None,
    user_id: int = None,
    parse_mode: Optional[str] = None
) -> bool:
    """
    Безопасно отправить сообщение с обработкой ошибок
    
    Returns:
        bool: True если сообщение было отправлено, False если ошибка
    """
    try:
        await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"❌ Telegram API error for user {user_id or message.from_user.id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error for user {user_id or message.from_user.id}: {e}")
        return False


def handle_telegram_errors(func):
    """
    Декоратор для автоматической обработки Telegram ошибок в обработчиках.
    Фильтрует лишние kwargs, которые Aiogram передаёт (например, 'dispatcher').
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Оставляем только те kwargs, которые ожидает целевая функция
            try:
                sig = inspect.signature(func)
                allowed = set(sig.parameters.keys())
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
            except Exception:
                filtered_kwargs = kwargs
            return await func(*args, **filtered_kwargs)
        except TelegramBadRequest as e:
            # Находим callback или message в аргументах
            callback = None
            message = None
            user_id = None
            
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg, 'answer'):
                    callback = arg
                    user_id = arg.from_user.id
                    break
                elif hasattr(arg, 'from_user') and hasattr(arg, 'reply'):
                    message = arg
                    user_id = arg.from_user.id
                    break
            
            error_msg = str(e).lower()
            
            if "message is not modified" in error_msg:
                if callback:
                    await callback.answer()
                return
            elif "message to edit not found" in error_msg:
                logger.warning(f"⚠️ Сообщение для редактирования не найдено для пользователя {user_id}")
                if callback:
                    await callback.answer()
                return
            else:
                logger.error(f"❌ Telegram API error for user {user_id}: {e}")
                if callback:
                    await callback.answer()
                return
        except Exception as e:
            logger.error(f"❌ Unexpected error in {func.__name__}: {e}")
            # Пытаемся найти callback для ответа
            for arg in args:
                if hasattr(arg, 'answer'):
                    try:
                        await arg.answer()
                    except:
                        pass
                    break
    
    return wrapper


def escape_markdown_v2(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2 Телеграма."""
    if not text:
        return ""
    specials = r"_[]()~`>#+-=|{}.!*"
    return re.sub(f"([{re.escape(specials)}])", r"\\\1", text)


def split_telegram_message(text: str, limit: int = 4000) -> List[str]:
    """Разбивает длинный текст на части, не превышающие limit символов."""
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    parts: List[str] = []
    buf: List[str] = []
    buf_len = 0

    for line in text.splitlines(keepends=True):
        if buf_len + len(line) > limit:
            parts.append("".join(buf))
            buf = [line]
            buf_len = len(line)
        else:
            buf.append(line)
            buf_len += len(line)

    if buf:
        parts.append("".join(buf))
    return parts