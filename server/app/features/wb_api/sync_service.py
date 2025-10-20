import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
try:
    from zoneinfo import ZoneInfo
    MSK_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    MSK_TZ = None
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBSyncLog
from .client import WBAPIClient
from .cache_manager import WBCacheManager
from .cabinet_manager import CabinetManager
from app.features.user.models import User

logger = logging.getLogger(__name__)


class WBSyncService:
    """
    Сервис синхронизации данных с Wildberries API
    """
    
    def __init__(self, db: Session, cache_manager: WBCacheManager = None):
        self.db = db
        self.cache_manager = cache_manager or WBCacheManager(db)
        self.cabinet_manager = CabinetManager(db)
    
    async def sync_all_data(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Синхронизация всех данных кабинета"""
        try:
            # Валидируем API ключ перед синхронизацией
            logger.info(f"Validating API key for cabinet {cabinet.id} before sync")
            validation_result = await self.cabinet_manager.validate_and_cleanup_cabinet(cabinet, max_retries=3)
            
            if not validation_result.get("valid", False):
                if validation_result.get("cabinet_removed", False):
                    logger.warning(f"Cabinet {cabinet.id} was removed due to invalid API key")
                    return {
                        "status": "error",
                        "message": "Cabinet removed due to invalid API key",
                        "cabinet_removed": True,
                        "validation_result": validation_result
                    }
                else:
                    logger.error(f"API validation failed for cabinet {cabinet.id}: {validation_result}")
                    return {
                        "status": "error",
                        "message": "API validation failed",
                        "validation_result": validation_result
                    }
            
            logger.info(f"API key validation successful for cabinet {cabinet.id}")
            
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
                ("stocks", self.sync_stocks(cabinet, client, date_from, date_to, should_notify)),
                ("reviews", self.sync_reviews(cabinet, client, date_from, date_to)),
                ("sales", self.sync_sales(cabinet, client, date_from, date_to, should_notify)),
                ("claims", self.sync_claims(cabinet, client, should_notify))
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
            logger.info(f"✅ Синхронизация кабинета {cabinet.id} завершена: {results}")
            
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
            # Даже при ошибке обновляем время синхронизации, чтобы избежать бесконечных "первых синхронизаций"
            try:
                cabinet.last_sync_at = datetime.now(timezone.utc)
                self.db.commit()
                logger.info(f"Обновлено время синхронизации кабинета {cabinet.id} несмотря на ошибку")
            except Exception as commit_error:
                logger.error(f"Не удалось обновить last_sync_at: {commit_error}")
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
            
            # Вспомогательная функция извлечения первой фото-ссылки
            def extract_first_photo_url(card: dict) -> str:
                photos = card.get("photos") or []
                if isinstance(photos, list) and photos:
                    first = photos[0]
                    return (
                        first.get("c516x688")
                        or first.get("c246x328")
                        or first.get("big")
                        or first.get("square")
                        or first.get("tm")
                    )
                return None

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
                
                photo_url = extract_first_photo_url(product_data)

                if existing:
                    # Обновляем существующий товар
                    existing.name = product_data.get("title")  # Исправлено: title вместо name
                    existing.vendor_code = product_data.get("vendorCode")
                    existing.brand = product_data.get("brand")
                    existing.category = product_data.get("subjectName")  # Исправлено: subjectName вместо category
                    if photo_url:
                        existing.image_url = photo_url
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
                        image_url=photo_url,
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
                # logger.info(f"Commissions data type: {type(commissions_data)}, length: {len(commissions_data) if isinstance(commissions_data, list) else 'N/A'}")
                # Печатаем образец данных для отладки (без шума в логах)
                if isinstance(commissions_data, list) and commissions_data:
                    sample = commissions_data[0]
                    # try:
                    #     # Ограничим ключевые поля для читаемости
                    #     sample_filtered = {k: sample.get(k) for k in list(sample.keys())[:10]}
                    #     logger.info(f"Commissions sample: {sample_filtered}")
                    # except Exception:
                    #     logger.info("Commissions sample: <unserializable>")
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
                        # Проверяем, изменились ли данные
                        new_status = "canceled" if order_data.get("isCancel", False) else "active"
                        new_total_price = order_data.get("totalPrice")
                        new_article = order_data.get("supplierArticle")
                        new_name = order_data.get("subject")
                        new_brand = order_data.get("brand")
                        new_size = order_data.get("techSize")
                        new_price = order_data.get("finishedPrice")
                        
                        # Проверяем реальные изменения в критичных полях
                        status_changed = existing.status != new_status
                        price_changed = existing.total_price != new_total_price
                        article_changed = existing.article != new_article
                        name_changed = existing.name != new_name
                        brand_changed = existing.brand != new_brand
                        size_changed = existing.size != new_size
                        finished_price_changed = existing.price != new_price
                        
                        # Обновляем только если есть реальные изменения
                        if status_changed or price_changed or article_changed or name_changed or brand_changed or size_changed or finished_price_changed:
                            changes = []
                            if status_changed:
                                changes.append(f"status {existing.status} -> {new_status}")
                            if price_changed:
                                changes.append(f"total_price {existing.total_price} -> {new_total_price}")
                            if article_changed:
                                changes.append(f"article {existing.article} -> {new_article}")
                            if name_changed:
                                changes.append(f"name {existing.name} -> {new_name}")
                            if brand_changed:
                                changes.append(f"brand {existing.brand} -> {new_brand}")
                            if size_changed:
                                changes.append(f"size {existing.size} -> {new_size}")
                            if finished_price_changed:
                                changes.append(f"price {existing.price} -> {new_price}")
                            
                            logger.info(f"Order {order_id} changed: {', '.join(changes)}")
                            
                            # Обновляем только изменившиеся поля
                            if status_changed:
                                existing.status = new_status
                            if price_changed:
                                existing.total_price = new_total_price
                            if article_changed:
                                existing.article = new_article
                            if name_changed:
                                existing.name = new_name
                            if brand_changed:
                                existing.brand = new_brand
                            if size_changed:
                                existing.size = new_size
                            if finished_price_changed:
                                existing.price = new_price
                            
                            # Обновляем остальные поля
                            existing.nm_id = nm_id
                            existing.barcode = order_data.get("barcode")
                            existing.quantity = 1
                            existing.order_date = self._parse_datetime(order_data.get("date"))
                        else:
                            # Данные не изменились, пропускаем обновление
                            continue
                        
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
                        # Выбор поля комиссии с учетом режима заказа
                        commission_field = self._select_commission_field(order_data)
                        commission_percent, commission_amount = self._calculate_commission(
                            existing.category, existing.subject, total_price, commissions_data, commission_field
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
                            commission_field = self._select_commission_field(order_data)
                            commission_percent, commission_amount = self._calculate_commission(
                                category, subject, total_price, commissions_data, commission_field
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
                            
                            try:
                                self.db.flush()  # Принудительно выполняем вставку для проверки уникальности
                                
                                # Уведомления о новых заказах обрабатываются через систему уведомлений
                                # (удален вызов несуществующего метода _send_new_order_notification)
                                
                                # logger.info(f"Created order {order_id}: commission_percent={commission_percent}, commission_amount={commission_amount}")
                                created += 1
                            except Exception as flush_error:
                                # Если заказ уже существует (race condition), пропускаем его
                                if "duplicate key" in str(flush_error).lower() or "unique constraint" in str(flush_error).lower() or "uniqueviolation" in str(flush_error).lower():
                                    logger.warning(f"Order {order_id} already exists, skipping: {flush_error}")
                                    self.db.rollback()  # Откатываем транзакцию
                                    continue
                                else:
                                    raise flush_error
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
        date_to: str,
        should_notify: bool = True
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
                    # Проверяем, изменились ли данные
                    new_quantity = stock_data.get("quantity")
                    new_last_updated = self._parse_datetime(stock_data.get("lastChangeDate"))
                    new_article = stock_data.get("supplierArticle")
                    new_brand = stock_data.get("brand")
                    new_size = stock_data.get("techSize")
                    
                    # Проверяем реальные изменения в критичных полях
                    quantity_changed = existing.quantity != new_quantity
                    date_changed = existing.last_updated != new_last_updated
                    article_changed = existing.article != new_article
                    brand_changed = existing.brand != new_brand
                    size_changed = existing.size != new_size
                    
                    # Обновляем только если есть реальные изменения
                    if quantity_changed or date_changed or article_changed or brand_changed or size_changed:
                        changes = []
                        if quantity_changed:
                            changes.append(f"quantity {existing.quantity} -> {new_quantity}")
                        if date_changed:
                            changes.append(f"date {existing.last_updated} -> {new_last_updated}")
                        if article_changed:
                            changes.append(f"article {existing.article} -> {new_article}")
                        if brand_changed:
                            changes.append(f"brand {existing.brand} -> {new_brand}")
                        if size_changed:
                            changes.append(f"size {existing.size} -> {new_size}")
                        
                        # Логирование изменений остатков убрано - слишком много шума
                        
                        # Обновляем только изменившиеся поля
                        if quantity_changed:
                            existing.quantity = new_quantity
                        if date_changed:
                            existing.last_updated = new_last_updated
                        if article_changed:
                            existing.article = new_article
                        if brand_changed:
                            existing.brand = new_brand
                        if size_changed:
                            existing.size = new_size
                        
                        # Обновляем остальные поля
                        existing.barcode = stock_data.get("barcode")
                        existing.in_way_to_client = stock_data.get("inWayToClient")
                        existing.in_way_from_client = stock_data.get("inWayFromClient")
                        existing.warehouse_name = stock_data.get("warehouseName")
                        
                        # Новые поля из WB API
                        existing.category = stock_data.get("category")
                        existing.subject = stock_data.get("subject")
                        existing.price = stock_data.get("Price")
                        existing.discount = stock_data.get("Discount")
                        existing.quantity_full = stock_data.get("quantityFull")
                        existing.is_supply = stock_data.get("isSupply")
                        existing.is_realization = stock_data.get("isRealization")
                        existing.sc_code = stock_data.get("SCCode")
                        
                        # Обновляем updated_at ТОЛЬКО при реальных изменениях
                        existing.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        # Данные не изменились, пропускаем обновление
                        continue
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
        """Парсинг даты из строки WB. Если без TZ — считаем МСК и конвертируем в UTC."""
        if not date_str:
            return None
        
        try:
            # Пробуем разные форматы дат
            for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    if dt.tzinfo is None:
                        # Без TZ: трактуем как МСК и переводим в UTC
                        if MSK_TZ is not None:
                            dt = dt.replace(tzinfo=MSK_TZ).astimezone(timezone.utc)
                        else:
                            # Фолбэк: сдвиг +3 часа
                            dt = dt.replace(tzinfo=timezone.utc) - timedelta(hours=3)
                    else:
                        # С TZ: приводим к UTC
                        dt = dt.astimezone(timezone.utc)
                    return dt
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

    def _select_commission_field(self, order_data: dict) -> str:
        """Определяет, какое поле комиссии использовать, исходя из режима заказа.
        Порядок приоритета: pickup -> booking -> supplierExpress -> supplier -> marketplace.
        Ожидаемые ключи в order_data (по наличию/истине): isPickup, isBooking, isSupplierExpress, isSupplier.
        """
        try:
            if order_data.get("isPickup"):
                return "kgvpPickup"
            if order_data.get("isBooking"):
                return "kgvpBooking"
            if order_data.get("isSupplierExpress"):
                return "kgvpSupplierExpress"
            if order_data.get("isSupplier"):
                return "kgvpSupplier"
        except Exception:
            pass
        return "kgvpMarketplace"

    def _calculate_commission(self, category: str, subject: str, total_price: float, commissions_data, commission_field: str = "kgvpMarketplace") -> tuple[float, float]:
        """Расчет комиссии для заказа на основе категории, предмета и режимного поля комиссии."""
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
                percent_value = commission.get(commission_field)
                
                # logger.info(f"Commission {i}: parentName='{parent_name}', subjectName='{subject_name}', kgvpMarketplace={kgvp_marketplace}")
                
                # Точное совпадение
                if (parent_name == category and subject_name == subject):
                    commission_percent = float(percent_value) if percent_value is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    # logger.info(f"Commission match ({commission_field}) for {category}/{subject}: {commission_percent}% -> {commission_amount}₽")
                    # logger.info(f"Found exact match: {category}/{subject} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
                
                # Нечеткое совпадение по предмету (если категории совпадают)
                if (parent_name == category and subject_name and subject and 
                    (subject_name.lower() in subject.lower() or subject.lower() in subject_name.lower())):
                    commission_percent = float(percent_value) if percent_value is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found fuzzy match: {category}/{subject} ~ {parent_name}/{subject_name} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
            
            # Если точного совпадения нет, ищем по категории
            # logger.info(f"No exact match found, searching by category: {category}")
            for i, commission in enumerate(commissions_data):
                if not isinstance(commission, dict):
                    continue
                
                parent_name = commission.get("parentName")
                percent_value = commission.get(commission_field)
                
                # Точное совпадение по категории
                if parent_name == category:
                    commission_percent = float(percent_value) if percent_value is not None else 0.0
                    commission_amount = (total_price * commission_percent) / 100
                    
                    # logger.info(f"Found exact category match: {category} -> {commission_percent}% = {commission_amount}₽")
                    return commission_percent, commission_amount
                
                # Нечеткое совпадение по категории
                if (parent_name and category and 
                    (parent_name.lower() in category.lower() or category.lower() in parent_name.lower())):
                    commission_percent = float(percent_value) if percent_value is not None else 0.0
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

    # Webhook уведомления удалены - теперь используется только polling система

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

    async def _get_product_statistics(self, cabinet_id: int, nm_id: int) -> Dict[str, Any]:
        """Получение статистики товара (выкуп, скорость заказов, продажи)"""
        try:
            # Получаем заказы за последние 30 дней для расчета статистики
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Заказы за 7 дней
            orders_7d = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id == nm_id,
                    WBOrder.order_date >= datetime.now(timezone.utc) - timedelta(days=7)
                )
            ).all()
            
            # Заказы за 14 дней
            orders_14d = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id == nm_id,
                    WBOrder.order_date >= datetime.now(timezone.utc) - timedelta(days=14)
                )
            ).all()
            
            # Заказы за 30 дней
            orders_30d = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id == nm_id,
                    WBOrder.order_date >= thirty_days_ago
                )
            ).all()
            
            # Рассчитываем статистику
            buyout_rates = {
                "7_days": 100.0 if orders_7d else 0.0,
                "14_days": 100.0 if orders_14d else 0.0,
                "30_days": 100.0 if orders_30d else 0.0
            }
            
            order_speed = {
                "7_days": len(orders_7d) / 7.0,
                "14_days": len(orders_14d) / 14.0,
                "30_days": len(orders_30d) / 30.0
            }
            
            sales_periods = {
                "7_days": len(orders_7d),
                "14_days": len(orders_14d),
                "30_days": len(orders_30d)
            }
            
            return {
                "buyout_rates": buyout_rates,
                "order_speed": order_speed,
                "sales_periods": sales_periods
            }
            
        except Exception as e:
            logger.error(f"Error getting product statistics: {e}")
            return {
                "buyout_rates": {},
                "order_speed": {},
                "sales_periods": {}
            }

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

    async def sync_sales(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        date_from: str, 
        date_to: str,
        should_notify: bool = False
    ) -> Dict[str, Any]:
        """Синхронизация продаж и возвратов"""
        try:
            logger.info(f"Starting sales sync for cabinet {cabinet.id}")
            
            # Получаем данные продаж из WB API
            # Для уменьшения нагрузки: после первичной загрузки используем узкое окно и инкрементальный флаг
            sales_data = await client.get_sales(date_from, flag=1)
            
            if not sales_data:
                logger.warning(f"No sales data received for cabinet {cabinet.id}")
                return {"status": "success", "records_processed": 0, "records_created": 0}
            
            # Импортируем CRUD для продаж
            from .crud_sales import WBSalesCRUD
            sales_crud = WBSalesCRUD()
            
            records_processed = 0
            records_created = 0
            
            for sale_item in sales_data:
                try:
                    # Определяем тип продажи (выкуп или возврат)
                    sale_type = "buyout"  # По умолчанию выкуп
                    
                    # Проверяем, является ли это возвратом
                    # В WB API возвраты определяются по:
                    # 1. Отрицательным суммам (totalPrice < 0)
                    # 2. Префиксу saleID (начинается с "R")
                    # 3. Полю isCancel = true
                    total_price = float(sale_item.get("totalPrice", 0))
                    sale_id = str(sale_item.get("srid", ""))
                    is_cancel = bool(sale_item.get("isCancel", False))
                    
                    if (total_price < 0 or 
                        sale_id.startswith("R") or 
                        is_cancel):
                        sale_type = "return"
                    
                    # Подготавливаем данные для сохранения
                    sale_data = {
                        "cabinet_id": cabinet.id,
                        "sale_id": str(sale_item.get("srid", "")),
                        "order_id": str(sale_item.get("orderId", "")),
                        "nm_id": sale_item.get("nmId", 0),
                        "product_name": sale_item.get("subject", ""),
                        "brand": sale_item.get("brand", ""),
                        "size": sale_item.get("techSize", ""),
                        "amount": float(sale_item.get("totalPrice", 0)),
                        "sale_date": self._parse_wb_date(sale_item.get("date")),
                        "type": sale_type,
                        "status": "completed",
                        "is_cancel": bool(sale_item.get("isCancel", False)),
                        "last_change_date": self._parse_wb_date(sale_item.get("lastChangeDate"))
                    }
                    
                    # Проверяем, существует ли уже такая запись
                    existing_sale = sales_crud.get_sale_by_sale_id(self.db, cabinet.id, sale_data["sale_id"])
                    
                    if not existing_sale:
                        # Создаем новую запись
                        sales_crud.create_sale(self.db, sale_data)
                        records_created += 1
                        
                        # Если нужно отправлять уведомления, обрабатываем новую продажу
                        if should_notify:
                            await self._process_sale_notification(cabinet, sale_data)
                    
                    records_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing sale item: {e}")
                    continue
            
            logger.info(f"Sales sync completed for cabinet {cabinet.id}: {records_processed} processed, {records_created} created")
            
            return {
                "status": "success",
                "records_processed": records_processed,
                "records_created": records_created
            }
            
        except Exception as e:
            logger.error(f"Sales sync failed for cabinet {cabinet.id}: {e}")
            return {"status": "error", "error_message": str(e)}

    async def sync_claims(
        self, 
        cabinet: WBCabinet, 
        client: WBAPIClient, 
        should_notify: bool = False
    ) -> Dict[str, Any]:
        """Синхронизация возвратов покупателей (Claims API)"""
        try:
            logger.info(f"Starting claims sync for cabinet {cabinet.id}")
            
            # Получаем активные и архивные возвраты
            active_claims = await client.get_claims(is_archive=False)
            archive_claims = await client.get_claims(is_archive=True)
            
            all_claims = active_claims + archive_claims
            logger.info(f"Received {len(all_claims)} total claims for cabinet {cabinet.id}")
            
            if not all_claims:
                return {
                    "status": "success",
                    "records_processed": 0,
                    "records_created": 0,
                    "records_updated": 0,
                    "records_errors": 0,
                    "message": "No claims data to sync"
                }
            
            from .crud_sales import WBSalesCRUD
            sales_crud = WBSalesCRUD()
            
            records_processed = 0
            records_created = 0
            records_updated = 0
            records_errors = 0
            
            for claim in all_claims:
                try:
                    records_processed += 1
                    
                    # Подготавливаем данные для сохранения
                    claim_data = {
                        "cabinet_id": cabinet.id,
                        "sale_id": str(claim.get("srid", "")),
                        "order_id": str(claim.get("order_dt", "")),
                        "nm_id": claim.get("nm_id", 0),
                        "product_name": claim.get("imt_name", ""),
                        "brand": "",  # В Claims API нет бренда
                        "size": "",   # В Claims API нет размера
                        "amount": float(claim.get("price", 0)),
                        "sale_date": self._parse_wb_date(claim.get("dt")),
                        "type": "return",  # Все Claims - это возвраты
                        "status": "completed" if claim.get("status") == 2 else "pending",
                        "is_cancel": claim.get("status") == 1,  # status=1 означает отклонение
                        "last_change_date": self._parse_wb_date(claim.get("dt_update"))
                    }
                    
                    # Проверяем, существует ли уже такая запись
                    existing_sale = sales_crud.get_sale_by_sale_id(self.db, cabinet.id, claim_data["sale_id"])
                    
                    if existing_sale:
                        # Обновляем существующую запись
                        for key, value in claim_data.items():
                            if key != "cabinet_id" and key != "sale_id":
                                setattr(existing_sale, key, value)
                        records_updated += 1
                    else:
                        # Создаем новую запись
                        sales_crud.create_sale(self.db, claim_data)
                        records_created += 1
                    
                except Exception as e:
                    records_errors += 1
                    logger.error(f"Error processing claim {claim.get('id', 'unknown')}: {e}")
                    continue
            
            # Логируем результат синхронизации
            logger.info(f"Claims sync completed for cabinet {cabinet.id}: "
                       f"{records_created} created, {records_updated} updated, {records_errors} errors")
            
            return {
                "status": "success",
                "records_processed": records_processed,
                "records_created": records_created,
                "records_updated": records_updated,
                "records_errors": records_errors,
                "message": f"Claims sync completed: {records_created} created, {records_updated} updated, {records_errors} errors"
            }
            
        except Exception as e:
            logger.error(f"Error syncing claims for cabinet {cabinet.id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Claims sync failed: {str(e)}"
            }
    
    async def _process_sale_notification(self, cabinet: WBCabinet, sale_data: Dict[str, Any]):
        """Обработка уведомления о новой продаже/возврате"""
        try:
            # Импортируем NotificationService
            from app.features.notifications.notification_service import NotificationService
            
            notification_service = NotificationService(self.db, self.cache_manager)
            
            # Получаем пользователя
            # user_id у кабинета более не используется напрямую
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            user = self.db.query(User).filter(User.id.in_(user_ids)).first() if user_ids else None
            if not user:
                logger.warning(f"User not found for cabinet {cabinet.id}")
                return
            
            # Определяем тип уведомления
            notification_type = "order_buyout" if sale_data["type"] == "buyout" else "order_return"
            
            # Создаем данные для уведомления
            notification_data = {
                "order_id": sale_data["order_id"],
                "product_name": sale_data["product_name"],
                "amount": sale_data["amount"],
                "type": sale_data["type"],
                "sale_date": sale_data["sale_date"].isoformat() if sale_data["sale_date"] else None
            }
            
            # Webhook удален - уведомления отправляются через polling
            result = {"success": True, "message": "Notification queued for polling"}
            
            if result.get("success"):
                logger.info(f"Sale notification sent for cabinet {cabinet.id}, sale {sale_data['sale_id']}")
            else:
                logger.warning(f"Failed to send sale notification: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error processing sale notification: {e}")
    
    def _parse_wb_date(self, date_str: str) -> Optional[datetime]:
        """Парсинг даты из WB API"""
        if not date_str:
            return None
        
        try:
            # WB API возвращает даты в формате "2025-01-28T12:00:00"
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None