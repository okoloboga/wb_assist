"""
Фоновые задачи для автоматической синхронизации данных
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from celery import current_task
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.celery_app import celery_app
from app.features.wb_api.sync_service import WBSyncService
from app.features.wb_api.models import WBCabinet, WBOrder
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def sync_cabinet_data(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Синхронизация данных для конкретного кабинета
    """
    try:
        logger.info(f"Начинаем синхронизацию кабинета {cabinet_id}")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            logger.error(f"Кабинет {cabinet_id} не найден")
            return {"status": "error", "message": "Кабинет не найден"}
        
        # Создаем сервис синхронизации
        sync_service = WBSyncService(db)
        
        # Выполняем синхронизацию (синхронная обертка для асинхронной функции)
        import asyncio
        result = asyncio.run(sync_service.sync_all_data(cabinet))
        
        # Обновляем время последней синхронизации
        from datetime import timezone
        cabinet.last_sync_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Синхронизация кабинета {cabinet_id} завершена: {result}")
        return {"status": "success", "cabinet_id": cabinet_id, "result": result}
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации кабинета {cabinet_id}: {e}")
        
        # Повторяем через 1 минуту при ошибке
        if self.request.retries < self.max_retries:
            logger.info(f"Повторная попытка синхронизации кабинета {cabinet_id} через 1 минуту")
            raise self.retry(countdown=60)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if 'db' in locals():
            db.close()


@celery_app.task
def sync_all_cabinets() -> Dict[str, Any]:
    """
    Проверяет все кабинеты и запускает синхронизацию для тех, кому пора
    """
    try:
        logger.info("Проверяем кабинеты для синхронизации")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем все активные кабинеты
        cabinets = db.query(WBCabinet).filter(WBCabinet.is_active == True).all()
        
        synced_count = 0
        skipped_count = 0
        
        for cabinet in cabinets:
            if should_sync_cabinet(cabinet):
                # Запускаем синхронизацию в фоне
                sync_cabinet_data.delay(cabinet.id)
                synced_count += 1
                logger.info(f"Запущена синхронизация кабинета {cabinet.id}")
            else:
                skipped_count += 1
        
        logger.info(f"Синхронизация: {synced_count} кабинетов запущено, {skipped_count} пропущено")
        return {
            "status": "success",
            "synced_count": synced_count,
            "skipped_count": skipped_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка проверки кабинетов: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        if 'db' in locals():
            db.close()


def should_sync_cabinet(cabinet: WBCabinet) -> bool:
    """
    Определяет, нужно ли синхронизировать кабинет
    """
    if not cabinet.last_sync_at:
        # Если никогда не синхронизировался, синхронизируем сразу
        return True
    
    # Вычисляем время следующей синхронизации
    next_sync_time = calculate_next_sync_time(cabinet)
    
    # Проверяем, пора ли синхронизироваться
    from datetime import timezone
    return datetime.now(timezone.utc) >= next_sync_time


def calculate_next_sync_time(cabinet: WBCabinet) -> datetime:
    """
    Вычисляет время следующей синхронизации для кабинета
    """
    from datetime import timezone
    
    # Базовое время - время первой синхронизации
    first_sync = cabinet.last_sync_at
    
    # Если время в базе naive, делаем его aware
    if first_sync.tzinfo is None:
        first_sync = first_sync.replace(tzinfo=timezone.utc)
    
    # Добавляем случайный офсет 0-4 минуты для распределения нагрузки
    random_offset = random.randint(0, 4 * 60)  # 0-4 минуты в секундах
    
    # Интервал синхронизации (5 минут)
    sync_interval = 5 * 60  # 5 минут в секундах
    
    # Вычисляем время следующей синхронизации
    next_sync = first_sync + timedelta(seconds=random_offset + sync_interval)
    
    return next_sync


def schedule_cabinet_sync(cabinet_id: int) -> None:
    """
    Планирует синхронизацию для нового кабинета
    """
    try:
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            logger.error(f"Кабинет {cabinet_id} не найден для планирования")
            return
        
        # Вычисляем время первой синхронизации (сейчас + случайный офсет)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        random_offset = random.randint(0, 4 * 60)  # 0-4 минуты
        first_sync_time = now + timedelta(seconds=random_offset)
        
        # Обновляем время последней синхронизации
        cabinet.last_sync_at = first_sync_time
        db.commit()
        
        logger.info(f"Запланирована первая синхронизация кабинета {cabinet_id} на {first_sync_time}")
        
    except Exception as e:
        logger.error(f"Ошибка планирования синхронизации кабинета {cabinet_id}: {e}")
    
    finally:
        if 'db' in locals():
            db.close()
