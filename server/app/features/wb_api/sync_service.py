import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBSyncLog
from .client import WBAPIClient
from .cache_manager import WBCacheManager

logger = logging.getLogger(__name__)


class WBSyncService:
    """
    Сервис синхронизации данных с Wildberries API
    """
    
    def __init__(self, db: Session, cache_manager: WBCacheManager = None):
        self.db = db
        self.cache_manager = cache_manager or WBCacheManager(db)
    
    async def sync_all_data(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Синхронизация всех данных кабинета"""
        try:
            client = WBAPIClient(cabinet)
            
            # Определяем период синхронизации (последние 30 дней)
            date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
            
            results = {}
            
            # Синхронизируем данные параллельно
            tasks = [
                self.sync_products(cabinet, client),
                self.sync_orders(cabinet, client, date_from, date_to),
                self.sync_stocks(cabinet, client, date_from, date_to),
                self.sync_reviews(cabinet, client, date_from, date_to)
            ]
            
            sync_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for i, result in enumerate(sync_results):
                if isinstance(result, Exception):
                    logger.error(f"Sync task {i} failed: {result}")
                    results[f"task_{i}"] = {"status": "error", "error": str(result)}
                else:
                    results[f"task_{i}"] = result
            
            # Обновляем время последней синхронизации
            cabinet.last_sync_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return {
                "status": "success",
                "results": results,
                "sync_time": cabinet.last_sync_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Sync all data failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_products(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient
    ) -> Dict[str, Any]:
        """Синхронизация товаров"""
        try:
            # Проверяем кэш
            cache_key = f"products_{cabinet.id}"
            cached_data = await self.cache_manager.get_products_cache(cabinet.id)
            
            if cached_data:
                return {
                    "status": "success",
                    "records_processed": cached_data.get("total", 0),
                    "records_created": 0,
                    "records_updated": 0,
                    "cached": True
                }
            
            # Получаем данные из API
            products_data = await client.get_products()
            
            if not products_data:
                return {"status": "error", "error_message": "No products data received"}
            
            created = 0
            updated = 0
            
            for product_data in products_data:
                nm_id = product_data.get("nmId")
                if not nm_id:
                    continue
                
                # Проверяем существующий товар
                existing = self.db.query(WBProduct).filter(
                    and_(
                        WBProduct.cabinet_id == cabinet.id,
                        WBProduct.nm_id == nm_id
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий товар
                    existing.name = product_data.get("name")
                    existing.vendor_code = product_data.get("vendorCode")
                    existing.brand = product_data.get("brand")
                    existing.category = product_data.get("category")
                    existing.price = product_data.get("price")
                    existing.discount_price = product_data.get("discountPrice")
                    existing.rating = product_data.get("rating")
                    existing.reviews_count = product_data.get("reviewsCount")
                    existing.in_stock = product_data.get("inStock", True)
                    existing.is_active = product_data.get("isActive", True)
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый товар
                    product = WBProduct(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        name=product_data.get("name"),
                        vendor_code=product_data.get("vendorCode"),
                        brand=product_data.get("brand"),
                        category=product_data.get("category"),
                        price=product_data.get("price"),
                        discount_price=product_data.get("discountPrice"),
                        rating=product_data.get("rating"),
                        reviews_count=product_data.get("reviewsCount"),
                        in_stock=product_data.get("inStock", True),
                        is_active=product_data.get("isActive", True)
                    )
                    self.db.add(product)
                    created += 1
            
            self.db.commit()
            
            # Сохраняем в кэш
            await self.cache_manager.set_products_cache(
                cabinet.id, 
                {"total": len(products_data), "products": products_data}
            )
            
            return {
                "status": "success",
                "records_processed": len(products_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Products sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_orders(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """Синхронизация заказов"""
        try:
            # Получаем данные из API
            orders_data = await client.get_orders(date_from, date_to)
            
            if not orders_data:
                return {"status": "error", "error_message": "No orders data received"}
            
            created = 0
            updated = 0
            
            for order_data in orders_data:
                order_id = order_data.get("orderId")
                nm_id = order_data.get("nmId")
                
                # Пропускаем заказы без order_id или nm_id
                if not order_id or not nm_id:
                    continue
                
                # Проверяем существующий заказ
                existing = self.db.query(WBOrder).filter(
                    and_(
                        WBOrder.cabinet_id == cabinet.id,
                        WBOrder.order_id == str(order_id)
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий заказ
                    existing.nm_id = nm_id
                    existing.article = order_data.get("supplierArticle")
                    existing.total_price = order_data.get("totalPrice")
                    existing.finished_price = order_data.get("finishedPrice")
                    existing.discount_percent = order_data.get("discountPercent")
                    existing.is_cancel = order_data.get("isCancel", False)
                    existing.is_realization = order_data.get("isRealization", False)
                    existing.order_date = self._parse_datetime(order_data.get("date"))
                    existing.last_change_date = self._parse_datetime(order_data.get("lastChangeDate"))
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый заказ
                    order = WBOrder(
                        cabinet_id=cabinet.id,
                        order_id=str(order_id),
                        nm_id=nm_id,
                        article=order_data.get("supplierArticle"),
                        total_price=order_data.get("totalPrice"),
                        finished_price=order_data.get("finishedPrice"),
                        discount_percent=order_data.get("discountPercent"),
                        is_cancel=order_data.get("isCancel", False),
                        is_realization=order_data.get("isRealization", False),
                        order_date=self._parse_datetime(order_data.get("date")),
                        last_change_date=self._parse_datetime(order_data.get("lastChangeDate"))
                    )
                    self.db.add(order)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(orders_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Orders sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_stocks(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """Синхронизация остатков"""
        try:
            # Получаем данные из API
            stocks_data = await client.get_stocks(date_from, date_to)
            
            if not stocks_data:
                return {"status": "error", "error_message": "No stocks data received"}
            
            created = 0
            updated = 0
            
            for stock_data in stocks_data:
                nm_id = stock_data.get("nmId")
                warehouse_id = stock_data.get("warehouseId")
                
                # Пропускаем остатки без nm_id
                if not nm_id:
                    continue
                
                # Проверяем существующий остаток
                existing = self.db.query(WBStock).filter(
                    and_(
                        WBStock.cabinet_id == cabinet.id,
                        WBStock.nm_id == nm_id,
                        WBStock.warehouse_id == warehouse_id
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий остаток
                    existing.article = stock_data.get("article")
                    existing.name = stock_data.get("name")
                    existing.brand = stock_data.get("brand")
                    existing.size = stock_data.get("size")
                    existing.barcode = stock_data.get("barcode")
                    existing.quantity = stock_data.get("quantity")
                    existing.in_way_to_client = stock_data.get("inWayToClient")
                    existing.in_way_from_client = stock_data.get("inWayFromClient")
                    existing.warehouse_name = stock_data.get("warehouseName")
                    existing.last_updated = self._parse_datetime(stock_data.get("lastChangeDate"))
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый остаток
                    stock = WBStock(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        article=stock_data.get("article"),
                        name=stock_data.get("name"),
                        brand=stock_data.get("brand"),
                        size=stock_data.get("size"),
                        barcode=stock_data.get("barcode"),
                        quantity=stock_data.get("quantity"),
                        in_way_to_client=stock_data.get("inWayToClient"),
                        in_way_from_client=stock_data.get("inWayFromClient"),
                        warehouse_id=warehouse_id,
                        warehouse_name=stock_data.get("warehouseName"),
                        last_updated=self._parse_datetime(stock_data.get("lastChangeDate"))
                    )
                    self.db.add(stock)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(stocks_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Stocks sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_reviews(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        date_from: str, 
        date_to: str
    ) -> Dict[str, Any]:
        """Синхронизация отзывов"""
        try:
            # Получаем данные из API
            reviews_data = await client.get_reviews(date_from, date_to)
            
            if not reviews_data:
                return {"status": "error", "error_message": "No reviews data received"}
            
            created = 0
            updated = 0
            
            for review_data in reviews_data:
                review_id = review_data.get("reviewId")
                nm_id = review_data.get("nmId")
                
                # Пропускаем отзывы без review_id
                if not review_id:
                    continue
                
                # Проверяем существующий отзыв
                existing = self.db.query(WBReview).filter(
                    and_(
                        WBReview.cabinet_id == cabinet.id,
                        WBReview.review_id == str(review_id)
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий отзыв
                    existing.nm_id = nm_id
                    existing.text = review_data.get("text")
                    existing.rating = review_data.get("rating")
                    existing.is_answered = review_data.get("isAnswered", False)
                    existing.created_date = self._parse_datetime(review_data.get("createdDate"))
                    existing.updated_date = self._parse_datetime(review_data.get("updatedDate"))
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый отзыв
                    review = WBReview(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        review_id=str(review_id),
                        text=review_data.get("text"),
                        rating=review_data.get("rating"),
                        is_answered=review_data.get("isAnswered", False),
                        created_date=self._parse_datetime(review_data.get("createdDate")),
                        updated_date=self._parse_datetime(review_data.get("updatedDate"))
                    )
                    self.db.add(review)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(reviews_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Reviews sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Парсинг даты из строки"""
        if not date_str:
            return None
        
        try:
            # Пробуем разные форматы дат
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            # Если ничего не подошло, возвращаем None
            return None
            
        except Exception:
            return None

    async def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        try:
            # Получаем последние логи синхронизации
            last_sync = self.db.query(WBSyncLog).order_by(
                WBSyncLog.started_at.desc()
            ).first()
            
            if not last_sync:
                return {
                    "status": "never_synced",
                    "message": "Синхронизация никогда не выполнялась"
                }
            
            return {
                "status": last_sync.status,
                "sync_type": last_sync.sync_type,
                "started_at": last_sync.started_at.isoformat() if last_sync.started_at else None,
                "completed_at": last_sync.completed_at.isoformat() if last_sync.completed_at else None,
                "records_processed": last_sync.records_processed,
                "records_created": last_sync.records_created,
                "records_updated": last_sync.records_updated,
                "records_errors": last_sync.records_errors,
                "error_message": last_sync.error_message
            }
            
        except Exception as e:
            logger.error(f"Get sync status failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}