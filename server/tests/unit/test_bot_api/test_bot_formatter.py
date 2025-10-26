"""
Unit тесты для форматирования сообщений Bot API
"""

import pytest
from datetime import datetime, timezone
from app.features.bot_api.formatter import BotMessageFormatter


class TestBotMessageFormatter:
    """Тесты для форматирования сообщений Telegram"""

    @pytest.fixture
    def formatter(self):
        """Фикстура для форматтера сообщений"""
        return BotMessageFormatter()

    def test_format_dashboard_message(self, formatter):
        """Тест форматирования dashboard сообщения"""
        dashboard_data = {
            "cabinet_name": "SLAVALOOK BRAND",
            "last_sync": "2 мин назад",
            "status": "Активен",
            "products": {
                "total": 45,
                "active": 42,
                "moderation": 3,
                "critical_stocks": 3
            },
            "orders_today": {
                "count": 19,
                "amount": 26790,
                "yesterday_count": 24,
                "yesterday_amount": 33840,
                "growth_percent": 12
            },
            "stocks": {
                "critical_count": 3,
                "zero_count": 1,
                "attention_needed": 2,
                "top_product": "Шифоновая блузка (73 шт/7дн)"
            },
            "reviews": {
                "new_count": 5,
                "average_rating": 4.8,
                "unanswered": 2,
                "total": 214
            },
            "recommendations": [
                "Пополнить остатки M, L, XL размеров",
                "Ответить на 2 отзыва",
                "Проверить товары на модерации"
            ]
        }
        
        result = formatter.format_dashboard(dashboard_data)
        
        assert "📊 ВАШ КАБИНЕТ WB" in result
        assert "SLAVALOOK BRAND" in result
        assert "Последняя синхронизация: 2 мин назад" in result
        assert "Всего товаров: 45" in result
        assert "Новых заказов: 19" in result
        assert "На сумму: 26 790₽" in result
        assert "Критичных товаров: 3" in result
        assert "Новых отзывов: 5" in result
        assert "Средний рейтинг: 4.8/5" in result

    def test_format_orders_message(self, formatter):
        """Тест форматирования сообщения о заказах"""
        orders_data = {
            "orders": [
                {
                    "id": 154,
                    "date": "2025-10-03T12:48:00",
                    "amount": 1410,
                    "product_name": "Шифоновая блузка (S)",
                    "brand": "SLAVALOOK BRAND",
                    "warehouse_from": "Электросталь",
                    "warehouse_to": "ЦФО/Москва",
                    "commission_percent": 29.5,
                    "rating": 4.8
                }
            ],
            "statistics": {
                "today_count": 19,
                "today_amount": 26790,
                "average_check": 1410,
                "growth_percent": 12,
                "amount_growth_percent": 8
            },
            "pagination": {
                "limit": 10,
                "offset": 0,
                "total": 19,
                "has_more": False
            }
        }
        
        result = formatter.format_orders(orders_data)
        
        assert "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ" in result
        assert "#154 | 12:48 | 1 410₽" in result
        assert "Шифоновая блузка (S)" in result
        assert "SLAVALOOK BRAND" in result
        assert "Электросталь -> ЦФО/Москва" in result
        assert "Комиссия: 29.5%" in result
        assert "Рейтинг: 4.8⭐" in result
        assert "Всего заказов: 19" in result
        assert "Общая сумма: 26 790₽" in result

    def test_format_critical_stocks_message(self, formatter):
        """Тест форматирования сообщения о критичных остатках"""
        stocks_data = {
            "critical_products": [
                {
                    "nm_id": 270591287,
                    "name": "Шифоновая блузка",
                    "brand": "SLAVALOOK BRAND",
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0},
                    "critical_sizes": ["M"],
                    "zero_sizes": ["L", "XL"],
                    "sales_per_day": 29.29,
                    "price": 1410,
                    "commission_percent": 29.5,
                    "days_left": {"M": 0, "S": 1}
                }
            ],
            "zero_products": [
                {
                    "nm_id": 270591289,
                    "name": "Платье вечернее",
                    "brand": "ELEGANCE",
                    "stocks": {"S": 0, "M": 0, "L": 0, "XL": 0},
                    "sales_per_day": 8.2,
                    "price": 2340,
                    "commission_percent": 32.0
                }
            ],
            "summary": {
                "critical_count": 2,
                "zero_count": 1,
                "attention_needed": 3,
                "potential_losses": 52.7
            },
            "recommendations": [
                "Срочно пополнить M, L, XL размеры",
                "Заказать товары с нулевыми остатками"
            ]
        }
        
        result = formatter.format_critical_stocks(stocks_data)
        
        assert "📦 КРИТИЧНЫЕ ОСТАТКИ" in result
        assert "⚠️ КРИТИЧНО" in result
        assert "Шифоновая блузка" in result
        assert "SLAVALOOK BRAND" in result
        assert "Остатки: S(13) M(1) L(0) XL(0)" in result
        assert "M(1) - осталось на 0 дней!" in result
        assert "🔴 НУЛЕВЫЕ ОСТАТКИ" in result
        assert "Платье вечернее" in result
        assert "Все размеры = 0!" in result
        assert "Критичных товаров: 2" in result
        assert "С нулевыми остатками: 1" in result

    def test_format_reviews_message(self, formatter):
        """Тест форматирования сообщения об отзывах"""
        reviews_data = {
            "new_reviews": [
                {
                    "id": "154",
                    "product_name": "Шифоновая блузка",
                    "rating": 5,
                    "text": "Отличное качество, быстро доставили!",
                    "time_ago": "2 часа назад",
                    "order_id": 154
                }
            ],
            "unanswered_questions": [
                {
                    "id": "q1",
                    "product_name": "Джинсы классические",
                    "text": "Какой размер выбрать?",
                    "time_ago": "3 часа назад"
                }
            ],
            "statistics": {
                "average_rating": 4.8,
                "total_reviews": 214,
                "answered_count": 212,
                "answered_percent": 99,
                "attention_needed": 1,
                "new_today": 5
            },
            "recommendations": [
                "Ответить на отзыв с рейтингом 2⭐",
                "Ответить на 2 неотвеченных вопроса"
            ]
        }
        
        result = formatter.format_reviews(reviews_data)
        
        assert "⭐ ОТЗЫВЫ И ВОПРОСЫ" in result
        assert "🆕 НОВЫЕ ОТЗЫВЫ (1):" in result
        assert "⭐⭐⭐⭐⭐ Шифоновая блузка | 5/5" in result
        assert "Отличное качество, быстро доставили!" in result
        assert "❓ НЕОТВЕЧЕННЫЕ ВОПРОСЫ (1):" in result
        assert "Какой размер выбрать?" in result
        assert "Средний рейтинг: 4.8/5" in result
        assert "Всего отзывов: 214" in result
        assert "Отвечено: 212 (99%)" in result

    def test_format_analytics_message(self, formatter):
        """Тест форматирования сообщения об аналитике"""
        analytics_data = {
            "sales_periods": {
                "today": {"count": 19, "amount": 26790},
                "yesterday": {"count": 24, "amount": 33840},
                "7_days": {"count": 156, "amount": 234500},
                "30_days": {"count": 541, "amount": 892300},
                "90_days": {"count": 686, "amount": 1156800}
            },
            "dynamics": {
                "yesterday_growth_percent": -21,
                "week_growth_percent": 12,
                "average_check": 1410,
                "conversion_percent": 3.2
            },
            "top_products": [
                {
                    "nm_id": 270591287,
                    "name": "Шифоновая блузка",
                    "sales_count": 73,
                    "sales_amount": 46800,
                    "rating": 4.8,
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0}
                }
            ],
            "stocks_summary": {
                "critical_count": 3,
                "zero_count": 1,
                "attention_needed": 2,
                "total_products": 45
            },
            "recommendations": [
                "Пополнить остатки топ-товаров",
                "Проанализировать падение продаж"
            ]
        }
        
        result = formatter.format_analytics(analytics_data)
        
        assert "📈 АНАЛИТИКА ПРОДАЖ" in result
        assert "Сегодня: 19 заказов на 26 790₽" in result
        assert "Вчера: 24 заказов на 33 840₽" in result
        assert "За 7 дней: 156 заказов на 234 500₽" in result
        assert "Рост к вчера: -21% по заказам" in result
        assert "Средний чек: 1 410₽" in result
        assert "Конверсия: 3.2%" in result
        assert "🏆 ТОП ТОВАРОВ" in result
        assert "Шифоновая блузка - 73 шт. (46 800₽)" in result

    def test_format_sync_status_message(self, formatter):
        """Тест форматирования сообщения о статусе синхронизации"""
        sync_data = {
            "last_sync": "2025-01-28T14:30:15",
            "status": "completed",
            "duration_seconds": 45,
            "cabinets_processed": 1,
            "updates": {
                "orders": {"new": 3, "total_today": 19},
                "stocks": {"updated": 12},
                "reviews": {"new": 2, "total_today": 5},
                "products": {"changed": 0},
                "analytics": {"recalculated": True}
            },
            "next_sync": "2025-01-28T14:31:00",
            "sync_mode": "automatic",
            "interval_seconds": 60,
            "statistics": {
                "successful_today": 1440,
                "errors_today": 0,
                "average_duration": 42,
                "last_error": None
            }
        }
        
        result = formatter.format_sync_status(sync_data)
        
        assert "🔄 СИНХРОНИЗАЦИЯ ДАННЫХ" in result
        assert "✅ ПОСЛЕДНЯЯ СИНХРОНИЗАЦИЯ" in result
        assert "Время: 2025-01-28T14:30:15" in result
        assert "Статус: Успешно завершена" in result
        assert "Длительность: 45 секунд" in result
        assert "Обработано кабинетов: 1" in result
        assert "Заказы: +3 новых (всего 19 за день)" in result
        assert "Остатки: 12 товаров обновлено" in result
        assert "Отзывы: +2 новых (всего 5 за день)" in result

    def test_format_new_order_notification(self, formatter):
        """Тест форматирования уведомления о новом заказе"""
        order_data = {
            "order_id": 154,
            "date": "2025-10-03T12:48:00",
            "amount": 1410,
            "product_name": "Шифоновая блузка (S)",
            "brand": "SLAVALOOK BRAND",
            "warehouse_from": "Электросталь",
            "warehouse_to": "ЦФО/Москва",
            "today_stats": {
                "count": 19,
                "amount": 26790
            },
            "stocks": {
                "S": 13,
                "M": 1,
                "L": 0,
                "XL": 0
            }
        }
        
        result = formatter.format_new_order_notification(order_data)
        
        assert "🎉 НОВЫЙ ЗАКАЗ!" in result
        assert "#154 | 12:48 | 1 410₽" in result
        assert "SLAVALOOK BRAND" in result
        assert "Шифоновая блузка (S)" in result
        assert "Электросталь -> ЦФО/Москва" in result
        assert "Сегодня: 19 заказов на 26 790₽" in result
        assert "Остаток: S(13) M(1) L(0) XL(0)" in result

    def test_format_critical_stocks_notification(self, formatter):
        """Тест форматирования уведомления о критичных остатках"""
        stocks_data = {
            "products": [
                {
                    "nm_id": 270591287,
                    "name": "Шифоновая блузка",
                    "brand": "SLAVALOOK BRAND",
                    "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0},
                    "critical_sizes": ["M"],
                    "zero_sizes": ["L", "XL"],
                    "days_left": {"M": 0}
                }
            ]
        }
        
        result = formatter.format_critical_stocks_notification(stocks_data)
        
        assert "⚠️ КРИТИЧНЫЕ ОСТАТКИ!" in result
        assert "Шифоновая блузка (SLAVALOOK BRAND)" in result
        assert "270591287" in result
        assert "Остатки: S(13) M(1) L(0) XL(0)" in result
        assert "Критично: M(1) - на 0 дней!" in result
        assert "Нулевые: L, XL на всех складах" in result

    def test_message_length_validation(self, formatter):
        """Тест проверки длины сообщения (лимит Telegram 4096 символов)"""
        # Создаем очень длинное сообщение
        long_data = {
            "orders": [{"id": i, "text": "Очень длинный текст " * 100} for i in range(50)]
        }
        
        result = formatter.format_orders(long_data)
        
        # Проверяем, что сообщение не превышает лимит
        assert len(result) <= 4096
        # Для очень длинных сообщений должно быть многоточие в конце
        if len(result) >= 4090:  # Близко к лимиту
            assert result.endswith("...")

    def test_empty_data_handling(self, formatter):
        """Тест обработки пустых данных"""
        empty_data = {
            "orders": [],
            "statistics": {"today_count": 0, "today_amount": 0}
        }
        
        result = formatter.format_orders(empty_data)
        
        assert "🛒 ПОСЛЕДНИЕ ЗАКАЗЫ" in result
        assert "Заказов не найдено" in result or "Нет заказов" in result
        assert "Всего заказов: 0" in result

    def test_error_message_formatting(self, formatter):
        """Тест форматирования сообщений об ошибках"""
        error_data = {
            "error_type": "wb_api_unavailable",
            "message": "WB API временно недоступен",
            "fallback_data": True
        }
        
        result = formatter.format_error(error_data)
        
        assert "❌ ОШИБКА" in result
        assert "WB API временно недоступен" in result
        assert "Показаны кэшированные данные" in result