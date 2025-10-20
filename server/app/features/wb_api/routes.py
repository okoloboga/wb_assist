from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from ...core.database import get_db
from .models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview, WBAnalyticsCache, WBWarehouse, WBSyncLog
from .client import WBAPIClient
from .sync_service import WBSyncService
from .cache_manager import WBCacheManager

router = APIRouter(prefix="/wb", tags=["Wildberries API"])


@router.post("/cabinets/", response_model=Dict[str, Any])
async def create_wb_cabinet(
    user_id: int,
    api_key: str,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Создание нового WB кабинета или подключение к существующему"""
    try:
        from .crud_cabinet_users import CabinetUserCRUD
        
        # Проверяем существование пользователя
        user_exists = db.execute(
            text("SELECT id FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        cabinet_crud = CabinetUserCRUD()
        
        # Ищем существующий кабинет с таким API ключом
        existing_cabinet = cabinet_crud.find_cabinet_by_api_key(db, api_key)
        
        if existing_cabinet:
            # Кабинет существует - проверяем, не подключен ли уже пользователь
            if cabinet_crud.is_user_in_cabinet(db, existing_cabinet.id, user_id):
                return {
                    "status": "already_connected",
                    "cabinet_id": existing_cabinet.id,
                    "name": existing_cabinet.name,
                    "message": "Пользователь уже подключен к этому кабинету"
                }
            
            # Подключаем пользователя к существующему кабинету
            cabinet_crud.add_user_to_cabinet(db, existing_cabinet.id, user_id)
            
            return {
                "status": "connected",
                "cabinet_id": existing_cabinet.id,
                "name": existing_cabinet.name,
                "message": "Подключен к существующему кабинету"
            }
        else:
            # Создаем новый кабинет
            cabinet = WBCabinet(
                api_key=api_key,
                name=name or f"WB Cabinet {user_id}"
            )
            
            db.add(cabinet)
            db.commit()
            db.refresh(cabinet)
            
            # Добавляем пользователя к кабинету
            cabinet_crud.add_user_to_cabinet(db, cabinet.id, user_id)
            
            return {
                "status": "created",
                "cabinet_id": cabinet.id,
                "name": cabinet.name,
                "message": "Создан новый кабинет"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating cabinet: {str(e)}")


@router.get("/cabinets/", response_model=List[Dict[str, Any]])
async def get_wb_cabinets(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Получение списка WB кабинетов"""
    try:
        from .crud_cabinet_users import CabinetUserCRUD
        
        if user_id:
            # Получаем кабинеты конкретного пользователя через связующую таблицу
            cabinet_crud = CabinetUserCRUD()
            cabinet_ids = cabinet_crud.get_user_cabinets(db, user_id)
            cabinets = db.query(WBCabinet).filter(WBCabinet.id.in_(cabinet_ids)).all()
        else:
            # Получаем все кабинеты
            cabinets = db.query(WBCabinet).all()
        
        return [
            {
                "id": cabinet.id,
                "name": cabinet.name,
                "is_active": cabinet.is_active,
                "last_sync_at": cabinet.last_sync_at.isoformat() if cabinet.last_sync_at else None,
                "created_at": cabinet.created_at.isoformat()
            }
            for cabinet in cabinets
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cabinets: {str(e)}")


@router.get("/cabinets/{cabinet_id}", response_model=Dict[str, Any])
async def get_wb_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Получение конкретного WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        return {
            "id": cabinet.id,
            "user_id": cabinet.user_id,
            "name": cabinet.name,
            "is_active": cabinet.is_active,
            "last_sync_at": cabinet.last_sync_at.isoformat() if cabinet.last_sync_at else None,
            "created_at": cabinet.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cabinet: {str(e)}")


@router.put("/cabinets/{cabinet_id}", response_model=Dict[str, Any])
async def update_wb_cabinet(
    cabinet_id: int,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Обновление WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        if name is not None:
            cabinet.name = name
        if is_active is not None:
            cabinet.is_active = is_active
        
        cabinet.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "status": "success",
            "cabinet_id": cabinet.id,
            "name": cabinet.name,
            "is_active": cabinet.is_active,
            "updated_at": cabinet.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating cabinet: {str(e)}")


@router.delete("/cabinets/{cabinet_id}", response_model=Dict[str, Any])
async def delete_wb_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Удаление WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        db.delete(cabinet)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Cabinet {cabinet_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting cabinet: {str(e)}")


@router.get("/cabinets/{cabinet_id}/products", response_model=List[Dict[str, Any]])
async def get_wb_products(
    cabinet_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Получение товаров WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        products = db.query(WBProduct).filter(
            WBProduct.cabinet_id == cabinet_id
        ).offset(offset).limit(limit).all()
        
        return [
            {
                "id": product.id,
                "nm_id": product.nm_id,
                "name": product.name,
                "vendor_code": product.vendor_code,
                "brand": product.brand,
                "category": product.category,
                "price": product.price,
                "discount_price": product.discount_price,
                "rating": product.rating,
                "reviews_count": product.reviews_count,
                "in_stock": product.in_stock,
                "is_active": product.is_active,
                "created_at": product.created_at.isoformat()
            }
            for product in products
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting products: {str(e)}")


@router.get("/cabinets/{cabinet_id}/orders", response_model=List[Dict[str, Any]])
async def get_wb_orders(
    cabinet_id: int,
    date_from: str = Query(..., description="Date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date to (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Получение заказов WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        query = db.query(WBOrder).filter(WBOrder.cabinet_id == cabinet_id)
        
        if date_from:
            query = query.filter(WBOrder.order_date >= date_from)
        if date_to:
            query = query.filter(WBOrder.order_date <= date_to)
        
        orders = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": order.id,
                "order_id": order.order_id,
                "nm_id": order.nm_id,
                "article": order.article,
                "name": order.name,
                "brand": order.brand,
                "size": order.size,
                "barcode": order.barcode,
                "quantity": order.quantity,
                "price": order.price,
                "total_price": order.total_price,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "status": order.status,
                "created_at": order.created_at.isoformat()
            }
            for order in orders
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting orders: {str(e)}")


@router.get("/cabinets/{cabinet_id}/stocks", response_model=List[Dict[str, Any]])
async def get_wb_stocks(
    cabinet_id: int,
    date_from: str = Query(..., description="Date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date to (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Получение остатков WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        query = db.query(WBStock).filter(WBStock.cabinet_id == cabinet_id)
        
        if date_from:
            query = query.filter(WBStock.last_updated >= date_from)
        if date_to:
            query = query.filter(WBStock.last_updated <= date_to)
        
        stocks = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": stock.id,
                "nm_id": stock.nm_id,
                "article": stock.article,
                "name": stock.name,
                "brand": stock.brand,
                "size": stock.size,
                "barcode": stock.barcode,
                "quantity": stock.quantity,
                "in_way_to_client": stock.in_way_to_client,
                "in_way_from_client": stock.in_way_from_client,
                "warehouse_id": stock.warehouse_id,
                "warehouse_name": stock.warehouse_name,
                "last_updated": stock.last_updated.isoformat() if stock.last_updated else None,
                "created_at": stock.created_at.isoformat()
            }
            for stock in stocks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stocks: {str(e)}")


@router.get("/cabinets/{cabinet_id}/reviews", response_model=List[Dict[str, Any]])
async def get_wb_reviews(
    cabinet_id: int,
    is_answered: Optional[bool] = Query(None, description="Filter by answered status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Получение отзывов WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        query = db.query(WBReview).filter(WBReview.cabinet_id == cabinet_id)
        
        if is_answered is not None:
            query = query.filter(WBReview.is_answered == is_answered)
        
        reviews = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": review.id,
                "nm_id": review.nm_id,
                "review_id": review.review_id,
                "text": review.text,
                "rating": review.rating,
                "is_answered": review.is_answered,
                "created_date": review.created_date.isoformat() if review.created_date else None,
                "updated_date": review.updated_date.isoformat() if review.updated_date else None,
                "created_at": review.created_at.isoformat()
            }
            for review in reviews
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reviews: {str(e)}")


@router.get("/cabinets/{cabinet_id}/warehouses", response_model=List[Dict[str, Any]])
async def get_wb_warehouses(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Получение складов WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        warehouses = db.query(WBWarehouse).filter(
            WBWarehouse.cabinet_id == cabinet_id
        ).all()
        
        return [
            {
                "id": warehouse.id,
                "warehouse_id": warehouse.warehouse_id,
                "name": warehouse.name,
                "address": warehouse.address,
                "is_active": warehouse.is_active,
                "created_at": warehouse.created_at.isoformat()
            }
            for warehouse in warehouses
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting warehouses: {str(e)}")


@router.get("/cabinets/{cabinet_id}/analytics", response_model=Dict[str, Any])
async def get_wb_analytics(
    cabinet_id: int,
    report_type: str = Query("sales", description="Report type: sales, reviews, stocks"),
    date_from: str = Query(..., description="Date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Date to (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Получение аналитики WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Проверяем кэш
        cache_manager = WBCacheManager(db)
        cached_data = await cache_manager.get_analytics_cache(
            cabinet_id, report_type, date_from, date_to
        )
        
        if cached_data:
            return {
                "status": "success",
                "data": cached_data,
                "cached": True,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Если данных нет в кэше, возвращаем базовую аналитику
        return {
            "status": "success",
            "data": {
                "report_type": report_type,
                "date_from": date_from,
                "date_to": date_to,
                "message": "Analytics data not available in cache"
            },
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")


@router.post("/cabinets/{cabinet_id}/sync", response_model=Dict[str, Any])
async def sync_wb_cabinet(
    cabinet_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Запуск синхронизации данных WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Запускаем синхронизацию в фоне
        cache_manager = WBCacheManager(db)
        sync_service = WBSyncService(db, cache_manager)
        
        background_tasks.add_task(sync_service.sync_all_data, cabinet)
        
        return {
            "status": "success",
            "message": f"Sync started for cabinet {cabinet_id}",
            "cabinet_id": cabinet_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting sync: {str(e)}")


@router.get("/cabinets/{cabinet_id}/sync/status", response_model=Dict[str, Any])
async def get_wb_sync_status(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Получение статуса синхронизации WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        # Получаем статус синхронизации
        cache_manager = WBCacheManager(db)
        sync_service = WBSyncService(db, cache_manager)
        status = await sync_service.get_sync_status()
        
        return {
            "status": "success",
            "cabinet_id": cabinet_id,
            "sync_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sync status: {str(e)}")