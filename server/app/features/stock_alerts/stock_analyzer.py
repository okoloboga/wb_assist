"""
Анализатор остатков - анализ текущих остатков с учетом динамики заказов
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from app.features.wb_api.models import WBStock, WBProduct, WBOrder

logger = logging.getLogger(__name__)


class DynamicStockAnalyzer:
    """Анализ динамики остатков на основе реальных заказов"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def analyze_stock_positions(
        self, 
        cabinet_id: int,
        perspective_days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Анализирует все позиции остатков для кабинета
        
        Логика:
        1. Получить все текущие остатки из WBStock
        2. Для каждой позиции (nm_id, warehouse_name, size):
           - Получить количество заказов за 30 дней (всегда)
           - Рассчитать avg_per_day = заказов за 30 дней / 30
           - Рассчитать days_remaining = current_stock / avg_per_day
           - Если days_remaining <= perspective_days → добавить в риск-лист
        3. Рассчитать days_remaining для каждой рисковой позиции
        
        Args:
            cabinet_id: ID кабинета для анализа
            perspective_days: Количество дней для фильтрации (показывать только если days_remaining <= perspective_days)
        
        Returns:
            Список рисковых позиций с прогнозами
        """
        try:
            logger.info(f"Starting stock analysis for cabinet {cabinet_id}, perspective_days={perspective_days}")
            
            # Получаем все текущие остатки
            stocks = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet_id,
                    WBStock.quantity > 0  # Анализируем только позиции с остатками
                )
            ).all()
            
            if not stocks:
                logger.info(f"No stocks found for cabinet {cabinet_id}")
                return []
            
            at_risk_positions = []
            
            # Всегда используем 30 дней для расчета среднего количества заказов в день
            ANALYSIS_DAYS = 30
            analysis_hours = ANALYSIS_DAYS * 24
            time_threshold = datetime.utcnow() - timedelta(hours=analysis_hours)
            
            # Анализируем каждую позицию
            for stock in stocks:
                try:
                    # Получаем количество заказов за последние 30 дней напрямую из wb_orders
                    warehouse_name = stock.warehouse_name or "Неизвестный склад"
                    size = stock.size or "ONE SIZE"
                    
                    orders_last_30_days = self.db.query(func.sum(WBOrder.quantity)).filter(
                        and_(
                            WBOrder.cabinet_id == cabinet_id,
                            WBOrder.nm_id == stock.nm_id,
                            WBOrder.warehouse_from == warehouse_name,
                            WBOrder.size == size,
                            WBOrder.order_date >= time_threshold
                        )
                    ).scalar() or 0
                    
                    current_stock = stock.quantity or 0
                    
                    # Рассчитываем avg_per_day (заказов за 30 дней / 30)
                    avg_per_day = orders_last_30_days / ANALYSIS_DAYS if ANALYSIS_DAYS > 0 else 0
                    
                    # Рассчитываем прогноз
                    days_remaining = await self.calculate_days_remaining(
                        current_stock, avg_per_day
                    )
                    
                    # Проверяем условие риска: days_remaining <= perspective_days и есть заказы
                    if days_remaining <= perspective_days and orders_last_30_days > 0:
                        # Определяем уровень риска
                        risk_level = self._determine_risk_level(days_remaining)
                        
                        # Получаем информацию о товаре
                        product = self.db.query(WBProduct).filter(
                            and_(
                                WBProduct.nm_id == stock.nm_id,
                                WBProduct.cabinet_id == cabinet_id
                            )
                        ).first()
                        
                        at_risk_positions.append({
                            "nm_id": stock.nm_id,
                            "name": product.name if product else f"Товар {stock.nm_id}",
                            "brand": product.brand if product else "",
                            "image_url": product.image_url if product else None,
                            "warehouse_name": warehouse_name,
                            "size": size,
                            "current_stock": current_stock,
                            "orders_last_24h": orders_last_30_days,  # Название поля оставлено для совместимости, но содержит данные за 30 дней
                            "days_remaining": days_remaining,
                            "risk_level": risk_level
                        })
                
                except Exception as e:
                    logger.error(f"Error analyzing stock position {stock.nm_id}: {e}")
                    continue
            
            logger.info(
                f"Stock analysis completed: {len(at_risk_positions)} at-risk positions "
                f"out of {len(stocks)} total"
            )
            
            return at_risk_positions
            
        except Exception as e:
            logger.error(f"Error in analyze_stock_positions: {e}")
            return []
    
    async def calculate_days_remaining(
        self,
        current_stock: int,
        orders_per_day: float
    ) -> float:
        """
        Расчет прогноза остатка в днях
        
        Formula: days_remaining = current_stock / orders_per_day
        
        Args:
            current_stock: Текущий остаток
            orders_per_day: Среднее количество заказов в день
        
        Returns:
            Количество дней (float), на которые хватит остатка
        """
        if orders_per_day <= 0:
            return float('inf')
        
        days = current_stock / orders_per_day
        return round(days, 2)
    
    def _determine_risk_level(self, days_remaining: float) -> str:
        """
        Определяет уровень риска на основе прогноза
        
        Args:
            days_remaining: Прогноз в днях
        
        Returns:
            Уровень риска: "high", "medium", "low"
        """
        if days_remaining < 0.5:
            return "high"
        elif days_remaining < 1.0:
            return "medium"
        else:
            return "low"
    
    async def get_position_analytics(
        self,
        cabinet_id: int,
        nm_id: int,
        warehouse_name: str,
        size: str
    ) -> Dict[str, Any]:
        """
        Детальная аналитика по конкретной позиции
        
        Args:
            cabinet_id: ID кабинета
            nm_id: ID товара
            warehouse_name: Название склада
            size: Размер
        
        Returns:
            Детальная аналитика позиции
        """
        try:
            # Получаем текущий остаток
            stock = self.db.query(WBStock).filter(
                and_(
                    WBStock.cabinet_id == cabinet_id,
                    WBStock.nm_id == nm_id,
                    WBStock.warehouse_name == warehouse_name,
                    WBStock.size == size
                )
            ).first()
            
            if not stock:
                return {
                    "error": "Stock not found"
                }
            
            # Получаем статистику за 24ч напрямую из wb_orders
            time_threshold_24h = datetime.utcnow() - timedelta(hours=24)
            orders_last_24h = self.db.query(func.sum(WBOrder.quantity)).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id == nm_id,
                    WBOrder.warehouse_from == warehouse_name,
                    WBOrder.size == size,
                    WBOrder.order_date >= time_threshold_24h
                )
            ).scalar() or 0
            
            # Получаем статистику за 7 дней напрямую из wb_orders
            time_threshold_7d = datetime.utcnow() - timedelta(hours=168)
            orders_last_7d = self.db.query(func.sum(WBOrder.quantity)).filter(
                and_(
                    WBOrder.cabinet_id == cabinet_id,
                    WBOrder.nm_id == nm_id,
                    WBOrder.warehouse_from == warehouse_name,
                    WBOrder.size == size,
                    WBOrder.order_date >= time_threshold_7d
                )
            ).scalar() or 0
            
            current_stock = stock.quantity or 0
            avg_per_day = orders_last_24h / 1.0  # За 24 часа = 1 день
            
            days_remaining = await self.calculate_days_remaining(current_stock, avg_per_day)
            
            # Определяем тренд (на основе сравнения недельной и суточной динамики)
            trend = "stable"
            if orders_last_7d > 0:
                avg_7d = orders_last_7d / 7
                if orders_last_24h > avg_7d * 1.2:
                    trend = "increasing"
                elif orders_last_24h < avg_7d * 0.8:
                    trend = "decreasing"
            
            return {
                "nm_id": nm_id,
                "warehouse_name": warehouse_name,
                "size": size,
                "current_stock": current_stock,
                "orders_last_24h": orders_last_24h,
                "orders_last_7d": orders_last_7d,
                "avg_orders_per_day": round(avg_per_day, 2),
                "days_remaining": days_remaining,
                "trend": trend,
                "risk_level": self._determine_risk_level(days_remaining)
            }
            
        except Exception as e:
            logger.error(f"Error getting position analytics: {e}")
            return {
                "error": str(e)
            }

