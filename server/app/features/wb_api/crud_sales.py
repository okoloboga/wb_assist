"""
CRUD операции для продаж и возвратов Wildberries
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from .models_sales import WBSales


class WBSalesCRUD:
    """CRUD операции для продаж и возвратов"""
    
    def create_sale(self, db: Session, sale_data: Dict[str, Any]) -> WBSales:
        """Создание новой записи о продаже/возврате"""
        sale = WBSales(**sale_data)
        db.add(sale)
        db.commit()
        db.refresh(sale)
        return sale
    
    def get_sales_by_cabinet(
        self, 
        db: Session, 
        cabinet_id: int, 
        limit: int = 100, 
        offset: int = 0,
        sale_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[WBSales]:
        """Получение продаж по кабинету с фильтрацией"""
        query = db.query(WBSales).filter(WBSales.cabinet_id == cabinet_id)
        
        if sale_type:
            query = query.filter(WBSales.type == sale_type)
        
        if date_from:
            query = query.filter(WBSales.sale_date >= date_from)
        
        if date_to:
            query = query.filter(WBSales.sale_date <= date_to)
        
        return query.order_by(desc(WBSales.sale_date)).offset(offset).limit(limit).all()
    
    def get_recent_sales(
        self, 
        db: Session, 
        cabinet_id: int, 
        limit: int = 10,
        sale_type: Optional[str] = None
    ) -> List[WBSales]:
        """Получение последних продаж"""
        query = db.query(WBSales).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.is_cancel == False  # Только не отмененные
            )
        )
        
        if sale_type:
            query = query.filter(WBSales.type == sale_type)
        
        return query.order_by(desc(WBSales.sale_date)).limit(limit).all()
    
    def get_buyouts(
        self, 
        db: Session, 
        cabinet_id: int, 
        limit: int = 10,
        date_from: Optional[datetime] = None
    ) -> List[WBSales]:
        """Получение только выкупов"""
        query = db.query(WBSales).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.type == "buyout",
                WBSales.is_cancel == False
            )
        )
        
        if date_from:
            query = query.filter(WBSales.sale_date >= date_from)
        
        return query.order_by(desc(WBSales.sale_date)).limit(limit).all()
    
    def get_returns(
        self, 
        db: Session, 
        cabinet_id: int, 
        limit: int = 10,
        date_from: Optional[datetime] = None
    ) -> List[WBSales]:
        """Получение только возвратов"""
        query = db.query(WBSales).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.type == "return",
                WBSales.is_cancel == False
            )
        )
        
        if date_from:
            query = query.filter(WBSales.sale_date >= date_from)
        
        return query.order_by(desc(WBSales.sale_date)).limit(limit).all()
    
    def get_sales_statistics(
        self, 
        db: Session, 
        cabinet_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Получение статистики продаж"""
        query = db.query(WBSales).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.is_cancel == False
            )
        )
        
        if date_from:
            query = query.filter(WBSales.sale_date >= date_from)
        
        if date_to:
            query = query.filter(WBSales.sale_date <= date_to)
        
        # Общая статистика
        total_count = query.count()
        total_amount = db.query(func.sum(WBSales.amount)).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.is_cancel == False
            )
        ).scalar() or 0
        
        # Статистика по типам
        buyouts_count = query.filter(WBSales.type == "buyout").count()
        returns_count = query.filter(WBSales.type == "return").count()
        
        buyouts_amount = db.query(func.sum(WBSales.amount)).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.type == "buyout",
                WBSales.is_cancel == False
            )
        ).scalar() or 0
        
        returns_amount = db.query(func.sum(WBSales.amount)).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.type == "return",
                WBSales.is_cancel == False
            )
        ).scalar() or 0
        
        return {
            "total_count": total_count,
            "total_amount": float(total_amount),
            "buyouts_count": buyouts_count,
            "buyouts_amount": float(buyouts_amount),
            "returns_count": returns_count,
            "returns_amount": float(returns_amount),
            "buyout_rate": (buyouts_count / total_count * 100) if total_count > 0 else 0
        }
    
    def get_sale_by_sale_id(self, db: Session, cabinet_id: int, sale_id: str) -> Optional[WBSales]:
        """Получение продажи по ID"""
        return db.query(WBSales).filter(
            and_(
                WBSales.cabinet_id == cabinet_id,
                WBSales.sale_id == sale_id
            )
        ).first()
    
    def update_sale(self, db: Session, sale_id: int, update_data: Dict[str, Any]) -> Optional[WBSales]:
        """Обновление записи о продаже"""
        sale = db.query(WBSales).filter(WBSales.id == sale_id).first()
        if not sale:
            return None
        
        for key, value in update_data.items():
            if hasattr(sale, key):
                setattr(sale, key, value)
        
        from app.utils.timezone import TimezoneUtils
        sale.updated_at = TimezoneUtils.now_msk()
        db.commit()
        db.refresh(sale)
        return sale
    
    def delete_sale(self, db: Session, sale_id: int) -> bool:
        """Удаление записи о продаже"""
        sale = db.query(WBSales).filter(WBSales.id == sale_id).first()
        if not sale:
            return False
        
        db.delete(sale)
        db.commit()
        return True
