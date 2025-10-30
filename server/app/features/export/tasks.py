"""
Фоновые задачи для автоматического экспорта в Google Sheets
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.celery_app import celery_app
from app.features.wb_api.models import WBCabinet
from .service import ExportService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def export_all_to_spreadsheets(self) -> Dict[str, Any]:
    """
    Экспортирует данные всех кабинетов в их Google Sheets таблицы
    """
    try:
        logger.info("Начинаем экспорт данных во все Google Sheets таблицы")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем все активные кабинеты с привязанными таблицами
        cabinets = db.query(WBCabinet).filter(
            and_(
                WBCabinet.is_active == True,
                WBCabinet.spreadsheet_id.isnot(None)
            )
        ).all()
        
        logger.info(f"Найдено кабинетов с таблицами: {len(cabinets)}")
        
        success_count = 0
        error_count = 0
        errors = []
        
        # Создаем сервис экспорта
        export_service = ExportService(db)
        
        # Обновляем таблицы для каждого кабинета
        for cabinet in cabinets:
            try:
                success = export_service.update_spreadsheet(cabinet.id)
                if success:
                    success_count += 1
                    logger.info(f"✅ Таблица кабинета {cabinet.id} обновлена")
                else:
                    error_count += 1
                    error_msg = f"Ошибка обновления таблицы кабинета {cabinet.id}"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_count += 1
                error_msg = f"Кабинет {cabinet.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        result = {
            "status": "completed",
            "total_cabinets": len(cabinets),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors[:5] if errors else []  # Только первые 5 ошибок
        }
        
        logger.info(f"Экспорт завершен: {success_count} успешно, {error_count} ошибок")
        
        db.close()
        return result
        
    except Exception as e:
        logger.error(f"Критическая ошибка при экспорте: {e}")
        db.close()
        raise


@celery_app.task(bind=True, max_retries=3)
def export_cabinet_to_spreadsheet(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Экспортирует данные конкретного кабинета в его Google Sheets таблицу
    """
    try:
        logger.info(f"Начинаем экспорт кабинета {cabinet_id}")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            logger.error(f"Кабинет {cabinet_id} не найден")
            db.close()
            return {"status": "error", "message": "Кабинет не найден"}
        
        if not cabinet.spreadsheet_id:
            logger.warning(f"Кабинет {cabinet_id} не имеет привязанной таблицы")
            db.close()
            return {"status": "skipped", "message": "Нет привязанной таблицы"}
        
        # Создаем сервис экспорта
        export_service = ExportService(db)
        
        # Обновляем таблицу
        success = export_service.update_spreadsheet(cabinet_id)
        
        db.close()
        
        if success:
            logger.info(f"✅ Таблица кабинета {cabinet_id} обновлена")
            return {"status": "success", "cabinet_id": cabinet_id}
        else:
            logger.error(f"❌ Ошибка обновления таблицы кабинета {cabinet_id}")
            return {"status": "error", "cabinet_id": cabinet_id, "message": "Ошибка обновления"}
        
    except Exception as e:
        logger.error(f"Критическая ошибка при экспорте кабинета {cabinet_id}: {e}")
        if 'db' in locals():
            db.close()
        raise

