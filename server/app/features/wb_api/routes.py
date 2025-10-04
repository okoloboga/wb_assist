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
from ..user.models import User

router = APIRouter(prefix="/wb", tags=["Wildberries API"])


@router.post("/cabinets/", response_model=Dict[str, Any])
async def create_wb_cabinet(
    user_id: int,
    api_key: str,
    name: str,
    db: Session = Depends(get_db)
):
    """Создание нового WB кабинета"""
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Проверяем уникальность API ключа
        existing_cabinet = db.query(WBCabinet).filter(WBCabinet.api_key == api_key).first()
        if existing_cabinet:
            raise HTTPException(status_code=400, detail="API key already exists")
        
        # Создаем кабинет
        cabinet = WBCabinet(
            user_id=user_id,
            api_key=api_key,
            cabinet_name=name,
            is_active=True
        )
        db.add(cabinet)
        db.commit()
        db.refresh(cabinet)
        
        return {
            "status": "success",
            "cabinet_id": cabinet.id,
            "message": "WB cabinet created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating cabinet: {str(e)}")


@router.get("/cabinets/{cabinet_id}", response_model=Dict[str, Any])
async def get_wb_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Получение информации о WB кабинете"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        return {
            "id": cabinet.id,
            "user_id": cabinet.user_id,
            "cabinet_name": cabinet.cabinet_name,
            "is_active": cabinet.is_active,
            "last_sync_at": cabinet.last_sync_at.isoformat() if cabinet.last_sync_at else None,
            "created_at": cabinet.created_at.isoformat(),
            "updated_at": cabinet.updated_at.isoformat() if cabinet.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cabinet: {str(e)}")


@router.get("/cabinets/", response_model=List[Dict[str, Any]])
async def list_wb_cabinets(
    user_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Получение списка WB кабинетов"""
    try:
        query = db.query(WBCabinet)
        
        if user_id:
            query = query.filter(WBCabinet.user_id == user_id)
        if is_active is not None:
            query = query.filter(WBCabinet.is_active == is_active)
        
        cabinets = query.all()
        
        return [
            {
                "id": cabinet.id,
                "user_id": cabinet.user_id,
                "cabinet_name": cabinet.cabinet_name,
                "is_active": cabinet.is_active,
                "last_sync_at": cabinet.last_sync_at.isoformat() if cabinet.last_sync_at else None,
                "created_at": cabinet.created_at.isoformat()
            }
            for cabinet in cabinets
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing cabinets: {str(e)}")


@router.post("/cabinets/{cabinet_id}/sync", response_model=Dict[str, Any])
async def sync_wb_cabinet(
    cabinet_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Синхронизация данных WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        if not cabinet.is_active:
            raise HTTPException(status_code=400, detail="Cabinet is not active")
        
        # Запускаем синхронизацию в фоне
        sync_service = WBSyncService(db)
        background_tasks.add_task(sync_service.sync_cabinet, cabinet)
        
        return {
            "status": "success",
            "message": "Sync started in background",
            "cabinet_id": cabinet_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting sync: {str(e)}")


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
                "article": product.article,
                "brand": product.brand,
                "name": product.name,
                "subject": product.subject,
                "category": product.category,
                "characteristics": product.characteristics,
                "sizes": product.sizes,
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
        
        # Фильтрация по датам
        if date_from:
            query = query.filter(WBOrder.order_date >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(WBOrder.order_date <= datetime.fromisoformat(date_to))
        
        orders = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": order.id,
                "order_id": order.order_id,
                "nm_id": order.nm_id,
                "article": order.article,
                "total_price": order.total_price,
                "finished_price": order.finished_price,
                "discount_percent": order.discount_percent,
                "is_cancel": order.is_cancel,
                "is_realization": order.is_realization,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "last_change_date": order.last_change_date.isoformat() if order.last_change_date else None
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
        
        # Фильтрация по датам
        if date_from:
            query = query.filter(WBStock.last_change_date >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.filter(WBStock.last_change_date <= datetime.fromisoformat(date_to))
        
        stocks = query.offset(offset).limit(limit).all()
        
        return [
            {
                "id": stock.id,
                "nm_id": stock.nm_id,
                "warehouse_id": stock.warehouse_id,
                "warehouse_name": stock.warehouse_name,
                "article": stock.article,
                "size": stock.size,
                "quantity": stock.quantity,
                "price": stock.price,
                "discount": stock.discount,
                "last_change_date": stock.last_change_date.isoformat() if stock.last_change_date else None
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
                "created_date": review.created_date.isoformat() if review.created_date else None
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
        
        warehouses = db.query(WBWarehouse).filter(WBWarehouse.cabinet_id == cabinet_id).all()
        
        return [
            {
                "id": warehouse.id,
                "warehouse_id": warehouse.warehouse_id,
                "name": warehouse.name,
                "address": warehouse.address,
                "region": warehouse.region,
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
        if report_type == "sales":
            orders = db.query(WBOrder).filter(
                WBOrder.cabinet_id == cabinet_id,
                WBOrder.is_realization == True
            ).all()
            
            total_sales = sum(order.finished_price or 0 for order in orders)
            total_orders = len(orders)
            
            analytics_data = {
                "total_sales": total_sales,
                "total_orders": total_orders,
                "avg_order_value": total_sales / total_orders if total_orders > 0 else 0
            }
            
        elif report_type == "reviews":
            reviews = db.query(WBReview).filter(WBReview.cabinet_id == cabinet_id).all()
            
            answered_reviews = [r for r in reviews if r.is_answered]
            avg_rating = sum(r.rating or 0 for r in reviews if r.rating) / len([r for r in reviews if r.rating]) if reviews else 0
            
            analytics_data = {
                "total_reviews": len(reviews),
                "answered_reviews": len(answered_reviews),
                "avg_rating": avg_rating
            }
            
        elif report_type == "stocks":
            stocks = db.query(WBStock).filter(WBStock.cabinet_id == cabinet_id).all()
            
            total_quantity = sum(stock.quantity or 0 for stock in stocks)
            total_value = sum((stock.quantity or 0) * (stock.price or 0) for stock in stocks)
            
            analytics_data = {
                "total_quantity": total_quantity,
                "total_value": total_value,
                "unique_products": len(set(stock.nm_id for stock in stocks))
            }
            
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        # Сохраняем в кэш
        await cache_manager.set_analytics_cache(
            cabinet_id, report_type, date_from, analytics_data, date_to
        )
        
        return {
            "status": "success",
            "data": analytics_data,
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")


@router.get("/cabinets/{cabinet_id}/sync-logs", response_model=List[Dict[str, Any]])
async def get_wb_sync_logs(
    cabinet_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Получение логов синхронизации WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        logs = db.query(WBSyncLog).filter(
            WBSyncLog.cabinet_id == cabinet_id
        ).order_by(WBSyncLog.started_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "sync_type": log.sync_type,
                "status": log.status,
                "started_at": log.started_at.isoformat(),
                "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                "records_processed": log.records_processed,
                "records_created": log.records_created,
                "records_updated": log.records_updated,
                "records_skipped": log.records_skipped,
                "error_message": log.error_message
            }
            for log in logs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sync logs: {str(e)}")


@router.post("/cabinets/{cabinet_id}/validate", response_model=Dict[str, Any])
async def validate_wb_cabinet(
    cabinet_id: int,
    db: Session = Depends(get_db)
):
    """Валидация API ключа WB кабинета"""
    try:
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        
        client = WBAPIClient(cabinet)
        is_valid = await client.validate_api_key()
        
        if is_valid:
            cabinet.is_active = True
            cabinet.updated_at = datetime.now(timezone.utc)
            db.commit()
        
        return {
            "status": "success",
            "is_valid": is_valid,
            "message": "API key is valid" if is_valid else "API key is invalid"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating cabinet: {str(e)}")


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
        
        # Деактивируем кабинет вместо удаления
        cabinet.is_active = False
        cabinet.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "status": "success",
            "message": "Cabinet deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting cabinet: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def wb_health_check(db: Session = Depends(get_db)):
    """Проверка здоровья WB API сервиса"""
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        
        # Проверяем количество активных кабинетов
        active_cabinets = db.query(WBCabinet).filter(WBCabinet.is_active == True).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "active_cabinets": active_cabinets,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")