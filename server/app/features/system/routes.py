"""
Системные маршруты для проверки здоровья и статуса приложения.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...core.database import get_db

system_router = APIRouter(prefix="/system", tags=["system"])


@system_router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Проверка здоровья приложения и подключения к БД.
    """
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "message": "Application is running",
                "database": "connected"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@system_router.get("/")
async def root():
    """
    Корневой эндпоинт API.
    """
    return JSONResponse(
        status_code=200,
        content={
            "message": "Telegram Bot Backend API",
            "status": "running",
            "version": "1.0.0"
        }
    )


@system_router.get("/status")
async def status_check():
    """
    Проверка статуса системы.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "active",
            "service": "wb_assist",
            "version": "1.0.0"
        }
    )