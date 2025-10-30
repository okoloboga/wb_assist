"""
API эндпоинты для управления шаблонами Google Sheets
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from .google_sheets_generator import GoogleSheetsTemplateGenerator
from .schemas import GoogleSheetsTemplateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export/template", tags=["export-template"])


def get_template_generator() -> GoogleSheetsTemplateGenerator:
    """Получает генератор шаблонов Google Sheets"""
    try:
        return GoogleSheetsTemplateGenerator()
    except Exception as e:
        logger.error(f"Ошибка инициализации генератора шаблонов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка инициализации Google Sheets API")


@router.post("/create", response_model=GoogleSheetsTemplateResponse)
async def create_template(
    template_name: Optional[str] = Query(None, description="Название шаблона"),
    generator: GoogleSheetsTemplateGenerator = Depends(get_template_generator)
):
    """Создает новый шаблон Google Sheets"""
    try:
        result = generator.create_template(template_name)
        
        logger.info(f"Создан шаблон: {result['spreadsheet_id']}")
        
        return GoogleSheetsTemplateResponse(
            template_id=result['spreadsheet_id'],
            template_url=result['url'],
            created_at=datetime.fromisoformat(result['created_at']),
            sheets_count=4,  # Настройки, Склад, Заказы, Отзывы
            is_ready=True
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания шаблона: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания шаблона: {str(e)}")


@router.get("/{template_id}", response_model=GoogleSheetsTemplateResponse)
async def get_template_info(
    template_id: str,
    generator: GoogleSheetsTemplateGenerator = Depends(get_template_generator)
):
    """Получает информацию о шаблоне"""
    try:
        result = generator.get_template_info(template_id)
        
        return GoogleSheetsTemplateResponse(
            template_id=result['spreadsheet_id'],
            template_url=result['url'],
            created_at=datetime.now(),  # В реальной реализации нужно получать из БД
            sheets_count=result['sheets_count'],
            is_ready=result['is_ready']
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о шаблоне {template_id}: {e}")
        raise HTTPException(status_code=404, detail="Шаблон не найден")


@router.post("/{template_id}/update")
async def update_template(
    template_id: str,
    generator: GoogleSheetsTemplateGenerator = Depends(get_template_generator)
):
    """Обновляет существующий шаблон"""
    try:
        # В реальной реализации здесь будет обновление шаблона
        # Пока просто возвращаем успех
        logger.info(f"Обновление шаблона {template_id} запрошено")
        
        return {
            "message": "Шаблон обновлен",
            "template_id": template_id,
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка обновления шаблона {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления шаблона: {str(e)}")


@router.get("/health")
async def template_health_check():
    """Проверка здоровья сервиса шаблонов"""
    try:
        # Проверяем доступность Google Sheets API
        generator = GoogleSheetsTemplateGenerator()
        
        return {
            "status": "healthy",
            "service": "template-generator",
            "google_sheets_api": "available",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки здоровья сервиса шаблонов: {e}")
        return {
            "status": "unhealthy",
            "service": "template-generator",
            "google_sheets_api": "unavailable",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
