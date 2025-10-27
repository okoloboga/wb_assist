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


@celery_app.task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 60})
def sync_cabinet_data(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Синхронизация данных для конкретного кабинета с retry логикой для Redis Sentinel
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
        
        # УБРАНО: Обновление last_sync_at теперь делается внутри sync_all_data()
        # для правильной работы с уведомлениями
        
        logger.info(f"Синхронизация кабинета {cabinet_id} завершена: {result}")
        return {"status": "success", "cabinet_id": cabinet_id, "result": result}
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации кабинета {cabinet_id}: {e}")
        
        # Специальная обработка для Redis Sentinel ошибок
        if "UNBLOCKED" in str(e) or "master -> replica" in str(e) or "ResponseError" in str(e):
            logger.warning(f"Redis Sentinel переключение обнаружено для кабинета {cabinet_id}, повторяем через 30 секунд")
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=30, exc=e)
        else:
            # Обычные ошибки - повторяем через 1 минуту
            if self.request.retries < self.max_retries:
                logger.info(f"Повторная попытка синхронизации кабинета {cabinet_id} через 1 минуту")
                raise self.retry(countdown=60, exc=e)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if 'db' in locals():
            db.close()


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30})
def sync_all_cabinets(self) -> Dict[str, Any]:
    """
    Проверяет все кабинеты и запускает синхронизацию для тех, кому пора
    С retry логикой для Redis Sentinel
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
        
        # Специальная обработка для Redis Sentinel ошибок
        if "UNBLOCKED" in str(e) or "master -> replica" in str(e) or "ResponseError" in str(e):
            logger.warning(f"Redis Sentinel переключение обнаружено при проверке кабинетов, повторяем через 30 секунд")
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=30, exc=e)
        else:
            # Обычные ошибки - повторяем через 1 минуту
            if self.request.retries < self.max_retries:
                logger.info(f"Повторная попытка проверки кабинетов через 1 минуту")
                raise self.retry(countdown=60, exc=e)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if 'db' in locals():
            db.close()


def should_sync_cabinet(cabinet: WBCabinet) -> bool:
    """
    Определяет, нужно ли синхронизировать кабинет
    """
    from datetime import timezone
    
    if not cabinet.last_sync_at:
        # Если никогда не синхронизировался, синхронизируем сразу
        return True
    
    now = datetime.now(timezone.utc)
    
    # Если время в базе naive, делаем его aware
    last_sync = cabinet.last_sync_at
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    
    # Проверяем, не прошло ли слишком много времени (более 30 минут)
    time_since_last_sync = now - last_sync
    if time_since_last_sync > timedelta(minutes=30):
        logger.warning(f"Кабинет {cabinet.id} не синхронизировался {time_since_last_sync}, принудительная синхронизация")
        return True
    
    # Вычисляем время следующей синхронизации
    next_sync_time = calculate_next_sync_time(cabinet)
    
    # Логируем для отладки
    logger.info(f"Кабинет {cabinet.id}: last_sync={last_sync}, now={now}, next_sync={next_sync_time}")
    logger.info(f"Кабинет {cabinet.id}: time_since_last_sync={time_since_last_sync}, should_sync={now >= next_sync_time}")
    
    # Проверяем, пора ли синхронизироваться
    return now >= next_sync_time


def calculate_next_sync_time(cabinet: WBCabinet) -> datetime:
    """
    Вычисляет время следующей синхронизации для кабинета
    """
    from datetime import timezone
    
    # Базовое время - время последней синхронизации
    last_sync = cabinet.last_sync_at
    
    # Если время в базе naive, делаем его aware
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)
    
    # Интервал синхронизации из переменной окружения
    import os
    sync_interval_env = os.getenv("SYNC_INTERVAL", "180")  # По умолчанию 3 минуты
    sync_interval = int(sync_interval_env)
    
    # Вычисляем время следующей синхронизации (без случайного офсета)
    next_sync = last_sync + timedelta(seconds=sync_interval)
    
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
