"""
Форматирование сводок для Telegram
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pytz


class DigestFormatter:
    """Форматирование ежедневных сводок для Telegram"""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Форматировать валюту"""
        return f"{amount:,.0f}₽".replace(",", " ")
    
    @staticmethod
    def format_date(date_str: str) -> str:
        """Форматировать дату"""
        try:
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.strftime("%d.%m.%Y")
        except:
            return date_str
    
    @staticmethod
    def format_daily_digest(data: Dict[str, Any], timezone: str = "Europe/Moscow") -> str:
        """
        Форматирование ежедневной сводки
        
        Args:
            data: Данные от DigestService.get_daily_digest()
        
        Returns:
            Отформатированное сообщение для Telegram
        """
        cabinet_name = data.get("cabinet_name", "Неизвестный кабинет")
        date_str = DigestFormatter.format_date(data.get("date", ""))
        
        orders = data.get("orders", {})
        sales = data.get("sales", {})
        reviews = data.get("reviews", {})
        
        # Получаем текущее время в timezone пользователя
        try:
            user_tz = pytz.timezone(timezone)
            current_utc = datetime.now(pytz.UTC)
            current_local = current_utc.astimezone(user_tz)
            time_str = current_local.strftime('%H:%M')
            # Время 24 часа назад
            yesterday_local = (current_utc - timedelta(hours=24)).astimezone(user_tz)
            yesterday_time_str = yesterday_local.strftime('%H:%M')
        except:
            # Fallback на UTC если timezone некорректный
            time_str = datetime.utcnow().strftime('%H:%M')
            yesterday_time_str = (datetime.utcnow() - timedelta(hours=24)).strftime('%H:%M')
        
        # Формируем сообщение
        message = f"""📊 Сводка за 24 часа WB
🏢 {cabinet_name}
📅 {date_str}
⏰ Период: {yesterday_time_str} - {time_str}

━━━━━━━━━━━━━━━━━━━━━━━━

🛒 ЗАКАЗЫ
• Новых заказов: {orders.get('count', 0)}
• На сумму: {DigestFormatter.format_currency(orders.get('amount', 0))}
• Динамика: {orders.get('growth_percent', 0):+.1f}% к предыдущим 24ч

💰 ПРОДАЖИ
• Выкупов: {sales.get('buyouts_count', 0)} ({DigestFormatter.format_currency(sales.get('buyouts_amount', 0))})
• Возвратов: {sales.get('returns_count', 0)} ({DigestFormatter.format_currency(sales.get('returns_amount', 0))})
• Коэффициент выкупа: {sales.get('buyout_rate', 0):.1f}%

⭐ ОТЗЫВЫ
• Новых отзывов: {reviews.get('new_count', 0)}
• Средний рейтинг: {reviews.get('average_rating', 0):.1f}/5 ⭐
• Негативных (1-3★): {reviews.get('negative_count', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━
🕐 Обновлено: {time_str}
🤖 WB Assist Bot"""
        
        return message

