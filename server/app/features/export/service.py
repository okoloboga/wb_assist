"""
Сервис для экспорта данных WB в Google Sheets
"""

import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...core.database import get_db
from ..wb_api.models import WBCabinet, WBOrder, WBStock, WBReview, WBProduct
from ..wb_api.models_sales import WBSales
from .models import ExportToken, ExportLog
from .schemas import ExportStatus, ExportDataType
from .schemas import ExportDataResponse, ExportStatsResponse, CabinetValidationResponse

logger = logging.getLogger(__name__)


class ExportService:
    """Сервис для экспорта данных в Google Sheets"""

    def __init__(self, db: Session):
        self.db = db
        self._sheets_service = None
    
    def _get_sheets_service(self):
        """Инициализирует Google Sheets API сервис"""
        if self._sheets_service is None:
            try:
                key_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'config/wb-assist.json')
                scopes = ['https://www.googleapis.com/auth/spreadsheets']
                
                credentials = service_account.Credentials.from_service_account_file(
                    key_file, 
                    scopes=scopes
                )
                
                self._sheets_service = build('sheets', 'v4', credentials=credentials)
                logger.info("Google Sheets API сервис инициализирован")
            except Exception as e:
                logger.error(f"Ошибка инициализации Google Sheets API: {e}")
                raise
        return self._sheets_service

    def get_cabinet_spreadsheet(self, cabinet_id: int) -> Optional[str]:
        """Возвращает spreadsheet_id привязанной таблицы кабинета или None"""
        cabinet = self.db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        return cabinet.spreadsheet_id if cabinet and cabinet.spreadsheet_id else None

    def create_export_token(self, user_id: int, cabinet_id: int) -> ExportToken:
        """Создает или возвращает существующий токен экспорта для кабинета"""
        # Проверяем, что кабинет существует и принадлежит пользователю
        cabinet = self.db.query(WBCabinet).filter(
            and_(WBCabinet.id == cabinet_id, WBCabinet.is_active == True)
        ).first()
        
        if not cabinet:
            raise ValueError(f"Кабинет {cabinet_id} не найден или неактивен")

        # Проверяем, есть ли уже токен для этого кабинета (даже деактивированный)
        # Токен всегда одинаковый для одного кабинета (детерминированный)
        existing_token = self.db.query(ExportToken).filter(
            ExportToken.cabinet_id == cabinet_id
        ).first()
        
        if existing_token:
            # Активируем токен на случай, если он был деактивирован
            existing_token.is_active = True
            self.db.commit()
            self.db.refresh(existing_token)
            logger.info(f"Возвращен существующий токен для кабинета {cabinet_id}, пользователя {user_id}")
            return existing_token

        # Создаем новый токен только если его еще нет
        # Токен будет фиксированным для этого кабинета
        token_value = ExportToken.generate_token(cabinet_id)
        export_token = ExportToken(
            token=token_value,
            user_id=user_id,
            cabinet_id=cabinet_id,
            is_active=True,
            rate_limit_remaining=60
        )
        
        self.db.add(export_token)
        self.db.commit()
        self.db.refresh(export_token)
        
        logger.info(f"Создан новый фиксированный токен для кабинета {cabinet_id}, пользователя {user_id}")
        return export_token

    def validate_token(self, token: str, cabinet_id: int) -> Tuple[bool, Optional[ExportToken]]:
        """Валидирует токен экспорта"""
        export_token = self.db.query(ExportToken).filter(
            and_(
                ExportToken.token == token,
                ExportToken.cabinet_id == cabinet_id,
                ExportToken.is_active == True
            )
        ).first()
        
        if not export_token:
            return False, None
            
        # Проверяем целостность токена
        if not export_token.verify_token(cabinet_id):
            logger.warning(f"Неверная целостность токена {token} для кабинета {cabinet_id}")
            return False, None
            
        # Проверяем rate limiting
        if export_token.is_rate_limited():
            logger.warning(f"Превышен лимит запросов для токена {token}")
            return False, export_token
            
        return True, export_token

    def log_export_request(
        self,
        token: ExportToken,
        status: ExportStatus,
        data_type: ExportDataType,
        rows_count: Optional[int] = None,
        error_message: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ExportLog:
        """Логирует запрос экспорта"""
        export_log = ExportLog(
            token_id=token.id,
            status=status.value,
            data_type=data_type.value,
            rows_count=rows_count,
            error_message=error_message,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(export_log)
        
        # Обновляем статистику токена
        if status == ExportStatus.SUCCESS:
            token.consume_rate_limit()
        
        self.db.commit()
        self.db.refresh(export_log)
        
        return export_log

    def get_orders_data(self, cabinet_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получает данные заказов для экспорта с названием товара из WBProduct"""
        orders = self.db.query(WBOrder, WBProduct).join(
            WBProduct,
            and_(
                WBOrder.nm_id == WBProduct.nm_id,
                WBOrder.cabinet_id == WBProduct.cabinet_id
            ),
            isouter=True
        ).filter(
            WBOrder.cabinet_id == cabinet_id
        ).order_by(desc(WBOrder.order_date)).limit(limit).all()
        
        # Получаем уникальные nm_id из заказов для сбора статистики
        unique_nm_ids = list(set(order.nm_id for order, _ in orders))
        
        # Собираем статистику для всех товаров оптимизированными запросами
        product_stats = {}
        if unique_nm_ids:
            # Получаем рейтинги товаров одним запросом
            products = self.db.query(WBProduct.nm_id, WBProduct.rating).filter(
                and_(
                    WBProduct.cabinet_id == cabinet_id,
                    WBProduct.nm_id.in_(unique_nm_ids)
                )
            ).all()
            ratings_dict = {nm_id: rating for nm_id, rating in products}
            
            # Общее количество заказов, выкупов и возвратов одним запросом с группировкой
            total_orders = self.db.query(
                WBOrder.nm_id,
                func.count(WBOrder.id).label('count')
            ).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id.in_(unique_nm_ids)
                )
            ).group_by(WBOrder.nm_id).all()
            total_orders_dict = {nm_id: count for nm_id, count in total_orders}
            
            total_buyouts = self.db.query(
                WBSales.nm_id,
                func.count(WBSales.id).label('count')
            ).filter(
                and_(
                    WBSales.cabinet_id == cabinet_id,
                    WBSales.nm_id.in_(unique_nm_ids),
                    WBSales.type == 'buyout',
                    WBSales.is_cancel == False
                )
            ).group_by(WBSales.nm_id).all()
            total_buyouts_dict = {nm_id: count for nm_id, count in total_buyouts}
            
            # Формируем словарь статистики для всех товаров
            for nm_id in unique_nm_ids:
                total_orders_count = total_orders_dict.get(nm_id, 0)
                total_buyouts_count = total_buyouts_dict.get(nm_id, 0)
                
                buyout_percent = (total_buyouts_count / total_orders_count * 100) if total_orders_count > 0 else 0.0
                
                product_stats[nm_id] = {
                    "rating": ratings_dict.get(nm_id),
                    "buyout_percent": buyout_percent
                }
        
        data = []
        for order, product in orders:
            image_url = product.image_url if product else None
            image_formula = f'=IMAGE("{image_url}")' if image_url else ''
            
            # Переводим статус на русский
            status_map = {
                "active": "Активный",
                "canceled": "Отменен"
            }
            status_ru = status_map.get(order.status.lower() if order.status else "", order.status or "")
            
            # Получаем статистику для товара
            stats = product_stats.get(order.nm_id, {})
            
            data.append({
                "photo": image_formula,                          # A - photo (formula)
                "order_id": order.order_id,                     # B - order_id
                "nm_id": order.nm_id,                           # C - nm_id
                "product_name": product.name if product else None,  # D - product.name
                "size": order.size,                             # E - size
                "status": status_ru,                            # F - status (русский)
                "order_date": order.order_date.strftime("%Y-%m-%d %H:%M") if order.order_date else None,  # G - order_date
                "warehouse_from": order.warehouse_from,         # H - warehouse_from
                "warehouse_to": order.warehouse_to,             # I - warehouse_to
                "total_price": order.total_price,               # J - total_price (перемещено после warehouse_to)
                "commission_amount": order.commission_amount,   # K - commission_amount
                "customer_price": order.customer_price,         # L - customer_price (поменяли с spp_percent)
                "spp_percent": order.spp_percent,               # M - spp_percent (поменяли с customer_price)
                "discount_percent": order.discount_percent,     # N - discount_percent
                "buyout_percent": round(stats.get('buyout_percent', 0), 2),  # O - % выкуп
                "rating": stats.get('rating')                   # P - Рейтинг
            })
        
        return data

    def get_stocks_data(self, cabinet_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получает данные остатков для экспорта с группировкой по складам (без размеров)"""
        # Получаем все записи для корректной агрегации
        stocks = self.db.query(WBStock, WBProduct).join(
            WBProduct,
            and_(
                WBStock.nm_id == WBProduct.nm_id,
                WBStock.cabinet_id == WBProduct.cabinet_id
            ),
            isouter=True
        ).filter(
            WBStock.cabinet_id == cabinet_id
        ).order_by(WBStock.nm_id, WBStock.warehouse_name).all()
        
        # Группируем по nm_id + warehouse_name и суммируем количества
        aggregated = {}
        for stock, product in stocks:
            key = (stock.nm_id, stock.warehouse_name)
            
            if key not in aggregated:
                image_url = product.image_url if product else None
                image_formula = f'=IMAGE("{image_url}")' if image_url else ''
                
                aggregated[key] = {
                    "photo": image_formula,
                    "nm_id": stock.nm_id,
                    "product_name": product.name if product else None,
                    "brand": stock.brand or "",
                    "warehouse_name": stock.warehouse_name,
                    "quantity": 0,
                    "in_way_to_client": 0,
                    "in_way_from_client": 0,
                    "price": stock.price or 0,
                    "discount": stock.discount or 0,
                    "last_updated": stock.last_updated
                }
            
            # Суммируем количества
            aggregated[key]["quantity"] += stock.quantity or 0
            aggregated[key]["in_way_to_client"] += stock.in_way_to_client or 0
            aggregated[key]["in_way_from_client"] += stock.in_way_from_client or 0
            
            # Обновляем дату на самую свежую
            if stock.last_updated and (not aggregated[key]["last_updated"] or stock.last_updated > aggregated[key]["last_updated"]):
                aggregated[key]["last_updated"] = stock.last_updated
        
        # Получаем уникальные nm_id для сбора статистики
        unique_nm_ids = list(set(item["nm_id"] for item in aggregated.values()))
        
        if not unique_nm_ids:
            return []
        
        # Собираем статистику для всех товаров оптимизированными запросами
        now = datetime.now(timezone.utc)
        periods = {
            "7_days": now - timedelta(days=7),
            "14_days": now - timedelta(days=14),
            "30_days": now - timedelta(days=30)
        }
        
        # Получаем рейтинги товаров одним запросом
        products = self.db.query(WBProduct.nm_id, WBProduct.rating).filter(
            and_(
                WBProduct.cabinet_id == cabinet_id,
                WBProduct.nm_id.in_(unique_nm_ids)
            )
        ).all()
        ratings_dict = {nm_id: rating for nm_id, rating in products}
        
        # Получаем заказы за периоды одним запросом с группировкой
        orders_7d = self.db.query(
            WBOrder.nm_id,
            func.count(WBOrder.id).label('count')
        ).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.nm_id.in_(unique_nm_ids),
                WBOrder.order_date >= periods["7_days"]
            )
        ).group_by(WBOrder.nm_id).all()
        orders_7d_dict = {nm_id: count for nm_id, count in orders_7d}
        
        orders_14d = self.db.query(
            WBOrder.nm_id,
            func.count(WBOrder.id).label('count')
        ).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.nm_id.in_(unique_nm_ids),
                WBOrder.order_date >= periods["14_days"]
            )
        ).group_by(WBOrder.nm_id).all()
        orders_14d_dict = {nm_id: count for nm_id, count in orders_14d}
        
        orders_30d = self.db.query(
            WBOrder.nm_id,
            func.count(WBOrder.id).label('count')
        ).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.nm_id.in_(unique_nm_ids),
                WBOrder.order_date >= periods["30_days"]
            )
        ).group_by(WBOrder.nm_id).all()
        orders_30d_dict = {nm_id: count for nm_id, count in orders_30d}
        
        # Получаем выкупы за периоды одним запросом с группировкой
        buyouts_7d = self.db.query(
            WBSales.nm_id,
            func.count(WBSales.id).label('count')
        ).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.nm_id.in_(unique_nm_ids),
                WBSales.sale_date >= periods["7_days"],
                WBSales.type == 'buyout',
                WBSales.is_cancel == False
            )
        ).group_by(WBSales.nm_id).all()
        buyouts_7d_dict = {nm_id: count for nm_id, count in buyouts_7d}
        
        buyouts_14d = self.db.query(
            WBSales.nm_id,
            func.count(WBSales.id).label('count')
        ).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.nm_id.in_(unique_nm_ids),
                WBSales.sale_date >= periods["14_days"],
                WBSales.type == 'buyout',
                WBSales.is_cancel == False
            )
        ).group_by(WBSales.nm_id).all()
        buyouts_14d_dict = {nm_id: count for nm_id, count in buyouts_14d}
        
        buyouts_30d = self.db.query(
            WBSales.nm_id,
            func.count(WBSales.id).label('count')
        ).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.nm_id.in_(unique_nm_ids),
                WBSales.sale_date >= periods["30_days"],
                WBSales.type == 'buyout',
                WBSales.is_cancel == False
            )
        ).group_by(WBSales.nm_id).all()
        buyouts_30d_dict = {nm_id: count for nm_id, count in buyouts_30d}
        
        # Общее количество заказов, выкупов и возвратов одним запросом с группировкой
        total_orders = self.db.query(
            WBOrder.nm_id,
            func.count(WBOrder.id).label('count')
        ).filter(
            and_(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.nm_id.in_(unique_nm_ids)
            )
        ).group_by(WBOrder.nm_id).all()
        total_orders_dict = {nm_id: count for nm_id, count in total_orders}
        
        total_buyouts = self.db.query(
            WBSales.nm_id,
            func.count(WBSales.id).label('count')
        ).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.nm_id.in_(unique_nm_ids),
                WBSales.type == 'buyout',
                WBSales.is_cancel == False
            )
        ).group_by(WBSales.nm_id).all()
        total_buyouts_dict = {nm_id: count for nm_id, count in total_buyouts}
        
        total_returns = self.db.query(
            WBSales.nm_id,
            func.count(WBSales.id).label('count')
        ).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.nm_id.in_(unique_nm_ids),
                WBSales.type == 'return',
                WBSales.is_cancel == False
            )
        ).group_by(WBSales.nm_id).all()
        total_returns_dict = {nm_id: count for nm_id, count in total_returns}
        
        # Формируем словарь статистики для всех товаров
        product_stats = {}
        for nm_id in unique_nm_ids:
            total_orders_count = total_orders_dict.get(nm_id, 0)
            total_buyouts_count = total_buyouts_dict.get(nm_id, 0)
            total_returns_count = total_returns_dict.get(nm_id, 0)
            
            buyout_percent = (total_buyouts_count / total_orders_count * 100) if total_orders_count > 0 else 0.0
            return_percent = (total_returns_count / total_orders_count * 100) if total_orders_count > 0 else 0.0
            
            product_stats[nm_id] = {
                "orders_7d": orders_7d_dict.get(nm_id, 0),
                "orders_14d": orders_14d_dict.get(nm_id, 0),
                "orders_30d": orders_30d_dict.get(nm_id, 0),
                "buyouts_7d": buyouts_7d_dict.get(nm_id, 0),
                "buyouts_14d": buyouts_14d_dict.get(nm_id, 0),
                "buyouts_30d": buyouts_30d_dict.get(nm_id, 0),
                "rating": ratings_dict.get(nm_id),
                "buyout_percent": buyout_percent,
                "return_percent": return_percent
            }
        
        # Преобразуем в список и форматируем даты
        data = []
        for key, item in aggregated.items():
            nm_id = item["nm_id"]
            stats = product_stats.get(nm_id, {})
            
            data.append({
                "photo": item["photo"],                              # A - photo (formula)
                "nm_id": item["nm_id"],                              # B - nm_id
                "product_name": item["product_name"],                # C - product.name
                "brand": item["brand"],                               # D - brand
                "warehouse_name": item["warehouse_name"],            # E - warehouse_name (size убран!)
                "quantity": item["quantity"],                        # F - quantity (суммировано)
                "in_way_to_client": item["in_way_to_client"],       # G - in_way_to_client (суммировано)
                "in_way_from_client": item["in_way_from_client"],   # H - in_way_from_client (суммировано)
                "orders_buyouts_7d": f"{stats.get('orders_7d', 0)} / {stats.get('buyouts_7d', 0)}",  # I - Заказ/Выкуп Неделя
                "orders_buyouts_14d": f"{stats.get('orders_14d', 0)} / {stats.get('buyouts_14d', 0)}",  # J - Заказ/Выкуп 2 Недели
                "orders_buyouts_30d": f"{stats.get('orders_30d', 0)} / {stats.get('buyouts_30d', 0)}",  # K - Заказ/Выкуп Месяц
                "price": item["price"],                              # L - price
                "discount": item["discount"],                        # M - discount
                "rating": stats.get('rating'),                       # N - Рейтинг (last_updated убран!)
                "buyout_percent": round(stats.get('buyout_percent', 0), 2),  # O - % выкуп
                "return_percent": round(stats.get('return_percent', 0), 2)   # P - % возврат
            })
        
        # Сортируем и ограничиваем результат
        data.sort(key=lambda x: (x["nm_id"], x["warehouse_name"]))
        return data[:limit]

    def get_reviews_data(self, cabinet_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получает данные отзывов для экспорта с названием товара и размером из WBProduct и WBStock"""
        # Сначала получаем все размеры из stock для кабинета
        stock_sizes = self.db.query(WBStock.nm_id, WBStock.size).filter(
            WBStock.cabinet_id == cabinet_id
        ).all()
        
        # Создаем словарь nm_id -> первый доступный размер
        size_map = {}
        for nm_id, size in stock_sizes:
            if size and nm_id not in size_map:
                size_map[nm_id] = size
        
        # Получаем отзывы с продуктами
        reviews = self.db.query(WBReview, WBProduct).join(
            WBProduct, 
            and_(
                WBReview.nm_id == WBProduct.nm_id,
                WBReview.cabinet_id == WBProduct.cabinet_id
            ),
            isouter=True
        ).filter(
            WBReview.cabinet_id == cabinet_id
        ).order_by(desc(WBReview.created_date)).limit(limit).all()
        
        data = []
        for review, product in reviews:
            image_url = product.image_url if product else None
            image_formula = f'=IMAGE("{image_url}")' if image_url else ''
            
            # Используем размер из review, если он есть и не 'ok', иначе берем из size_map
            size = review.matching_size if review.matching_size and review.matching_size != 'ok' else size_map.get(review.nm_id)
            
            data.append({
                "photo": image_formula,                        # A - photo (formula)
                "review_id": review.review_id,                 # B - review_id
                "nm_id": review.nm_id,                         # C - nm_id
                "product_name": product.name if product else None,  # D - product.name
                "rating": review.rating,                       # E - rating
                "text": review.text,                           # F - text
                "pros": review.pros,                           # G - pros
                "cons": review.cons,                           # H - cons
                "user_name": review.user_name,                 # I - user_name
                "color": review.color,                         # J - color
                "matching_size": size,                         # K - size (из review или stock)
                "created_date": review.created_date.strftime("%Y-%m-%d %H:%M") if review.created_date else None,  # L - created_date
                "is_answered": "✅" if review.is_answered else "❌",  # M - is_answered
                "was_viewed": "✅" if review.was_viewed else "❌"  # N - was_viewed
            })
        
        return data

    def get_export_data(
        self, 
        cabinet_id: int, 
        data_type: ExportDataType, 
        limit: int = 1000
    ) -> ExportDataResponse:
        """Получает данные для экспорта по типу"""
        start_time = datetime.now()
        
        if data_type == ExportDataType.ORDERS:
            data = self.get_orders_data(cabinet_id, limit)
        elif data_type == ExportDataType.STOCKS:
            data = self.get_stocks_data(cabinet_id, limit)
        elif data_type == ExportDataType.REVIEWS:
            data = self.get_reviews_data(cabinet_id, limit)
        else:
            raise ValueError(f"Неподдерживаемый тип данных: {data_type}")
        
        # Получаем время последней синхронизации кабинета
        cabinet = self.db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        last_updated = cabinet.last_sync_at if cabinet else None
        
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return ExportDataResponse(
            data=data,
            total_rows=len(data),
            last_updated=last_updated,
            cabinet_id=cabinet_id,
            data_type=data_type
        )

    def validate_cabinet(self, cabinet_id: int) -> CabinetValidationResponse:
        """Валидирует кабинет и проверяет наличие данных"""
        cabinet = self.db.query(WBCabinet).filter(
            and_(WBCabinet.id == cabinet_id, WBCabinet.is_active == True)
        ).first()
        
        if not cabinet:
            return CabinetValidationResponse(
                is_valid=False,
                cabinet_id=cabinet_id,
                has_data=False
            )
        
        # Подсчитываем данные по типам
        orders_count = self.db.query(WBOrder).filter(WBOrder.cabinet_id == cabinet_id).count()
        stocks_count = self.db.query(WBStock).filter(WBStock.cabinet_id == cabinet_id).count()
        reviews_count = self.db.query(WBReview).filter(WBReview.cabinet_id == cabinet_id).count()
        
        data_counts = {
            "orders": orders_count,
            "stocks": stocks_count,
            "reviews": reviews_count
        }
        
        has_data = any(count > 0 for count in data_counts.values())
        
        return CabinetValidationResponse(
            is_valid=True,
            cabinet_id=cabinet_id,
            cabinet_name=cabinet.name,
            has_data=has_data,
            last_sync=cabinet.last_sync_at,
            data_counts=data_counts
        )

    def get_export_stats(self, token: ExportToken, days: int = 7) -> ExportStatsResponse:
        """Получает статистику экспорта для токена"""
        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Общая статистика
        total_requests = self.db.query(ExportLog).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.timestamp >= since_date
            )
        ).count()
        
        successful_requests = self.db.query(ExportLog).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.status == ExportStatus.SUCCESS.value,
                ExportLog.timestamp >= since_date
            )
        ).count()
        
        failed_requests = self.db.query(ExportLog).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.status == ExportStatus.ERROR.value,
                ExportLog.timestamp >= since_date
            )
        ).count()
        
        rate_limited_requests = self.db.query(ExportLog).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.status == ExportStatus.RATE_LIMIT.value,
                ExportLog.timestamp >= since_date
            )
        ).count()
        
        # Среднее время ответа
        avg_response_time = self.db.query(func.avg(ExportLog.response_time_ms)).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.response_time_ms.isnot(None),
                ExportLog.timestamp >= since_date
            )
        ).scalar() or 0
        
        # Самый запрашиваемый тип данных
        most_requested = self.db.query(
            ExportLog.data_type,
            func.count(ExportLog.data_type).label('count')
        ).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.timestamp >= since_date
            )
        ).group_by(ExportLog.data_type).order_by(desc('count')).first()
        
        most_requested_data_type = most_requested[0] if most_requested else "unknown"
        
        # Запросы за последние 24 часа
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        last_24h_requests = self.db.query(ExportLog).filter(
            and_(
                ExportLog.token_id == token.id,
                ExportLog.timestamp >= last_24h
            )
        ).count()
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        return ExportStatsResponse(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            rate_limited_requests=rate_limited_requests,
            success_rate=round(success_rate, 2),
            avg_response_time_ms=round(avg_response_time, 2),
            last_24h_requests=last_24h_requests,
            most_requested_data_type=most_requested_data_type
        )

    def revoke_token(self, token: str) -> bool:
        """Отзывает токен экспорта"""
        export_token = self.db.query(ExportToken).filter(
            ExportToken.token == token
        ).first()
        
        if not export_token:
            return False
            
        export_token.is_active = False
        self.db.commit()
        
        logger.info(f"Токен {token} отозван")
        return True
    
    @staticmethod
    def extract_spreadsheet_id(url: str) -> str:
        """Извлекает ID из Google Sheets URL"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        raise ValueError(f"Неверный формат URL: {url}")
    
    def set_cabinet_spreadsheet(self, cabinet_id: int, spreadsheet_url: str) -> Dict[str, Any]:
        """Сохраняет spreadsheet_id для кабинета"""
        # Извлекаем ID из URL
        try:
            spreadsheet_id = self.extract_spreadsheet_id(spreadsheet_url)
        except ValueError as e:
            raise ValueError(f"Не удалось извлечь ID из URL: {e}")
        
        # Проверяем доступ к таблице
        try:
            service = self._get_sheets_service()
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        except HttpError as e:
            if e.resp.status == 403:
                raise ValueError(
                    "Нет доступа к таблице. "
                    "Убедитесь, что вы дали доступ боту: wb-assist-sheets@wb-assist.iam.gserviceaccount.com"
                )
            else:
                raise ValueError(f"Ошибка доступа к таблице: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка проверки доступа: {e}")
        
        # Обновляем кабинет
        cabinet = self.db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise ValueError(f"Кабинет {cabinet_id} не найден")
        
        cabinet.spreadsheet_id = spreadsheet_id
        self.db.commit()
        
        logger.info(f"Сохранен spreadsheet_id для кабинета {cabinet_id}: {spreadsheet_id}")
        
        return {
            "cabinet_id": cabinet_id,
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        }
    
    def update_spreadsheet(self, cabinet_id: int) -> bool:
        """Обновляет Google Sheets таблицу данными кабинета"""
        # Получаем кабинет
        cabinet = self.db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet or not cabinet.spreadsheet_id:
            logger.warning(f"Кабинет {cabinet_id} не имеет привязанной таблицы")
            return False
        
        spreadsheet_id = cabinet.spreadsheet_id
        
        try:
            service = self._get_sheets_service()
            
            # Получаем данные
            logger.info(f"Начинаем получение данных для кабинета {cabinet_id}...")
            orders_data = self.get_orders_data(cabinet_id, limit=10000)
            logger.info(f"Получено {len(orders_data)} заказов")
            
            stocks_data = self.get_stocks_data(cabinet_id, limit=10000)
            logger.info(f"Получено {len(stocks_data)} остатков")
            
            reviews_data = self.get_reviews_data(cabinet_id, limit=10000)
            logger.info(f"Получено {len(reviews_data)} отзывов")
            
            # Обновляем заказы
            if orders_data:
                logger.info("Формируем данные для листа Заказы...")
                values = [[
                    order.get('photo', ''),              # A - photo (formula)
                    order.get('order_id', ''),           # B - order_id
                    order.get('nm_id', ''),              # C - nm_id
                    order.get('product_name', ''),       # D - product.name
                    order.get('size', ''),               # E - size
                    order.get('status', ''),             # F - status (quantity и price убраны)
                    order.get('order_date', ''),         # G - order_date
                    order.get('warehouse_from', ''),     # H - warehouse_from
                    order.get('warehouse_to', ''),       # I - warehouse_to
                    order.get('total_price', 0),         # J - total_price (перемещено после warehouse_to)
                    order.get('commission_amount', 0),   # K - commission_amount
                    order.get('customer_price', 0),      # L - customer_price (поменяли с spp_percent)
                    order.get('spp_percent', 0),         # M - spp_percent (поменяли с customer_price)
                    order.get('discount_percent', 0),    # N - discount_percent
                    order.get('buyout_percent', 0),      # O - % выкуп
                    order.get('rating')                  # P - Рейтинг
                ] for order in orders_data]
                
                # Очищаем старые данные
                logger.info("Очищаем старые данные в листе Заказы...")
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='🛒 Заказы!A2:P'  # Изменено с A2:N на A2:P (добавлены колонки % выкуп и Рейтинг)
                ).execute()
                
                # Записываем новые данные
                if values:
                    logger.info(f"Записываем {len(values)} строк в лист Заказы...")
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='🛒 Заказы!A2',
                        valueInputOption='USER_ENTERED',
                        body={'values': values}
                    ).execute()
                    logger.info("Лист Заказы успешно обновлен")
            
            # Обновляем остатки
            if stocks_data:
                logger.info("Формируем данные для листа Склад...")
                values = [[
                    stock.get('photo', ''),               # A - photo (formula)
                    stock.get('nm_id', ''),               # B - nm_id
                    stock.get('product_name', ''),        # C - product.name
                    stock.get('brand', ''),               # D - brand
                    stock.get('warehouse_name', ''),      # E - warehouse_name (size убран!)
                    stock.get('quantity', 0),             # F - quantity (суммировано)
                    stock.get('in_way_to_client', 0),     # G - in_way_to_client (суммировано)
                    stock.get('in_way_from_client', 0),   # H - in_way_from_client (суммировано)
                    stock.get('orders_buyouts_7d', ''),   # I - Заказ/Выкуп Неделя
                    stock.get('orders_buyouts_14d', ''),  # J - Заказ/Выкуп 2 Недели
                    stock.get('orders_buyouts_30d', ''),  # K - Заказ/Выкуп Месяц
                    stock.get('price', 0),                # L - price
                    stock.get('discount', 0),             # M - discount
                    stock.get('rating'),                  # N - Рейтинг (last_updated убран!)
                    stock.get('buyout_percent', 0),       # O - % выкуп
                    stock.get('return_percent', 0)        # P - % возврат
                ] for stock in stocks_data]
                
                # Очищаем старые данные
                logger.info("Очищаем старые данные в листе Склад...")
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='📦 Склад!A2:P'  # Изменено с A2:Q на A2:P (убрана колонка last_updated)
                ).execute()
                
                # Записываем новые данные
                if values:
                    logger.info(f"Записываем {len(values)} строк в лист Склад...")
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='📦 Склад!A2',
                        valueInputOption='USER_ENTERED',
                        body={'values': values}
                    ).execute()
                    logger.info("Лист Склад успешно обновлен")
            
            # Обновляем отзывы
            if reviews_data:
                logger.info("Формируем данные для листа Отзывы...")
                values = [[
                    review.get('photo', ''),                # A - photo (formula)
                    review.get('review_id', ''),            # B - review_id
                    review.get('nm_id', ''),                # C - nm_id
                    review.get('product_name', ''),         # D - product.name
                    review.get('rating', 0),                # E - rating
                    review.get('text', ''),                 # F - text
                    review.get('pros', ''),                 # G - pros
                    review.get('cons', ''),                 # H - cons
                    review.get('user_name', ''),            # I - user_name
                    review.get('color', ''),                # J - color
                    review.get('matching_size', ''),        # K - matching_size
                    review.get('created_date', ''),         # L - created_date
                    review.get('is_answered', ''),          # M - is_answered
                    review.get('was_viewed', '')            # N - was_viewed
                ] for review in reviews_data]
                
                # Очищаем старые данные
                logger.info("Очищаем старые данные в листе Отзывы...")
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='⭐ Отзывы!A2:N'
                ).execute()
                
                # Записываем новые данные
                if values:
                    logger.info(f"Записываем {len(values)} строк в лист Отзывы...")
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='⭐ Отзывы!A2',
                        valueInputOption='USER_ENTERED',
                        body={'values': values}
                    ).execute()
                    logger.info("Лист Отзывы успешно обновлен")
            
            logger.info(f"Таблица {spreadsheet_id} успешно обновлена для кабинета {cabinet_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP ошибка при обновлении таблицы {spreadsheet_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы {spreadsheet_id}: {e}")
            return False
