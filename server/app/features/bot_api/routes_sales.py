"""
Bot API эндпоинты для продаж и возвратов
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from ...core.database import get_db
from ..wb_api.crud_sales import WBSalesCRUD
from ..wb_api.models import WBCabinet
from ..user.crud import UserCRUD

router = APIRouter(prefix="/sales", tags=["bot-sales"])


@router.get("/recent")
async def get_recent_sales(
    user_id: int = Query(..., description="ID пользователя"),
    limit: int = Query(10, description="Количество записей"),
    sale_type: Optional[str] = Query(None, description="Тип продажи (buyout/return)"),
    db: Session = Depends(get_db)
):
    """Получение последних продаж и возвратов"""
    try:
        # Получаем кабинет пользователя через связующую таблицу
        from ..wb_api.crud_cabinet_users import CabinetUserCRUD
        cabinet_user_crud = CabinetUserCRUD()
        
        cabinet_ids = cabinet_user_crud.get_user_cabinets(db, user_id)
        if not cabinet_ids:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Берем первый активный кабинет
        cabinet = db.query(WBCabinet).filter(
            WBCabinet.id.in_(cabinet_ids),
            WBCabinet.is_active == True
        ).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        sales_crud = WBSalesCRUD()
        sales = sales_crud.get_recent_sales(db, cabinet.id, limit, sale_type)
        
        # Форматируем данные для ответа
        sales_data = []
        for sale in sales:
            sales_data.append({
                "id": sale.id,
                "sale_id": sale.sale_id,
                "order_id": sale.order_id,
                "nm_id": sale.nm_id,
                "product_name": sale.product_name,
                "brand": sale.brand,
                "size": sale.size,
                "amount": sale.amount,
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
                "type": sale.type,
                "status": sale.status,
                "is_cancel": sale.is_cancel
            })
        
        # Получаем статистику
        stats = sales_crud.get_sales_statistics(db, cabinet.id)
        
        return {
            "success": True,
            "data": {
                "sales": sales_data,
                "statistics": stats
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/buyouts")
async def get_buyouts(
    user_id: int = Query(..., description="ID пользователя"),
    limit: int = Query(10, description="Количество записей"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Получение только выкупов"""
    try:
        # Получаем кабинет пользователя через связующую таблицу
        from ..wb_api.crud_cabinet_users import CabinetUserCRUD
        cabinet_user_crud = CabinetUserCRUD()
        
        cabinet_ids = cabinet_user_crud.get_user_cabinets(db, user_id)
        if not cabinet_ids:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Берем первый активный кабинет
        cabinet = db.query(WBCabinet).filter(
            WBCabinet.id.in_(cabinet_ids),
            WBCabinet.is_active == True
        ).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        sales_crud = WBSalesCRUD()
        
        # Парсим дату если указана
        date_from_dt = None
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        buyouts = sales_crud.get_buyouts(db, cabinet.id, limit, date_from_dt)
        
        # Форматируем данные для ответа
        buyouts_data = []
        for buyout in buyouts:
            buyouts_data.append({
                "id": buyout.id,
                "sale_id": buyout.sale_id,
                "order_id": buyout.order_id,
                "nm_id": buyout.nm_id,
                "product_name": buyout.product_name,
                "brand": buyout.brand,
                "size": buyout.size,
                "amount": buyout.amount,
                "sale_date": buyout.sale_date.isoformat() if buyout.sale_date else None,
                "status": buyout.status
            })
        
        return {
            "success": True,
            "data": {
                "buyouts": buyouts_data,
                "count": len(buyouts_data)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/returns")
async def get_returns(
    user_id: int = Query(..., description="ID пользователя"),
    limit: int = Query(10, description="Количество записей"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Получение только возвратов"""
    try:
        # Получаем кабинет пользователя через связующую таблицу
        from ..wb_api.crud_cabinet_users import CabinetUserCRUD
        cabinet_user_crud = CabinetUserCRUD()
        
        cabinet_ids = cabinet_user_crud.get_user_cabinets(db, user_id)
        if not cabinet_ids:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Берем первый активный кабинет
        cabinet = db.query(WBCabinet).filter(
            WBCabinet.id.in_(cabinet_ids),
            WBCabinet.is_active == True
        ).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        sales_crud = WBSalesCRUD()
        
        # Парсим дату если указана
        date_from_dt = None
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        returns = sales_crud.get_returns(db, cabinet.id, limit, date_from_dt)
        
        # Форматируем данные для ответа
        returns_data = []
        for return_item in returns:
            returns_data.append({
                "id": return_item.id,
                "sale_id": return_item.sale_id,
                "order_id": return_item.order_id,
                "nm_id": return_item.nm_id,
                "product_name": return_item.product_name,
                "brand": return_item.brand,
                "size": return_item.size,
                "amount": return_item.amount,
                "sale_date": return_item.sale_date.isoformat() if return_item.sale_date else None,
                "status": return_item.status
            })
        
        return {
            "success": True,
            "data": {
                "returns": returns_data,
                "count": len(returns_data)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/statistics")
async def get_sales_statistics(
    user_id: int = Query(..., description="ID пользователя"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Получение статистики продаж"""
    try:
        # Получаем кабинет пользователя через связующую таблицу
        from ..wb_api.crud_cabinet_users import CabinetUserCRUD
        cabinet_user_crud = CabinetUserCRUD()
        
        cabinet_ids = cabinet_user_crud.get_user_cabinets(db, user_id)
        if not cabinet_ids:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Берем первый активный кабинет
        cabinet = db.query(WBCabinet).filter(
            WBCabinet.id.in_(cabinet_ids),
            WBCabinet.is_active == True
        ).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        sales_crud = WBSalesCRUD()
        
        # Парсим даты если указаны
        date_from_dt = None
        date_to_dt = None
        
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
        
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        stats = sales_crud.get_sales_statistics(db, cabinet.id, date_from_dt, date_to_dt)
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
