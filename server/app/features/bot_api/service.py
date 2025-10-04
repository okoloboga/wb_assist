"""
Bot API сервис для интеграции с Telegram ботом
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet
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
        # Заглушка - в реальности здесь будет запрос к БД
        return {
            "cabinet_name": cabinet.cabinet_name,
            "last_sync": "2 мин назад",
            "status": "Активен",
            "products": {"total": 45, "active": 42, "moderation": 3, "critical_stocks": 3},
            "orders_today": {"count": 19, "amount": 26790, "yesterday_count": 24, "yesterday_amount": 33840, "growth_percent": 12},
            "stocks": {"critical_count": 3, "zero_count": 1, "attention_needed": 2, "top_product": "Test Product"},
            "reviews": {"new_count": 5, "average_rating": 4.8, "unanswered": 2, "total": 214},
            "recommendations": ["Test recommendation"]
        }

    async def _fetch_orders_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение заказов из БД"""
        # Заглушка
        return {
            "orders": [],
            "statistics": {"today_count": 0, "today_amount": 0, "average_check": 0, "growth_percent": 0, "amount_growth_percent": 0},
            "pagination": {"limit": limit, "offset": offset, "total": 0, "has_more": False}
        }

    async def _fetch_critical_stocks_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение критичных остатков из БД"""
        # Заглушка
        return {
            "critical_products": [],
            "zero_products": [],
            "summary": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "potential_losses": 0},
            "recommendations": []
        }

    async def _fetch_reviews_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение отзывов из БД"""
        # Заглушка
        return {
            "new_reviews": [],
            "unanswered_questions": [],
            "statistics": {"average_rating": 0, "total_reviews": 0, "answered_count": 0, "answered_percent": 0, "attention_needed": 0, "new_today": 0},
            "recommendations": []
        }

    async def _fetch_analytics_from_db(self, cabinet: WBCabinet, period: str) -> Dict[str, Any]:
        """Получение аналитики из БД"""
        # Заглушка
        return {
            "sales_periods": {"today": {"count": 0, "amount": 0}, "yesterday": {"count": 0, "amount": 0}, "7_days": {"count": 0, "amount": 0}, "30_days": {"count": 0, "amount": 0}, "90_days": {"count": 0, "amount": 0}},
            "dynamics": {"yesterday_growth_percent": 0, "week_growth_percent": 0, "average_check": 0, "conversion_percent": 0},
            "top_products": [],
            "stocks_summary": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "total_products": 0},
            "recommendations": []
        }