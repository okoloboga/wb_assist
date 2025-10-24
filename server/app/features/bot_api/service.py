"""
Bot API сервис для интеграции с Telegram ботом
"""

import logging
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session, joinedload, selectinload
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview
from sqlalchemy import func, and_, or_, text
from datetime import datetime, timezone, timedelta
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService
from app.utils.timezone import TimezoneUtils
from .formatter import BotMessageFormatter

logger = logging.getLogger(__name__)


class BotAPIService:
    """Сервис для Bot API"""
    
    def __init__(self, db: Session, cache_manager: WBCacheManager = None, sync_service: WBSyncService = None):
        self.db = db
        self.cache_manager = cache_manager or WBCacheManager(db)
        self.sync_service = sync_service or WBSyncService(db, self.cache_manager)
        self.formatter = BotMessageFormatter()
        self.cache_ttl = 300  # 5 минут кэш

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по telegram_id с автоматическим созданием"""
        try:
            
            # Используем прямой SQL запрос вместо ORM
            result = self.db.execute(
                text("SELECT id, telegram_id, username, first_name, last_name, created_at FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            ).fetchone()
            
            if not result:
                # Пользователь не найден - создаем его автоматически
                logger.info(f"❌ Пользователь {telegram_id} не найден, создаем автоматически")
                
                # Создаем пользователя с базовыми данными
                from app.features.user.schemas import UserCreate
                from app.features.user.crud import UserCRUD
                
                user_crud = UserCRUD(self.db)
                user_data = UserCreate(
                    telegram_id=telegram_id,
                    username=None,
                    first_name=f"User_{telegram_id}",  # Временное имя
                    last_name=None
                )
                
                user, created = user_crud.create_or_update_user(user_data)
                
                if created:
                    logger.info(f"✅ Автоматически создан пользователь: {telegram_id}")
                else:
                    logger.info(f"🔄 Найден существующий пользователь: {telegram_id}")
                
                return {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created_at": user.created_at
                }
            else:
                return {
                "id": result[0],
                "telegram_id": result[1],
                "username": result[2],
                "first_name": result[3],
                "last_name": result[4],
                "created_at": result[5]
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения/создания пользователя: {e}")
            return None

    async def get_user_cabinet(self, telegram_id: int) -> Optional[WBCabinet]:
        """Получение кабинета пользователя по telegram_id (новая система общих кабинетов)"""
        try:
            # Сначала получаем пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
            
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            
            # Получаем кабинеты пользователя через связующую таблицу
            cabinet_ids = cabinet_user_crud.get_user_cabinets(self.db, user["id"])
            
            if not cabinet_ids:
                return None
            
            # Возвращаем первый активный кабинет
            cabinet = self.db.query(WBCabinet).filter(
                WBCabinet.id.in_(cabinet_ids),
                WBCabinet.is_active == True
            ).first()
            
            return cabinet
            
        except Exception as e:
            logger.error(f"Ошибка получения кабинета пользователя: {e}")
            return None

    async def get_dashboard(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Получение дашборда пользователя"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            dashboard_data = await self._fetch_dashboard_from_db(cabinet)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_dashboard(dashboard_data)
            
            return {
                "success": True,
                "data": dashboard_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": {},
                "reviews": {},
                "analytics": {},
                "order": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения дашборда: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_recent_orders(self, user: Dict[str, Any], limit: int = 10, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
        """Получение последних заказов пользователя с кэшированием"""
        try:
            
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                logger.error(f"❌ [get_recent_orders] Cabinet not found for telegram_id={user['telegram_id']}")
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            
            # Временно отключаем кэширование для заказов, чтобы новые заказы сразу появлялись
            # TODO: Добавить инвалидацию кэша при создании новых заказов
            
            # Получаем данные из БД
            orders_data = await self._fetch_orders_from_db(cabinet, limit, offset, status)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_orders(orders_data)
            
            
            result = {
                "success": True,
                "data": orders_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": orders_data.get("orders", []),
                "pagination": orders_data.get("pagination", {}),
                "statistics": orders_data.get("statistics", {}),
                "stocks": {},
                "reviews": {},
                "analytics": {},
                "order": None
            }
            
            # Кэширование отключено для заказов (см. комментарий выше)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_orders_statistics(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Получение полной статистики по заказам"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем статистику заказов
            orders_stats = await self._get_orders_statistics_from_db(cabinet)
            
            # Получаем статистику продаж
            sales_stats = await self._get_sales_statistics_from_db(cabinet)
            
            # Формируем полную статистику
            full_stats = {
                "orders": orders_stats,
                "sales": sales_stats,
                "summary": {
                    "total_orders": orders_stats["total_orders"],
                    "active_orders": orders_stats["active_orders"],
                    "canceled_orders": orders_stats["canceled_orders"],
                    "total_sales": sales_stats["total_sales"],
                    "buyouts": sales_stats["buyouts"],
                    "returns": sales_stats["returns"],
                    "buyout_rate": sales_stats["buyout_rate"]
                }
            }
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_orders_statistics(full_stats)
            
            return {
                "success": True,
                "data": full_stats,
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики заказов: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_order_detail(self, user: Dict[str, Any], order_id: int) -> Dict[str, Any]:
        """Получение деталей заказа"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем заказ из БД
            order = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.id == order_id,
                    WBOrder.cabinet_id == cabinet.id
                )
            ).first()
            
            
            if not order:
                return {
                    "success": False,
                    "error": "Заказ не найден"
                }
            
            # Получаем данные о товаре (рейтинг, отзывы)
            product = self.db.query(WBProduct).filter(
                and_(
                    WBProduct.cabinet_id == order.cabinet_id,
                    WBProduct.nm_id == order.nm_id
                )
            ).first()
            
            # Получаем остатки товара по размерам
            stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == order.cabinet_id,
                    WBStock.nm_id == order.nm_id
                )
            ).all()
            
            # Формируем остатки по размерам (суммируем по всем складам)
            stocks_dict = {}
            for stock in stocks:
                size = stock.size or "ONE SIZE"
                quantity = stock.quantity or 0
                # Суммируем остатки по всем складам для одного размера
                if size in stocks_dict:
                    stocks_dict[size] += quantity
                else:
                    stocks_dict[size] = quantity
            
            # Получаем статистику отзывов для товара
            reviews_count = self.db.query(WBReview).filter(
                and_(
                    WBReview.cabinet_id == order.cabinet_id,
                    WBReview.nm_id == order.nm_id
                )
            ).count()
            
            # Получаем статистику продаж для товара
            try:
                product_stats = await self._get_product_statistics(cabinet.id, order.nm_id)
            except Exception as e:
                logger.error(f"Ошибка получения статистики товара: {e}")
                product_stats = {"buyout_rates": {}, "order_speed": {}, "sales_periods": {}}
            
            # Получаем статистику по всем заказам этого товара
            from sqlalchemy import case
            from ..wb_api.models_sales import WBSales
            
            # Статистика заказов (активные и отмененные)
            orders_stats = self.db.query(
                func.count(WBOrder.id).label('total_orders'),
                func.count(case((WBOrder.status == 'active', 1))).label('active_orders'),
                func.count(case((WBOrder.status == 'canceled', 1))).label('canceled_orders')
            ).filter(
                and_(
                    WBOrder.cabinet_id == order.cabinet_id,
                    WBOrder.nm_id == order.nm_id
                )
            ).first()
            
            # Статистика продаж (выкупы и возвраты из таблицы WBSales)
            sales_stats = self.db.query(
                func.count(case((WBSales.type == 'buyout', 1))).label('buyout_count'),
                func.count(case((WBSales.type == 'return', 1))).label('return_count')
            ).filter(
                and_(
                    WBSales.cabinet_id == order.cabinet_id,
                    WBSales.nm_id == order.nm_id,
                    WBSales.is_cancel == False  # Только не отмененные
                )
            ).first()
            
            # Получаем распределение рейтингов
            rating_distribution = self.db.query(
                WBReview.rating,
                func.count(WBReview.id).label('count')
            ).filter(
                and_(
                    WBReview.cabinet_id == order.cabinet_id,
                    WBReview.nm_id == order.nm_id,
                    WBReview.rating.isnot(None)
                )
            ).group_by(WBReview.rating).all()
            
            # Форматируем распределение рейтингов
            rating_dist_dict = {int(row.rating): row.count for row in rating_distribution}
            
            # Получаем средний рейтинг из отзывов (более точный)
            avg_rating = self.db.query(func.avg(WBReview.rating)).filter(
                and_(
                    WBReview.cabinet_id == order.cabinet_id,
                    WBReview.nm_id == order.nm_id,
                    WBReview.rating.isnot(None)
                )
            ).scalar()
            
            # Форматируем данные заказа
            image_url = product.image_url if product and hasattr(product, 'image_url') else None
            logger.info(f"📢 Order detail - Product found: {product is not None}")
            logger.info(f"📢 Order detail - Product image_url: {image_url}")
            
            order_data = {
                "id": order.id,
                "date": self._convert_to_msk_iso(order.order_date) if order.order_date else None,
                "amount": order.total_price or 0,
                "product_name": order.name or "Неизвестно",
                "brand": order.brand or "Неизвестно",
                "warehouse_from": order.warehouse_from,
                "warehouse_to": order.warehouse_to,
                "commission_percent": order.commission_percent or 0.0,
                "commission_amount": order.commission_amount or 0.0,
                "rating": product.rating if product else 0.0,  # Реальный рейтинг из WBProduct
                "reviews_count": reviews_count,  # Реальное количество отзывов
                "image_url": image_url,  # URL изображения товара
                # Новые поля из WB API
                "spp_percent": order.spp_percent or 0.0,
                "customer_price": order.customer_price or 0.0,
                "discount_percent": order.discount_percent or 0.0,
                # Логистика исключена из системы
                # Дополнительные поля для детального отчета
                "order_id": order.order_id,
                "nm_id": order.nm_id,
                "article": order.article,
                "size": order.size,
                "barcode": order.barcode,
                "quantity": order.quantity,
                "price": order.price,
                "total_price": order.total_price,
                "order_date": self._convert_to_msk_iso(order.order_date) if order.order_date else None,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                # Остатки товара
                "stocks": stocks_dict,
                # Реальная статистика
                "buyout_rates": product_stats["buyout_rates"],
                "order_speed": product_stats["order_speed"],
                "sales_periods": product_stats["sales_periods"],
                # Статистика заказов по товару
                "orders_stats": {
                    "total_orders": orders_stats.total_orders or 0 if orders_stats else 0,
                    "active_orders": orders_stats.active_orders or 0 if orders_stats else 0,
                    "canceled_orders": orders_stats.canceled_orders or 0 if orders_stats else 0,
                    "buyout_orders": sales_stats.buyout_count or 0 if sales_stats else 0,
                    "return_orders": sales_stats.return_count or 0 if sales_stats else 0
                },
                # Распределение рейтингов
                "rating_distribution": rating_dist_dict,
                # Средний рейтинг из отзывов (более точный)
                "avg_rating": round(float(avg_rating), 2) if avg_rating else 0.0
            }
            
            # Отладочный лог
            logger.info(f"Order data for order {order_id}: spp_percent={order.spp_percent}, customer_price={order.customer_price}, discount_percent={order.discount_percent}")
            logger.info(f"Order data keys: {list(order_data.keys())}")
            logger.info(f"📢 Final order_data image_url: {order_data.get('image_url')}")
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_order_detail({"order": order_data})
            
            return {
                "success": True,
                "data": order_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": {},
                "reviews": {},
                "analytics": {},
                "order": order_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей заказа: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_orders_statistics_from_db(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение статистики заказов из БД"""
        try:
            # Общее количество заказов
            total_orders = self.db.query(WBOrder).filter(WBOrder.cabinet_id == cabinet.id).count()
            
            # Активные заказы
            active_orders = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.status == 'active'
                )
            ).count()
            
            # Отмененные заказы
            canceled_orders = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.status == 'canceled'
                )
            ).count()
            
            # Заказы без статуса
            no_status_orders = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.status.is_(None)
                )
            ).count()
            
            return {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "canceled_orders": canceled_orders,
                "no_status_orders": no_status_orders,
                "active_percentage": (active_orders / total_orders * 100) if total_orders > 0 else 0,
                "canceled_percentage": (canceled_orders / total_orders * 100) if total_orders > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики заказов: {e}")
            return {
                "total_orders": 0,
                "active_orders": 0,
                "canceled_orders": 0,
                "no_status_orders": 0,
                "active_percentage": 0,
                "canceled_percentage": 0
            }

    async def _get_sales_statistics_from_db(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение статистики продаж из БД"""
        try:
            from ..wb_api.crud_sales import WBSalesCRUD
            sales_crud = WBSalesCRUD()
            
            # Получаем статистику продаж
            stats = sales_crud.get_sales_statistics(self.db, cabinet.id)
            
            return {
                "total_sales": stats.get("total_count", 0),
                "buyouts": stats.get("buyouts_count", 0),
                "returns": stats.get("returns_count", 0),
                "buyout_rate": stats.get("buyout_rate", 0),
                "total_amount": stats.get("total_amount", 0),
                "buyouts_amount": stats.get("buyouts_amount", 0),
                "returns_amount": stats.get("returns_amount", 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики продаж: {e}")
            return {
                "total_sales": 0,
                "buyouts": 0,
                "returns": 0,
                "buyout_rate": 0,
                "total_amount": 0,
                "buyouts_amount": 0,
                "returns_amount": 0
            }

    async def get_critical_stocks(self, user, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение критичных остатков"""
        try:
            # Получаем telegram_id из объекта user
            telegram_id = user.telegram_id if hasattr(user, 'telegram_id') else user["telegram_id"]
            cabinet = await self.get_user_cabinet(telegram_id)
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Отладочный лог
            logger.info(f"get_critical_stocks: cabinet type: {type(cabinet)}, cabinet.id: {cabinet.id}")
            
            # Получаем данные из БД
            stocks_data = await self._fetch_critical_stocks_from_db(cabinet, limit, offset)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_critical_stocks(stocks_data)
            
            return {
                "success": True,
                "data": stocks_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": stocks_data,
                "reviews": {},
                "analytics": {},
                "order": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения критичных остатков: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_reviews_summary(self, user, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение сводки по отзывам"""
        try:
            # Получаем telegram_id из объекта user
            telegram_id = user.telegram_id if hasattr(user, 'telegram_id') else user["telegram_id"]
            cabinet = await self.get_user_cabinet(telegram_id)
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            reviews_data = await self._fetch_reviews_from_db(cabinet, limit, offset)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_reviews(reviews_data)
            
            return {
                "success": True,
                "data": reviews_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": {},
                "reviews": reviews_data,
                "analytics": {},
                "order": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения отзывов: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_analytics_sales(self, user: Dict[str, Any], period: str = "7d") -> Dict[str, Any]:
        """Получение аналитики продаж"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            analytics_data = await self._fetch_analytics_from_db(cabinet, period)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_analytics(analytics_data)
            
            return {
                "success": True,
                "data": analytics_data,
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": {},
                "reviews": {},
                "analytics": analytics_data,
                "order": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def start_sync(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск синхронизации данных"""
        try:
            logger.info(f"start_sync called with user: {user}")
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            logger.info(f"cabinet: {cabinet}, type: {type(cabinet)}")
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Запускаем синхронизацию
            logger.info(f"Calling sync_all_data for cabinet {cabinet.id}")
            result = await self.sync_service.sync_all_data(cabinet)
            logger.info(f"sync_all_data result: {result}")
            
            if result["status"] == "success":
                return {
                    "success": True,
                    "data": result,
                    "telegram_text": "🔄 Синхронизация завершена успешно!"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error_message", "Ошибка синхронизации")
                }
                
        except Exception as e:
            logger.error(f"Ошибка запуска синхронизации: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        try:
            status = await self.sync_service.get_sync_status()
            
            return {
                "success": True,
                "data": status,
                "telegram_text": f"📊 Статус синхронизации: {status.get('status', 'Неизвестно')}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса синхронизации: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def connect_cabinet(self, user: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Подключение WB кабинета или замена существующего (новая система общих кабинетов)"""
        try:
            logger.info(f"connect_cabinet called with user: {user}, api_key: {api_key}")
            logger.info(f"user type: {type(user)}")
            
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            
            # Проверяем, есть ли уже кабинет с этим API ключом
            existing_cabinet = cabinet_user_crud.find_cabinet_by_api_key(self.db, api_key)
            
            if existing_cabinet:
                # Кабинет с таким API ключом уже существует
                logger.info(f"Found existing cabinet {existing_cabinet.id} with API key")
                
                # Проверяем, подключен ли уже пользователь к этому кабинету
                if cabinet_user_crud.is_user_in_cabinet(self.db, existing_cabinet.id, user["id"]):
                    return {
                        "success": False,
                        "error": "Пользователь уже подключен к этому кабинету"
                    }
                
                # Подключаем пользователя к существующему кабинету
                cabinet_user_crud.add_user_to_cabinet(self.db, existing_cabinet.id, user["id"])
                
                return {
                    "success": True,
                    "message": "Подключен к существующему кабинету",
                    "cabinet_id": str(existing_cabinet.id),
                    "cabinet_name": existing_cabinet.name,
                    "connected_at": existing_cabinet.created_at.isoformat() if existing_cabinet.created_at else None,
                    "api_key_status": "valid",
                    "telegram_text": f"✅ Подключен к существующему кабинету!\n\n🏢 Кабинет: {existing_cabinet.name}\n🔑 API ключ: {api_key[:8]}...\n📊 Статус: Активен\n\nТеперь вы можете получать уведомления о новых заказах и остатках!"
                }
            
            # API ключ новый - создаем новый кабинет
            logger.info(f"Creating new cabinet for user {user['id']}")
            from app.features.wb_api.client import WBAPIClient
            
            # Создаем временный объект кабинета для валидации
            temp_cabinet = WBCabinet(
                api_key=api_key,
                name="temp",
                is_active=True
            )
            wb_client = WBAPIClient(temp_cabinet)
            logger.info(f"WBAPIClient created successfully")
            
            try:
                # Пробуем получить данные для валидации
                warehouses = await wb_client.get_warehouses()
                if not warehouses:
                    return {
                        "success": False,
                        "error": "Invalid API key"
                    }
            except Exception:
                return {
                    "success": False,
                    "error": "Invalid API key"
                }
            
            # Создаем новый кабинет
            cabinet = WBCabinet(
                api_key=api_key,
                name=f"WB Cabinet {user['telegram_id']}",
                is_active=True
            )
            
            self.db.add(cabinet)
            self.db.commit()
            self.db.refresh(cabinet)
            
            # Подключаем пользователя к новому кабинету
            cabinet_user_crud.add_user_to_cabinet(self.db, cabinet.id, user["id"])
            
            # Запускаем первичную синхронизацию для нового кабинета
            try:
                from app.features.sync.tasks import sync_cabinet_data
                sync_cabinet_data.delay(cabinet.id)
                logger.info(f"🚀 Запущена первичная синхронизация для кабинета {cabinet.id}")
            except Exception as sync_error:
                logger.error(f"Ошибка запуска синхронизации: {sync_error}")
            
            # Форматируем ответ
            cabinet_data = {
                "cabinet_id": str(cabinet.id),
                "cabinet_name": cabinet.name,
                "api_key": api_key,
                "connected_at": cabinet.created_at.isoformat() if cabinet.created_at else None,
                "status": "connected",
                "api_key_status": "valid"
            }
            
            # Специальное сообщение для первичной синхронизации
            telegram_text = f"🔑 API ключ: 🔑 Валидный\n\n🔄 Запускаю первичную синхронизацию данных...\n⏳ Это может занять 3-5 минут. Пожалуйста, подождите.\n📊 Загружаю товары, заказы, остатки и отзывы..."
            
            return {
                "success": True,
                "data": cabinet_data,
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка подключения кабинета: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_cabinet_status(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса кабинетов пользователя (новая система общих кабинетов)"""
        try:
            from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            
            # Получаем все кабинеты пользователя через связующую таблицу
            cabinet_ids = cabinet_user_crud.get_user_cabinets(self.db, user["id"])
            
            if not cabinet_ids:
                return {
                    "success": True,
                    "data": {
                        "cabinets": [],
                        "total_cabinets": 0,
                        "active_cabinets": 0,
                        "last_check": datetime.now(timezone.utc).isoformat()
                    },
                    "telegram_text": "🔑 СТАТУС WB КАБИНЕТОВ\n\n❌ Нет подключенных кабинетов"
                }
            
            # Получаем кабинеты по ID
            cabinets = self.db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
            
            # Форматируем данные кабинетов
            cabinet_data = []
            active_count = 0
            
            for cabinet in cabinets:
                if cabinet.is_active:
                    active_count += 1
                
                cabinet_data.append({
                    "id": f"cabinet_{cabinet.id}",
                    "name": cabinet.name or "Неизвестный кабинет",
                    "status": "active" if cabinet.is_active else "inactive",
                    "api_key": cabinet.api_key,  # Добавляем API ключ
                    "api_key_status": "valid" if cabinet.is_active else "invalid",
                    "connected_at": cabinet.created_at.isoformat() if cabinet.created_at else None,
                    "last_sync": TimezoneUtils.from_utc(cabinet.last_sync_at).isoformat() if cabinet.last_sync_at else None
                })
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_cabinet_status_message({"cabinets": cabinet_data})
            
            return {
                "success": True,
                "data": {
                    "cabinets": cabinet_data,
                    "total_cabinets": len(cabinets),
                    "active_cabinets": active_count,
                    "last_check": datetime.now(timezone.utc).isoformat()
                },
                "telegram_text": telegram_text,
                # Единообразные поля для всех эндпоинтов
                "orders": [],
                "pagination": {},
                "statistics": {},
                "stocks": {},
                "reviews": {},
                "analytics": {},
                "order": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса кабинетов: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _fetch_dashboard_from_db(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Получение данных дашборда из БД"""
        try:
            # Начало дня в МСК
            now_msk = TimezoneUtils.now_msk()
            today_start_msk = TimezoneUtils.get_today_start_msk()
            yesterday_start_msk = TimezoneUtils.get_yesterday_start_msk()
            
            # Конвертируем в UTC для фильтров БД
            today_start = TimezoneUtils.to_utc(today_start_msk)
            yesterday_start = TimezoneUtils.to_utc(yesterday_start_msk)
            
            # Товары - считаем уникальные nm_id из остатков (реальные товары на складе)
            total_products = self.db.query(WBStock.nm_id).filter(
                WBStock.cabinet_id == cabinet.id
            ).distinct().count()
            
            # Активные товары - товары с остатками > 0
            active_products = self.db.query(WBStock.nm_id).filter(
                and_(
                    WBStock.cabinet_id == cabinet.id,
                    WBStock.quantity > 0
                )
            ).distinct().count()
            
            # Используем правильную логику подсчета критичных остатков
            stocks_summary = self._get_stocks_summary(cabinet.id)
            critical_stocks = stocks_summary["critical_count"]
            
            # Заказы за сегодня
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= today_start,
                    WBOrder.status != 'canceled'
                )
            ).all()
            
            orders_yesterday = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= yesterday_start,
                    WBOrder.order_date < today_start,
                    WBOrder.status != 'canceled'
                )
            ).all()
            
            today_count = len(orders_today)
            today_amount = sum(order.total_price or 0 for order in orders_today)
            yesterday_count = len(orders_yesterday)
            yesterday_amount = sum(order.total_price or 0 for order in orders_yesterday)
            
            # Рост в процентах
            growth_percent = 0.0
            if yesterday_count > 0:
                growth_percent = ((today_count - yesterday_count) / yesterday_count) * 100
            
            # Отзывы
            reviews = self.db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id
            ).all()
            
            new_reviews = len([r for r in reviews if r.created_date and r.created_date >= today_start])
            unanswered_reviews = len([r for r in reviews if not r.is_answered])
            avg_rating = sum(r.rating or 0 for r in reviews) / len(reviews) if reviews else 0.0
            
            return {
                "cabinet_name": cabinet.name or "Неизвестный кабинет",
                "last_sync": TimezoneUtils.format_for_user(cabinet.last_sync_at) if cabinet.last_sync_at else "Никогда",
                "status": "Активен" if cabinet.is_active else "Неактивен",
                "products": {
                    "total": total_products,
                    "active": active_products,
                    "moderation": 0,  # TODO: Добавить подсчет товаров на модерации
                    "critical_stocks": critical_stocks
                },
                "orders_today": {
                    "count": today_count,
                    "amount": today_amount,
                    "yesterday_count": yesterday_count,
                    "yesterday_amount": yesterday_amount,
                    "growth_percent": growth_percent
                },
                "stocks": {
                    "critical_count": stocks_summary["critical_count"],
                    "zero_count": stocks_summary["zero_count"],
                    "attention_needed": stocks_summary["attention_needed"],
                    "top_product": "Нет данных"  # TODO: Добавить расчет топ товара
                },
                "reviews": {
                    "new_count": new_reviews,
                    "average_rating": round(avg_rating, 1),
                    "unanswered": unanswered_reviews,
                    "total": len(reviews)
                },
                "recommendations": ["Все в порядке!"]  # TODO: Добавить умные рекомендации
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения данных дашборда: {e}")
            return {
                "cabinet_name": "Ошибка",
                "last_sync": "Ошибка",
                "status": "Ошибка",
                "products": {"total": 0, "active": 0, "moderation": 0, "critical_stocks": 0},
                "orders_today": {"count": 0, "amount": 0, "yesterday_count": 0, "yesterday_amount": 0, "growth_percent": 0.0},
                "stocks": {"critical_count": 0, "zero_count": 0, "attention_needed": 0, "top_product": "Ошибка"},
                "reviews": {"new_count": 0, "average_rating": 0.0, "unanswered": 0, "total": 0},
                "recommendations": ["Ошибка получения данных"]
            }

    async def _fetch_orders_from_db(self, cabinet: WBCabinet, limit: int, offset: int, status: Optional[str] = None) -> Dict[str, Any]:
        """Получение заказов из БД"""
        try:
            
            # Начало дня в МСК
            now_msk = TimezoneUtils.now_msk()
            today_start_msk = TimezoneUtils.get_today_start_msk()
            yesterday_start_msk = TimezoneUtils.get_yesterday_start_msk()
            
            
            # Конвертируем в UTC для фильтров БД
            today_start = TimezoneUtils.to_utc(today_start_msk)
            yesterday_start = TimezoneUtils.to_utc(yesterday_start_msk)
            
            # Оптимизированный запрос с eager loading
            orders_query = self.db.query(WBOrder).options(
                joinedload(WBOrder.cabinet)  # Загружаем кабинет
            ).filter(
                WBOrder.cabinet_id == cabinet.id
            )
            
            
            # Применяем фильтр по статусу если указан
            if status:
                orders_query = orders_query.filter(WBOrder.status == status)
            
            orders_query = orders_query.order_by(WBOrder.created_at.desc())
            
            total_orders = orders_query.count()
            
            orders = orders_query.offset(offset).limit(limit).all()
            
            
            
            # Получаем все nm_id для batch загрузки продуктов
            nm_ids = [order.nm_id for order in orders]
            products = self.db.query(WBProduct).filter(
                WBProduct.cabinet_id == cabinet.id,
                WBProduct.nm_id.in_(nm_ids)
            ).all()
            
            # Создаем словарь для быстрого поиска продуктов
            products_dict = {p.nm_id: p for p in products}
            
            # Формируем список заказов
            orders_list = []
            for order in orders:
                # Получаем продукт из предзагруженного словаря
                product = products_dict.get(order.nm_id)
                
                # Конвертируем дату в МСК для отображения
                order_date_msk = None
                if order.order_date:
                    # Если дата без timezone, считаем что это UTC
                    if order.order_date.tzinfo is None:
                        order_date_utc = order.order_date.replace(tzinfo=timezone.utc)
                    else:
                        order_date_utc = order.order_date
                    # Конвертируем в МСК
                    order_date_msk = TimezoneUtils.from_utc(order_date_utc)
                
                orders_list.append({
                    "id": order.id,
                    "order_id": order.order_id,  # ← ДОБАВЛЕНО!
                    "order_date": order_date_msk.isoformat() if order_date_msk else None,  # ← МСК!
                    "status": order.status,  # ← ДОБАВЛЕНО!
                    "date": order_date_msk.isoformat() if order_date_msk else None,  # ← МСК!
                    "amount": order.total_price or 0,
                    "product_name": order.name or "Неизвестно",
                    "brand": order.brand or "Неизвестно",
                    "warehouse_from": order.warehouse_from,
                    "warehouse_to": order.warehouse_to,
                    "commission_percent": order.commission_percent or 0.0,
                    "rating": product.rating if product else 0.0,  # Реальный рейтинг из WBProduct
                    "nm_id": order.nm_id,  # Добавляем nm_id
                    # Новые поля из WB API
                    "spp_percent": order.spp_percent,
                    "customer_price": order.customer_price,
                    "discount_percent": order.discount_percent,
                    # Логистика исключена из системы
                })
            
            # Статистика за сегодня
            orders_today = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= today_start,
                    WBOrder.status != 'canceled'
                )
            ).all()
            
            orders_yesterday = self.db.query(WBOrder).filter(
                and_(
                    WBOrder.cabinet_id == cabinet.id,
                    WBOrder.order_date >= yesterday_start,
                    WBOrder.order_date < today_start,
                    WBOrder.status != 'canceled'
                )
            ).all()
            
            today_count = len(orders_today)
            today_amount = sum(order.total_price or 0 for order in orders_today)
            yesterday_count = len(orders_yesterday)
            yesterday_amount = sum(order.total_price or 0 for order in orders_yesterday)
            
            # Рост в процентах
            growth_percent = 0.0
            if yesterday_count > 0:
                growth_percent = ((today_count - yesterday_count) / yesterday_count) * 100
            
            return {
                "orders": orders_list,
                "total_orders": total_orders,
                "statistics": {
                    "today_count": today_count,
                    "today_amount": today_amount,
                    "yesterday_count": yesterday_count,
                    "yesterday_amount": yesterday_amount,
                    "growth_percent": growth_percent,
                    "amount_growth_percent": 0.0,  # TODO: Добавить расчет роста по сумме
                    "average_check": today_amount / today_count if today_count > 0 else 0
                },
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_orders,
                    "has_more": (offset + limit) < total_orders
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            return {
                "orders": [],
                "total_orders": 0,
                "statistics": {"count": 0, "amount": 0, "yesterday_count": 0, "yesterday_amount": 0, "growth_percent": 0.0, "amount_growth_percent": 0.0, "average_check": 0.0},
                "pagination": {"limit": limit, "offset": offset, "total": 0, "has_more": False}
            }

    async def _fetch_critical_stocks_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение критичных остатков из БД"""
        try:
            # Получаем товары с критичными остатками (общая сумма <= 5)
            critical_products_query = self.db.query(WBStock.nm_id).filter(
                WBStock.cabinet_id == cabinet.id
            ).group_by(WBStock.nm_id).having(
                func.sum(WBStock.quantity) <= 5
            )
            
            # Получаем nm_id критичных товаров
            critical_nm_ids = [row[0] for row in critical_products_query.all()]
            
            if not critical_nm_ids:
                return {
                    "critical_products": [],
                    "zero_products": [],
                    "summary": {
                        "critical_count": 0,
                        "zero_count": 0,
                        "attention_needed": 0,
                        "potential_losses": 0.0
                    },
                    "recommendations": ["✅ Все товары в норме!"]
                }
            
            # Получаем детальную информацию по критичным товарам
            stocks_query = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet.id,
                    WBStock.nm_id.in_(critical_nm_ids)
                )
            ).order_by(WBStock.nm_id, WBStock.quantity.asc())
            
            total_stocks = stocks_query.count()
            stocks = stocks_query.offset(offset).limit(limit).all()
            
            # Формируем список остатков
            stocks_list = []
            for stock in stocks:
                # Используем данные из остатков для названия товара
                # Если есть category и subject, формируем название из них
                if stock.category and stock.subject:
                    product_name = f"{stock.category} - {stock.subject}"
                else:
                    product_name = "Неизвестно"
                
                product_brand = stock.brand or "Неизвестно"
                
                stocks_list.append({
                    "id": stock.id,
                    "nm_id": stock.nm_id,
                    "name": product_name,
                    "brand": product_brand,
                    "size": stock.size or "Неизвестно",
                    "quantity": stock.quantity or 0,
                    "warehouse_name": stock.warehouse_name or "Неизвестно",
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None,
                    # Новые поля из WB API
                    "category": stock.category,
                    "subject": stock.subject,
                    "price": stock.price,
                    "discount": stock.discount,
                    "quantity_full": stock.quantity_full,
                    "is_supply": stock.is_supply,
                    "is_realization": stock.is_realization,
                    "sc_code": stock.sc_code
                })
            
            # Получаем комиссии для расчета
            try:
                from app.features.wb_api.client import WBAPIClient
                client = WBAPIClient(cabinet.api_key)
                commissions_data = await client.get_commissions()
            except Exception as e:
                logger.warning(f"Не удалось получить комиссии: {e}")
                commissions_data = []
            
            # Группируем по товарам (nm_id)
            products_dict = {}
            for stock in stocks_list:
                nm_id = stock["nm_id"]
                if nm_id not in products_dict:
                    # Получаем категорию и предмет для расчета комиссии
                    category = stock.get("category")
                    subject = stock.get("subject")
                    
                    # Рассчитываем комиссию
                    commission_percent = 0.0
                    if category and subject and commissions_data:
                        for commission in commissions_data:
                            if (commission.get("parentName") == category and 
                                commission.get("subjectName") == subject):
                                commission_percent = commission.get("kgvpMarketplace", 0.0)
                                break
                    
                    products_dict[nm_id] = {
                        "nm_id": nm_id,
                        "name": stock["name"],
                        "brand": stock["brand"],
                        "stocks": {},
                        "critical_sizes": [],
                        "zero_sizes": [],
                        "days_left": {},
                        "sales_per_day": 0.0,
                        "price": stock.get("price", 0.0),
                        "commission_percent": commission_percent,
                        # Новые поля из WB API остатков
                        "category": stock.get("category"),
                        "subject": stock.get("subject"),
                        "discount": stock.get("discount", 0.0),
                        "quantity_full": stock.get("quantity_full"),
                        "is_supply": stock.get("is_supply"),
                        "is_realization": stock.get("is_realization"),
                        "sc_code": stock.get("sc_code")
                    }
                
                # Добавляем остатки по размерам
                size = stock["size"] or "Unknown"
                products_dict[nm_id]["stocks"][size] = stock["quantity"]
                
                # Определяем критические размеры
                if stock["quantity"] <= 5 and stock["quantity"] > 0:
                    products_dict[nm_id]["critical_sizes"].append(size)
                elif stock["quantity"] == 0:
                    products_dict[nm_id]["zero_sizes"].append(size)
            
            # Разделяем на критические и нулевые товары
            critical_products = []
            zero_products = []
            
            for product in products_dict.values():
                if product["critical_sizes"]:
                    critical_products.append(product)
                elif product["zero_sizes"] and not product["critical_sizes"]:
                    zero_products.append(product)
            
            return {
                "critical_products": critical_products,
                "zero_products": zero_products,
                "summary": {
                    "critical_count": len(critical_products),
                    "zero_count": len(zero_products),
                    "attention_needed": len(critical_products) + len(zero_products),
                    "potential_losses": sum(p["sales_per_day"] for p in critical_products + zero_products)
                },
                "recommendations": [
                    "Пополнить остатки критичных товаров",
                    "Проверить товары с нулевыми остатками"
                ]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения критичных остатков: {e}")
            return {
                "critical_products": [],
                "zero_products": [],
                "summary": {
                    "critical_count": 0,
                    "zero_count": 0,
                    "attention_needed": 0,
                    "potential_losses": 0.0
                },
                "recommendations": ["Ошибка получения данных"]
            }

    async def _fetch_reviews_from_db(self, cabinet: WBCabinet, limit: int, offset: int) -> Dict[str, Any]:
        """Получение отзывов из БД"""
        try:
            # Получаем отзывы
            reviews_query = self.db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id
            ).order_by(WBReview.created_date.desc())
            
            total_reviews = reviews_query.count()
            reviews = reviews_query.offset(offset).limit(limit).all()
            
            # Формируем список отзывов
            reviews_list = []
            for review in reviews:
                reviews_list.append({
                    "id": review.id,
                    "nm_id": review.nm_id,
                    "review_id": review.review_id,
                    "text": review.text or "",
                    "rating": review.rating or 0,
                    "is_answered": review.is_answered,
                    "created_date": review.created_date.isoformat() if review.created_date else None,
                    # Новые поля из WB API отзывов
                    "pros": review.pros,
                    "cons": review.cons,
                    "user_name": review.user_name,
                    "color": review.color,
                    "bables": review.bables,
                    "matching_size": review.matching_size,
                    "was_viewed": review.was_viewed,
                    "supplier_feedback_valuation": review.supplier_feedback_valuation,
                    "supplier_product_valuation": review.supplier_product_valuation
                })
            
            # Статистика
            new_reviews = len([r for r in reviews if r.created_date and r.created_date >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)])
            unanswered_reviews = len([r for r in reviews if not r.is_answered])
            avg_rating = sum(r.rating or 0 for r in reviews) / len(reviews) if reviews else 0.0
            
            return {
                "new_reviews": reviews_list,  # Список отзывов
                "unanswered_questions": [],  # Пока пустой список вопросов
                "statistics": {
                "total_reviews": total_reviews,
                    "new_today": new_reviews,
                    "unanswered": unanswered_reviews,
                "average_rating": round(avg_rating, 1),
                    "answered_count": total_reviews - unanswered_reviews,
                    "answered_percent": round((total_reviews - unanswered_reviews) / total_reviews * 100, 1) if total_reviews > 0 else 0.0,
                    "attention_needed": len([r for r in reviews if r.rating and r.rating <= 3]),
                    "new_today": new_reviews
                },
                "recommendations": ["Все отзывы обработаны"] if unanswered_reviews == 0 else [f"Требуют ответа: {unanswered_reviews} отзывов"]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения отзывов: {e}")
            return {
                "reviews": [],
                "total_reviews": 0,
                "new_reviews": 0,
                "unanswered_reviews": 0,
                "average_rating": 0.0,
                "pagination": {"limit": limit, "offset": offset, "total": 0}
            }

    async def _fetch_analytics_from_db(self, cabinet: WBCabinet, period: str) -> Dict[str, Any]:
        """Получение аналитики из БД"""
        try:
            # Начало периодов в МСК
            now_msk = TimezoneUtils.now_msk()
            today_start_msk = TimezoneUtils.get_today_start_msk()
            yesterday_start_msk = TimezoneUtils.get_yesterday_start_msk()
            week_start_msk = TimezoneUtils.get_week_start_msk()
            month_start_msk = TimezoneUtils.get_month_start_msk()
            quarter_start_msk = now_msk - timedelta(days=90)
            
            # Конвертируем в UTC для фильтров БД
            today_start = TimezoneUtils.to_utc(today_start_msk)
            yesterday_start = TimezoneUtils.to_utc(yesterday_start_msk)
            week_start = TimezoneUtils.to_utc(week_start_msk)
            month_start = TimezoneUtils.to_utc(month_start_msk)
            quarter_start = TimezoneUtils.to_utc(quarter_start_msk)
            
            # Продажи по периодам
            sales_periods = {
                "today": self._get_orders_period(cabinet.id, today_start, TimezoneUtils.to_utc(now_msk)),
                "yesterday": self._get_orders_period(cabinet.id, yesterday_start, today_start),
                "7_days": self._get_orders_period(cabinet.id, week_start, TimezoneUtils.to_utc(now_msk)),
                "30_days": self._get_orders_period(cabinet.id, month_start, TimezoneUtils.to_utc(now_msk))
            }
            
            # Динамика
            dynamics = self._calculate_dynamics(sales_periods)
            
            # Топ товары
            top_products = self._get_top_products(cabinet.id, week_start, TimezoneUtils.to_utc(now_msk))
            
            # Сводка остатков
            stocks_summary = self._get_stocks_summary(cabinet.id)
            
            # Рекомендации
            recommendations = self._generate_recommendations(sales_periods, stocks_summary)
            
            return {
                "sales_periods": sales_periods,
                "dynamics": dynamics,
                "top_products": top_products,
                "stocks_summary": stocks_summary,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {
                "sales_periods": {
                    "today": {"count": 0, "amount": 0},
                    "yesterday": {"count": 0, "amount": 0},
                    "7_days": {"count": 0, "amount": 0},
                    "30_days": {"count": 0, "amount": 0}
                },
                "dynamics": {
                    "yesterday_growth_percent": 0.0,
                    "week_growth_percent": 0.0,
                    "average_check": 0.0,
                    "conversion_percent": 0.0
                },
                "top_products": [],
                "stocks_summary": {
                    "critical_count": 0,
                    "zero_count": 0,
                    "attention_needed": 0,
                    "total_products": 0
                },
                "recommendations": ["Ошибка получения данных"]
            }

    def _get_orders_period(self, cabinet_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение заказов за период"""
        orders = self.db.query(WBOrder).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.order_date >= start_date,
                WBOrder.order_date < end_date,
                WBOrder.status != 'canceled'
            )
        ).all()
        
        count = len(orders)
        amount = sum(order.total_price or 0 for order in orders)
        
        return {"count": count, "amount": amount}

    def _calculate_dynamics(self, sales_periods: Dict[str, Any]) -> Dict[str, float]:
        """Расчет динамики продаж"""
        today = sales_periods["today"]
        yesterday = sales_periods["yesterday"]
        week = sales_periods["7_days"]
        
        # Рост к вчера
        yesterday_growth = 0.0
        if yesterday["count"] > 0:
            yesterday_growth = ((today["count"] - yesterday["count"]) / yesterday["count"]) * 100
        
        # Рост к прошлой неделе
        week_growth = 0.0
        if week["count"] > 0:
            week_growth = ((today["count"] - week["count"]) / week["count"]) * 100
        
        # Средний чек
        average_check = today["amount"] / today["count"] if today["count"] > 0 else 0.0
        
        # Конверсия (заглушка - в реальности нужны данные о просмотрах)
        conversion_percent = 0.0  # TODO: Добавить расчет конверсии
        
        return {
            "yesterday_growth_percent": yesterday_growth,
            "week_growth_percent": week_growth,
            "average_check": average_check,
            "conversion_percent": conversion_percent
        }

    def _get_top_products(self, cabinet_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Получение топ товаров"""
        # Группируем заказы по товарам
        orders = self.db.query(WBOrder).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.order_date >= start_date,
                WBOrder.order_date < end_date,
                WBOrder.status != 'canceled'
            )
        ).all()
        
        # Группировка по nm_id
        products_dict = {}
        for order in orders:
            nm_id = order.nm_id
            if nm_id not in products_dict:
                products_dict[nm_id] = {
                    "nm_id": nm_id,
                    "name": order.name or "Неизвестно",
                    "sales_count": 0,
                    "sales_amount": 0.0,
                    "rating": 0.0,
                    "stocks": {}
                }
            products_dict[nm_id]["sales_count"] += 1
            products_dict[nm_id]["sales_amount"] += order.total_price or 0
        
        # Получаем рейтинги и остатки для каждого товара
        for nm_id in products_dict:
            # Рейтинг из отзывов
            review = self.db.query(WBReview).filter(
                and_(
                    WBReview.cabinet_id == cabinet_id,
                    WBReview.nm_id == nm_id
                )
            ).first()
            if review:
                products_dict[nm_id]["rating"] = review.rating or 0.0
            
            # Остатки по размерам
            stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet_id,
                    WBStock.nm_id == nm_id
                )
            ).all()
            
            stocks_dict = {}
            for stock in stocks:
                size = stock.size or "Unknown"
                quantity = stock.quantity or 0
                # Суммируем остатки по всем складам для одного размера
                if size in stocks_dict:
                    stocks_dict[size] += quantity
                else:
                    stocks_dict[size] = quantity
            products_dict[nm_id]["stocks"] = stocks_dict
        
        # Сортируем по количеству продаж
        top_products = sorted(products_dict.values(), key=lambda x: x["sales_count"], reverse=True)
        
        return top_products[:5]  # Топ 5

    def _get_stocks_summary(self, cabinet_id: int) -> Dict[str, int]:
        """Получение сводки остатков"""
        # Критичные товары: товары с общей суммой остатков <= 5 по всем размерам и складам
        critical_products = self.db.query(WBStock.nm_id).filter(
            WBStock.cabinet_id == cabinet_id
        ).group_by(WBStock.nm_id).having(
            func.sum(WBStock.quantity) <= 5
        ).count()
        
        # Товары с нулевыми остатками: товары с общей суммой остатков = 0
        zero_products = self.db.query(WBStock.nm_id).filter(
            WBStock.cabinet_id == cabinet_id
        ).group_by(WBStock.nm_id).having(
            func.sum(WBStock.quantity) == 0
        ).count()
        
        # Общее количество товаров
        total_products = self.db.query(WBStock.nm_id).filter(
            WBStock.cabinet_id == cabinet_id
        ).distinct().count()
        
        return {
            "critical_count": critical_products,
            "zero_count": zero_products,
            "attention_needed": critical_products + zero_products,
            "total_products": total_products
        }

    def _generate_recommendations(self, sales_periods: Dict[str, Any], stocks_summary: Dict[str, int]) -> List[str]:
        """Генерация рекомендаций"""
        recommendations = []
        
        # Анализ продаж
        today = sales_periods["today"]
        yesterday = sales_periods["yesterday"]
        
        if today["count"] < yesterday["count"]:
            recommendations.append("📉 Продажи упали - проверьте рекламу")
        
        # Анализ остатков
        if stocks_summary["zero_count"] > 0:
            recommendations.append(f"📦 {stocks_summary['zero_count']} товаров с нулевыми остатками")
        
        if stocks_summary["critical_count"] > 0:
            recommendations.append(f"⚠️ {stocks_summary['critical_count']} товаров с критичными остатками")
        
        if not recommendations:
            recommendations.append("✅ Все в порядке!")
        
        return recommendations

    async def _get_product_statistics(self, cabinet_id: int, nm_id: int) -> Dict[str, Any]:
        """Получение статистики для конкретного товара"""
        try:
            now = datetime.now(timezone.utc)
            
            # Периоды для расчета
            periods = {
                "7_days": now - timedelta(days=7),
                "14_days": now - timedelta(days=14),
                "30_days": now - timedelta(days=30)
            }
            
            # Получаем выкупы товара за разные периоды из таблицы WBSales
            from ..wb_api.models_sales import WBSales
            sales_periods = {}
            for period_name, start_date in periods.items():
                buyouts = self.db.query(WBSales).filter(
                    and_(
                        WBSales.cabinet_id == cabinet_id,
                        WBSales.nm_id == nm_id,
                        WBSales.sale_date >= start_date,
                        WBSales.type == 'buyout',
                        WBSales.is_cancel == False
                    )
                ).all()
                sales_periods[period_name] = len(buyouts)
            
            # Рассчитываем выкуп (пока упрощенно - все заказы считаем выкупленными)
            buyout_rates = {}
            for period_name in ["7_days", "14_days", "30_days"]:
                if period_name in sales_periods:
                    # Упрощенный расчет: считаем что все заказы выкуплены
                    buyout_rates[period_name] = 100.0 if sales_periods[period_name] > 0 else 0.0
                else:
                    buyout_rates[period_name] = 0.0
            
            # Рассчитываем скорость заказов (заказов в день)
            order_speed = {}
            for period_name in ["7_days", "14_days", "30_days"]:
                if period_name in sales_periods:
                    days = int(period_name.split('_')[0])
                    order_speed[period_name] = sales_periods[period_name] / days if days > 0 else 0.0
                else:
                    order_speed[period_name] = 0.0
            
            return {
                "buyout_rates": buyout_rates,
                "order_speed": order_speed,
                "sales_periods": sales_periods
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики товара: {e}")
            return {
                "buyout_rates": {"7_days": 0.0, "14_days": 0.0, "30_days": 0.0},
                "order_speed": {"7_days": 0.0, "14_days": 0.0, "30_days": 0.0},
                "sales_periods": {"7_days": 0, "14_days": 0, "30_days": 0}
            }
    
    def _convert_to_msk_iso(self, dt: datetime) -> str:
        """Конвертация datetime в МСК и возврат ISO строки"""
        try:
            if dt is None:
                return None
            
            # Если дата без timezone, считаем что это UTC
            if dt.tzinfo is None:
                dt_utc = dt.replace(tzinfo=timezone.utc)
            else:
                dt_utc = dt
            
            # Конвертируем в МСК
            dt_msk = TimezoneUtils.from_utc(dt_utc)
            return dt_msk.isoformat()
            
        except Exception as e:
            logger.error(f"Ошибка конвертации даты в МСК: {e}")
            return dt.isoformat() if dt else None