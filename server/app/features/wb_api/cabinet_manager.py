"""
Cabinet Manager - управление кабинетами WB с автоматическим удалением при невалидном API
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import WBCabinet, WBOrder, WBProduct, WBStock, WBReview
from .models_sales import WBSales
from .client import WBAPIClient

logger = logging.getLogger(__name__)


class CabinetManager:
    """Менеджер кабинетов с автоматическим удалением при невалидном API"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def validate_and_cleanup_cabinet(self, cabinet: WBCabinet, max_retries: int = 3) -> Dict[str, Any]:
        """
        Валидация кабинета с автоматическим удалением при невалидном API
        
        Args:
            cabinet: Кабинет для валидации
            max_retries: Максимальное количество попыток валидации
            
        Returns:
            Dict с результатом валидации и действий
        """
        try:
            logger.info(f"Starting cabinet validation for cabinet {cabinet.id}")
            
            # Создаем клиент для валидации
            client = WBAPIClient(cabinet)
            
            # Валидируем API ключ (retry логика уже есть в _make_request)
            logger.info(f"Validating API key for cabinet {cabinet.id}")
            validation_result = await client.validate_api_key()
            
            if validation_result.get("valid", False):
                logger.info(f"API key validation successful for cabinet {cabinet.id}")
                return {
                    "success": True,
                    "valid": True,
                    "message": "API key is valid",
                    "attempts": 1
                }
            
            # Если API невалиден, удаляем кабинет
            logger.error(f"API validation failed for cabinet {cabinet.id}. Removing cabinet.")
            
            # Получаем всех пользователей кабинета для уведомления
            from .crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            
            if not user_ids:
                logger.error(f"No users found for cabinet {cabinet.id}")
                return {
                    "success": False,
                    "valid": False,
                    "message": "API key invalid and no users found",
                    "attempts": 1,
                    "cabinet_removed": False
                }
            
            # Удаляем кабинет и все связанные данные
            cleanup_result = await self._cleanup_cabinet_data(cabinet)
            
            # Отправляем уведомления всем пользователям кабинета
            notification_results = []
            for user_id in user_ids:
                user_data = self._get_user_data(user_id)
                if user_data:
                    notification_result = await self._send_cabinet_removal_notification(
                        user_data, cabinet, validation_result
                    )
                    notification_results.append(notification_result)
            
            return {
                "success": True,
                "valid": False,
                "message": "API key invalid, cabinet removed",
                "attempts": 1,
                "cabinet_removed": cleanup_result["success"],
                "notifications_sent": len(notification_results),
                "validation_error": validation_result
            }
            
        except Exception as e:
            logger.error(f"Error during cabinet validation for cabinet {cabinet.id}: {e}")
            return {
                "success": False,
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "attempts": 0,
                "cabinet_removed": False
            }
    
    def _get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        try:
            from app.features.user.models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return None
            
            return {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        except Exception as e:
            logger.error(f"Error getting user data for user {user_id}: {e}")
            return None
    
    async def _cleanup_cabinet_data(self, cabinet: WBCabinet) -> Dict[str, Any]:
        """Удаление всех данных кабинета"""
        try:
            logger.info(f"Cleaning up data for cabinet {cabinet.id}")
            
            # Удаляем все связанные данные
            deleted_counts = {
                "orders": 0,
                "products": 0,
                "stocks": 0,
                "reviews": 0,
                "sales": 0,
                "cabinet_users": 0
            }
            
            # Удаляем связи пользователей с кабинетом
            from .models_cabinet_users import CabinetUser
            cabinet_users_query = self.db.query(CabinetUser).filter(CabinetUser.cabinet_id == cabinet.id)
            deleted_counts["cabinet_users"] = cabinet_users_query.count()
            cabinet_users_query.delete(synchronize_session=False)
            
            # Удаляем заказы
            orders_query = self.db.query(WBOrder).filter(WBOrder.cabinet_id == cabinet.id)
            deleted_counts["orders"] = orders_query.count()
            orders_query.delete(synchronize_session=False)
            
            # Удаляем товары
            products_query = self.db.query(WBProduct).filter(WBProduct.cabinet_id == cabinet.id)
            deleted_counts["products"] = products_query.count()
            products_query.delete(synchronize_session=False)
            
            # Удаляем остатки
            stocks_query = self.db.query(WBStock).filter(WBStock.cabinet_id == cabinet.id)
            deleted_counts["stocks"] = stocks_query.count()
            stocks_query.delete(synchronize_session=False)
            
            # Удаляем отзывы
            reviews_query = self.db.query(WBReview).filter(WBReview.cabinet_id == cabinet.id)
            deleted_counts["reviews"] = reviews_query.count()
            reviews_query.delete(synchronize_session=False)
            
            # Удаляем продажи
            sales_query = self.db.query(WBSales).filter(WBSales.cabinet_id == cabinet.id)
            deleted_counts["sales"] = sales_query.count()
            sales_query.delete(synchronize_session=False)
            
            # Удаляем сам кабинет
            cabinet_name = cabinet.name
            self.db.delete(cabinet)
            self.db.commit()
            
            logger.info(f"Cabinet {cabinet.id} and all related data removed successfully. "
                       f"Deleted: {deleted_counts}")
            
            return {
                "success": True,
                "cabinet_name": cabinet_name,
                "deleted_counts": deleted_counts
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up cabinet {cabinet.id}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_cabinet_removal_notification(
        self, 
        user_data: Dict[str, Any], 
        cabinet: WBCabinet, 
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Отправка уведомления боту об удалении кабинета"""
        try:
            # Формируем данные для уведомления
            notification_data = {
                "cabinet_id": cabinet.id,
                "cabinet_name": cabinet.name,
                "user_id": user_data["user_id"],
                "telegram_id": user_data["telegram_id"],
                "validation_error": validation_result,
                "removal_reason": "API key invalid or withdrawn",
                "removal_timestamp": cabinet.updated_at.isoformat() if cabinet.updated_at else None
            }
            
            # Ленивый импорт для избежания циклических зависимостей
            from app.features.bot_api.webhook import WebhookSender
            from app.features.bot_api.formatter import BotMessageFormatter
            
            webhook_sender = WebhookSender()
            message_formatter = BotMessageFormatter()
            
            # Формируем сообщение для бота
            message = message_formatter.format_cabinet_removal_notification(notification_data)
            
            # Отправляем webhook
            webhook_result = await webhook_sender.send_cabinet_removal_notification(
                user_data["telegram_id"], 
                notification_data
            )
            
            logger.info(f"Cabinet removal notification sent for cabinet {cabinet.id}: {webhook_result}")
            
            return {
                "success": webhook_result.get("success", False),
                "message": message,
                "webhook_result": webhook_result
            }
            
        except Exception as e:
            logger.error(f"Error sending cabinet removal notification for cabinet {cabinet.id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_all_cabinets(self, max_retries: int = 3) -> Dict[str, Any]:
        """Валидация всех кабинетов с автоматическим удалением невалидных"""
        try:
            logger.info("Starting validation of all cabinets")
            
            # Получаем все кабинеты
            cabinets = self.db.query(WBCabinet).all()
            
            if not cabinets:
                logger.info("No cabinets found for validation")
                return {
                    "success": True,
                    "total_cabinets": 0,
                    "valid_cabinets": 0,
                    "removed_cabinets": 0,
                    "errors": 0
                }
            
            results = {
                "total_cabinets": len(cabinets),
                "valid_cabinets": 0,
                "removed_cabinets": 0,
                "errors": 0,
                "details": []
            }
            
            for cabinet in cabinets:
                try:
                    result = await self.validate_and_cleanup_cabinet(cabinet, max_retries)
                    
                    if result.get("valid", False):
                        results["valid_cabinets"] += 1
                    elif result.get("cabinet_removed", False):
                        results["removed_cabinets"] += 1
                    else:
                        results["errors"] += 1
                    
                    # Получаем пользователей кабинета для деталей
                    from .crud_cabinet_users import CabinetUserCRUD
                    cabinet_user_crud = CabinetUserCRUD()
                    user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
                    
                    results["details"].append({
                        "cabinet_id": cabinet.id,
                        "user_ids": user_ids,
                        "cabinet_name": cabinet.name,
                        "result": result
                    })
                    
                except Exception as e:
                    logger.error(f"Error validating cabinet {cabinet.id}: {e}")
                    results["errors"] += 1
                    
                    # Получаем пользователей кабинета для деталей
                    from .crud_cabinet_users import CabinetUserCRUD
                    cabinet_user_crud = CabinetUserCRUD()
                    user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
                    
                    results["details"].append({
                        "cabinet_id": cabinet.id,
                        "user_ids": user_ids,
                        "cabinet_name": cabinet.name,
                        "error": str(e)
                    })
            
            logger.info(f"Cabinet validation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during cabinet validation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
