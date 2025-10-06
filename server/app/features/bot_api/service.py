"""
Bot API сервис для интеграции с Telegram ботом
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.features.wb_api.models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview
from sqlalchemy import func, and_, or_, text
from datetime import datetime, timezone, timedelta
from app.features.wb_api.cache_manager import WBCacheManager
from app.features.wb_api.sync_service import WBSyncService
from .formatter import BotMessageFormatter

logger = logging.getLogger(__name__)


class BotAPIService:
    """Сервис для Bot API"""
    
    def __init__(self, db: Session, cache_manager: WBCacheManager = None, sync_service: WBSyncService = None):
        self.db = db
        self.cache_manager = cache_manager or WBCacheManager(db)
        self.sync_service = sync_service or WBSyncService(db, self.cache_manager)
        self.formatter = BotMessageFormatter()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по telegram_id"""
        try:
            # Используем прямой SQL запрос вместо ORM
            result = self.db.execute(
                text("SELECT id, telegram_id, username, first_name, last_name, created_at FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            ).fetchone()
            
            if not result:
                return None
            
            return {
                "id": result[0],
                "telegram_id": result[1],
                "username": result[2],
                "first_name": result[3],
                "last_name": result[4],
                "created_at": result[5]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None

    async def get_user_cabinet(self, telegram_id: int) -> Optional[WBCabinet]:
        """Получение кабинета пользователя по telegram_id"""
        try:
            # Сначала получаем пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None
            
            # Получаем кабинет пользователя
            cabinet = self.db.query(WBCabinet).filter(
                WBCabinet.user_id == user["id"]
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
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения дашборда: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_recent_orders(self, user: Dict[str, Any], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение последних заказов пользователя"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            orders_data = await self._fetch_orders_from_db(cabinet, limit, offset)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_orders(orders_data)
            
            return {
                "success": True,
                "data": orders_data,
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
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
            
            # Форматируем данные заказа
            order_data = {
                "id": order.id,
                "date": order.order_date.isoformat() if order.order_date else None,
                "amount": order.total_price or 0,
                "product_name": order.name or "Неизвестно",
                "brand": order.brand or "Неизвестно",
                "warehouse_from": "Неизвестно",  # Заглушка - в реальности из WBWarehouse
                "warehouse_to": "Неизвестно",    # Заглушка - в реальности из WBWarehouse
                "commission_percent": order.commission_percent or 0.0,  # Реальные данные из БД
                "commission_amount": order.commission_amount or 0.0,  # Реальные данные из БД
                "rating": 0.0,  # Заглушка - в реальности из WBReview
                # Дополнительные поля для детального отчета
                "order_id": order.order_id,
                "nm_id": order.nm_id,
                "article": order.article,
                "size": order.size,
                "barcode": order.barcode,
                "quantity": order.quantity,
                "price": order.price,
                "total_price": order.total_price,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "status": order.status,
                "created_at": order.created_at.isoformat()
            }
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_order_detail({"order": order_data})
            
            return {
                "success": True,
                "data": order_data,
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей заказа: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_critical_stocks(self, user: Dict[str, Any], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение критичных остатков"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            stocks_data = await self._fetch_critical_stocks_from_db(cabinet, limit, offset)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_critical_stocks_message(stocks_data)
            
            return {
                "success": True,
                "data": stocks_data,
                "telegram_text": telegram_text
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения критичных остатков: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_reviews_summary(self, user: Dict[str, Any], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """Получение сводки по отзывам"""
        try:
            cabinet = await self.get_user_cabinet(user["telegram_id"])
            if not cabinet:
                return {
                    "success": False,
                    "error": "Кабинет WB не найден"
                }
            
            # Получаем данные из БД
            reviews_data = await self._fetch_reviews_from_db(cabinet, limit, offset)
            
            # Форматируем Telegram сообщение
            telegram_text = self.formatter.format_reviews_message(reviews_data)
            
            return {
                "success": True,
                "data": reviews_data,
                "telegram_text": telegram_text
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
            telegram_text = self.formatter.format_analytics_message(analytics_data)
            
            return {
                "success": True,
                "data": analytics_data,
                "telegram_text": telegram_text
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
        """Подключение WB кабинета"""
        try:
            logger.info(f"connect_cabinet called with user: {user}, api_key: {api_key}")
            logger.info(f"user type: {type(user)}")
            # Проверяем, есть ли уже кабинет у пользователя
            existing_cabinet = self.db.query(WBCabinet).filter(
                WBCabinet.user_id == user["id"]
            ).first()
            if existing_cabinet:
                return {
                    "success": False,
                    "error": "Cabinet already connected"
                }
            
            # Проверяем, не используется ли уже этот API ключ
            existing_key = self.db.query(WBCabinet).filter(
                WBCabinet.api_key == api_key
            ).first()
            if existing_key:
                return {
                    "success": False,
                    "error": "API key already in use"
                }
            
            # Валидируем API ключ через WB API
            logger.info(f"Creating WBAPIClient with api_key: {api_key}")
            from app.features.wb_api.client import WBAPIClient
            
            # Создаем временный объект кабинета для валидации
            temp_cabinet = WBCabinet(
                user_id=user["id"],
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
            
            # Создаем кабинет
            cabinet = WBCabinet(
                user_id=user["id"],
                api_key=api_key,
                name=f"WB Cabinet {user['telegram_id']}",
                is_active=True
            )
            
            self.db.add(cabinet)
            self.db.commit()
            self.db.refresh(cabinet)
            
            # Форматируем ответ
            cabinet_data = {
                "cabinet_id": str(cabinet.id),
                "cabinet_name": cabinet.name,
                "api_key": api_key,
                "connected_at": cabinet.created_at.isoformat() if cabinet.created_at else None,
                "status": "connected",
                "api_key_status": "valid"
            }
            
            telegram_text = self.formatter.format_cabinet_connect_message(cabinet_data)
            
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
        """Получение статуса кабинетов пользователя"""
        try:
            # Получаем все кабинеты пользователя
            cabinets = self.db.query(WBCabinet).filter(
                WBCabinet.user_id == user["id"]
            ).all()
            
            if not cabinets:
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
                    "api_key_status": "valid" if cabinet.is_active else "invalid",
                    "connected_at": cabinet.created_at.isoformat() if cabinet.created_at else None,
                    "last_sync": cabinet.last_sync_at.isoformat() if cabinet.last_sync_at else None
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
                "telegram_text": telegram_text
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
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            # Товары
            total_products = self.db.query(WBProduct).filter(
                WBProduct.cabinet_id == cabinet.id
            ).count()
            
            active_products = self.db.query(WBProduct).filter(
                and_(
                    WBProduct.cabinet_id == cabinet.id,
                    WBProduct.is_active == True
                )
            ).count()
            
            critical_stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet.id,
                    WBStock.quantity <= 5
                )
            ).count()
            
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
                "last_sync": cabinet.last_sync_at.strftime("%d.%m.%Y %H:%M") if cabinet.last_sync_at else "Никогда",
                "status": "Активен" if cabinet.is_active else "Неактивен",
                "products": {
                    "total": total_products,
                    "active": active_products,
                    "moderation": 0,  # Заглушка
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
                    "critical_count": critical_stocks,
                    "zero_count": self.db.query(WBStock).filter(
                        and_(
                            WBStock.cabinet_id == cabinet.id,
                            WBStock.quantity == 0
                        )
                    ).count(),
                    "attention_needed": critical_stocks,
                    "top_product": "Нет данных"  # Заглушка
                },
                "reviews": {
                    "new_count": new_reviews,
                    "average_rating": round(avg_rating, 1),
                    "unanswered": unanswered_reviews,
                    "total": len(reviews)
                },
                "recommendations": ["Все в порядке!"]  # Заглушка
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
                    WBOrder.status != 'canceled'
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
                    "amount_growth_percent": 0.0,  # Заглушка
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
            # Получаем товары с критичными остатками
            stocks_query = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet.id,
                    WBStock.quantity <= 5
                )
            ).order_by(WBStock.quantity.asc())
            
            total_stocks = stocks_query.count()
            stocks = stocks_query.offset(offset).limit(limit).all()
            
            # Формируем список остатков
            stocks_list = []
            for stock in stocks:
                stocks_list.append({
                    "id": stock.id,
                    "nm_id": stock.nm_id,
                    "name": stock.name or "Неизвестно",
                    "brand": stock.brand or "Неизвестно",
                    "size": stock.size or "Неизвестно",
                    "quantity": stock.quantity or 0,
                    "warehouse_name": stock.warehouse_name or "Неизвестно",
                    "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
                })
            
            return {
                "stocks": stocks_list,
                "total_stocks": total_stocks,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_stocks
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения критичных остатков: {e}")
            return {
                "stocks": [],
                "total_stocks": 0,
                "pagination": {"limit": limit, "offset": offset, "total": 0}
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
                    "created_date": review.created_date.isoformat() if review.created_date else None
                })
            
            # Статистика
            new_reviews = len([r for r in reviews if r.created_date and r.created_date >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)])
            unanswered_reviews = len([r for r in reviews if not r.is_answered])
            avg_rating = sum(r.rating or 0 for r in reviews) / len(reviews) if reviews else 0.0
            
            return {
                "reviews": reviews_list,
                "total_reviews": total_reviews,
                "new_reviews": new_reviews,
                "unanswered_reviews": unanswered_reviews,
                "average_rating": round(avg_rating, 1),
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total": total_reviews
                }
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
            # Заглушка - в реальности здесь должна быть сложная аналитика
            return {
                "period": period,
                "sales": {
                    "total_amount": 0,
                    "total_orders": 0,
                    "average_order": 0
                },
                "products": {
                    "total": 0,
                    "active": 0,
                    "top_selling": "Нет данных"
                },
                "reviews": {
                    "total": 0,
                    "average_rating": 0.0,
                    "unanswered": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {
                "period": period,
                "sales": {"total_amount": 0, "total_orders": 0, "average_order": 0},
                "products": {"total": 0, "active": 0, "top_selling": "Ошибка"},
                "reviews": {"total": 0, "average_rating": 0.0, "unanswered": 0}
            }