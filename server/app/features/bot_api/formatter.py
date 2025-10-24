"""
Форматирование сообщений для Telegram Bot API
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from app.utils.timezone import TimezoneUtils

logger = logging.getLogger(__name__)


class BotMessageFormatter:
    """Класс для форматирования сообщений Telegram"""
    
    def __init__(self, max_length: int = 4096):
        self.max_length = max_length
    
    def format_dashboard(self, data: Dict[str, Any]) -> str:
        """Форматирование dashboard сообщения"""
        try:
            cabinet_name = data.get("cabinet_name", "Неизвестный кабинет")
            last_sync = data.get("last_sync") or "Никогда"
            status = data.get("status", "Неизвестно")
            
            products = data.get("products", {})
            orders_today = data.get("orders_today", {})
            stocks = data.get("stocks", {})
            reviews = data.get("reviews", {})
            
            message = f"""🔄 Обновление: {last_sync}

🛒 ЗАКАЗЫ (сегодня)
• Новых заказов: {orders_today.get('count', 0)}
• На сумму: {orders_today.get('amount', 0):,.0f}₽
• Вчера: {orders_today.get('yesterday_count', 0)} заказов на {orders_today.get('yesterday_amount', 0):,.0f}₽
• Рост к вчера: {orders_today.get('growth_percent', 0):+.0f}% по количеству

📦 ОСТАТКИ
• Критичных товаров: {stocks.get('critical_count', 0)}
• С нулевыми остатками: {stocks.get('zero_count', 0)}
• Требуют внимания: {stocks.get('attention_needed', 0)}

⭐ ОТЗЫВЫ
• Средний рейтинг: {reviews.get('average_rating', 0):.1f}/5
• Неотвеченных: {reviews.get('unanswered', 0)}
• Всего отзывов: {reviews.get('total', 0)}

📦 ТОВАРЫ
• Всего товаров: {products.get('total', 0)}
• Активных: {products.get('active', 0)}"""
            
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
                    # Используем WB Order ID вместо внутреннего ID
                    wb_order_id = order.get('order_id', order.get('id', 'N/A'))
                    # Простое форматирование даты
                    order_date = self._format_datetime_simple(order.get("date", ""))
                    amount = order.get('amount', 0)
                    warehouse_from = order.get('warehouse_from', 'N/A')
                    warehouse_to = order.get('warehouse_to', 'N/A')
                    
                    message += f"""🧾 {wb_order_id}
   {order_date} | {amount:,.0f}₽
   {warehouse_from} → {warehouse_to}

"""
            
            message += "💡 Нажмите номер заказа для детального отчета"
            
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
                    
                    # Получаем новые поля
                    category = product.get('category', 'Неизвестно')
                    subject = product.get('subject', 'Неизвестно')
                    price = product.get('price', 0)
                    discount = product.get('discount', 0)
                    final_price = price - discount if price and discount else price
                    
                    message += f"""📦 {product.get('name', 'N/A')} ({product.get('brand', 'N/A')})
   🆔 {product.get('nm_id', 'N/A')}
   🏷️ Категория: {category} → {subject}
   💰 Цена: {price:,.0f}₽ {f"(-{discount:,.0f}₽ = {final_price:,.0f}₽)" if discount > 0 else ""}
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
                    user_name = review.get("user_name", "Аноним")
                    color = review.get("color", "")
                    pros = review.get("pros", "")
                    cons = review.get("cons", "")
                    
                    message += f"""{stars} | {rating}/5
   Пользователь: {user_name} {f"({color})" if color else ""}
   Плюсы: {pros if pros else "Не указаны"}
   Минусы: {cons if cons else "Не указаны"}

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
                ("За 30 дней", "30_days")
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
        """Форматирование уведомления о новом заказе в полном формате"""
        try:
            # Используем полный формат заказа
            return self.format_order_detail({"order": data})
            
        except Exception as e:
            logger.error(f"Ошибка форматирования уведомления о заказе: {e}")
            return "❌ Ошибка форматирования уведомления о заказе"

    def format_critical_stocks_notification(self, data: Dict[str, Any]) -> str:
        """Форматирование уведомления о критичных остатках"""
        try:
            products = data.get("products", [])
            
            message = "⚠️ КРИТИЧНЫЕ ОСТАТКИ\n\n"
            
            for product in products[:3]:  # Ограничиваем количество
                nm_id = product.get("nm_id", "N/A")
                # Надежный fallback для названия товара
                name = product.get("name") or product.get("product_name") or product.get("title") or f"Товар {nm_id}"
                stocks = product.get("stocks", {})
                critical_sizes = product.get("critical_sizes", [])
                zero_sizes = product.get("zero_sizes", [])
                days_left = product.get("days_left", {})
                
                stocks_str = self._format_stocks(stocks)
                
                message += f"""📦 {name}
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
        """Форматирование даты/времени с отображением по МСК."""
        try:
            if not datetime_str:
                return "N/A"
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            # Конвертируем в МСК
            msk_dt = TimezoneUtils.to_msk(dt)
            # Форматируем как ДД.ММ.ГГГГ ЧЧ:ММ
            return msk_dt.strftime("%d.%m.%Y %H:%M")
        except:
            return datetime_str
    
    def _format_datetime_simple(self, datetime_str: str) -> str:
        """Форматирование даты/времени с конвертацией в МСК."""
        try:
            if not datetime_str:
                return "N/A"
            
            # Если время уже в МСК формате (содержит +03:00), просто форматируем
            if '+03:00' in datetime_str:
                # Заменяем T на пробел и убираем секунды и timezone
                # 2025-10-24T11:02:25+03:00 -> 2025-10-24 11:02
                formatted = datetime_str.replace('T', ' ')
                # Убираем секунды и timezone (все после :MM)
                if ':' in formatted:
                    # Находим позицию второго двоеточия (секунды)
                    parts = formatted.split(':')
                    if len(parts) >= 2:
                        # Берем только дату и часы:минуты
                        date_part = parts[0]  # 2025-10-24 11
                        time_part = parts[1]  # 02
                        return f"{date_part}:{time_part}"
            
            # Fallback: полная конвертация для других форматов
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            msk_dt = TimezoneUtils.to_msk(dt)
            return msk_dt.strftime("%Y-%m-%d %H:%M")
        except:
            return datetime_str

    def _format_stocks(self, stocks: Dict[str, int]) -> str:
        """Форматирование остатков по размерам"""
        if not stocks:
            return "N/A"
        
        stock_parts = []
        # Получаем все размеры из данных
        for size, count in stocks.items():
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

    def format_order_detail(self, data: Dict[str, Any]) -> str:
        """Форматирование детального отчета заказа"""
        try:
            order = data.get("order", {})
            if not order:
                return "❌ Данные заказа не найдены"
            
            # Основная информация
            order_id = order.get("id", "N/A")
            wb_order_id = order.get("order_id", "N/A")
            order_date = self._format_datetime_simple(order.get("date", ""))
            status = order.get("status", "unknown")
            
            # Товар
            nm_id = order.get("nm_id", "N/A")
            product_name = order.get("product_name", "Неизвестно")
            article = order.get("article", "")
            size = order.get("size", "")
            barcode = order.get("barcode", "")
            
            # Финансы
            total_price = order.get("total_price", 0)
            spp_percent = order.get("spp_percent", 0)
            customer_price = order.get("customer_price", 0)
            discount_percent = order.get("discount_percent", 0)
            
            # Склады
            warehouse_from = order.get("warehouse_from", "")
            warehouse_to = order.get("warehouse_to", "")
            
            # Продажи
            sales_periods = order.get("sales_periods", {})
            
            # Статистика заказов
            orders_stats = order.get("orders_stats", {})
            
            # Рейтинги
            avg_rating = order.get("avg_rating", 0)
            reviews_count = order.get("reviews_count", 0)
            rating_distribution = order.get("rating_distribution", {})
            
            # Остатки
            stocks = order.get("stocks", {})
            
            # Определяем тип заказа по статусу
            status_map = {
                "active": "🧾ЗАКАЗ🧾",
                "buyout": "💰ВЫКУП💰", 
                "canceled": "↩️ОТМЕНА↩️",
                "return": "🔴ВОЗВРАТ🔴"
            }
            order_type = status_map.get(status, "🧾ЗАКАЗ🧾")
            
            # Форматируем дату и время (с конвертацией в МСК)
            formatted_datetime = self._format_datetime_simple(order_date)
            
            # Формируем сообщение в новом формате
            message = f"""{order_type}
🆔 {wb_order_id}
{formatted_datetime}

👗 {nm_id} / {article} / ({size})
🎹 {barcode}"""
            
            message += f"""

💰 Финансы:
Цена заказа: {total_price:,.1f}₽
СПП %: {spp_percent}%
Цена для покупателя: {customer_price:,.1f}₽
Скидка: {discount_percent}%"""
            
            if warehouse_from or warehouse_to:
                message += f"\n\n🚛 {warehouse_from} -> {warehouse_to}"
            
            # Выкупы в табличном формате
            if sales_periods:
                sales_7 = sales_periods.get('7_days', 0)
                sales_14 = sales_periods.get('14_days', 0)
                sales_30 = sales_periods.get('30_days', 0)
                message += f"""

📈 Выкупы за периоды:
7 | 14 | 30 дней:
{sales_7} | {sales_14} | {sales_30}"""
            
            # Статистика заказов
            if orders_stats:
                total_orders = orders_stats.get('total_orders', 0)
                active_orders = orders_stats.get('active_orders', 0)
                canceled_orders = orders_stats.get('canceled_orders', 0)
                buyout_orders = orders_stats.get('buyout_orders', 0)
                return_orders = orders_stats.get('return_orders', 0)
                
                message += f"""

🔍 Статистика по заказам:
Всего: {total_orders} заказов
Активные: {active_orders}
Отмененные: {canceled_orders}
Выкупы: {buyout_orders}
Возвраты: {return_orders}"""
            
            # Рейтинги и отзывы
            message += f"""

⭐ Рейтинг и отзывы:
Средний рейтинг: {avg_rating:.2f}
Всего отзывов: {reviews_count}"""
            
            # Распределение рейтингов в вертикальном формате (в процентах)
            if rating_distribution and reviews_count > 0:
                # Собираем данные по звездам (от 5 до 1)
                stars_5 = rating_distribution.get(5, 0)
                stars_4 = rating_distribution.get(4, 0)
                stars_3 = rating_distribution.get(3, 0)
                stars_2 = rating_distribution.get(2, 0)
                stars_1 = rating_distribution.get(1, 0)
                
                # Рассчитываем проценты
                pct_5 = (stars_5 / reviews_count) * 100
                pct_4 = (stars_4 / reviews_count) * 100
                pct_3 = (stars_3 / reviews_count) * 100
                pct_2 = (stars_2 / reviews_count) * 100
                pct_1 = (stars_1 / reviews_count) * 100
                
                message += f"""

5⭐ - {pct_5:.1f}%
4⭐ - {pct_4:.1f}%
3⭐ - {pct_3:.1f}%
2⭐ - {pct_2:.1f}%
1⭐ - {pct_1:.1f}%"""
            
            # Остатки
            if stocks:
                message += "\n\n📦 Остатки по размерам:"
                for size_key in sorted(stocks.keys()):
                    quantity = stocks[size_key]
                    message += f"\n{size_key}: {quantity} шт."
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования детального отчета заказа: {e}")
            return "❌ Ошибка форматирования детального отчета заказа"

    # ===== МЕТОДЫ ДЛЯ WB КАБИНЕТОВ =====

    def format_cabinet_status_message(self, cabinet_data: Dict[str, Any]) -> str:
        """Форматирование сообщения статуса кабинетов"""
        try:
            cabinets = cabinet_data.get("cabinets", [])
            if not cabinets:
                return "🔑 СТАТУС WB КАБИНЕТОВ\n\n❌ Нет подключенных кабинетов"
            
            message = "🔑 СТАТУС WB КАБИНЕТОВ\n\n"
            
            for i, cabinet in enumerate(cabinets, 1):
                name = cabinet.get('name', 'Неизвестный кабинет')
                status = cabinet.get('status', 'inactive')
                api_status = cabinet.get('api_key_status', 'invalid')
                connected_at = cabinet.get('connected_at')
                last_sync = cabinet.get('last_sync')
                
                # Статус кабинета
                status_emoji = "✅" if status == "active" else "❌"
                status_text = "Активен" if status == "active" else "Неактивен"
                
                # Статус API ключа
                api_emoji = "🔑" if api_status == "valid" else "⚠️"
                api_text = "Валидный" if api_status == "valid" else "Невалидный"
                
                message += f"🏢 {name}\n"
                message += f"• Статус: {status_emoji} {status_text}\n"
                message += f"• API ключ: {api_emoji} {api_text}\n"
                
                if connected_at:
                    try:
                        dt = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                        message += f"• Подключен: {dt.strftime('%d.%m.%Y %H:%M')}\n"
                    except:
                        message += f"• Подключен: {connected_at}\n"
                
                if last_sync:
                    try:
                        dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                        message += f"• Последняя синхронизация: {dt.strftime('%d.%m.%Y %H:%M')}\n"
                    except:
                        message += f"• Последняя синхронизация: {last_sync}\n"
                
                if i < len(cabinets):
                    message += "\n"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования статуса кабинетов: {e}")
            return "❌ Ошибка форматирования статуса кабинетов"

    def format_cabinet_connect_message(self, connect_data: Dict[str, Any]) -> str:
        """Форматирование сообщения успешного подключения кабинета"""
        try:
            cabinet_name = connect_data.get("cabinet_name", "Неизвестный кабинет")
            status = connect_data.get("status", "unknown")
            connected_at = connect_data.get("connected_at")
            api_key_status = connect_data.get("api_key_status", "unknown")
            
            if status != "connected":
                return "❌ ОШИБКА ПОДКЛЮЧЕНИЯ\n\n🔧 Не удалось подключить кабинет"
            
            # Форматируем время подключения
            connect_time = "только что"
            if connected_at:
                try:
                    dt = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                    connect_time = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    connect_time = connected_at
            
            message = f"""✅ КАБИНЕТ ПОДКЛЮЧЕН!

🏢 {cabinet_name}
🔑 API ключ: {'🔑 Валидный' if api_key_status == 'valid' else '⚠️ Невалидный'}
📅 Подключен: {connect_time}

🎉 Кабинет успешно подключен и готов к работе!
📊 Теперь вы можете получать данные о заказах, остатках и отзывах."""
            
            return message
            
        except Exception as e:
            logger.error(f"Ошибка форматирования подключения кабинета: {e}")
            return "✅ КАБИНЕТ ПОДКЛЮЧЕН!\n\n🎉 Кабинет успешно подключен!"

    def format_cabinet_connect_error_message(self, error_data: Dict[str, Any]) -> str:
        """Форматирование сообщения ошибки подключения кабинета"""
        try:
            error = error_data.get('error', 'Неизвестная ошибка')
            return f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ\n\n🔧 {error}"
        except Exception as e:
            logger.error(f"Ошибка форматирования ошибки подключения: {e}")
            return "❌ ОШИБКА ПОДКЛЮЧЕНИЯ\n\n🔧 Произошла ошибка"

    def format_cabinet_already_exists_message(self, error_data: Dict[str, Any]) -> str:
        """Форматирование сообщения о существующем кабинете"""
        try:
            return "⚠️ КАБИНЕТ УЖЕ ПОДКЛЮЧЕН\n\n🔑 У вас уже есть активный кабинет WB"
        except Exception as e:
            logger.error(f"Ошибка форматирования сообщения о существующем кабинете: {e}")
            return "⚠️ КАБИНЕТ УЖЕ ПОДКЛЮЧЕН"

    def _format_time_ago(self, dt: datetime) -> str:
        """Форматирование времени 'назад'"""
        try:
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt
            
            if diff.total_seconds() < 60:
                return f"{int(diff.total_seconds())} сек назад"
            elif diff.total_seconds() < 3600:
                return f"{int(diff.total_seconds() / 60)} мин назад"
            elif diff.total_seconds() < 86400:
                return f"{int(diff.total_seconds() / 3600)} ч назад"
            else:
                return f"{int(diff.total_seconds() / 86400)} дн назад"
        except Exception as e:
            logger.error(f"Ошибка форматирования времени: {e}")
            return "недавно"

    def _format_permissions(self, permissions: List[str]) -> str:
        """Форматирование списка прав доступа"""
        try:
            if not permissions:
                return "Нет прав доступа"
            
            permission_map = {
                "read_orders": "Чтение заказов",
                "read_stocks": "Чтение остатков", 
                "read_reviews": "Чтение отзывов",
                "read_products": "Чтение товаров",
                "read_analytics": "Чтение аналитики"
            }
            
            formatted = [permission_map.get(p, p) for p in permissions]
            return ", ".join(formatted)
        except Exception as e:
            logger.error(f"Ошибка форматирования прав: {e}")
            return "Нет прав доступа"

    def _format_api_key_status(self, status: str) -> str:
        """Форматирование статуса API ключа"""
        try:
            status_map = {
                "valid": "🔑 Валидный",
                "invalid": "⚠️ Невалидный",
                "expired": "⏰ Истек",
                "unknown": "❓ Неизвестен"
            }
            return status_map.get(status, "❓ Неизвестен")
        except Exception as e:
            logger.error(f"Ошибка форматирования статуса API ключа: {e}")
            return "❓ Неизвестен"

    def _format_cabinet_status(self, status: str) -> str:
        """Форматирование статуса кабинета"""
        try:
            status_map = {
                "active": "✅ Активен",
                "inactive": "❌ Неактивен",
                "suspended": "⏸️ Приостановлен",
                "unknown": "❓ Неизвестен"
            }
            return status_map.get(status, "❓ Неизвестен")
        except Exception as e:
            logger.error(f"Ошибка форматирования статуса кабинета: {e}")
            return "❓ Неизвестен"

    def format_orders_statistics(self, data: Dict[str, Any]) -> str:
        """Форматирование полной статистики по заказам"""
        try:
            orders = data.get("orders", {})
            sales = data.get("sales", {})
            summary = data.get("summary", {})
            
            message = "📊 ПОЛНАЯ СТАТИСТИКА ЗАКАЗОВ\n\n"
            
            # Статистика заказов
            message += "🛒 ЗАКАЗЫ:\n"
            message += f"• Всего заказов: {orders.get('total_orders', 0)}\n"
            message += f"• Активные: {orders.get('active_orders', 0)} ({orders.get('active_percentage', 0):.1f}%)\n"
            message += f"• Отмененные: {orders.get('canceled_orders', 0)} ({orders.get('canceled_percentage', 0):.1f}%)\n"
            message += f"• Без статуса: {orders.get('no_status_orders', 0)}\n\n"
            
            # Статистика продаж
            message += "💰 ПРОДАЖИ:\n"
            message += f"• Всего продаж: {sales.get('total_sales', 0)}\n"
            message += f"• Выкупы: {sales.get('buyouts', 0)} ({sales.get('buyout_rate', 0):.1f}%)\n"
            message += f"• Возвраты: {sales.get('returns', 0)}\n"
            message += f"• Общая сумма: {sales.get('total_amount', 0):,.0f}₽\n"
            message += f"• Сумма выкупов: {sales.get('buyouts_amount', 0):,.0f}₽\n"
            message += f"• Сумма возвратов: {sales.get('returns_amount', 0):,.0f}₽\n\n"
            
            # Сводка
            message += "📈 СВОДКА:\n"
            message += f"• Всего заказов: {summary.get('total_orders', 0)}\n"
            message += f"• Активных: {summary.get('active_orders', 0)}\n"
            message += f"• Отмененных: {summary.get('canceled_orders', 0)}\n"
            message += f"• Всего продаж: {summary.get('total_sales', 0)}\n"
            message += f"• Выкупов: {summary.get('buyouts', 0)}\n"
            message += f"• Возвратов: {summary.get('returns', 0)}\n"
            message += f"• Процент выкупа: {summary.get('buyout_rate', 0):.1f}%\n"
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования статистики заказов: {e}")
            return "❌ Ошибка форматирования статистики заказов"

    def format_cabinet_removal_notification(self, data: Dict[str, Any]) -> str:
        """Форматирование уведомления об удалении кабинета"""
        try:
            cabinet_name = data.get("cabinet_name", "Неизвестный кабинет")
            validation_error = data.get("validation_error", {})
            removal_reason = data.get("removal_reason", "API ключ недействителен")
            
            message = f"""🚨 КАБИНЕТ УДАЛЕН

🏢 Кабинет: {cabinet_name}
❌ Причина: {removal_reason}

📋 Детали ошибки:
• Статус: {validation_error.get('status_code', 'N/A')}
• Сообщение: {validation_error.get('message', 'N/A')}
• Код ошибки: {validation_error.get('error_code', 'N/A')}

⚠️ Кабинет был автоматически удален из-за недействительного API ключа.
Все данные кабинета (заказы, товары, остатки, отзывы, продажи) были удалены.

💡 Для продолжения работы добавьте новый API ключ через команду /connect"""
            
            return self._truncate_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования уведомления об удалении кабинета: {e}")
            return "❌ Ошибка форматирования уведомления об удалении кабинета"