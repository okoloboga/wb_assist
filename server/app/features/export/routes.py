"""
API эндпоинты для экспорта данных в Google Sheets
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from .service import ExportService, ExportStatus, ExportDataType
from .schemas import (
    ExportTokenCreate,
    ExportTokenResponse,
    ExportDataResponse,
    ExportStatsResponse,
    ExportErrorResponse,
    CabinetValidationResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/export", tags=["export"])


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    """Получает сервис экспорта"""
    return ExportService(db)


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Извлекает IP адрес и User-Agent из запроса"""
    ip_address = request.client.host if request.client else None
    
    # Пытаемся получить реальный IP через заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent")
    
    return ip_address, user_agent


@router.post("/token", response_model=ExportTokenResponse)
async def create_export_token(
    token_data: ExportTokenCreate,
    service: ExportService = Depends(get_export_service)
):
    """Создает новый токен экспорта для кабинета"""
    try:
        export_token = service.create_export_token(
            user_id=token_data.user_id,
            cabinet_id=token_data.cabinet_id
        )
        
        logger.info(f"Создан токен экспорта для кабинета {token_data.cabinet_id}")
        
        return ExportTokenResponse(
            token=export_token.token,
            cabinet_id=export_token.cabinet_id,
            created_at=export_token.created_at,
            is_active=export_token.is_active,
            rate_limit_remaining=export_token.rate_limit_remaining,
            rate_limit_reset=export_token.rate_limit_reset
        )
        
    except ValueError as e:
        logger.warning(f"Ошибка создания токена: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при создании токена: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/token/{token}/validate")
async def validate_export_token(
    token: str,
    cabinet_id: int = Query(..., description="ID кабинета WB"),
    service: ExportService = Depends(get_export_service)
):
    """Валидирует токен экспорта"""
    is_valid, export_token = service.validate_token(token, cabinet_id)
    
    if not is_valid:
        if export_token and export_token.is_rate_limited():
            raise HTTPException(
                status_code=429, 
                detail="Превышен лимит запросов. Попробуйте позже."
            )
        else:
            raise HTTPException(
                status_code=401, 
                detail="Неверный токен или кабинет"
            )
    
    return {
        "valid": True,
        "cabinet_id": export_token.cabinet_id,
        "rate_limit_remaining": export_token.rate_limit_remaining,
        "rate_limit_reset": export_token.rate_limit_reset
    }


@router.delete("/token/{token}")
async def revoke_export_token(
    token: str,
    service: ExportService = Depends(get_export_service)
):
    """Отзывает токен экспорта"""
    success = service.revoke_token(token)
    
    if not success:
        raise HTTPException(status_code=404, detail="Токен не найден")
    
    return {"message": "Токен успешно отозван"}


@router.get("/orders/{cabinet_id}", response_model=ExportDataResponse)
async def get_orders_export(
    cabinet_id: int,
    token: str = Query(..., description="Токен экспорта"),
    limit: int = Query(1000, ge=1, le=5000, description="Лимит записей"),
    request: Request = None,
    service: ExportService = Depends(get_export_service)
):
    """Экспортирует данные заказов для Google Sheets"""
    start_time = datetime.now()
    
    # Валидируем токен
    is_valid, export_token = service.validate_token(token, cabinet_id)
    if not is_valid:
        if export_token and export_token.is_rate_limited():
            service.log_export_request(
                export_token, ExportStatus.RATE_LIMIT, ExportDataType.ORDERS,
                ip_address=get_client_info(request)[0],
                user_agent=get_client_info(request)[1]
            )
            raise HTTPException(
                status_code=429, 
                detail="Превышен лимит запросов. Попробуйте позже."
            )
        else:
            raise HTTPException(
                status_code=401, 
                detail="Неверный токен или кабинет"
            )
    
    try:
        # Получаем данные
        response = service.get_export_data(cabinet_id, ExportDataType.ORDERS, limit)
        
        # Логируем успешный запрос
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.SUCCESS, ExportDataType.ORDERS,
            rows_count=response.total_rows,
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        return response
        
    except Exception as e:
        # Логируем ошибку
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.ERROR, ExportDataType.ORDERS,
            error_message=str(e),
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        logger.error(f"Ошибка экспорта заказов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных заказов")


@router.get("/stocks/{cabinet_id}", response_model=ExportDataResponse)
async def get_stocks_export(
    cabinet_id: int,
    token: str = Query(..., description="Токен экспорта"),
    limit: int = Query(1000, ge=1, le=5000, description="Лимит записей"),
    request: Request = None,
    service: ExportService = Depends(get_export_service)
):
    """Экспортирует данные остатков для Google Sheets"""
    start_time = datetime.now()
    
    # Валидируем токен
    is_valid, export_token = service.validate_token(token, cabinet_id)
    if not is_valid:
        if export_token and export_token.is_rate_limited():
            service.log_export_request(
                export_token, ExportStatus.RATE_LIMIT, ExportDataType.STOCKS,
                ip_address=get_client_info(request)[0],
                user_agent=get_client_info(request)[1]
            )
            raise HTTPException(
                status_code=429, 
                detail="Превышен лимит запросов. Попробуйте позже."
            )
        else:
            raise HTTPException(
                status_code=401, 
                detail="Неверный токен или кабинет"
            )
    
    try:
        # Получаем данные
        response = service.get_export_data(cabinet_id, ExportDataType.STOCKS, limit)
        
        # Логируем успешный запрос
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.SUCCESS, ExportDataType.STOCKS,
            rows_count=response.total_rows,
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        return response
        
    except Exception as e:
        # Логируем ошибку
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.ERROR, ExportDataType.STOCKS,
            error_message=str(e),
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        logger.error(f"Ошибка экспорта остатков: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных остатков")


@router.get("/reviews/{cabinet_id}", response_model=ExportDataResponse)
async def get_reviews_export(
    cabinet_id: int,
    token: str = Query(..., description="Токен экспорта"),
    limit: int = Query(1000, ge=1, le=5000, description="Лимит записей"),
    request: Request = None,
    service: ExportService = Depends(get_export_service)
):
    """Экспортирует данные отзывов для Google Sheets"""
    start_time = datetime.now()
    
    # Валидируем токен
    is_valid, export_token = service.validate_token(token, cabinet_id)
    if not is_valid:
        if export_token and export_token.is_rate_limited():
            service.log_export_request(
                export_token, ExportStatus.RATE_LIMIT, ExportDataType.REVIEWS,
                ip_address=get_client_info(request)[0],
                user_agent=get_client_info(request)[1]
            )
            raise HTTPException(
                status_code=429, 
                detail="Превышен лимит запросов. Попробуйте позже."
            )
        else:
            raise HTTPException(
                status_code=401, 
                detail="Неверный токен или кабинет"
            )
    
    try:
        # Получаем данные
        response = service.get_export_data(cabinet_id, ExportDataType.REVIEWS, limit)
        
        # Логируем успешный запрос
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.SUCCESS, ExportDataType.REVIEWS,
            rows_count=response.total_rows,
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        return response
        
    except Exception as e:
        # Логируем ошибку
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        service.log_export_request(
            export_token, ExportStatus.ERROR, ExportDataType.REVIEWS,
            error_message=str(e),
            response_time_ms=response_time,
            ip_address=get_client_info(request)[0],
            user_agent=get_client_info(request)[1]
        )
        
        logger.error(f"Ошибка экспорта отзывов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных отзывов")


@router.get("/cabinet/{cabinet_id}/validate", response_model=CabinetValidationResponse)
async def validate_cabinet(
    cabinet_id: int,
    service: ExportService = Depends(get_export_service)
):
    """Валидирует кабинет и проверяет наличие данных для экспорта"""
    try:
        return service.validate_cabinet(cabinet_id)
    except Exception as e:
        logger.error(f"Ошибка валидации кабинета {cabinet_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка валидации кабинета")


@router.get("/token/{token}/stats", response_model=ExportStatsResponse)
async def get_export_stats(
    token: str,
    cabinet_id: int = Query(..., description="ID кабинета WB"),
    days: int = Query(7, ge=1, le=30, description="Количество дней для статистики"),
    service: ExportService = Depends(get_export_service)
):
    """Получает статистику экспорта для токена"""
    # Валидируем токен
    is_valid, export_token = service.validate_token(token, cabinet_id)
    if not is_valid:
        raise HTTPException(
            status_code=401, 
            detail="Неверный токен или кабинет"
        )
    
    try:
        return service.get_export_stats(export_token, days)
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@router.get("/sync-interval")
async def get_sync_interval():
    """Получает интервал синхронизации из переменной окружения"""
    import os
    sync_interval_env = os.getenv("SYNC_INTERVAL", "21600")  # По умолчанию 6 часов (21600 секунд)
    sync_interval_seconds = int(sync_interval_env)
    
    return {
        "sync_interval_seconds": sync_interval_seconds,
        "sync_interval_minutes": sync_interval_seconds // 60,
        "sync_interval_hours": sync_interval_seconds // 3600,
        "description": f"Данные обновляются каждые {sync_interval_seconds // 60} минут"
    }


@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса экспорта"""
    return {
        "status": "healthy",
        "service": "export",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/cabinet/{cabinet_id}/spreadsheet")
async def set_cabinet_spreadsheet(
    cabinet_id: int,
    spreadsheet_url: str = Query(..., description="Ссылка на Google Sheets таблицу"),
    service: ExportService = Depends(get_export_service)
):
    """Сохраняет spreadsheet_id для кабинета"""
    try:
        result = service.set_cabinet_spreadsheet(cabinet_id, spreadsheet_url)
        logger.info(f"Сохранен spreadsheet_id для кабинета {cabinet_id}: {result['spreadsheet_id']}")
        return result
    except ValueError as e:
        logger.warning(f"Ошибка сохранения spreadsheet: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при сохранении spreadsheet: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cabinet/{cabinet_id}/update")
async def update_cabinet_spreadsheet(
    cabinet_id: int,
    service: ExportService = Depends(get_export_service)
):
    """Обновляет Google Sheets таблицу кабинета"""
    try:
        success = service.update_spreadsheet(cabinet_id)
        if success:
            return {
                "status": "success",
                "message": "Таблица успешно обновлена",
                "cabinet_id": cabinet_id
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail="Кабинет не имеет привязанной таблицы или произошла ошибка обновления"
            )
    except Exception as e:
        logger.error(f"Ошибка обновления таблицы кабинета {cabinet_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления таблицы")
