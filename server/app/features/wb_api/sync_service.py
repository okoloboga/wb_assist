import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBSyncLog
from .client import WBAPIClient
from .cache_manager import WBCacheManager
from app.features.user.models import User

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
            # Проверяем, нужно ли отправлять уведомления (один раз в начале)
            should_notify = await self._should_send_notification(cabinet)
            if should_notify:
                logger.info(f"📢 Notifications ENABLED for cabinet {cabinet.id}")
            else:
                logger.info(f"🔇 Notifications DISABLED for cabinet {cabinet.id} (first sync or long break)")
            
            client = WBAPIClient(cabinet)
            
            # Определяем период синхронизации (последние 30 дней)
            date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
            
            results = {}
            
            # Синхронизируем данные последовательно для избежания конфликтов
            logger.info(f"Starting sync_all_data for cabinet {cabinet.id}")
            sync_tasks = [
                ("products", self.sync_products(cabinet, client)),
                ("orders", self.sync_orders(cabinet, client, date_from, date_to, should_notify)),
                ("stocks", self.sync_stocks(cabinet, client, date_from, date_to)),
                ("reviews", self.sync_reviews(cabinet, client, date_from, date_to))
            ]
            
            for task_name, task in sync_tasks:
                try:
                    result = await task
                    results[task_name] = result
                    logger.info(f"Sync {task_name} completed: {result.get('status', 'unknown')}")
                except Exception as e:
                    logger.error(f"Sync {task_name} failed: {e}")
                    results[task_name] = {"status": "error", "error": str(e)}
            
            # Обновляем цены товаров из остатков
            try:
                price_result = await self.update_product_prices_from_stocks(cabinet)
                results["product_prices"] = price_result
                logger.info(f"Product prices updated: {price_result.get('updated_products', 0)} products")
            except Exception as e:
                logger.error(f"Failed to update product prices: {e}")
                results["product_prices"] = {"status": "error", "error": str(e)}
            
            # Обновляем рейтинги товаров из отзывов
            try:
                rating_result = await self.update_product_ratings_from_reviews(cabinet)
                results["product_ratings"] = rating_result
                logger.info(f"Product ratings updated: {rating_result.get('updated_products', 0)} products")
            except Exception as e:
                logger.error(f"Failed to update product ratings: {e}")
                results["product_ratings"] = {"status": "error", "error": str(e)}
            
            # Обновляем время последней синхронизации
            cabinet.last_sync_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Планируем автоматическую синхронизацию для нового кабинета
            if not cabinet.last_sync_at:
                logger.info(f"Планируем автоматическую синхронизацию для кабинета {cabinet.id}")
                # Импортируем здесь, чтобы избежать циклического импорта
                from app.features.sync.tasks import schedule_cabinet_sync
                schedule_cabinet_sync(cabinet.id)
            
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
            
            logger.info(f"Fetched {len(products_data)} products from WB API")
            
            created = 0
            updated = 0
            
            for product_data in products_data:
                nm_id = product_data.get("nmID")  # Исправлено: nmID вместо nmId
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
                    existing.name = product_data.get("title")  # Исправлено: title вместо name
                    existing.vendor_code = product_data.get("vendorCode")
                    existing.brand = product_data.get("brand")
                    existing.category = product_data.get("subjectName")  # Исправлено: subjectName вместо category
                    # Цены и рейтинги получаем из других API (остатки, отзывы)
                    # existing.price = product_data.get("price")  # НЕТ в API товаров
                    # existing.discount_price = product_data.get("discountPrice")  # НЕТ в API товаров
                    # existing.rating = product_data.get("rating")  # НЕТ в API товаров
                    # existing.reviews_count = product_data.get("reviewsCount")  # НЕТ в API товаров
                    existing.in_stock = product_data.get("inStock", True)
                    existing.is_active = product_data.get("isActive", True)
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый товар
                    product = WBProduct(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        name=product_data.get("title"),  # Исправлено: title вместо name
                        vendor_code=product_data.get("vendorCode"),
                        brand=product_data.get("brand"),
                        category=product_data.get("subjectName"),  # Исправлено: subjectName вместо category
                        # Цены и рейтинги получаем из других API (остатки, отзывы)
                        # price=product_data.get("price"),  # НЕТ в API товаров
                        # discount_price=product_data.get("discountPrice"),  # НЕТ в API товаров
                        # rating=product_data.get("rating"),  # НЕТ в API товаров
                        # reviews_count=product_data.get("reviewsCount"),  # НЕТ в API товаров
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
        date_to: str,
        should_notify: bool = False
    ) -> Dict[str, Any]:
        """Синхронизация заказов"""
        try:
            # Добавляем таймаут для всего процесса
            import asyncio
            return await asyncio.wait_for(
                self._sync_orders_internal(cabinet, client, date_from, date_to, should_notify),
                timeout=300  # 5 минут максимум
            )
        except asyncio.TimeoutError:
            logger.error("Orders sync timeout after 5 minutes")
            return {"status": "error", "error_message": "Sync timeout"}
        except Exception as e:
            logger.error(f"Orders sync failed: {str(e)}")
            return {"status": "error", "error_message": str(e)}

    async def _sync_orders_internal(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        date_from: str, 
        date_to: str,
        should_notify: bool = False
    ) -> Dict[str, Any]:
        """Внутренний метод синхронизации заказов"""
        try:
            logger.info(f"Starting orders sync for cabinet {cabinet.id}, dates: {date_from} to {date_to}")
            
            # Проверяем, сколько товаров есть в базе для этого кабинета
            products_count = self.db.query(WBProduct).filter(WBProduct.cabinet_id == cabinet.id).count()
                # logger.info(f"Products in database for cabinet {cabinet.id}: {products_count}")
            
            # Получаем данные из API
            logger.info("Fetching orders from WB API...")
            orders_data = await client.get_orders(date_from, date_to)
            logger.info(f"Received {len(orders_data) if orders_data else 0} orders from API")
            
            # Получаем комиссии для расчета
            try:
                commissions_data = await client.get_commissions()
                logger.info(f"Commissions data type: {type(commissions_data)}, length: {len(commissions_data) if isinstance(commissions_data, list) else 'N/A'}")
                # logger.info(f"Commissions data content: {commissions_data}")
            except Exception as e:
                logger.error(f"Failed to get commissions: {e}")
                commissions_data = []
            
            if not orders_data:
                return {"status": "error", "error_message": "No orders data received"}
            
            created = 0
            updated = 0
            processed_order_ids = set()  # Отслеживаем обработанные order_id в рамках одного запроса
            
            logger.info(f"Processing {len(orders_data)} orders from WB API")
            
            
            for i, order_data in enumerate(orders_data):
                try:
                    order_id = order_data.get("gNumber")
                    nm_id = order_data.get("nmId")
                    
                    # Пропускаем заказы без order_id или nm_id
                    if not order_id or not nm_id:
                        continue
                    
                    # Специальная обработка для заказов без nm_id в базе
                    if not nm_id:
                        logger.warning(f"Order {order_id} has no nm_id in WB API data")
                        continue
                    
                    # Пропускаем дубликаты в рамках одного запроса
                    if order_id in processed_order_ids:
                        continue
                    processed_order_ids.add(order_id)
                    
                    # Проверяем существующий заказ
                    existing = self.db.query(WBOrder).filter(
                        and_(
                            WBOrder.cabinet_id == cabinet.id,
                            WBOrder.order_id == str(order_id)
                        )
                    ).first()
                    
                    if existing:
                        # Обновляем существующий заказ
                        old_nm_id = existing.nm_id
                        existing.nm_id = nm_id
                        if old_nm_id != nm_id:
                            logger.info(f"Updated order {order_id}: nm_id {old_nm_id} -> {nm_id}")
                        # else:
                            # Order already has nm_id, no need to log
                        existing.article = order_data.get("supplierArticle")
                        existing.name = order_data.get("subject")  # Исправлено: subject вместо name
                        existing.brand = order_data.get("brand")
                        existing.size = order_data.get("techSize")  # Исправлено: techSize вместо size
                        existing.barcode = order_data.get("barcode")
                        existing.quantity = 1  # Исправлено: всегда 1, так как нет поля quantity
                        existing.price = order_data.get("finishedPrice")  # Исправлено: finishedPrice вместо price
                        existing.total_price = order_data.get("totalPrice")
                        existing.status = "canceled" if order_data.get("isCancel", False) else "active"  # Исправлено: вычисляем статус
                        existing.order_date = self._parse_datetime(order_data.get("date"))
                        
                        # Получаем категорию и предмет из товара по nmId
                        product = self.db.query(WBProduct).filter(
                            and_(
                                WBProduct.cabinet_id == cabinet.id,
                                WBProduct.nm_id == nm_id
                            )
                        ).first()
                        
                        if product:
                            existing.category = product.category  # subjectName из товара
                            existing.subject = product.name       # title из товара
                            # logger.info(f"Found product for nmId={nm_id}: category='{product.category}', subject='{product.name}'")
                        else:
                            # Fallback: используем данные из заказа
                            existing.category = order_data.get("subject")  # subject из заказа как категория
                            existing.subject = order_data.get("subject")   # subject из заказа как предмет
                            # logger.info(f"Product not found for nmId={nm_id}, using order data: category='{existing.category}', subject='{existing.subject}'")
                        
                        total_price = order_data.get("totalPrice", 0)
                        commission_percent, commission_amount = self._calculate_commission(
                            existing.category, existing.subject, total_price, commissions_data
                        )
                        existing.commission_percent = commission_percent
                        existing.commission_amount = commission_amount
                        
                        # Новые поля из WB API
                        existing.warehouse_from = order_data.get("warehouseName")
                        existing.warehouse_to = order_data.get("regionName")
                        existing.spp_percent = order_data.get("spp")
                        existing.customer_price = order_data.get("finishedPrice")
                        existing.discount_percent = order_data.get("discountPercent")
                        
                        # Расчет логистики (упрощенный расчет)
                        logistics_amount = self._calculate_logistics(
                            order_data.get("warehouseName"), 
                            order_data.get("regionName"),
                            total_price
                        )
                        existing.logistics_amount = logistics_amount
                        
                        # logger.info(f"Updated order {order_id}: commission_percent={commission_percent}, commission_amount={commission_amount}")
                        
                        existing.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Создаем новый заказ
                        try:
                            # Получаем категорию и предмет из товара по nmId
                            product = self.db.query(WBProduct).filter(
                                and_(
                                    WBProduct.cabinet_id == cabinet.id,
                                    WBProduct.nm_id == nm_id
                                )
                            ).first()
                            
                            if product:
                                category = product.category  # subjectName из товара
                                subject = product.name       # title из товара
                                # logger.info(f"Found product for nmId={nm_id}: category='{product.category}', subject='{product.name}'")
                            else:
                                # Fallback: используем данные из заказа
                                category = order_data.get("subject")  # subject из заказа как категория
                                subject = order_data.get("subject")   # subject из заказа как предмет
                                # logger.info(f"Product not found for nmId={nm_id}, using order data: category='{category}', subject='{subject}'")
                            
                            total_price = order_data.get("totalPrice", 0)
                            commission_percent, commission_amount = self._calculate_commission(
                                category, subject, total_price, commissions_data
                            )
                            
                            
                            order = WBOrder(
                                cabinet_id=cabinet.id,
                                order_id=str(order_id),
                                nm_id=nm_id,
                                article=order_data.get("supplierArticle"),
                                name=order_data.get("subject"),  # Исправлено: subject вместо name
                                brand=order_data.get("brand"),
                                size=order_data.get("techSize"),  # Исправлено: techSize вместо size
                                barcode=order_data.get("barcode"),
                                # Поля категории и комиссии
                                category=category,
                                subject=subject,
                                commission_percent=commission_percent,
                                commission_amount=commission_amount,
                                quantity=1,  # Исправлено: всегда 1, так как нет поля quantity
                                price=order_data.get("finishedPrice"),  # Исправлено: finishedPrice вместо price
                                total_price=order_data.get("totalPrice"),
                                # Новые поля из WB API
                                warehouse_from=order_data.get("warehouseName"),
                                warehouse_to=order_data.get("regionName"),
                                spp_percent=order_data.get("spp"),
                                customer_price=order_data.get("finishedPrice"),
                                discount_percent=order_data.get("discountPercent"),
                                # Расчет логистики (упрощенный расчет)
                                logistics_amount=self._calculate_logistics(
                                    order_data.get("warehouseName"), 
                                    order_data.get("regionName"),
                                    total_price
                                ),
                                status="canceled" if order_data.get("isCancel", False) else "active",  # Исправлено: вычисляем статус
                                order_date=self._parse_datetime(order_data.get("date"))
                            )
                            
                            self.db.add(order)
                            self.db.flush()  # Принудительно выполняем вставку для проверки уникальности
                            
                            # Отправляем уведомление о новом заказе только если разрешено
                            if should_notify:
                                await self._send_new_order_notification(cabinet, order_data, order)
                            
                            # logger.info(f"Created order {order_id}: commission_percent={commission_percent}, commission_amount={commission_amount}")
                            created += 1
                        except Exception as insert_error:
                            # Если заказ уже существует (race condition), пропускаем его
                            if "duplicate key" in str(insert_error).lower() or "unique constraint" in str(insert_error).lower():
                                logger.warning(f"Order {order_id} already exists, skipping")
                                continue
                            else:
                                raise insert_error
                        
                except Exception as order_error:
                    logger.warning(f"Failed to process order {order_id}: {order_error}")
                    continue
            
            self.db.commit()
            
            return {
                "status": "success",
                "records_processed": len(orders_data),
                "records_created": created,
                "records_updated": updated
            }
            
        except Exception as e:
            logger.error(f"Orders sync failed: {str(e)}")
            # Откатываем транзакцию при ошибке
            try:
                self.db.rollback()
            except:
                pass
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
                    existing.article = stock_data.get("supplierArticle")
                    existing.name = stock_data.get("name")  # НЕТ в API, оставляем как есть
                    existing.brand = stock_data.get("brand")
                    existing.size = stock_data.get("techSize")
                    existing.barcode = stock_data.get("barcode")
                    existing.quantity = stock_data.get("quantity")
                    existing.in_way_to_client = stock_data.get("inWayToClient")
                    existing.in_way_from_client = stock_data.get("inWayFromClient")
                    existing.warehouse_name = stock_data.get("warehouseName")
                    existing.last_updated = self._parse_datetime(stock_data.get("lastChangeDate"))
                    # Новые поля из WB API
                    existing.category = stock_data.get("category")
                    existing.subject = stock_data.get("subject")
                    existing.price = stock_data.get("Price")
                    existing.discount = stock_data.get("Discount")
                    existing.quantity_full = stock_data.get("quantityFull")
                    existing.is_supply = stock_data.get("isSupply")
                    existing.is_realization = stock_data.get("isRealization")
                    existing.sc_code = stock_data.get("SCCode")
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый остаток
                    stock = WBStock(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        article=stock_data.get("supplierArticle"),
                        name=stock_data.get("name"),  # НЕТ в API, оставляем как есть
                        brand=stock_data.get("brand"),
                        size=stock_data.get("techSize"),
                        barcode=stock_data.get("barcode"),
                        quantity=stock_data.get("quantity"),
                        in_way_to_client=stock_data.get("inWayToClient"),
                        in_way_from_client=stock_data.get("inWayFromClient"),
                        warehouse_id=warehouse_id,
                        warehouse_name=stock_data.get("warehouseName"),
                        last_updated=self._parse_datetime(stock_data.get("lastChangeDate")),
                        # Новые поля из WB API
                        category=stock_data.get("category"),
                        subject=stock_data.get("subject"),
                        price=stock_data.get("Price"),
                        discount=stock_data.get("Discount"),
                        quantity_full=stock_data.get("quantityFull"),
                        is_supply=stock_data.get("isSupply"),
                        is_realization=stock_data.get("isRealization"),
                        sc_code=stock_data.get("SCCode")
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
            # Получаем ВСЕ отзывы с пагинацией
            all_reviews_data = []
            skip = 0
            take = 1000
            total_fetched = 0
            
            while True:
                reviews_response = await client.get_reviews(is_answered=True, take=take, skip=skip)
                
                if not reviews_response or "data" not in reviews_response:
                    break
                
                reviews_data = reviews_response["data"].get("feedbacks", [])
                if not reviews_data:
                    break
                
                all_reviews_data.extend(reviews_data)
                total_fetched += len(reviews_data)
                
                logger.info(f"Fetched {len(reviews_data)} reviews (skip={skip}, total={total_fetched})")
                
                # Если получили меньше чем запрашивали, значит это последняя страница
                if len(reviews_data) < take:
                    break
                
                skip += take
            
            logger.info(f"Total reviews fetched from WB API: {total_fetched}")
            
            if not all_reviews_data:
                return {"status": "success", "records_processed": 0, "records_created": 0, "records_updated": 0}
            
            reviews_data = all_reviews_data
            
            created = 0
            updated = 0
            
            for review_data in reviews_data:
                review_id = review_data.get("id")  # Исправлено: id вместо reviewId
                nm_id = review_data.get("productDetails", {}).get("nmId")  # Исправлено: из productDetails
                
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
                    existing.rating = review_data.get("productValuation")  # Исправлено: productValuation вместо rating
                    existing.is_answered = review_data.get("answer") is not None  # Исправлено: проверяем наличие ответа
                    existing.created_date = self._parse_datetime(review_data.get("createdDate"))
                    existing.updated_date = self._parse_datetime(review_data.get("createdDate"))  # Исправлено: нет updatedDate
                    
                    # Новые поля из WB API отзывов
                    existing.pros = review_data.get("pros")
                    existing.cons = review_data.get("cons")
                    existing.user_name = review_data.get("userName")
                    existing.color = review_data.get("color")
                    existing.bables = str(review_data.get("bables", [])) if review_data.get("bables") else None
                    existing.matching_size = review_data.get("matchingSize")
                    existing.was_viewed = review_data.get("wasViewed")
                    existing.supplier_feedback_valuation = review_data.get("supplierFeedbackValuation")
                    existing.supplier_product_valuation = review_data.get("supplierProductValuation")
                    
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Создаем новый отзыв
                    review = WBReview(
                        cabinet_id=cabinet.id,
                        nm_id=nm_id,
                        review_id=str(review_id),
                        text=review_data.get("text"),
                        rating=review_data.get("productValuation"),  # Исправлено: productValuation вместо rating
                        is_answered=review_data.get("answer") is not None,  # Исправлено: проверяем наличие ответа
                        created_date=self._parse_datetime(review_data.get("createdDate")),
                        updated_date=self._parse_datetime(review_data.get("createdDate")),  # Исправлено: нет updatedDate
                        
                        # Новые поля из WB API отзывов
                        pros=review_data.get("pros"),
                        cons=review_data.get("cons"),
                        user_name=review_data.get("userName"),
                        color=review_data.get("color"),
                        bables=str(review_data.get("bables", [])) if review_data.get("bables") else None,
                        matching_size=review_data.get("matchingSize"),
                        was_viewed=review_data.get("wasViewed"),
                        supplier_feedback_valuation=review_data.get("supplierFeedbackValuation"),
                        supplier_product_valuation=review_data.get("supplierProductValuation")
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

    def _calculate_commission(self, category: str, subject: str, total_price: float, commissions_data) -> tuple[float, float]:
        """Расчет комиссии для заказа на основе категории и предмета"""
        try:
            if not category or not subject or not total_price or not commissions_data:
                # logger.warning(f"Missing data: category={category}, subject={subject}, total_price={total_price}, commissions_data={bool(commissions_data)}")
                return 0.0, 0.0
            
            # logger.info(f"Calculating commission for category='{category}', subject='{subject}', total_price={total_price}")
            
            # Проверяем, что commissions_data - это список
            if not isinstance(commissions_data, list):
                logger.warning(f"Commissions data is not a list: {type(commissions_data)}")
                return 0.0, 0.0
            
            if len(commissions_data) == 0:
                logger.warning("Commissions data is empty")
                return 0.0, 0.0
            
            # logger.info(f"Searching through {len(commissions_data)} commission records")
            # logger.info(f"First commission record structure: {commissions_data[0] if commissions_data else 'No data'}")
            
            # Ищем комиссию по категории и предмету (точное совпадение)
            for i, commission in enumerate(commissions_data):
                if not isinstance(commission, dict):
                    logger.debug(f"Commission record {i} is not a dict: {type(commission)}")
                    continue
                    
                parent_name = commission.get("parentName")
                subject_name = commission.get("subjectName")
                kgvp_marketplace = commission.get("kgvpMarketplace")
                
                # logger.info(f"Commission {i}: parentName='{parent_name}', subjectName='{subject_name}', kgvpMarketplace={kgvp_marketplace}")
                
                # Точное совпадение
                if (parent_name == category and subject_name == subject):
                    commission_percent = float(kgvp_marketplace) if kgvp_marketplace is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found exact match: {category}/{subject} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
                
                # Нечеткое совпадение по предмету (если категории совпадают)
                if (parent_name == category and subject_name and subject and 
                    (subject_name.lower() in subject.lower() or subject.lower() in subject_name.lower())):
                    commission_percent = float(kgvp_marketplace) if kgvp_marketplace is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found fuzzy match: {category}/{subject} ~ {parent_name}/{subject_name} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
            
            # Если точного совпадения нет, ищем по категории
            # logger.info(f"No exact match found, searching by category: {category}")
            for i, commission in enumerate(commissions_data):
                if not isinstance(commission, dict):
                    continue
                
                parent_name = commission.get("parentName")
                kgvp_marketplace = commission.get("kgvpMarketplace")
                
                # Точное совпадение по категории
                if parent_name == category:
                    commission_percent = float(kgvp_marketplace) if kgvp_marketplace is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found exact category match: {category} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
                
                # Нечеткое совпадение по категории
                if (parent_name and category and 
                    (parent_name.lower() in category.lower() or category.lower() in parent_name.lower())):
                    commission_percent = float(kgvp_marketplace) if kgvp_marketplace is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found fuzzy category match: {category} ~ {parent_name} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
            
            # Если ничего не найдено, используем дефолтную комиссию 20%

            commission_percent = 20.0
            commission_amount = (total_price * commission_percent) / 100
            return commission_percent, commission_amount
            
        except Exception as e:
            logger.error(f"Commission calculation failed: {e}")
            return 0.0, 0.0
    
    def _calculate_logistics(self, warehouse_from: str, warehouse_to: str, total_price: float) -> float:
        """Расчет логистики на основе склада отправления и региона доставки"""
        try:
            if not warehouse_from or not warehouse_to or not total_price:
                return 0.0
            
            # Упрощенный расчет логистики на основе расстояния и цены
            # В реальности нужно использовать тарифы WB API
            
            # Базовые тарифы по регионам (примерные)
            region_tariffs = {
                "Москва": 0.0,  # Бесплатная доставка в Москву
                "Московская область": 50.0,
                "Санкт-Петербург": 100.0,
                "Ленинградская область": 150.0,
                "Центральный федеральный округ": 200.0,
                "Северо-Западный федеральный округ": 250.0,
                "Южный федеральный округ": 300.0,
                "Приволжский федеральный округ": 350.0,
                "Уральский федеральный округ": 400.0,
                "Сибирский федеральный округ": 500.0,
                "Дальневосточный федеральный округ": 600.0,
            }
            
            # Ищем тариф для региона
            for region, tariff in region_tariffs.items():
                if region in warehouse_to:
                    return tariff
            
            # Если регион не найден, используем средний тариф
            return 300.0
            
        except Exception as e:
            logger.error(f"Logistics calculation failed: {e}")
            return 0.0

    async def update_product_prices_from_stocks(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Обновление цен товаров из остатков"""
        try:
            # Получаем все остатки для кабинета
            stocks = self.db.query(WBStock).filter(
                WBStock.cabinet_id == cabinet.id
            ).all()
            
            updated_count = 0
            
            for stock in stocks:
                if stock.price is not None:
                    # Обновляем цену товара
                    product = self.db.query(WBProduct).filter(
                        and_(
                            WBProduct.cabinet_id == cabinet.id,
                            WBProduct.nm_id == stock.nm_id
                        )
                    ).first()
                    
                    if product:
                        product.price = stock.price
                        product.discount_price = stock.discount if stock.discount else None
                        updated_count += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "updated_products": updated_count
            }
            
        except Exception as e:
            logger.error(f"Failed to update product prices: {e}")
            return {"status": "error", "error_message": str(e)}

    async def update_product_ratings_from_reviews(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Обновление рейтингов товаров из отзывов"""
        try:
            # Получаем все отзывы для кабинета
            reviews = self.db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id
            ).all()
            
            # Группируем отзывы по товарам
            product_reviews = {}
            for review in reviews:
                if review.nm_id and review.rating:
                    if review.nm_id not in product_reviews:
                        product_reviews[review.nm_id] = []
                    product_reviews[review.nm_id].append(review.rating)
            
            updated_count = 0
            
            # Обновляем рейтинги товаров
            for nm_id, ratings in product_reviews.items():
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    
                    product = self.db.query(WBProduct).filter(
                        and_(
                            WBProduct.cabinet_id == cabinet.id,
                            WBProduct.nm_id == nm_id
                        )
                    ).first()
                    
                    if product:
                        product.rating = round(avg_rating, 1)
                        product.reviews_count = len(ratings)
                        updated_count += 1
            
            self.db.commit()
            
            return {
                "status": "success",
                "updated_products": updated_count
            }
            
        except Exception as e:
            logger.error(f"Failed to update product ratings: {e}")
            return {"status": "error", "error_message": str(e)}

    async def _send_new_order_notification(self, cabinet: WBCabinet, order_data: Dict[str, Any], order: WBOrder):
        """Отправка уведомления о новом заказе"""
        try:
            # Импортируем WebhookSender здесь, чтобы избежать циклического импорта
            from app.features.bot_api.webhook import WebhookSender
            
            # Получаем пользователя кабинета
            user = self.db.query(User).filter(User.id == cabinet.user_id).first()
            if not user:
                logger.warning(f"User not found for cabinet {cabinet.id}")
                return
            
            # Формируем данные для уведомления
            today_stats = await self._get_today_stats(cabinet)
            stocks = await self._get_order_stocks(cabinet, order.nm_id)
            
            notification_data = {
                "order_id": order.order_id,
                "date": order.order_date.isoformat() if order.order_date else datetime.now(timezone.utc).isoformat(),
                "amount": float(order.total_price or 0),
                "product_name": order.name or "Неизвестно",
                "brand": order.brand or "Неизвестно",
                "warehouse_from": order.warehouse_from or "Неизвестно",
                "warehouse_to": order.warehouse_to or "Неизвестно",
                "today_stats": today_stats,
                "stocks": stocks
            }
            
            # Логируем данные, которые отправляются в бота
            logger.info(f"📤 WEBHOOK DATA for user {user.telegram_id}:")
            logger.info(f"   Order ID: {notification_data['order_id']}")
            logger.info(f"   Amount: {notification_data['amount']}₽")
            logger.info(f"   Product: {notification_data['product_name']}")
            logger.info(f"   Brand: {notification_data['brand']}")
            logger.info(f"   Route: {notification_data['warehouse_from']} → {notification_data['warehouse_to']}")
            logger.info(f"   Today stats: {today_stats}")
            logger.info(f"   Stocks: {stocks}")
            logger.info(f"   Telegram ID: {user.telegram_id}")
            logger.info(f"   Cabinet ID: {cabinet.id}")
            
            # URL бота для webhook
            bot_webhook_url = f"http://bot-webhook:8001/webhook/notifications"
            
            # Создаем экземпляр WebhookSender
            webhook_sender = WebhookSender()
            
            # Отправляем уведомление
            result = await webhook_sender.send_new_order_notification(
                telegram_id=user.telegram_id,
                order_data=notification_data,
                bot_webhook_url=bot_webhook_url
            )
            
            if result.get("success"):
                logger.info(f"✅ WEBHOOK SUCCESS: Order {order.order_id} notification sent to user {user.telegram_id}")
                logger.info(f"   Attempts: {result.get('attempts', 'N/A')}")
                logger.info(f"   Status: {result.get('status', 'N/A')}")
            else:
                logger.error(f"❌ WEBHOOK FAILED: Order {order.order_id} notification failed for user {user.telegram_id}")
                logger.error(f"   Error: {result.get('error', 'Unknown error')}")
                logger.error(f"   Attempts: {result.get('attempts', 'N/A')}")
                logger.error(f"   Status: {result.get('status', 'N/A')}")
                
        except Exception as e:
            logger.error(f"Error sending new order notification: {e}")

    async def _get_today_stats(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение статистики за сегодня"""
        try:
            today = datetime.now(timezone.utc).date()
            
            # Подсчитываем заказы за сегодня
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    func.date(WBOrder.order_date) == today
                )
            ).all()
            
            count = len(orders_today)
            amount = sum(float(order.total_price or 0) for order in orders_today)
            
            return {
                "count": count,
                "amount": amount
            }
        except Exception as e:
            logger.error(f"Error getting today stats: {e}")
            return {"count": 0, "amount": 0}

    async def _get_order_stocks(self, cabinet: WBCabinet, nm_id: int) -> Dict[str, int]:
        """Получение остатков по товару"""
        try:
            stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet.id,
                    WBStock.nm_id == nm_id
                )
            ).all()
            
            stocks_dict = {}
            for stock in stocks:
                size = stock.size or "Unknown"
                quantity = stock.quantity or 0
                stocks_dict[size] = quantity
                
            return stocks_dict
        except Exception as e:
            logger.error(f"Error getting order stocks: {e}")
            return {}

    async def _should_send_notification(self, cabinet: WBCabinet) -> bool:
        """Проверяет, нужно ли отправлять уведомления (не первая синхронизация)"""
        try:
            # Проверяем, была ли уже синхронизация ранее
            # Если last_sync_at не установлен или очень старый, значит это первая синхронизация
            if not cabinet.last_sync_at:
                return False
            
            # Проверяем, была ли синхронизация в последние 24 часа
            # Если нет, значит это первая синхронизация после долгого перерыва
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            time_diff = now - cabinet.last_sync_at
            
            if time_diff > timedelta(hours=24):
                return False
            
            # Если синхронизация была недавно, отправляем уведомления
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification eligibility: {e}")
            # В случае ошибки не отправляем уведомления
            return False