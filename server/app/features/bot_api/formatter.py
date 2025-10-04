"""
Форматирование сообщений для Telegram Bot API
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BotMessageFormatter:
    """Класс для форматирования сообщений Telegram"""
    
    def __init__(self, max_length: int = 4096):
        self.max_length = max_length
    
    def format_dashboard(self, data: Dict[str, Any]) -> str:
        """Форматирование dashboard сообщения"""
        try:
            cabinet_name = data.get("cabinet_name", "Неизвестный кабинет")
            last_sync = data.get("last_sync", "Неизвестно")
            status = data.get("status", "Неизвестно")
            
            products = data.get("products", {})
            orders_today = data.get("orders_today", {})
            stocks = data.get("stocks", {})
            reviews = data.get("reviews", {})
            recommendations = data.get("recommendations", [])
            
            message = f"""📊 ВАШ КАБИНЕТ WB

🏢 {cabinet_name}
🔄 Последняя синхронизация: {last_sync}
📈 Статус: ✅ {status}

📦 ТОВАРЫ
• Всего товаров: {products.get('total', 0)}
• Активных: {products.get('active', 0)}
• На модерации: {products.get('moderation', 0)}
• Критичных остатков: {products.get('critical_stocks', 0)}

🛒 ЗАКАЗЫ (сегодня)
• Новых заказов: {orders_today.get('count', 0)}
• На сумму: {orders_today.get('amount', 0):,.0f}₽
• Вчера: {orders_today.get('yesterday_count', 0)} заказов на {orders_today.get('yesterday_amount', 0):,.0f}₽
• Рост к вчера: {orders_today.get('growth_percent', 0):+.0f}% по количеству

📦 ОСТАТКИ
• Критичных товаров: {stocks.get('critical_count', 0)}
• С нулевыми остатками: {stocks.get('zero_count', 0)}
• Требуют внимания: {stocks.get('attention_needed', 0)}
• Топ товар: {stocks.get('top_product', 'Нет данных')}

⭐ ОТЗЫВЫ
• Новых отзывов: {reviews.get('new_count', 0)}
• Средний рейтинг: {reviews.get('average_rating', 0):.1f}/5
• Неотвеченных: {reviews.get('unanswered', 0)}
• Всего отзывов: {reviews.get('total', 0)}"""

            if recommendations:
                message += "\n\n💡 РЕКОМЕНДАЦИИ"
                for rec in recommendations[:5]:  # Ограничиваем количество рекомендаций
                    message += f"\n• {rec}"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования dashboard: {e}")
            return "❌ Ошибка форматирования данных dashboard"

    def format_orders(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения о заказах"""
        try:
            orders = data.get("orders", [])
            statistics = data.get("statistics", {})
            pagination = data.get("pagination", {})
            
            message = "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ\n\n"
            
            if not orders:
                message += "Заказов не найдено"
            else:
                for order in orders[:10]:  # Ограничиваем количество заказов
                    order_date = self._format_datetime(order.get("date", ""))
                    message += f"""🧾 #{order.get('id', 'N/A')} | {order_date} | {order.get('amount', 0):,.0f}₽
   {order.get('product_name', 'N/A')} | {order.get('brand', 'N/A')}
   {order.get('warehouse_from', 'N/A')} → {order.get('warehouse_to', 'N/A')}
   Комиссия: {order.get('commission_percent', 0):.1f}% | Рейтинг: {order.get('rating', 0):.1f}⭐

"""
            
            message += f"""📊 СТАТИСТИКА ЗА СЕГОДНЯ
• Всего заказов: {statistics.get('today_count', 0)}
• Общая сумма: {statistics.get('today_amount', 0):,.0f}₽
• Средний чек: {statistics.get('average_check', 0):,.0f}₽
• Рост к вчера: {statistics.get('growth_percent', 0):+.0f}% по количеству, {statistics.get('amount_growth_percent', 0):+.0f}% по сумме

💡 Нажмите номер заказа для детального отчета"""
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования заказов: {e}")
            return "❌ Ошибка форматирования данных заказов"

    def format_critical_stocks(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения о критичных остатках"""
        try:
            critical_products = data.get("critical_products", [])
            zero_products = data.get("zero_products", [])
            summary = data.get("summary", {})
            recommendations = data.get("recommendations", [])
            
            message = "📦 КРИТИЧНЫЕ ОСТАТКИ\n\n"
            
            if critical_products:
                message += "⚠️ КРИТИЧНО (остаток < 5 шт):\n"
                for product in critical_products[:5]:  # Ограничиваем количество
                    stocks_str = self._format_stocks(product.get("stocks", {}))
                    critical_sizes = product.get("critical_sizes", [])
                    zero_sizes = product.get("zero_sizes", [])
                    days_left = product.get("days_left", {})
                    
                    message += f"""📦 {product.get('name', 'N/A')} ({product.get('brand', 'N/A')})
   🆔 {product.get('nm_id', 'N/A')}
   📊 Остатки: {stocks_str}
"""
                    if critical_sizes:
                        critical_info = []
                        for size in critical_sizes:
                            days = days_left.get(size, 0)
                            critical_info.append(f"{size}({product.get('stocks', {}).get(size, 0)}) - осталось на {days} дней!")
                        message += f"   ⚠️ {' '.join(critical_info)}\n"
                    
                    message += f"""   📈 Продажи: {product.get('sales_per_day', 0):.1f} шт/день (7дн)
   💰 Цена: {product.get('price', 0):,.0f}₽ | Комиссия: {product.get('commission_percent', 0):.1f}%

"""
            
            if zero_products:
                message += "🔴 НУЛЕВЫЕ ОСТАТКИ:\n"
                for product in zero_products[:3]:  # Ограничиваем количество
                    stocks_str = self._format_stocks(product.get("stocks", {}))
                    message += f"""📦 {product.get('name', 'N/A')} ({product.get('brand', 'N/A')})
   🆔 {product.get('nm_id', 'N/A')}
   📊 Остатки: {stocks_str}
   🔴 Все размеры = 0!
   📈 Продажи: {product.get('sales_per_day', 0):.1f} шт/день (7дн)
   💰 Цена: {product.get('price', 0):,.0f}₽ | Комиссия: {product.get('commission_percent', 0):.1f}%

"""
            
            message += f"""📊 СВОДКА
• Критичных товаров: {summary.get('critical_count', 0)}
• С нулевыми остатками: {summary.get('zero_count', 0)}
• Требуют срочного пополнения: {summary.get('attention_needed', 0)}
• Потенциальные потери: {summary.get('potential_losses', 0):.1f} шт/день

💡 РЕКОМЕНДАЦИИ"""
            
            for rec in recommendations[:3]:  # Ограничиваем количество рекомендаций
                message += f"\n• {rec}"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования критичных остатков: {e}")
            return "❌ Ошибка форматирования данных остатков"

    def format_reviews(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения об отзывах"""
        try:
            new_reviews = data.get("new_reviews", [])
            unanswered_questions = data.get("unanswered_questions", [])
            statistics = data.get("statistics", {})
            recommendations = data.get("recommendations", [])
            
            message = "⭐ ОТЗЫВЫ И ВОПРОСЫ\n\n"
            
            if new_reviews:
                message += f"🆕 НОВЫЕ ОТЗЫВЫ ({len(new_reviews)}):\n"
                for review in new_reviews[:5]:  # Ограничиваем количество
                    rating = review.get("rating", 0)
                    stars = "⭐" * rating
                    message += f"""{stars} {review.get('product_name', 'N/A')} | {rating}/5
   "{review.get('text', 'N/A')}"
   Время: {review.get('time_ago', 'N/A')} | ID: #{review.get('order_id', 'N/A')}

"""
            
            if unanswered_questions:
                message += f"❓ НЕОТВЕЧЕННЫЕ ВОПРОСЫ ({len(unanswered_questions)}):\n"
                for question in unanswered_questions[:3]:  # Ограничиваем количество
                    message += f"""• "{question.get('text', 'N/A')}" - {question.get('product_name', 'N/A')}
  Время: {question.get('time_ago', 'N/A')} | Требует ответа

"""
            
            message += f"""📊 СТАТИСТИКА
• Средний рейтинг: {statistics.get('average_rating', 0):.1f}/5
• Всего отзывов: {statistics.get('total_reviews', 0)}
• Отвечено: {statistics.get('answered_count', 0)} ({statistics.get('answered_percent', 0):.0f}%)
• Требуют внимания: {statistics.get('attention_needed', 0)} (низкий рейтинг)
• Новых за день: {statistics.get('new_today', 0)}

💡 РЕКОМЕНДАЦИИ"""
            
            for rec in recommendations[:3]:  # Ограничиваем количество рекомендаций
                message += f"\n• {rec}"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования отзывов: {e}")
            return "❌ Ошибка форматирования данных отзывов"

    def format_analytics(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения об аналитике"""
        try:
            sales_periods = data.get("sales_periods", {})
            dynamics = data.get("dynamics", {})
            top_products = data.get("top_products", [])
            stocks_summary = data.get("stocks_summary", {})
            recommendations = data.get("recommendations", [])
            
            message = "📈 АНАЛИТИКА ПРОДАЖ\n\n"
            
            # Продажи по периодам
            message += "📊 ПРОДАЖИ ПО ПЕРИОДАМ\n"
            for period_name, period_key in [
                ("Сегодня", "today"),
                ("Вчера", "yesterday"),
                ("За 7 дней", "7_days"),
                ("За 30 дней", "30_days"),
                ("За 90 дней", "90_days")
            ]:
                period_data = sales_periods.get(period_key, {})
                count = period_data.get("count", 0)
                amount = period_data.get("amount", 0)
                message += f"• {period_name}: {count} заказов на {amount:,.0f}₽\n"
            
            # Динамика
            message += f"""\n📈 ДИНАМИКА
• Рост к вчера: {dynamics.get('yesterday_growth_percent', 0):+.0f}% по заказам, {dynamics.get('yesterday_growth_percent', 0):+.0f}% по сумме
• Рост к прошлой неделе: {dynamics.get('week_growth_percent', 0):+.0f}% по заказам
• Средний чек: {dynamics.get('average_check', 0):,.0f}₽ (стабильно)
• Конверсия: {dynamics.get('conversion_percent', 0):.1f}% (норма)

🏆 ТОП ТОВАРОВ (7 дней)"""
            
            for i, product in enumerate(top_products[:3], 1):  # Ограничиваем количество
                stocks_str = self._format_stocks(product.get("stocks", {}))
                message += f"""\n{i}. {product.get('name', 'N/A')} - {product.get('sales_count', 0)} шт. ({product.get('sales_amount', 0):,.0f}₽)
   Рейтинг: {product.get('rating', 0):.1f}⭐ | Остаток: {stocks_str}"""
            
            # Остатки
            message += f"""

📦 ОСТАТКИ
• Критичных товаров: {stocks_summary.get('critical_count', 0)}
• С нулевыми остатками: {stocks_summary.get('zero_count', 0)}
• Требуют пополнения: {stocks_summary.get('attention_needed', 0)}
• Общий остаток: {stocks_summary.get('total_products', 0)} товаров

💡 РЕКОМЕНДАЦИИ"""
            
            for rec in recommendations[:4]:  # Ограничиваем количество рекомендаций
                message += f"\n• {rec}"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования аналитики: {e}")
            return "❌ Ошибка форматирования данных аналитики"

    def format_sync_status(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения о статусе синхронизации"""
        try:
            last_sync = data.get("last_sync", "Неизвестно")
            status = data.get("status", "Неизвестно")
            duration = data.get("duration_seconds", 0)
            cabinets_processed = data.get("cabinets_processed", 0)
            updates = data.get("updates", {})
            next_sync = data.get("next_sync", "Неизвестно")
            sync_mode = data.get("sync_mode", "Неизвестно")
            interval = data.get("interval_seconds", 0)
            statistics = data.get("statistics", {})
            
            message = f"""🔄 СИНХРОНИЗАЦИЯ ДАННЫХ

✅ ПОСЛЕДНЯЯ СИНХРОНИЗАЦИЯ
• Время: {last_sync}
• Статус: {"Успешно завершена" if status == "completed" else status}
• Длительность: {duration} секунд
• Обработано кабинетов: {cabinets_processed}

📊 ОБНОВЛЕНО
• Заказы: +{updates.get('orders', {}).get('new', 0)} новых (всего {updates.get('orders', {}).get('total_today', 0)} за день)
• Остатки: {updates.get('stocks', {}).get('updated', 0)} товаров обновлено
• Отзывы: +{updates.get('reviews', {}).get('new', 0)} новых (всего {updates.get('reviews', {}).get('total_today', 0)} за день)
• Товары: {updates.get('products', {}).get('changed', 0)} изменений
• Аналитика: {"пересчитана" if updates.get('analytics', {}).get('recalculated') else "не обновлялась"}

⏰ СЛЕДУЮЩАЯ СИНХРОНИЗАЦИЯ
• Через: {self._calculate_time_until_next_sync(next_sync)}
• Режим: {"Автоматический" if sync_mode == "automatic" else sync_mode}
• Интервал: каждую минуту

🔄 РУЧНАЯ СИНХРОНИЗАЦИЯ
• Нажмите /sync для принудительного обновления
• Обычно занимает 30-60 секунд
• Обновит все данные из WB API

📈 СТАТИСТИКА СИНХРОНИЗАЦИИ
• Успешных за день: {statistics.get('successful_today', 0)}
• Ошибок за день: {statistics.get('errors_today', 0)}
• Среднее время: {statistics.get('average_duration', 0):.0f} секунд
• Последняя ошибка: {statistics.get('last_error', 'нет')}"""
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования статуса синхронизации: {e}")
            return "❌ Ошибка форматирования данных синхронизации"

    def format_new_order_notification(self, data: Dict[str, Any]) -> str:
        """Форматирование уведомления о новом заказе"""
        try:
            order_id = data.get("order_id", "N/A")
            order_date = self._format_datetime(data.get("date", ""))
            amount = data.get("amount", 0)
            product_name = data.get("product_name", "N/A")
            brand = data.get("brand", "N/A")
            warehouse_from = data.get("warehouse_from", "N/A")
            warehouse_to = data.get("warehouse_to", "N/A")
            today_stats = data.get("today_stats", {})
            stocks = data.get("stocks", {})
            
            stocks_str = self._format_stocks(stocks)
            
            message = f"""🎉 НОВЫЙ ЗАКАЗ!

🧾 #{order_id} | {order_date} | {amount:,.0f}₽
👑 {brand}
✏ {product_name}
🚛 {warehouse_from} → {warehouse_to}

📊 Сегодня: {today_stats.get('count', 0)} заказов на {today_stats.get('amount', 0):,.0f}₽
📦 Остаток: {stocks_str}

💡 Нажмите /order_{order_id} для полного отчета"""
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования уведомления о заказе: {e}")
            return "❌ Ошибка форматирования уведомления о заказе"

    def format_critical_stocks_notification(self, data: Dict[str, Any]) -> str:
        """Форматирование уведомления о критичных остатках"""
        try:
            products = data.get("products", [])
            
            message = "⚠️ КРИТИЧНЫЕ ОСТАТКИ!\n\n"
            
            for product in products[:3]:  # Ограничиваем количество
                nm_id = product.get("nm_id", "N/A")
                name = product.get("name", "N/A")
                brand = product.get("brand", "N/A")
                stocks = product.get("stocks", {})
                critical_sizes = product.get("critical_sizes", [])
                zero_sizes = product.get("zero_sizes", [])
                days_left = product.get("days_left", {})
                
                stocks_str = self._format_stocks(stocks)
                
                message += f"""📦 {name} ({brand})
🆔 {nm_id}
📊 Остатки: {stocks_str}

"""
                
                if critical_sizes:
                    critical_info = []
                    for size in critical_sizes:
                        days = days_left.get(size, 0)
                        critical_info.append(f"{size}({stocks.get(size, 0)}) - на {days} дней!")
                    message += f"⚠️ Критично: {' '.join(critical_info)}\n"
                
                if zero_sizes:
                    message += f"🔴 Нулевые: {', '.join(zero_sizes)} на всех складах\n"
                
                message += "\n"
            
            message += "💡 Нажмите /stocks для подробного отчета"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования уведомления об остатках: {e}")
            return "❌ Ошибка форматирования уведомления об остатках"

    def format_error(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения об ошибке"""
        try:
            error_type = data.get("error_type", "unknown")
            message = data.get("message", "Произошла неизвестная ошибка")
            fallback_data = data.get("fallback_data", False)
            
            if error_type == "wb_api_unavailable":
                error_msg = "❌ ОШИБКА\n\nWB API временно недоступен"
                if fallback_data:
                    error_msg += "\n\nПоказаны кэшированные данные"
            elif error_type == "database_error":
                error_msg = "❌ ОШИБКА\n\nОшибка базы данных"
            else:
                error_msg = f"❌ ОШИБКА\n\n{message}"
            
            return self._truncate_message(error_msg)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования сообщения об ошибке: {e}")
            return "❌ Ошибка сервера"

    def _format_datetime(self, datetime_str: str) -> str:
        """Форматирование даты и времени"""
        try:
            if not datetime_str:
                return "N/A"
            
            # Пытаемся распарсить ISO формат
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except:
            return datetime_str

    def _format_stocks(self, stocks: Dict[str, int]) -> str:
        """Форматирование остатков по размерам"""
        if not stocks:
            return "N/A"
        
        stock_parts = []
        for size in ["S", "M", "L", "XL"]:
            count = stocks.get(size, 0)
            stock_parts.append(f"{size}({count})")
        
        return " ".join(stock_parts)

    def _calculate_time_until_next_sync(self, next_sync: str) -> str:
        """Расчет времени до следующей синхронизации"""
        try:
            if not next_sync or next_sync == "Неизвестно":
                return "Неизвестно"
            
            next_dt = datetime.fromisoformat(next_sync.replace('Z', '+00:00'))
            now = datetime.now(next_dt.tzinfo)
            diff = next_dt - now
            
            if diff.total_seconds() <= 0:
                return "Сейчас"
            elif diff.total_seconds() < 60:
                return f"{int(diff.total_seconds())} секунд"
            else:
                return f"{int(diff.total_seconds() / 60)} минут"
        except:
            return next_sync

    def _truncate_message(self, message: str) -> str:
        """Обрезка сообщения до максимальной длины"""
        if len(message) <= self.max_length:
            return message
        
        # Обрезаем до максимальной длины с учетом многоточия
        truncated = message[:self.max_length - 3]
        
        # Пытаемся обрезать по последнему переносу строки
        last_newline = truncated.rfind('\n')
        if last_newline > self.max_length * 0.8:  # Если последний перенос не слишком далеко
            truncated = truncated[:last_newline]
        
        return truncated + "..."