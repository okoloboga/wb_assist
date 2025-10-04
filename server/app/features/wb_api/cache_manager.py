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
            cache_record = self.db.query(WBAnalyticsCache).filter(
                and_(
                    WBAnalyticsCache.cache_key == cache_key,
                    WBAnalyticsCache.cache_type == cache_type,
                    WBAnalyticsCache.expires_at > datetime.now(timezone.utc)
                )
            ).first()
            
            if cache_record:
                return cache_record.data
            
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
            
            # Сохраняем в PostgreSQL
            cache_record = self.db.query(WBAnalyticsCache).filter(
                and_(
                    WBAnalyticsCache.cache_key == cache_key,
                    WBAnalyticsCache.cache_type == cache_type
                )
            ).first()
            
            if cache_record:
                # Обновляем существующую запись
                cache_record.data = data
                cache_record.expires_at = expires_at
                cache_record.updated_at = datetime.now(timezone.utc)
            else:
                # Создаем новую запись
                cache_record = WBAnalyticsCache(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    data=data,
                    expires_at=expires_at
                )
                self.db.add(cache_record)
            
            self.db.commit()
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
            # Инвалидируем в Redis
            if self.redis:
                if cache_key:
                    await self.redis.delete(cache_key)
                elif cache_type:
                    # Удаляем все ключи данного типа
                    pattern = f"wb:{cache_type}:*"
                    keys = await self.redis.keys(pattern)
                    if keys:
                        await self.redis.delete(*keys)
                elif cabinet_id:
                    # Удаляем все ключи для кабинета
                    pattern = f"wb:*:cabinet:{cabinet_id}:*"
                    keys = await self.redis.keys(pattern)
                    if keys:
                        await self.redis.delete(*keys)
            
            # Инвалидируем в PostgreSQL
            query = self.db.query(WBAnalyticsCache)
            
            if cache_key:
                query = query.filter(WBAnalyticsCache.cache_key == cache_key)
            elif cache_type:
                query = query.filter(WBAnalyticsCache.cache_type == cache_type)
            elif cabinet_id:
                query = query.filter(WBAnalyticsCache.cache_key.like(f"%cabinet:{cabinet_id}%"))
            
            cache_records = query.all()
            for record in cache_records:
                self.db.delete(record)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            self.db.rollback()
            return False

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

    async def get_products_cache(
        self, 
        cabinet_id: int, 
        filters: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Получение кэшированного списка товаров"""
        cache_key = self._build_products_key(cabinet_id, filters)
        return await self.get_cached_data(cache_key, "products")

    async def set_products_cache(
        self, 
        cabinet_id: int, 
        data: Dict[str, Any],
        filters: Dict[str, Any] = None
    ) -> bool:
        """Сохранение списка товаров в кэш"""
        cache_key = self._build_products_key(cabinet_id, filters)
        return await self.set_cached_data(cache_key, data, "products")

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
        data: Dict[str, Any],
        date_from: str,
        date_to: str = None
    ) -> bool:
        """Сохранение заказов в кэш"""
        cache_key = self._build_orders_key(cabinet_id, date_from, date_to)
        return await self.set_cached_data(cache_key, data, "orders")

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
        data: Dict[str, Any],
        date_from: str,
        date_to: str = None
    ) -> bool:
        """Сохранение остатков в кэш"""
        cache_key = self._build_stocks_key(cabinet_id, date_from, date_to)
        return await self.set_cached_data(cache_key, data, "stocks")

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

    async def cleanup_expired_cache(self) -> int:
        """Очистка устаревшего кэша"""
        try:
            # Очищаем PostgreSQL
            expired_records = self.db.query(WBAnalyticsCache).filter(
                WBAnalyticsCache.expires_at < datetime.now(timezone.utc)
            ).all()
            
            count = len(expired_records)
            for record in expired_records:
                self.db.delete(record)
            
            self.db.commit()
            
            # Очищаем Redis (если доступен)
            if self.redis:
                # Redis автоматически удаляет ключи по TTL, но можно принудительно очистить
                pass
            
            logger.info(f"Cleaned up {count} expired cache records")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {str(e)}")
            self.db.rollback()
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        try:
            # Статистика PostgreSQL
            total_records = self.db.query(WBAnalyticsCache).count()
            expired_records = self.db.query(WBAnalyticsCache).filter(
                WBAnalyticsCache.expires_at < datetime.now(timezone.utc)
            ).count()
            
            # Статистика по типам
            type_stats = {}
            for cache_type in self.cache_ttl.keys():
                count = self.db.query(WBAnalyticsCache).filter(
                    WBAnalyticsCache.cache_type == cache_type
                ).count()
                type_stats[cache_type] = count
            
            return {
                "total_records": total_records,
                "expired_records": expired_records,
                "active_records": total_records - expired_records,
                "type_stats": type_stats,
                "redis_available": self.redis is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}

    async def warm_up_cache(self, cabinet_id: int) -> bool:
        """Прогрев кэша для кабинета"""
        try:
            # Здесь можно добавить логику предварительного заполнения кэша
            # популярными запросами для кабинета
            
            logger.info(f"Warming up cache for cabinet {cabinet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error warming up cache: {str(e)}")
            return False

    async def health_check(self) -> bool:
        """Проверка здоровья кэш-менеджера"""
        try:
            # Проверяем подключение к БД
            self.db.execute("SELECT 1")
            
            # Проверяем Redis (если доступен)
            if self.redis:
                await self.redis.ping()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache manager health check failed: {str(e)}")
            return False