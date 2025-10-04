import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .client import WBAPIClient
from .models import (
    WBCabinet, WBOrder, WBProduct, WBStock, WBReview, 
    WBAnalyticsCache, WBWarehouse, WBSyncLog
)

logger = logging.getLogger(__name__)


class WBSyncService:
    """Сервис синхронизации данных с Wildberries API"""
    
    def __init__(self, db: Session):
        self.db = db
        self.is_running = False

    async def sync_cabinet(
        self, 
        cabinet: WBCabinet, 
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Синхронизация данных для конкретного кабинета"""
        
        sync_log = self.create_sync_log(cabinet.id, "full", "running")
        
        try:
            client = WBAPIClient(cabinet)
            
            # Валидация API ключа
            if not await client.validate_api_key():
                raise Exception("Invalid API key")
            
            # Получаем дату последней синхронизации
            last_sync = cabinet.last_sync_at or datetime.now(timezone.utc) - timedelta(days=7)
            date_from = last_sync.strftime("%Y-%m-%d")
            date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # Синхронизируем данные параллельно
            results = await asyncio.gather(
                self.sync_warehouses(cabinet, client),
                self.sync_products(cabinet, client),
                self.sync_orders(cabinet, client, date_from, date_to),
                self.sync_stocks(cabinet, client, date_from, date_to),
                self.sync_reviews(cabinet, client),
                self.sync_questions(cabinet, client),
                self.sync_sales(cabinet, client, date_from),
                return_exceptions=True
            )
            
            # Обрабатываем результаты
            total_processed = 0
            total_created = 0
            total_updated = 0
            
            for result in results:
                if isinstance(result, dict) and result.get("status") == "success":
                    total_processed += result.get("records_processed", 0)
                    total_created += result.get("records_created", 0)
                    total_updated += result.get("records_updated", 0)
                elif isinstance(result, Exception):
                    logger.error(f"Sync error: {str(result)}")
            
            # Обновляем время последней синхронизации
            cabinet.last_sync_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Обновляем лог синхронизации
            self.update_sync_log(
                sync_log.id, 
                "success", 
                records_processed=total_processed,
                records_created=total_created,
                records_updated=total_updated
            )
            
            return {
                "status": "success",
                "warehouses_processed": results[0].get("records_processed", 0) if not isinstance(results[0], Exception) else 0,
                "products_processed": results[1].get("records_processed", 0) if not isinstance(results[1], Exception) else 0,
                "orders_processed": results[2].get("records_processed", 0) if not isinstance(results[2], Exception) else 0,
                "stocks_processed": results[3].get("records_processed", 0) if not isinstance(results[3], Exception) else 0,
                "reviews_processed": results[4].get("records_processed", 0) if not isinstance(results[4], Exception) else 0,
                "questions_processed": results[5].get("records_processed", 0) if not isinstance(results[5], Exception) else 0,
                "sales_processed": results[6].get("records_processed", 0) if not isinstance(results[6], Exception) else 0
            }
            
        except Exception as e:
            logger.error(f"Sync failed for cabinet {cabinet.id}: {str(e)}")
            
            # Обновляем лог с ошибкой
            self.update_sync_log(sync_log.id, "error", error_message=str(e))
            
            return {
                "status": "error",
                "error_message": str(e)
            }

    async def sync_warehouses(self, cabinet: WBCabinet, client: WBAPIClient) -> Dict[str, Any]:
        """Синхронизация складов"""
        try:
            warehouses_data = await client.get_warehouses()
            
            created = 0
            updated = 0
            
            for warehouse_data in warehouses_data:
                existing = self.db.query(WBWarehouse).filter(
                    and_(
                        WBWarehouse.cabinet_id == cabinet.id,
                        WBWarehouse.warehouse_id == warehouse_data["warehouseId"]
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий склад
                    existing.name = warehouse_data.get("name")
                    existing.address = warehouse_data.get("address")
                    existing.region = warehouse_data.get("region")
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый склад
                    warehouse = WBWarehouse(
                        cabinet_id=cabinet.id,
                        warehouse_id=warehouse_data["warehouseId"],
                        name=warehouse_data.get("name"),
                        address=warehouse_data.get("address"),
                        region=warehouse_data.get("region")
                    )
                    self.db.add(warehouse)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(warehouses_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Warehouses sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_products(self, cabinet: WBCabinet, client: WBAPIClient) -> Dict[str, Any]:
        """Синхронизация товаров"""
        try:
            products_data = await client.get_products()
            
            created = 0
            updated = 0
            
            for product_data in products_data:
                existing = self.db.query(WBProduct).filter(
                    and_(
                        WBProduct.cabinet_id == cabinet.id,
                        WBProduct.nm_id == product_data["nmId"]
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий товар
                    existing.article = product_data.get("vendorCode")
                    existing.brand = product_data.get("brand")
                    existing.name = product_data.get("title")
                    existing.subject = product_data.get("subject")
                    existing.category = product_data.get("category")
                    existing.characteristics = product_data.get("characteristics", [])
                    existing.sizes = [size.get("name") for size in product_data.get("sizes", [])]
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый товар
                    product = WBProduct(
                        cabinet_id=cabinet.id,
                        nm_id=product_data["nmId"],
                        article=product_data.get("vendorCode"),
                        brand=product_data.get("brand"),
                        name=product_data.get("title"),
                        subject=product_data.get("subject"),
                        category=product_data.get("category"),
                        characteristics=product_data.get("characteristics", []),
                        sizes=[size.get("name") for size in product_data.get("sizes", [])]
                    )
                    self.db.add(product)
                    created += 1
            
            self.db.commit()
            
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
            orders_data = await client.get_orders(date_from, date_to)
            
            created = 0
            updated = 0
            
            for order_data in orders_data:
                existing = self.db.query(WBOrder).filter(
                    and_(
                        WBOrder.cabinet_id == cabinet.id,
                        WBOrder.order_id == str(order_data.get("orderId", ""))
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий заказ
                    existing.nm_id = order_data.get("nmId")
                    existing.article = order_data.get("supplierArticle")
                    existing.total_price = order_data.get("totalPrice")
                    existing.finished_price = order_data.get("finishedPrice")
                    existing.discount_percent = order_data.get("discountPercent")
                    existing.is_cancel = order_data.get("isCancel", False)
                    existing.is_realization = order_data.get("isRealization", False)
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый заказ
                    order = WBOrder(
                        cabinet_id=cabinet.id,
                        order_id=str(order_data.get("orderId", "")),
                        nm_id=order_data.get("nmId"),
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
            stocks_data = await client.get_stocks(date_from, date_to)
            
            created = 0
            updated = 0
            
            for stock_data in stocks_data:
                existing = self.db.query(WBStock).filter(
                    and_(
                        WBStock.cabinet_id == cabinet.id,
                        WBStock.nm_id == stock_data.get("nmId"),
                        WBStock.warehouse_id == stock_data.get("warehouseId"),
                        WBStock.size == stock_data.get("size")
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий остаток
                    existing.quantity = stock_data.get("quantity")
                    existing.price = stock_data.get("price")
                    existing.discount = stock_data.get("discount")
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый остаток
                    stock = WBStock(
                        cabinet_id=cabinet.id,
                        nm_id=stock_data.get("nmId"),
                        warehouse_id=stock_data.get("warehouseId"),
                        warehouse_name=stock_data.get("warehouseName"),
                        article=stock_data.get("supplierArticle"),
                        size=stock_data.get("size"),
                        quantity=stock_data.get("quantity"),
                        price=stock_data.get("price"),
                        discount=stock_data.get("discount"),
                        last_change_date=self._parse_datetime(stock_data.get("lastChangeDate"))
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

    async def sync_reviews(self, cabinet: WBCabinet, client: WBAPIClient) -> Dict[str, Any]:
        """Синхронизация отзывов"""
        try:
            reviews_data = await client.get_reviews()
            reviews = reviews_data.get("data", {}).get("feedbacks", [])
            
            created = 0
            updated = 0
            
            for review_data in reviews:
                existing = self.db.query(WBReview).filter(
                    and_(
                        WBReview.cabinet_id == cabinet.id,
                        WBReview.review_id == str(review_data.get("id", ""))
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий отзыв
                    existing.text = review_data.get("text")
                    existing.rating = review_data.get("productValuation")
                    existing.is_answered = review_data.get("isAnswered", False)
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый отзыв
                    review = WBReview(
                        cabinet_id=cabinet.id,
                        nm_id=review_data.get("nmId"),
                        review_id=str(review_data.get("id", "")),
                        text=review_data.get("text"),
                        rating=review_data.get("productValuation"),
                        is_answered=review_data.get("isAnswered", False),
                        created_date=self._parse_datetime(review_data.get("createdDate"))
                    )
                    self.db.add(review)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(reviews),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Reviews sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_questions(self, cabinet: WBCabinet, client: WBAPIClient) -> Dict[str, Any]:
        """Синхронизация вопросов"""
        try:
            questions_data = await client.get_questions()
            questions = questions_data.get("data", {}).get("questions", [])
            
            created = 0
            updated = 0
            
            for question_data in questions:
                existing = self.db.query(WBReview).filter(
                    and_(
                        WBReview.cabinet_id == cabinet.id,
                        WBReview.review_id == str(question_data.get("id", ""))
                    )
                ).first()
                
                if existing:
                    # Обновляем существующий вопрос
                    existing.text = question_data.get("text")
                    existing.is_answered = question_data.get("isAnswered", False)
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый вопрос (используем ту же таблицу что и отзывы)
                    question = WBReview(
                        cabinet_id=cabinet.id,
                        nm_id=question_data.get("nmId"),
                        review_id=str(question_data.get("id", "")),
                        text=question_data.get("text"),
                        rating=None,  # У вопросов нет рейтинга
                        is_answered=question_data.get("isAnswered", False),
                        created_date=self._parse_datetime(question_data.get("createdDate"))
                    )
                    self.db.add(question)
                    created += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(questions),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Questions sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_sales(self, cabinet: WBCabinet, client: WBAPIClient, date_from: str) -> Dict[str, Any]:
        """Синхронизация продаж"""
        try:
            sales_data = await client.get_sales(date_from)
            
            # Продажи обычно не хранятся отдельно, а используются для расчета аналитики
            # Здесь мы можем обновить кэш аналитики
            
            return {
                "status": "success",
                "records_processed": len(sales_data),
                "records_created": 0,
                "records_updated": 0
            }
            
        except Exception as e:
            logger.error(f"Sales sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def sync_all_active_cabinets(self) -> Dict[str, Any]:
        """Синхронизация всех активных кабинетов"""
        try:
            self.is_running = True
            
            cabinets = self.get_active_cabinets()
            results = []
            
            for cabinet in cabinets:
                result = await self.sync_cabinet(cabinet)
                results.append(result)
            
            self.is_running = False
            
            return {
                "status": "success",
                "cabinets_processed": len(cabinets),
                "results": results
            }
            
        except Exception as e:
            self.is_running = False
            logger.error(f"Sync all cabinets failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    def get_active_cabinets(self) -> List[WBCabinet]:
        """Получение списка активных кабинетов"""
        return self.db.query(WBCabinet).filter(WBCabinet.is_active == True).all()

    def create_sync_log(
        self, 
        cabinet_id: int, 
        sync_type: str, 
        status: str = "running"
    ) -> WBSyncLog:
        """Создание лога синхронизации"""
        sync_log = WBSyncLog(
            cabinet_id=cabinet_id,
            sync_type=sync_type,
            status=status,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(sync_log)
        self.db.commit()
        return sync_log

    def update_sync_log(
        self, 
        log_id: int, 
        status: str, 
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        records_skipped: int = 0,
        error_message: str = None
    ):
        """Обновление лога синхронизации"""
        sync_log = self.db.query(WBSyncLog).filter(WBSyncLog.id == log_id).first()
        if sync_log:
            sync_log.status = status
            sync_log.finished_at = datetime.now(timezone.utc)
            sync_log.records_processed = records_processed
            sync_log.records_created = records_created
            sync_log.records_updated = records_updated
            sync_log.records_skipped = records_skipped
            sync_log.error_message = error_message
            self.db.commit()

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Парсинг даты из строки"""
        if not date_str:
            return None
        
        try:
            # Пробуем разные форматы
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def calculate_analytics(
        self, 
        nm_id: int, 
        orders_data: List[Dict], 
        reviews_data: List[Dict]
    ) -> Dict[str, Any]:
        """Расчет аналитики для товара"""
        # Подсчет продаж
        sales_count = len([o for o in orders_data if o.get("isRealization", False)])
        sales_amount = sum(o.get("totalPrice", 0) for o in orders_data if o.get("isRealization", False))
        
        # Подсчет выкупов
        buyouts_count = len([o for o in orders_data if o.get("isRealization", False) and not o.get("isCancel", False)])
        buyouts_amount = sum(o.get("totalPrice", 0) for o in orders_data if o.get("isRealization", False) and not o.get("isCancel", False))
        
        # Расчет выкупа
        buyout_rate = buyouts_count / sales_count if sales_count > 0 else 0
        
        # Расчет рейтинга
        ratings = [r.get("productValuation", 0) for r in reviews_data if r.get("productValuation")]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        return {
            "sales_count": sales_count,
            "sales_amount": sales_amount,
            "buyouts_count": buyouts_count,
            "buyouts_amount": buyouts_amount,
            "buyout_rate": buyout_rate,
            "avg_rating": avg_rating,
            "reviews_count": len(reviews_data)
        }

    def analyze_delta(
        self, 
        old_data: List[Dict], 
        new_data: List[Dict], 
        key_field: str
    ) -> Dict[str, List[Dict]]:
        """Анализ изменений в данных"""
        old_keys = {item[key_field]: item for item in old_data}
        new_keys = {item[key_field]: item for item in new_data}
        
        created = [item for key, item in new_keys.items() if key not in old_keys]
        updated = [item for key, item in new_keys.items() if key in old_keys and item != old_keys[key]]
        deleted = [item for key, item in old_keys.items() if key not in new_keys]
        
        return {
            "created": created,
            "updated": updated,
            "deleted": deleted
        }

    def log_sync_error(self, cabinet_id: int, error_type: str, error_message: str):
        """Логирование ошибки синхронизации"""
        logger.error(f"Cabinet {cabinet_id}: {error_type} - {error_message}")

    def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        last_sync = self.db.query(WBSyncLog).filter(
            WBSyncLog.status == "success"
        ).order_by(WBSyncLog.finished_at.desc()).first()
        
        active_cabinets = self.get_active_cabinets()
        
        return {
            "is_running": self.is_running,
            "last_sync": last_sync.finished_at.isoformat() if last_sync else None,
            "next_sync": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "total_cabinets": len(active_cabinets),
            "active_cabinets": len(active_cabinets)
        }

    async def health_check(self) -> bool:
        """Проверка здоровья сервиса синхронизации"""
        try:
            # Простая проверка подключения к БД
            self.db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Sync service health check failed: {str(e)}")
            return False