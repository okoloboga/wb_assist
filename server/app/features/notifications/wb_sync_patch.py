"""
Патч для интеграции NotificationService с WBSyncService
"""

import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from .wb_sync_integration import WBSyncNotificationIntegration

logger = logging.getLogger(__name__)


def patch_wb_sync_service(sync_service, db: Session):
    """Патч WBSyncService для использования NotificationService"""
    try:
        # Создаем интеграцию
        integration = WBSyncNotificationIntegration(db)
        
        # Заменяем метод отправки уведомлений о новых заказах
        original_send_new_order = sync_service._send_new_order_notification
        sync_service._send_new_order_notification = integration.create_notification_service_wrapper(
            original_send_new_order
        )
        
        # Заменяем метод отправки уведомлений о критичных остатках
        if hasattr(sync_service, '_send_critical_stocks_notification'):
            original_send_stocks = sync_service._send_critical_stocks_notification
            sync_service._send_critical_stocks_notification = integration.create_notification_service_wrapper(
                original_send_stocks
            )
        
        logger.info("WBSyncService successfully patched with NotificationService")
        return True
        
    except Exception as e:
        logger.error(f"Failed to patch WBSyncService: {e}")
        return False


def create_patched_sync_service(db: Session):
    """Создает WBSyncService с интегрированным NotificationService"""
    from app.features.wb_api.sync_service import WBSyncService
    
    # Создаем обычный WBSyncService
    sync_service = WBSyncService(db)
    
    # Применяем патч
    patch_success = patch_wb_sync_service(sync_service, db)
    
    if not patch_success:
        logger.warning("Failed to patch WBSyncService, using original implementation")
    
    return sync_service
