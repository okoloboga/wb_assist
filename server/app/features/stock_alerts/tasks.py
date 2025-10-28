"""
Celery задачи для системы динамических уведомлений по остаткам
"""

from datetime import date, timedelta
from typing import Dict, Any
import logging

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.features.wb_api.models import WBCabinet
from app.features.user.models import User
from app.features.wb_api.crud_cabinet_users import CabinetUserCRUD
from .sales_aggregator import DailySalesAggregator
from .notification_service import StockAlertNotificationService
from .crud import DailySalesAnalyticsCRUD, StockAlertHistoryCRUD

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def aggregate_daily_sales_task(self, cabinet_id: int, date_str: str = None) -> Dict[str, Any]:
    """
    Задача агрегации заказов за день
    
    Запускается: Ежедневно в 00:30 (через 30 минут после начала дня)
    
    Args:
        cabinet_id: ID кабинета
        date_str: Дата для агрегации (YYYY-MM-DD), если None - вчерашний день
    """
    db = next(get_db())
    
    try:
        # Определяем дату для агрегации
        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = date.today() - timedelta(days=1)  # Вчерашний день
        
        logger.info(f"Starting daily sales aggregation for cabinet {cabinet_id}, date {target_date}")
        
        # Создаем агрегатор и запускаем агрегацию
        aggregator = DailySalesAggregator(db)
        
        # Используем синхронный вызов для Celery
        import asyncio
        result = asyncio.run(aggregator.aggregate_orders_for_date(cabinet_id, target_date))
        
        logger.info(f"Daily sales aggregation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in aggregate_daily_sales_task: {e}")
        # Retry с экспоненциальной задержкой
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def aggregate_daily_sales_all_cabinets(self) -> Dict[str, Any]:
    """
    Агрегация продаж за вчерашний день для всех активных кабинетов + проверка алертов
    
    Запускается: Ежедневно в настраиваемое время (STOCK_ALERT_CHECK_TIME)
    """
    db = next(get_db())
    
    try:
        yesterday = date.today() - timedelta(days=1)
        logger.info(f"Starting daily sales aggregation and stock alerts check for all cabinets, date {yesterday}")
        
        # Получаем все активные кабинеты
        cabinets = db.query(WBCabinet).filter(WBCabinet.is_active == True).all()
        
        aggregation_processed = 0
        aggregation_failed = 0
        alerts_processed = 0
        alerts_failed = 0
        total_alerts_sent = 0
        
        for cabinet in cabinets:
            try:
                # 1. Агрегируем данные за вчерашний день
                aggregator = DailySalesAggregator(db)
                import asyncio
                agg_result = asyncio.run(aggregator.aggregate_orders_for_date(cabinet.id, yesterday))
                
                if agg_result.get("status") == "success":
                    aggregation_processed += 1
                    logger.info(f"Aggregation completed for cabinet {cabinet.id}: {agg_result}")
                else:
                    aggregation_failed += 1
                    logger.error(f"Aggregation failed for cabinet {cabinet.id}: {agg_result}")
                    continue
                
                # 2. Сразу проверяем алерты для этого кабинета
                try:
                    # Получаем пользователей кабинета
                    cabinet_user_crud = CabinetUserCRUD()
                    user_ids = cabinet_user_crud.get_cabinet_users(db, cabinet.id)
                    
                    cabinet_alerts_sent = 0
                    
                    for user_id in user_ids:
                        try:
                            user = db.query(User).filter(User.id == user_id).first()
                            if not user:
                                continue
                            
                            bot_webhook_url = getattr(user, 'bot_webhook_url', None)
                            if not bot_webhook_url:
                                logger.warning(f"No webhook URL for user {user_id}")
                                continue
                            
                            # Проверяем алерты
                            notification_service = StockAlertNotificationService(db)
                            alert_result = asyncio.run(notification_service.check_and_send_alerts(
                                cabinet_id=cabinet.id,
                                user_id=user_id,
                                bot_webhook_url=bot_webhook_url
                            ))
                            
                            cabinet_alerts_sent += alert_result.get("alerts_sent", 0)
                            logger.info(f"Alerts for user {user_id}: {alert_result}")
                            
                        except Exception as e:
                            logger.error(f"Error checking alerts for user {user_id}: {e}")
                            alerts_failed += 1
                            continue
                    
                    total_alerts_sent += cabinet_alerts_sent
                    alerts_processed += 1
                    logger.info(f"Stock alerts completed for cabinet {cabinet.id}: {cabinet_alerts_sent} alerts sent")
                    
                except Exception as e:
                    logger.error(f"Error checking alerts for cabinet {cabinet.id}: {e}")
                    alerts_failed += 1
                
            except Exception as e:
                logger.error(f"Error processing cabinet {cabinet.id}: {e}")
                aggregation_failed += 1
        
        logger.info(
            f"Daily aggregation and alerts completed: "
            f"{aggregation_processed} cabinets aggregated, {aggregation_failed} failed, "
            f"{alerts_processed} cabinets checked for alerts, {alerts_failed} failed, "
            f"{total_alerts_sent} total alerts sent"
        )
        
        return {
            "status": "success",
            "date": str(yesterday),
            "aggregation": {
                "cabinets_processed": aggregation_processed,
                "cabinets_failed": aggregation_failed
            },
            "alerts": {
                "cabinets_processed": alerts_processed,
                "cabinets_failed": alerts_failed,
                "total_alerts_sent": total_alerts_sent
            }
        }
        
    except Exception as e:
        logger.error(f"Error in aggregate_daily_sales_all_cabinets: {e}")
        raise self.retry(exc=e, countdown=60)
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def check_stock_alerts_task(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Задача проверки и отправки уведомлений по остаткам
    
    Запускается: При каждой синхронизации остатков (после sync_cabinet_data)
    
    Args:
        cabinet_id: ID кабинета для проверки
    """
    db = next(get_db())
    
    try:
        logger.info(f"Starting stock alerts check for cabinet {cabinet_id}")
        
        # Получаем кабинет
        cabinet = db.query(WBCabinet).filter(WBCabinet.id == cabinet_id).first()
        if not cabinet:
            logger.warning(f"Cabinet {cabinet_id} not found")
            return {"status": "error", "error": "Cabinet not found"}
        
        # Получаем пользователей кабинета
        cabinet_user_crud = CabinetUserCRUD()
        user_ids = cabinet_user_crud.get_cabinet_users(db, cabinet_id)
        
        if not user_ids:
            logger.warning(f"No users found for cabinet {cabinet_id}")
            return {"status": "error", "error": "No users found"}
        
        total_sent = 0
        
        # Проверяем алерты для каждого пользователя
        for user_id in user_ids:
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    continue
                
                bot_webhook_url = getattr(user, 'bot_webhook_url', None)
                if not bot_webhook_url:
                    logger.warning(f"No webhook URL for user {user_id}")
                    continue
                
                # Создаем сервис и проверяем алерты
                notification_service = StockAlertNotificationService(db)
                
                # Используем синхронный вызов для Celery
                import asyncio
                result = asyncio.run(notification_service.check_and_send_alerts(
                    cabinet_id=cabinet_id,
                    user_id=user_id,
                    bot_webhook_url=bot_webhook_url
                ))
                
                total_sent += result.get("alerts_sent", 0)
                logger.info(f"Stock alerts for user {user_id}: {result}")
                
            except Exception as e:
                logger.error(f"Error checking alerts for user {user_id}: {e}")
                continue
        
        logger.info(f"Stock alerts check completed: {total_sent} total alerts sent")
        
        return {
            "status": "success",
            "cabinet_id": cabinet_id,
            "total_alerts_sent": total_sent
        }
        
    except Exception as e:
        logger.error(f"Error in check_stock_alerts_task: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def cleanup_old_analytics_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Очистка старых данных аналитики
    
    Запускается: Раз в неделю (воскресенье 03:00)
    
    Args:
        days_to_keep: Сколько дней хранить данные
    """
    db = next(get_db())
    
    try:
        logger.info(f"Starting cleanup of old analytics data (keeping {days_to_keep} days)")
        
        # Очищаем daily_sales_analytics
        analytics_crud = DailySalesAnalyticsCRUD()
        deleted_analytics = analytics_crud.delete_old_records(db, days_to_keep)
        
        # Очищаем stock_alert_history (храним дольше - 90 дней)
        alert_crud = StockAlertHistoryCRUD()
        deleted_alerts = alert_crud.delete_old_records(db, days_to_keep=90)
        
        logger.info(
            f"Cleanup completed: {deleted_analytics} analytics records, "
            f"{deleted_alerts} alert history records deleted"
        )
        
        return {
            "status": "success",
            "deleted_analytics": deleted_analytics,
            "deleted_alerts": deleted_alerts
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_analytics_task: {e}")
        raise self.retry(exc=e, countdown=60)
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def initialize_analytics_for_cabinet(self, cabinet_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Первичная загрузка аналитики для нового кабинета
    
    Args:
        cabinet_id: ID кабинета
        days: Количество дней для загрузки
    """
    db = next(get_db())
    
    try:
        logger.info(f"Initializing analytics for cabinet {cabinet_id} ({days} days)")
        
        aggregator = DailySalesAggregator(db)
        
        # Используем синхронный вызов для Celery
        import asyncio
        result = asyncio.run(aggregator.aggregate_last_n_days(cabinet_id, days))
        
        logger.info(f"Analytics initialization completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error initializing analytics: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()

