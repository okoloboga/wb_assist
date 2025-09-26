"""
Маршруты для статистики и аналитики.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ...core.database import get_db
from ..user.crud import UserCRUD

stats_router = APIRouter(prefix="/stats", tags=["statistics"])


@stats_router.get("/")
async def get_stats(db: Session = Depends(get_db)):
    """
    Получение общей статистики системы.
    """
    user_crud = UserCRUD(db)
    total_users = await user_crud.get_total_users()
    
    return JSONResponse(
        status_code=200,
        content={
            "total_users": total_users,
            "status": "active"
        }
    )


@stats_router.get("/analytics")
async def get_analytics():
    """
    Получение аналитических данных.
    """
    return JSONResponse(
        status_code=200,
        content={
            "analytics": {
                "active_sessions": 0,
                "requests_per_minute": 0,
                "uptime": "running"
            }
        }
    )