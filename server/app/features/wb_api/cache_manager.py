import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import WBAnalyticsCache, WBCabinet

logger = logging.getLogger(__name__)


class WBCacheManager:
    """Менеджер кэширования данных Wildberries"""
    
    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.cache_ttl = {
            "analytics": 3600,  # 1 час
            "products": 1800,   # 30 минут
            "orders": 300,      # 5 минут
            "stocks": 300,      # 5 минут
            "reviews": 1800,    # 30 минут
            "warehouses": 3600  # 1 час
        }

    async def get_cached_data(
        self, 
        cache_key: str, 
        cache_type: str = "analytics"
    ) -> Optional[Dict[str, Any]]:
        """Получение данных из кэша"""
        try:
            # Сначала пробуем Redis
            if self.redis:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            
            # Если Redis недоступен, используем PostgreSQL
            # WBAnalyticsCache не поддерживает общий кэш, только аналитику
            # Пока возвращаем None для общих кэшей
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data: {str(e)}")
            return None

    async def set_cached_data(
        self, 
        cache_key: str, 
        data: Dict[str, Any], 
        cache_type: str = "analytics",
        ttl: Optional[int] = None
    ) -> bool:
        """Сохранение данных в кэш"""
        try:
            if ttl is None:
                ttl = self.cache_ttl.get(cache_type, 3600)
            
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            
            # Сохраняем в Redis
            if self.redis:
                await self.redis.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(data, default=str)
                )
            
            # WBAnalyticsCache не поддерживает общий кэш, только аналитику
            # Пока не сохраняем в PostgreSQL для общих кэшей
            return True
            
        except Exception as e:
            logger.error(f"Error setting cached data: {str(e)}")
            self.db.rollback()
            return False

    async def invalidate_cache(
        self, 
        cache_key: str = None, 
        cache_type: str = None,
        cabinet_id: int = None
    ) -> bool:
        """Инвалидация кэша"""
        try:
            # Инвалидируем Redis кэш
            if self.redis:
                if cache_key:
                    await self.redis.delete(cache_key)
                elif cache_type:
                    # Удаляем все ключи с определенным типом
                    pattern = f"wb:{cache_type}:*"
                    keys = await self.redis.keys(pattern)
                    if keys:
                        await self.redis.delete(*keys)
                elif cabinet_id:
                    # Удаляем все ключи для определенного кабинета
                    pattern = f"wb:*:cabinet:{cabinet_id}:*"
                    keys = await self.redis.keys(pattern)
                    if keys:
                        await self.redis.delete(*keys)
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return False

    # Специфичные методы для аналитики
    async def get_analytics_cache(
        self, 
        cabinet_id: int, 
        report_type: str, 
        date_from: str, 
        date_to: str = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированной аналитики"""
        cache_key = self._build_analytics_key(cabinet_id, report_type, date_from, date_to)
        return await self.get_cached_data(cache_key, "analytics")

    async def set_analytics_cache(
        self, 
        cabinet_id: int, 
        report_type: str, 
        date_from: str, 
        data: Dict[str, Any],
        date_to: str = None
    ) -> bool:
        """Сохранение аналитики в кэш"""
        cache_key = self._build_analytics_key(cabinet_id, report_type, date_from, date_to)
        return await self.set_cached_data(cache_key, data, "analytics")

    # Специфичные методы для товаров
    async def get_products_cache(
        self, 
        cabinet_id: int, 
        filters: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированных товаров"""
        cache_key = self._build_products_key(cabinet_id, filters)
        return await self.get_cached_data(cache_key, "products")

    async def set_products_cache(
        self, 
        cabinet_id: int, 
        data: Dict[str, Any],
        filters: Dict[str, Any] = None
    ) -> bool:
        """Сохранение товаров в кэш"""
        cache_key = self._build_products_key(cabinet_id, filters)
        return await self.set_cached_data(cache_key, data, "products")

    # Специфичные методы для заказов
    async def get_orders_cache(
        self, 
        cabinet_id: int, 
        date_from: str, 
        date_to: str = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированных заказов"""
        cache_key = self._build_orders_key(cabinet_id, date_from, date_to)
        return await self.get_cached_data(cache_key, "orders")

    async def set_orders_cache(
        self, 
        cabinet_id: int, 
        date_from: str, 
        data: Dict[str, Any],
        date_to: str = None
    ) -> bool:
        """Сохранение заказов в кэш"""
        cache_key = self._build_orders_key(cabinet_id, date_from, date_to)
        return await self.set_cached_data(cache_key, data, "orders")

    # Специфичные методы для остатков
    async def get_stocks_cache(
        self, 
        cabinet_id: int, 
        date_from: str, 
        date_to: str = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированных остатков"""
        cache_key = self._build_stocks_key(cabinet_id, date_from, date_to)
        return await self.get_cached_data(cache_key, "stocks")

    async def set_stocks_cache(
        self, 
        cabinet_id: int, 
        date_from: str, 
        data: Dict[str, Any],
        date_to: str = None
    ) -> bool:
        """Сохранение остатков в кэш"""
        cache_key = self._build_stocks_key(cabinet_id, date_from, date_to)
        return await self.set_cached_data(cache_key, data, "stocks")

    # Специфичные методы для отзывов
    async def get_reviews_cache(
        self, 
        cabinet_id: int, 
        is_answered: bool = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированных отзывов"""
        cache_key = self._build_reviews_key(cabinet_id, is_answered)
        return await self.get_cached_data(cache_key, "reviews")

    async def set_reviews_cache(
        self, 
        cabinet_id: int, 
        data: Dict[str, Any],
        is_answered: bool = None
    ) -> bool:
        """Сохранение отзывов в кэш"""
        cache_key = self._build_reviews_key(cabinet_id, is_answered)
        return await self.set_cached_data(cache_key, data, "reviews")

    async def get_warehouses_cache(self, cabinet_id: int) -> Optional[Dict[str, Any]]:
        """Получение кэшированных складов"""
        cache_key = self._build_warehouses_key(cabinet_id)
        return await self.get_cached_data(cache_key, "warehouses")

    async def set_warehouses_cache(
        self, 
        cabinet_id: int, 
        data: Dict[str, Any]
    ) -> bool:
        """Сохранение складов в кэш"""
        cache_key = self._build_warehouses_key(cabinet_id)
        return await self.set_cached_data(cache_key, data, "warehouses")

    def _build_analytics_key(
        self, 
        cabinet_id: int, 
        report_type: str, 
        date_from: str, 
        date_to: str = None
    ) -> str:
        """Построение ключа для аналитики"""
        key_parts = ["wb", "analytics", f"cabinet:{cabinet_id}", report_type, date_from]
        if date_to:
            key_parts.append(date_to)
        return ":".join(key_parts)

    def _build_products_key(
        self, 
        cabinet_id: int, 
        filters: Dict[str, Any] = None
    ) -> str:
        """Построение ключа для товаров"""
        key_parts = ["wb", "products", f"cabinet:{cabinet_id}"]
        if filters:
            filter_str = "_".join([f"{k}:{v}" for k, v in sorted(filters.items())])
            key_parts.append(filter_str)
        return ":".join(key_parts)

    def _build_orders_key(
        self, 
        cabinet_id: int, 
        date_from: str, 
        date_to: str = None
    ) -> str:
        """Построение ключа для заказов"""
        key_parts = ["wb", "orders", f"cabinet:{cabinet_id}", date_from]
        if date_to:
            key_parts.append(date_to)
        return ":".join(key_parts)

    def _build_stocks_key(
        self, 
        cabinet_id: int, 
        date_from: str, 
        date_to: str = None
    ) -> str:
        """Построение ключа для остатков"""
        key_parts = ["wb", "stocks", f"cabinet:{cabinet_id}", date_from]
        if date_to:
            key_parts.append(date_to)
        return ":".join(key_parts)

    def _build_reviews_key(
        self, 
        cabinet_id: int, 
        is_answered: bool = None
    ) -> str:
        """Построение ключа для отзывов"""
        key_parts = ["wb", "reviews", f"cabinet:{cabinet_id}"]
        if is_answered is not None:
            key_parts.append(f"answered:{is_answered}")
        return ":".join(key_parts)

    def _build_warehouses_key(self, cabinet_id: int) -> str:
        """Построение ключа для складов"""
        return f"wb:warehouses:cabinet:{cabinet_id}"

    # Методы для работы с WBAnalyticsCache (специфичные для аналитики)
    async def get_analytics_from_db(
        self, 
        cabinet_id: int, 
        nm_id: int, 
        period: str
    ) -> Optional[WBAnalyticsCache]:
        """Получение аналитики из БД"""
        try:
            return self.db.query(WBAnalyticsCache).filter(
                and_(
                    WBAnalyticsCache.cabinet_id == cabinet_id,
                    WBAnalyticsCache.nm_id == nm_id,
                    WBAnalyticsCache.period == period
                )
            ).first()
        except Exception as e:
            logger.error(f"Error getting analytics from DB: {str(e)}")
            return None

    async def save_analytics_to_db(
        self, 
        cabinet_id: int, 
        nm_id: int, 
        period: str, 
        data: Dict[str, Any]
    ) -> bool:
        """Сохранение аналитики в БД"""
        try:
            # Проверяем, существует ли запись
            existing = await self.get_analytics_from_db(cabinet_id, nm_id, period)
            
            if existing:
                # Обновляем существующую запись
                existing.sales_count = data.get('sales_count', 0)
                existing.sales_amount = data.get('sales_amount', 0.0)
                existing.buyouts_count = data.get('buyouts_count', 0)
                existing.buyouts_amount = data.get('buyouts_amount', 0.0)
                existing.buyout_rate = data.get('buyout_rate', 0.0)
                existing.avg_order_speed = data.get('avg_order_speed', 0.0)
                existing.reviews_count = data.get('reviews_count', 0)
                existing.avg_rating = data.get('avg_rating', 0.0)
                existing.last_calculated = datetime.now(timezone.utc)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # Создаем новую запись
                analytics = WBAnalyticsCache(
                    cabinet_id=cabinet_id,
                    nm_id=nm_id,
                    period=period,
                    sales_count=data.get('sales_count', 0),
                    sales_amount=data.get('sales_amount', 0.0),
                    buyouts_count=data.get('buyouts_count', 0),
                    buyouts_amount=data.get('buyouts_amount', 0.0),
                    buyout_rate=data.get('buyout_rate', 0.0),
                    avg_order_speed=data.get('avg_order_speed', 0.0),
                    reviews_count=data.get('reviews_count', 0),
                    avg_rating=data.get('avg_rating', 0.0),
                    last_calculated=datetime.now(timezone.utc)
                )
                self.db.add(analytics)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving analytics to DB: {str(e)}")
            self.db.rollback()
            return False