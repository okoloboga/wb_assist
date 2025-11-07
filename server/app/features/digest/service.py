"""
Бизнес-логика для digest feature
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.features.wb_api.models import WBCabinet, WBOrder, WBStock, WBReview
from app.features.wb_api.models_sales import WBSales
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)


class DigestService:
    """Сервис для получения данных ежедневных сводок"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_daily_digest(self, cabinet_id: int, target_date: Optional[date] = None, 
                        start_datetime: Optional[datetime] = None, end_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Получить данные для ежедневной сводки
        
        Args:
            cabinet_id: ID кабинета
            target_date: Дата сводки (по умолчанию вчера)
            start_datetime: Начало временного диапазона (если не указан, берем 24 часа назад)
            end_datetime: Конец временного диапазона (если не указан, берем текущее время)
        
        Returns:
            Dict с данными сводки
        """
        try:
            # Определяем временной диапазон
            if end_datetime is None:
                end_datetime = datetime.utcnow()
            
            if start_datetime is None:
                start_datetime = end_datetime - timedelta(hours=24)
            
            # Для обратной совместимости с target_date
            if target_date is not None and start_datetime is None and end_datetime is None:
                # Старый режим - по дате
                pass
            else:
                # Новый режим - по временному диапазону
                target_date = end_datetime.date()
            
            # Получаем кабинет
            cabinet = self.db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
            if not cabinet:
                raise ValueError(f"Cabinet {cabinet_id} not found")
            
            # Собираем данные
            orders_data = self._get_orders_data(cabinet_id, target_date, start_datetime, end_datetime)
            sales_data = self._get_sales_data(cabinet_id, target_date, start_datetime, end_datetime)
            stocks_data = self._get_stocks_data(cabinet_id)
            reviews_data = self._get_reviews_data(cabinet_id, target_date, start_datetime, end_datetime)
            
            return {
                "cabinet_name": cabinet.name or "Кабинет WB",
                "date": target_date.isoformat(),
                "orders": orders_data,
                "sales": sales_data,
                "stocks": stocks_data,
                "reviews": reviews_data
            }
            
        except Exception as e:
            logger.error(f"Error getting daily digest for cabinet {cabinet_id}: {e}")
            raise
    
    def _get_orders_data(self, cabinet_id: int, target_date: date, 
                        start_datetime: Optional[datetime] = None, end_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        """Получить данные по заказам за временной период"""
        try:
            # Определяем фильтр по времени
            if start_datetime and end_datetime:
                # Новый режим - последние 24 часа
                time_filter = and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.order_date >= start_datetime,
                    WBOrder.order_date <= end_datetime
                )
                
                # Для сравнения - предыдущие 24 часа
                prev_start = start_datetime - timedelta(hours=24)
                prev_end = end_datetime - timedelta(hours=24)
                prev_time_filter = and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.order_date >= prev_start,
                    WBOrder.order_date <= prev_end
                )
            else:
                # Старый режим - по дате
                time_filter = and_(
                    WBOrder.cabinet_id == cabinet_id,
                    func.date(WBOrder.order_date) == target_date
                )
                
                # Заказы за предыдущий день (для сравнения)
                prev_date = target_date - timedelta(days=1)
                prev_time_filter = and_(
                    WBOrder.cabinet_id == cabinet_id,
                    func.date(WBOrder.order_date) == prev_date
                )
            
            # Заказы за текущий период
            orders_count = self.db.query(func.count(WBOrder.id)).filter(time_filter).scalar() or 0
            orders_amount = self.db.query(func.sum(WBOrder.total_price)).filter(time_filter).scalar() or 0
            
            # Заказы за предыдущий период (для сравнения)
            prev_orders_count = self.db.query(func.count(WBOrder.id)).filter(prev_time_filter).scalar() or 0
            
            # Рост
            growth_percent = 0
            if prev_orders_count > 0:
                growth_percent = ((orders_count - prev_orders_count) / prev_orders_count) * 100
            
            return {
                "count": orders_count,
                "amount": float(orders_amount),
                "growth_percent": round(growth_percent, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting orders data: {e}")
            return {"count": 0, "amount": 0, "growth_percent": 0}
    
    def _get_sales_data(self, cabinet_id: int, target_date: date, 
                        start_datetime: Optional[datetime] = None, end_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        """Получить данные по продажам за временной период"""
        try:
            # Определяем фильтр по времени
            if start_datetime and end_datetime:
                # Новый режим - последние 24 часа
                buyouts_filter = and_(
                    WBSales.cabinet_id == cabinet_id,
                    WBSales.sale_date >= start_datetime,
                    WBSales.sale_date <= end_datetime,
                    WBSales.type == 'buyout',
                    WBSales.is_cancel == False  # Исключаем отмененные
                )
                
                returns_filter = and_(
                    WBSales.cabinet_id == cabinet_id,
                    WBSales.sale_date >= start_datetime,
                    WBSales.sale_date <= end_datetime,
                    WBSales.type == 'return',
                    WBSales.is_cancel == False  # Исключаем отмененные
                )
            else:
                # Старый режим - по дате
                buyouts_filter = and_(
                    WBSales.cabinet_id == cabinet_id,
                    func.date(WBSales.sale_date) == target_date,
                    WBSales.type == 'buyout',
                    WBSales.is_cancel == False  # Исключаем отмененные
                )
                
                returns_filter = and_(
                    WBSales.cabinet_id == cabinet_id,
                    func.date(WBSales.sale_date) == target_date,
                    WBSales.type == 'return',
                    WBSales.is_cancel == False  # Исключаем отмененные
                )
            
            # Выкупы
            buyouts = self.db.query(WBSales).filter(buyouts_filter).all()
            buyouts_count = len(buyouts)
            buyouts_amount = sum(sale.amount or 0 for sale in buyouts)
            
            # Возвраты
            returns = self.db.query(WBSales).filter(returns_filter).all()
            returns_count = len(returns)
            returns_amount = sum(sale.amount or 0 for sale in returns)
            
            # Логируем для отладки
            logger.debug(
                f"Sales data for cabinet {cabinet_id}, date {target_date}: "
                f"buyouts={buyouts_count} (amount={buyouts_amount}), "
                f"returns={returns_count} (amount={returns_amount})"
            )
            
            # Коэффициент выкупа
            total_sales = buyouts_count + returns_count
            buyout_rate = (buyouts_count / total_sales * 100) if total_sales > 0 else 0
            
            return {
                "buyouts_count": buyouts_count,
                "buyouts_amount": float(buyouts_amount),
                "returns_count": returns_count,
                "returns_amount": float(returns_amount),
                "buyout_rate": round(buyout_rate, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting sales data: {e}")
            return {
                "buyouts_count": 0,
                "buyouts_amount": 0,
                "returns_count": 0,
                "returns_amount": 0,
                "buyout_rate": 0
            }
    
    def _get_stocks_data(self, cabinet_id: int) -> Dict[str, Any]:
        """Получить данные по остаткам"""
        try:
            # Критичные остатки (< 10 шт)
            critical_count = self.db.query(func.count(func.distinct(WBStock.nm_id))).filter(
                and_(
                    WBStock.cabinet_id == cabinet_id,
                    WBStock.quantity < 10,
                    WBStock.quantity > 0
                )
            ).scalar() or 0
            
            # Нулевые остатки
            zero_count = self.db.query(func.count(func.distinct(WBStock.nm_id))).filter(
                and_(
                    WBStock.cabinet_id == cabinet_id,
                    WBStock.quantity == 0
                )
            ).scalar() or 0
            
            return {
                "critical_count": critical_count,
                "zero_count": zero_count,
                "attention_needed": critical_count + zero_count
            }
            
        except Exception as e:
            logger.error(f"Error getting stocks data: {e}")
            return {"critical_count": 0, "zero_count": 0, "attention_needed": 0}
    
    def _get_reviews_data(self, cabinet_id: int, target_date: date, 
                         start_datetime: Optional[datetime] = None, end_datetime: Optional[datetime] = None) -> Dict[str, Any]:
        """Получить данные по отзывам за временной период"""
        try:
            # Определяем фильтр по времени
            if start_datetime and end_datetime:
                # Новый режим - последние 24 часа
                reviews_filter = and_(
                    WBReview.cabinet_id == cabinet_id,
                    WBReview.created_date >= start_datetime,
                    WBReview.created_date <= end_datetime
                )
            else:
                # Старый режим - по дате
                reviews_filter = and_(
                    WBReview.cabinet_id == cabinet_id,
                    func.date(WBReview.created_date) == target_date
                )
            
            # Новые отзывы за период
            new_reviews = self.db.query(WBReview).filter(reviews_filter).all()
            
            new_count = len(new_reviews)
            
            # Средний рейтинг (за все время)
            avg_rating = self.db.query(func.avg(WBReview.rating)).filter(
                WBReview.cabinet_id == cabinet_id
            ).scalar() or 0
            
            # Негативные отзывы (1-3 звезды)
            negative_count = len([r for r in new_reviews if r.rating and r.rating <= 3])
            
            return {
                "new_count": new_count,
                "average_rating": round(float(avg_rating), 1),
                "negative_count": negative_count
            }
            
        except Exception as e:
            logger.error(f"Error getting reviews data: {e}")
            return {"new_count": 0, "average_rating": 0, "negative_count": 0}

