from typing import Dict, Any, Optional
from datetime import datetime


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