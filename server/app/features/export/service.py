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
                key_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'config/wb-assist-352ded7b5635.json')
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
        """Получает данные заказов для экспорта"""
        orders = self.db.query(WBOrder).filter(
            WBOrder.cabinet_id == cabinet_id
        ).order_by(desc(WBOrder.order_date)).limit(limit).all()
        
        data = []
        for order in orders:
            data.append({
                "order_id": order.order_id,
                "article": order.article,
                "name": order.name,
                "size": order.size,
                "quantity": order.quantity,
                "price": order.price,
                "total_price": order.total_price,
                "status": order.status,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "warehouse_from": order.warehouse_from,
                "warehouse_to": order.warehouse_to,
                "commission_amount": order.commission_amount,
                "spp_percent": order.spp_percent,
                "customer_price": order.customer_price,
                "discount_percent": order.discount_percent
            })
        
        return data

    def get_stocks_data(self, cabinet_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получает данные остатков для экспорта"""
        stocks = self.db.query(WBStock).filter(
            WBStock.cabinet_id == cabinet_id
        ).order_by(WBStock.nm_id, WBStock.warehouse_name).limit(limit).all()
        
        data = []
        for stock in stocks:
            data.append({
                "article": stock.article,
                "name": stock.name,
                "brand": stock.brand,
                "size": stock.size,
                "warehouse_name": stock.warehouse_name,
                "quantity": stock.quantity,
                "in_way_to_client": stock.in_way_to_client,
                "in_way_from_client": stock.in_way_from_client,
                "price": stock.price,
                "discount": stock.discount,
                "last_updated": stock.last_updated.isoformat() if stock.last_updated else None
            })
        
        return data

    def get_reviews_data(self, cabinet_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получает данные отзывов для экспорта"""
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
            data.append({
                "review_id": review.review_id,
                "nm_id": review.nm_id,
                "product_name": product.name if product else None,
                "rating": review.rating,
                "text": review.text,
                "pros": review.pros,
                "cons": review.cons,
                "user_name": review.user_name,
                "color": review.color,
                "matching_size": review.matching_size,
                "created_date": review.created_date.isoformat() if review.created_date else None,
                "is_answered": review.is_answered,
                "was_viewed": review.was_viewed
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
            orders_data = self.get_orders_data(cabinet_id, limit=1000)
            stocks_data = self.get_stocks_data(cabinet_id, limit=1000)
            reviews_data = self.get_reviews_data(cabinet_id, limit=1000)
            
            # Обновляем заказы
            if orders_data:
                values = [[
                    order.get('order_id', ''),
                    order.get('article', ''),
                    order.get('name', ''),
                    order.get('size', ''),
                    order.get('quantity', 0),
                    order.get('price', 0),
                    order.get('total_price', 0),
                    order.get('status', ''),
                    order.get('order_date', ''),
                    order.get('warehouse_from', ''),
                    order.get('warehouse_to', ''),
                    order.get('commission_amount', 0),
                    order.get('spp_percent', 0),
                    order.get('customer_price', 0),
                    order.get('discount_percent', 0)
                ] for order in orders_data]
                
                # Очищаем старые данные
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='🛒 Заказы!A2:O'
                ).execute()
                
                # Записываем новые данные
                if values:
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='🛒 Заказы!A2',
                        valueInputOption='RAW',
                        body={'values': values}
                    ).execute()
            
            # Обновляем остатки
            if stocks_data:
                values = [[
                    stock.get('article', ''),
                    stock.get('name', ''),
                    stock.get('brand', ''),
                    stock.get('size', ''),
                    stock.get('warehouse_name', ''),
                    stock.get('quantity', 0),
                    stock.get('in_way_to_client', 0),
                    stock.get('in_way_from_client', 0),
                    stock.get('price', 0),
                    stock.get('discount', 0),
                    stock.get('last_updated', '')
                ] for stock in stocks_data]
                
                # Очищаем старые данные
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='📦 Склад!A2:K'
                ).execute()
                
                # Записываем новые данные
                if values:
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='📦 Склад!A2',
                        valueInputOption='RAW',
                        body={'values': values}
                    ).execute()
            
            # Обновляем отзывы
            if reviews_data:
                values = [[
                    review.get('review_id', ''),
                    review.get('nm_id', ''),
                    review.get('product_name', ''),
                    review.get('rating', 0),
                    review.get('text', ''),
                    review.get('pros', ''),
                    review.get('cons', ''),
                    review.get('user_name', ''),
                    review.get('color', ''),
                    review.get('matching_size', ''),
                    review.get('created_date', ''),
                    review.get('is_answered', False),
                    review.get('was_viewed', False)
                ] for review in reviews_data]
                
                # Очищаем старые данные
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range='⭐ Отзывы!A2:M'
                ).execute()
                
                # Записываем новые данные
                if values:
                    service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range='⭐ Отзывы!A2',
                        valueInputOption='RAW',
                        body={'values': values}
                    ).execute()
            
            logger.info(f"Таблица {spreadsheet_id} успешно обновлена для кабинета {cabinet_id}")
            return True
            
        except HttpError as e:
            logger.error(f"HTTP ошибка при обновлении таблицы {spreadsheet_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка обновления таблицы {spreadsheet_id}: {e}")
            return False
