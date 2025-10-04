"""
Bot API сервис для интеграции с Telegram ботом
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone, timedelta
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService
from .formatter import BotMessageFormatter

logger = logging.getLogger(__name__)


class BotAPIService:
    """Сервис для Bot API"""
    
    def __init__(self, db: Session, cache_manager: WBCacheManager, sync_service: WBSyncService):
        self.db = db
        self.cache_manager = cache_manager
        self.sync_service = sync_service
        self.formatter = BotMessageFormatter()

    async def get_user_cabinet(self, telegram_id: int) -> Optional[WBCabinet]:
        """Получение кабинета пользователя по telegram_id"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            cabinet = self.db.query(WBCabinet).filter(
                WBCabinet.user_id == user.id,
                WBCabinet.is_active == True
            ).first()
            
            return cabinet
        except Exception as e:
            logger.error(f"Ошибка получения кабинета для telegram_id {telegram_id}: {e}")
            return None

    async def get_dashboard_data(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение данных dashboard"""
        try:
            # Пытаемся получить из кэша
            cache_key = f"bot:dashboard:cabinet:{cabinet.id}"
            cached_data = await self.cache_manager.get_cached_data(cache_key, "bot_dashboard")
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "telegram_text": self.formatter.format_dashboard(cached_data)
                }
            
            # Если нет в кэше, получаем из БД
            dashboard_data = await self._fetch_dashboard_from_db(cabinet)
            
            # Сохраняем в кэш
            await self.cache_manager.set_cached_data(cache_key, dashboard_data, "bot_dashboard", ttl=300)
            
            return {
                "success": True,
                "data": dashboard_data,
                "telegram_text": self.formatter.format_dashboard(dashboard_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения dashboard для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def get_recent_orders(self, cabinet: WBCabinet, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение последних заказов"""
        try:
            cache_key = f"bot:orders:cabinet:{cabinet.id}:limit:{limit}:offset:{offset}"
            cached_data = await self.cache_manager.get_cached_data(cache_key, "bot_orders")
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "telegram_text": self.formatter.format_orders(cached_data)
                }
            
            # Получаем из БД
            orders_data = await self._fetch_orders_from_db(cabinet, limit, offset)
            
            # Сохраняем в кэш
            await self.cache_manager.set_cached_data(cache_key, orders_data, "bot_orders", ttl=300)
            
            return {
                "success": True,
                "data": orders_data,
                "telegram_text": self.formatter.format_orders(orders_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def get_critical_stocks(self, cabinet: WBCabinet, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Получение критичных остатков"""
        try:
            cache_key = f"bot:stocks:cabinet:{cabinet.id}:limit:{limit}:offset:{offset}"
            cached_data = await self.cache_manager.get_cached_data(cache_key, "bot_stocks")
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "telegram_text": self.formatter.format_critical_stocks(cached_data)
                }
            
            # Получаем из БД
            stocks_data = await self._fetch_critical_stocks_from_db(cabinet, limit, offset)
            
            # Сохраняем в кэш
            await self.cache_manager.set_cached_data(cache_key, stocks_data, "bot_stocks", ttl=300)
            
            return {
                "success": True,
                "data": stocks_data,
                "telegram_text": self.formatter.format_critical_stocks(stocks_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения остатков для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def get_reviews_summary(self, cabinet: WBCabinet, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение сводки отзывов"""
        try:
            cache_key = f"bot:reviews:cabinet:{cabinet.id}:limit:{limit}:offset:{offset}"
            cached_data = await self.cache_manager.get_cached_data(cache_key, "bot_reviews")
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "telegram_text": self.formatter.format_reviews(cached_data)
                }
            
            # Получаем из БД
            reviews_data = await self._fetch_reviews_from_db(cabinet, limit, offset)
            
            # Сохраняем в кэш
            await self.cache_manager.set_cached_data(cache_key, reviews_data, "bot_reviews", ttl=300)
            
            return {
                "success": True,
                "data": reviews_data,
                "telegram_text": self.formatter.format_reviews(reviews_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения отзывов для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def get_analytics_sales(self, cabinet: WBCabinet, period: str = "7d") -> Dict[str, Any]:
        """Получение аналитики продаж"""
        try:
            cache_key = f"bot:analytics:cabinet:{cabinet.id}:period:{period}"
            cached_data = await self.cache_manager.get_cached_data(cache_key, "bot_analytics")
            
            if cached_data:
                return {
                    "success": True,
                    "data": cached_data,
                    "telegram_text": self.formatter.format_analytics(cached_data)
                }
            
            # Получаем из БД
            analytics_data = await self._fetch_analytics_from_db(cabinet, period)
            
            # Сохраняем в кэш
            await self.cache_manager.set_cached_data(cache_key, analytics_data, "bot_analytics", ttl=1800)
            
            return {
                "success": True,
                "data": analytics_data,
                "telegram_text": self.formatter.format_analytics(analytics_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def start_sync(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Запуск синхронизации"""
        try:
            result = await self.sync_service.sync_cabinet(cabinet)
            
            return {
                "success": True,
                "data": {
                    "sync_id": f"sync_{cabinet.id}_{int(result.get('timestamp', 0))}",
                    "status": "started",
                    "message": "Синхронизация запущена"
                },
                "telegram_text": self.formatter.format_sync_status({
                    "last_sync": "Сейчас",
                    "status": "started",
                    "duration_seconds": 0,
                    "cabinets_processed": 1,
                    "updates": {"orders": {"new": 0}, "stocks": {"updated": 0}, "reviews": {"new": 0}, "products": {"changed": 0}, "analytics": {"recalculated": False}},
                    "next_sync": "Через минуту",
                    "sync_mode": "manual",
                    "interval_seconds": 60,
                    "statistics": {"successful_today": 0, "errors_today": 0, "average_duration": 0, "last_error": None}
                })
            }
            
        except Exception as e:
            logger.error(f"Ошибка запуска синхронизации для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера"
            }

    async def get_sync_status(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        try:
            status_data = await self.sync_service.get_sync_status(cabinet)
            
            return {
                "success": True,
                "data": status_data,
                "telegram_text": self.formatter.format_sync_status(status_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса синхронизации для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера"
            }

    # Вспомогательные методы для получения данных из БД
    async def _fetch_dashboard_from_db(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение данных dashboard из БД"""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            # Статус кабинета
            status = "Активен" if cabinet.is_active else "Неактивен"
            
            # Время последней синхронизации
            if cabinet.last_sync_at:
                sync_diff = now - cabinet.last_sync_at
                if sync_diff.total_seconds() < 60:
                    last_sync = f"{int(sync_diff.total_seconds())} сек назад"
                elif sync_diff.total_seconds() < 3600:
                    last_sync = f"{int(sync_diff.total_seconds() / 60)} мин назад"
                else:
                    last_sync = f"{int(sync_diff.total_seconds() / 3600)} ч назад"
            else:
                last_sync = "Никогда"
            
            # Товары
            total_products = self.db.query(WBProduct).filter(
                WBProduct.cabinet_id == cabinet.id
            ).count()
            
            active_products = self.db.query(WBProduct).filter(
                and_(WBProduct.cabinet_id == cabinet.id, WBProduct.is_active == True)
            ).count()
            
            # Заказы за сегодня
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            today_count = len(orders_today)
            today_amount = sum(order.total_price or 0 for order in orders_today)
            
            # Заказы за вчера
            orders_yesterday = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= yesterday_start,
                    WBOrder.order_date < today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            yesterday_count = len(orders_yesterday)
            yesterday_amount = sum(order.total_price or 0 for order in orders_yesterday)
            
            # Рост заказов
            if yesterday_count > 0:
                growth_percent = round(((today_count - yesterday_count) / yesterday_count) * 100, 1)
            else:
                growth_percent = 100.0 if today_count > 0 else 0.0
            
            # Остатки
            stocks = self.db.query(WBStock).filter(
                WBStock.cabinet_id == cabinet.id
            ).all()
            
            # Группируем остатки по товарам
            stock_by_product = {}
            for stock in stocks:
                if stock.nm_id not in stock_by_product:
                    stock_by_product[stock.nm_id] = {}
                stock_by_product[stock.nm_id][stock.size or "UNKNOWN"] = stock.quantity or 0
            
            critical_count = 0
            zero_count = 0
            attention_needed = 0
            
            for nm_id, sizes in stock_by_product.items():
                total_stock = sum(sizes.values())
                if total_stock == 0:
                    zero_count += 1
                elif total_stock < 5:
                    critical_count += 1
                elif total_stock < 10:
                    attention_needed += 1
            
            # Топ товар (по заказам за 7 дней)
            week_ago = now - timedelta(days=7)
            top_orders = self.db.query(
                WBOrder.nm_id,
                func.count(WBOrder.id).label('order_count')
            ).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= week_ago,
                    WBOrder.is_cancel == False
                )
            ).group_by(WBOrder.nm_id).order_by(func.count(WBOrder.id).desc()).first()
            
            top_product = "Нет данных"
            if top_orders:
                product = self.db.query(WBProduct).filter(
                    and_(WBProduct.cabinet_id == cabinet.id, WBProduct.nm_id == top_orders.nm_id)
                ).first()
                if product:
                    top_product = f"{product.name} ({top_orders.order_count} шт/7дн)"
            
            # Отзывы
            reviews_today = self.db.query(WBReview).filter(
                and_(
                    WBReview.cabinet_id == cabinet.id,
                    WBReview.created_at >= today_start
                )
            ).count()
            
            all_reviews = self.db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id
            ).all()
            
            total_reviews = len(all_reviews)
            if total_reviews > 0:
                avg_rating = sum(review.rating or 0 for review in all_reviews) / total_reviews
            else:
                avg_rating = 0.0
            
            # Неотвеченные отзывы (заглушка - в реальности нужна логика определения)
            unanswered = 0
            
            # Рекомендации
            recommendations = []
            if critical_count > 0:
                recommendations.append(f"Пополнить остатки {critical_count} критичных товаров")
            if zero_count > 0:
                recommendations.append(f"Заказать {zero_count} товаров с нулевыми остатками")
            if unanswered > 0:
                recommendations.append(f"Ответить на {unanswered} отзывов")
            if not recommendations:
                recommendations.append("Все в порядке!")
            
            return {
                "cabinet_name": cabinet.cabinet_name,
                "last_sync": last_sync,
                "status": status,
                "products": {
                    "total": total_products,
                    "active": active_products,
                    "moderation": 0,  # Заглушка - в реальности нужна логика модерации
                    "critical_stocks": critical_count
                },
                "orders_today": {
                    "count": today_count,
                    "amount": today_amount,
                    "yesterday_count": yesterday_count,
                    "yesterday_amount": yesterday_amount,
                    "growth_percent": growth_percent
                },
                "stocks": {
                    "critical_count": critical_count,
                    "zero_count": zero_count,
                    "attention_needed": attention_needed,
                    "top_product": top_product
                },
                "reviews": {
                    "new_count": reviews_today,
                    "average_rating": round(avg_rating, 1),
                    "unanswered": unanswered,
                    "total": total_reviews
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения dashboard из БД для кабинета {cabinet.id}: {e}")
            # Возвращаем базовые данные при ошибке
            return {
                "cabinet_name": cabinet.cabinet_name,
                "last_sync": "Ошибка",
                "status": "Ошибка",
                "products": {"total": 0, "active": 0, "moderation": 0, "critical_stocks": 0},
                "orders_today": {"count": 0, "amount": 0, "yesterday_count": 0, "yesterday_amount": 0, "growth_percent": 0},
                "stocks": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "top_product": "Нет данных"},
                "reviews": {"new_count": 0, "average_rating": 0.0, "unanswered": 0, "total": 0},
                "recommendations": ["Ошибка получения данных"]
            }

    async def _fetch_orders_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение заказов из БД"""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            # Получаем заказы с пагинацией
            orders_query = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.is_cancel == False
                )
            ).order_by(WBOrder.order_date.desc())
            
            total_orders = orders_query.count()
            orders = orders_query.offset(offset).limit(limit).all()
            
            # Формируем список заказов
            orders_list = []
            for order in orders:
                orders_list.append({
                    "id": order.id,
                    "date": order.order_date.isoformat() if order.order_date else None,
                    "amount": order.total_price or 0,
                    "product_name": order.name or "Неизвестно",
                    "brand": order.brand or "Неизвестно",
                    "warehouse_from": "Неизвестно",  # Заглушка - в реальности из WBWarehouse
                    "warehouse_to": "Неизвестно",    # Заглушка - в реальности из WBWarehouse
                    "commission_percent": 0,  # Заглушка - в реальности из WB API
                    "rating": 0  # Заглушка - в реальности из WBReview
                })
            
            # Статистика за сегодня
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            today_count = len(orders_today)
            today_amount = sum(order.total_price or 0 for order in orders_today)
            
            # Статистика за вчера
            orders_yesterday = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= yesterday_start,
                    WBOrder.order_date < today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            yesterday_count = len(orders_yesterday)
            yesterday_amount = sum(order.total_price or 0 for order in orders_yesterday)
            
            # Рост заказов
            if yesterday_count > 0:
                growth_percent = round(((today_count - yesterday_count) / yesterday_count) * 100, 1)
            else:
                growth_percent = 100.0 if today_count > 0 else 0.0
            
            # Рост суммы
            if yesterday_amount > 0:
                amount_growth_percent = round(((today_amount - yesterday_amount) / yesterday_amount) * 100, 1)
            else:
                amount_growth_percent = 100.0 if today_amount > 0 else 0.0
            
            # Средний чек
            average_check = round(today_amount / today_count, 0) if today_count > 0 else 0
            
            return {
                "orders": orders_list,
                "statistics": {
                    "today_count": today_count,
                    "today_amount": today_amount,
                    "average_check": average_check,
                    "growth_percent": growth_percent,
                    "amount_growth_percent": amount_growth_percent
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_orders,
                    "has_more": (offset + limit) < total_orders
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов из БД для кабинета {cabinet.id}: {e}")
            return {
                "orders": [],
                "statistics": {"today_count": 0, "today_amount": 0, "average_check": 0, "growth_percent": 0, "amount_growth_percent": 0},
                "pagination": {"limit": limit, "offset": offset, "total": 0, "has_more": False}
            }

    async def _fetch_critical_stocks_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение критичных остатков из БД"""
        try:
            # Получаем все остатки
            stocks = self.db.query(WBStock).filter(
                WBStock.cabinet_id == cabinet.id
            ).all()
            
            # Группируем остатки по товарам
            stock_by_product = {}
            for stock in stocks:
                if stock.nm_id not in stock_by_product:
                    stock_by_product[stock.nm_id] = {
                        "product": None,
                        "stocks": {},
                        "total_stock": 0,
                        "price": stock.price or 0
                    }
                stock_by_product[stock.nm_id]["stocks"][stock.size or "UNKNOWN"] = stock.quantity or 0
                stock_by_product[stock.nm_id]["total_stock"] += stock.quantity or 0
            
            # Получаем информацию о товарах
            for nm_id in stock_by_product.keys():
                product = self.db.query(WBProduct).filter(
                    and_(WBProduct.cabinet_id == cabinet.id, WBProduct.nm_id == nm_id)
                ).first()
                stock_by_product[nm_id]["product"] = product
            
            # Разделяем на критичные и нулевые
            critical_products = []
            zero_products = []
            
            for nm_id, data in stock_by_product.items():
                product = data["product"]
                if not product:
                    continue
                
                total_stock = data["total_stock"]
                stocks_dict = data["stocks"]
                
                # Определяем критичные и нулевые размеры
                critical_sizes = []
                zero_sizes = []
                days_left = {}
                
                for size, quantity in stocks_dict.items():
                    if quantity == 0:
                        zero_sizes.append(size)
                    elif quantity < 5:
                        critical_sizes.append(size)
                        # Заглушка для расчета дней - в реальности нужна логика продаж
                        days_left[size] = 0
                
                product_data = {
                    "nm_id": nm_id,
                    "name": product.name or "Неизвестно",
                    "brand": product.brand or "Неизвестно",
                    "stocks": stocks_dict,
                    "critical_sizes": critical_sizes,
                    "zero_sizes": zero_sizes,
                    "sales_per_day": 0,  # Заглушка - в реальности из WBOrder
                    "price": data["price"],
                    "commission_percent": 0,  # Заглушка - в реальности из WB API
                    "days_left": days_left
                }
                
                if total_stock == 0:
                    zero_products.append(product_data)
                elif total_stock < 5 or critical_sizes:
                    critical_products.append(product_data)
            
            # Применяем пагинацию
            critical_products = critical_products[offset:offset + limit]
            zero_products = zero_products[offset:offset + limit]
            
            # Сводка
            critical_count = len([p for p in stock_by_product.values() if p["total_stock"] < 5 and p["total_stock"] > 0])
            zero_count = len([p for p in stock_by_product.values() if p["total_stock"] == 0])
            attention_needed = len([p for p in stock_by_product.values() if 5 <= p["total_stock"] < 10])
            
            # Потенциальные потери (заглушка)
            potential_losses = sum(p["total_stock"] for p in stock_by_product.values() if p["total_stock"] < 5)
            
            # Рекомендации
            recommendations = []
            if critical_count > 0:
                recommendations.append(f"Срочно пополнить {critical_count} критичных товаров")
            if zero_count > 0:
                recommendations.append(f"Заказать {zero_count} товаров с нулевыми остатками")
            if attention_needed > 0:
                recommendations.append(f"Проанализировать {attention_needed} товаров с низкими остатками")
            if not recommendations:
                recommendations.append("Все остатки в порядке!")
            
            return {
                "critical_products": critical_products,
                "zero_products": zero_products,
                "summary": {
                    "critical_count": critical_count,
                    "zero_count": zero_count,
                    "attention_needed": attention_needed,
                    "potential_losses": potential_losses
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения критичных остатков из БД для кабинета {cabinet.id}: {e}")
            return {
                "critical_products": [],
                "zero_products": [],
                "summary": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "potential_losses": 0},
                "recommendations": ["Ошибка получения данных"]
            }

    async def _fetch_reviews_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение отзывов из БД"""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Получаем все отзывы
            all_reviews = self.db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id
            ).all()
            
            # Новые отзывы за сегодня
            new_reviews_today = self.db.query(WBReview).filter(
                and_(
                    WBReview.cabinet_id == cabinet.id,
                    WBReview.created_at >= today_start
                )
            ).order_by(WBReview.created_at.desc()).limit(limit).all()
            
            # Формируем список новых отзывов
            new_reviews = []
            for review in new_reviews_today:
                # Получаем информацию о товаре
                product = self.db.query(WBProduct).filter(
                    and_(WBProduct.cabinet_id == cabinet.id, WBProduct.nm_id == review.nm_id)
                ).first()
                
                # Время назад
                time_ago = "Неизвестно"
                if review.created_at:
                    diff = now - review.created_at
                    if diff.total_seconds() < 3600:
                        time_ago = f"{int(diff.total_seconds() / 60)} мин назад"
                    elif diff.total_seconds() < 86400:
                        time_ago = f"{int(diff.total_seconds() / 3600)} ч назад"
                    else:
                        time_ago = f"{int(diff.total_seconds() / 86400)} дн назад"
                
                new_reviews.append({
                    "id": str(review.id),
                    "product_name": product.name if product else "Неизвестно",
                    "rating": review.rating or 0,
                    "text": review.text or "",
                    "time_ago": time_ago,
                    "order_id": review.order_id or "N/A"
                })
            
            # Неотвеченные вопросы (заглушка - в реальности нужна логика)
            unanswered_questions = []
            
            # Статистика
            total_reviews = len(all_reviews)
            if total_reviews > 0:
                avg_rating = sum(review.rating or 0 for review in all_reviews) / total_reviews
            else:
                avg_rating = 0.0
            
            # Заглушки для статистики
            answered_count = total_reviews  # В реальности нужна логика определения отвеченных
            answered_percent = 100.0 if total_reviews > 0 else 0.0
            attention_needed = len([r for r in all_reviews if (r.rating or 0) < 3])  # Низкие рейтинги
            new_today = len(new_reviews_today)
            
            # Рекомендации
            recommendations = []
            if attention_needed > 0:
                recommendations.append(f"Ответить на {attention_needed} отзывов с низким рейтингом")
            if len(unanswered_questions) > 0:
                recommendations.append(f"Ответить на {len(unanswered_questions)} неотвеченных вопросов")
            if avg_rating < 4.0 and total_reviews > 0:
                recommendations.append("Проанализировать жалобы на качество")
            if not recommendations:
                recommendations.append("Все отзывы обработаны!")
            
            return {
                "new_reviews": new_reviews,
                "unanswered_questions": unanswered_questions,
                "statistics": {
                    "average_rating": round(avg_rating, 1),
                    "total_reviews": total_reviews,
                    "answered_count": answered_count,
                    "answered_percent": round(answered_percent, 1),
                    "attention_needed": attention_needed,
                    "new_today": new_today
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения отзывов из БД для кабинета {cabinet.id}: {e}")
            return {
                "new_reviews": [],
                "unanswered_questions": [],
                "statistics": {"average_rating": 0, "total_reviews": 0, "answered_count": 0, "answered_percent": 0, "attention_needed": 0, "new_today": 0},
                "recommendations": ["Ошибка получения данных"]
            }

    async def _fetch_analytics_from_db(self, cabinet: WBCabinet, period: str) -> Dict[str, Any]:
        """Получение аналитики из БД"""
        try:
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            quarter_ago = now - timedelta(days=90)
            
            # Заказы за разные периоды
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            orders_yesterday = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= yesterday_start,
                    WBOrder.order_date < today_start,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            orders_7_days = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= week_ago,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            orders_30_days = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= month_ago,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            orders_90_days = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= quarter_ago,
                    WBOrder.is_cancel == False
                )
            ).all()
            
            # Продажи по периодам
            sales_periods = {
                "today": {
                    "count": len(orders_today),
                    "amount": sum(order.total_price or 0 for order in orders_today)
                },
                "yesterday": {
                    "count": len(orders_yesterday),
                    "amount": sum(order.total_price or 0 for order in orders_yesterday)
                },
                "7_days": {
                    "count": len(orders_7_days),
                    "amount": sum(order.total_price or 0 for order in orders_7_days)
                },
                "30_days": {
                    "count": len(orders_30_days),
                    "amount": sum(order.total_price or 0 for order in orders_30_days)
                },
                "90_days": {
                    "count": len(orders_90_days),
                    "amount": sum(order.total_price or 0 for order in orders_90_days)
                }
            }
            
            # Динамика
            yesterday_growth_percent = 0
            if sales_periods["yesterday"]["count"] > 0:
                yesterday_growth_percent = round(
                    ((sales_periods["today"]["count"] - sales_periods["yesterday"]["count"]) / 
                     sales_periods["yesterday"]["count"]) * 100, 1
                )
            elif sales_periods["today"]["count"] > 0:
                yesterday_growth_percent = 100.0
            
            week_growth_percent = 0
            if period == "7d" and len(orders_7_days) > 0:
                # Сравниваем с предыдущей неделей
                prev_week_start = week_ago - timedelta(days=7)
                prev_week_orders = self.db.query(WBOrder).filter(
                    and_(
                        WBOrder.cabinet_id == cabinet.id,
                        WBOrder.order_date >= prev_week_start,
                        WBOrder.order_date < week_ago,
                        WBOrder.is_cancel == False
                    )
                ).all()
                
                if len(prev_week_orders) > 0:
                    week_growth_percent = round(
                        ((len(orders_7_days) - len(prev_week_orders)) / len(prev_week_orders)) * 100, 1
                    )
                elif len(orders_7_days) > 0:
                    week_growth_percent = 100.0
            
            # Средний чек
            average_check = 0
            if sales_periods["today"]["count"] > 0:
                average_check = round(sales_periods["today"]["amount"] / sales_periods["today"]["count"], 0)
            
            # Конверсия (заглушка - в реальности нужны данные о просмотрах)
            conversion_percent = 0.0
            
            # Топ товары за выбранный период
            period_orders = orders_7_days if period == "7d" else orders_30_days if period == "30d" else orders_90_days
            
            # Группируем заказы по товарам
            product_sales = {}
            for order in period_orders:
                nm_id = order.nm_id
                if nm_id not in product_sales:
                    product_sales[nm_id] = {"count": 0, "amount": 0}
                product_sales[nm_id]["count"] += 1
                product_sales[nm_id]["amount"] += order.total_price or 0
            
            # Сортируем по количеству продаж
            top_products_data = sorted(product_sales.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
            
            top_products = []
            for nm_id, sales_data in top_products_data:
                product = self.db.query(WBProduct).filter(
                    and_(WBProduct.cabinet_id == cabinet.id, WBProduct.nm_id == nm_id)
                ).first()
                
                if product:
                    # Получаем остатки
                    stocks = self.db.query(WBStock).filter(
                        and_(WBStock.cabinet_id == cabinet.id, WBStock.nm_id == nm_id)
                    ).all()
                    
                    stocks_dict = {}
                    for stock in stocks:
                        stocks_dict[stock.size or "UNKNOWN"] = stock.quantity or 0
                    
                    # Средний рейтинг (заглушка)
                    rating = 4.5
                    
                    top_products.append({
                        "nm_id": nm_id,
                        "name": product.name or "Неизвестно",
                        "sales_count": sales_data["count"],
                        "sales_amount": sales_data["amount"],
                        "rating": rating,
                        "stocks": stocks_dict
                    })
            
            # Сводка по остаткам
            all_stocks = self.db.query(WBStock).filter(WBStock.cabinet_id == cabinet.id).all()
            
            stock_by_product = {}
            for stock in all_stocks:
                if stock.nm_id not in stock_by_product:
                    stock_by_product[stock.nm_id] = 0
                stock_by_product[stock.nm_id] += stock.quantity or 0
            
            critical_count = len([s for s in stock_by_product.values() if 0 < s < 5])
            zero_count = len([s for s in stock_by_product.values() if s == 0])
            attention_needed = len([s for s in stock_by_product.values() if 5 <= s < 10])
            total_products = len(stock_by_product)
            
            stocks_summary = {
                "critical_count": critical_count,
                "zero_count": zero_count,
                "attention_needed": attention_needed,
                "total_products": total_products
            }
            
            # Рекомендации
            recommendations = []
            if critical_count > 0:
                recommendations.append(f"Пополнить остатки {critical_count} критичных товаров")
            if zero_count > 0:
                recommendations.append(f"Заказать {zero_count} товаров с нулевыми остатками")
            if yesterday_growth_percent < -20:
                recommendations.append("Проанализировать падение продаж")
            if average_check < 1000 and sales_periods["today"]["count"] > 0:
                recommendations.append("Оптимизировать цены на медленно продающиеся товары")
            if not recommendations:
                recommendations.append("Все показатели в норме!")
            
            return {
                "sales_periods": sales_periods,
                "dynamics": {
                    "yesterday_growth_percent": yesterday_growth_percent,
                    "week_growth_percent": week_growth_percent,
                    "average_check": average_check,
                    "conversion_percent": conversion_percent
                },
                "top_products": top_products,
                "stocks_summary": stocks_summary,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики из БД для кабинета {cabinet.id}: {e}")
            return {
                "sales_periods": {"today": {"count": 0, "amount": 0}, "yesterday": {"count": 0, "amount": 0}, "7_days": {"count": 0, "amount": 0}, "30_days": {"count": 0, "amount": 0}, "90_days": {"count": 0, "amount": 0}},
                "dynamics": {"yesterday_growth_percent": 0, "week_growth_percent": 0, "average_check": 0, "conversion_percent": 0},
                "top_products": [],
                "stocks_summary": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "total_products": 0},
                "recommendations": ["Ошибка получения данных"]
            }

    async def get_order_detail(self, cabinet: WBCabinet, order_id: int) -> Dict[str, Any]:
        """Получение детальной информации о заказе"""
        try:
            # Получаем заказ из БД
            order = self.db.query(WBOrder).filter(
                WBOrder.id == order_id,
                WBOrder.cabinet_id == cabinet.id
            ).first()
            
            if not order:
                return {
                    "success": False,
                    "error": f"Заказ {order_id} не найден"
                }
            
            # Получаем дополнительные данные для детального отчета
            order_detail = await self._fetch_order_detail_from_db(cabinet, order)
            
            return {
                "success": True,
                "data": order_detail,
                "telegram_text": self.formatter.format_order_detail(order_detail)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей заказа {order_id} для кабинета {cabinet.id}: {e}")
            return {
                "success": False,
                "error": "Ошибка сервера" if "WB API" not in str(e) else "WB API временно недоступен"
            }

    async def _fetch_order_detail_from_db(self, cabinet: WBCabinet, order: WBOrder) -> Dict[str, Any]:
        """Получение детальных данных заказа из БД"""
        # Заглушка - в реальности здесь будет сложная логика получения всех данных
        return {
            "order": {
                "id": order.id,
                "date": order.order_date.isoformat() if order.order_date else None,
                "brand": order.brand or "Неизвестно",
                "product_name": order.product_name or "Неизвестно",
                "nm_id": order.nm_id,
                "supplier_article": order.supplier_article or "",
                "size": order.size or "",
                "barcode": order.barcode or "",
                "warehouse_from": order.warehouse_from or "",
                "warehouse_to": order.warehouse_to or "",
                "order_amount": order.order_amount or 0,
                "commission_percent": order.commission_percent or 0,
                "commission_amount": order.commission_amount or 0,
                "spp_percent": order.spp_percent or 0,
                "customer_price": order.customer_price or 0,
                "logistics_amount": order.logistics_amount or 0,
                "dimensions": order.dimensions or "",
                "volume_liters": order.volume_liters or 0,
                "warehouse_rate_per_liter": order.warehouse_rate_per_liter or 0,
                "warehouse_rate_extra": order.warehouse_rate_extra or 0,
                "rating": order.rating or 0,
                "reviews_count": order.reviews_count or 0,
                "buyout_rates": {
                    "7_days": order.buyout_7_days or 0,
                    "14_days": order.buyout_14_days or 0,
                    "30_days": order.buyout_30_days or 0
                },
                "order_speed": {
                    "7_days": order.order_speed_7_days or 0,
                    "14_days": order.order_speed_14_days or 0,
                    "30_days": order.order_speed_30_days or 0
                },
                "sales_periods": {
                    "7_days": order.sales_7_days or 0,
                    "14_days": order.sales_14_days or 0,
                    "30_days": order.sales_30_days or 0,
                    "60_days": order.sales_60_days or 0,
                    "90_days": order.sales_90_days or 0
                },
                "category_availability": order.category_availability or "",
                "stocks": {
                    "L": order.stock_L or 0,
                    "M": order.stock_M or 0,
                    "S": order.stock_S or 0,
                    "XL": order.stock_XL or 0
                },
                "stock_days": {
                    "L": order.stock_days_L or 0,
                    "M": order.stock_days_M or 0,
                    "S": order.stock_days_S or 0,
                    "XL": order.stock_days_XL or 0
                }
            }
        }