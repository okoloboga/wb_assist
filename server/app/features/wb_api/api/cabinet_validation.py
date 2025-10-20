"""
API endpoints for cabinet validation and cleanup
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.wb_api.cabinet_manager import CabinetManager
from app.features.wb_api.models import WBCabinet

router = APIRouter()


@router.post("/validate-all")
async def validate_all_cabinets(
    max_retries: int = 3,
    db: Session = Depends(get_db)
):
    """
    Валидация всех кабинетов с автоматическим удалением невалидных
    
    Args:
        max_retries: Максимальное количество попыток валидации для каждого кабинета
        
    Returns:
        Результат валидации всех кабинетов
    """
    try:
        cabinet_manager = CabinetManager(db)
        result = await cabinet_manager.validate_all_cabinets(max_retries)
        
        return {
            "success": True,
            "message": "Cabinet validation completed",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating cabinets: {str(e)}"
        )


@router.post("/validate/{cabinet_id}")
async def validate_cabinet(
    cabinet_id: int,
    max_retries: int = 3,
    db: Session = Depends(get_db)
):
    """
    Валидация конкретного кабинета с автоматическим удалением при невалидном API
    
    Args:
        cabinet_id: ID кабинета для валидации
        max_retries: Максимальное количество попыток валидации
        
    Returns:
        Результат валидации кабинета
    """
    try:
        # Получаем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cabinet not found"
            )
        
        cabinet_manager = CabinetManager(db)
        result = await cabinet_manager.validate_and_cleanup_cabinet(cabinet, max_retries)
        
        return {
            "success": True,
            "message": "Cabinet validation completed",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating cabinet: {str(e)}"
        )


@router.get("/status")
async def get_cabinet_validation_status(
    db: Session = Depends(get_db)
):
    """
    Получение статуса валидации кабинетов
    
    Returns:
        Статистика по кабинетам
    """
    try:
        # Получаем общую статистику по кабинетам
        total_cabinets = db.query(WBCabinet).count()
        
        # Получаем кабинеты с недавними ошибками синхронизации
        from app.features.wb_api.models import WBSyncLog
        from datetime import datetime, timezone, timedelta
        
        recent_errors = db.query(WBSyncLog).filter(
            WBSyncLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
            WBSyncLog.status == "error"
        ).count()
        
        return {
            "success": True,
            "data": {
                "total_cabinets": total_cabinets,
                "recent_sync_errors": recent_errors,
                "last_validation": "Not implemented yet"  # TODO: Добавить поле last_validation в БД
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cabinet status: {str(e)}"
        )
