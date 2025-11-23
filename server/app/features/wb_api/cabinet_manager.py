"""
Cabinet Manager - управление кабинетами WB с автоматическим удалением при невалидном API
"""

import logging
import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
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
            
            try:
                validation_result = await client.validate_api_key()
            except Exception as e:
                # Timeout и другие сетевые ошибки - НЕ удаляем кабинет!
                logger.warning(f"API validation error for cabinet {cabinet.id}: {e}")
                return {
                    "success": True,  # НЕ False!
                    "valid": True,    # НЕ False!
                    "message": f"Validation error (timeout/network): {str(e)}",
                    "attempts": 1,
                    "warning": True
                }
            
            if validation_result.get("valid", False):
                logger.info(f"API key validation successful for cabinet {cabinet.id}")
                return {
                    "success": True,
                    "valid": True,
                    "message": "API key is valid",
                    "attempts": 1
                }
            
            # Если API невалиден (статус 401), удаляем кабинет
            logger.error(f"API validation failed for cabinet {cabinet.id}. Removing cabinet.")
            
            # КРИТИЧНО: Получаем полные данные пользователей ДО удаления кабинета
            from .crud_cabinet_users import CabinetUserCRUD
            cabinet_user_crud = CabinetUserCRUD()
            user_ids = cabinet_user_crud.get_cabinet_users(self.db, cabinet.id)
            
            # Сохраняем полные данные пользователей с telegram_id ДО удаления
            users_data: List[Dict[str, Any]] = []
            for user_id in user_ids:
                user_data = self._get_user_data(user_id)
                if user_data and user_data.get("telegram_id"):
                    users_data.append(user_data)
            
            # Сохраняем информацию о кабинете ДО удаления
            cabinet_info = {
                "id": cabinet.id,
                "name": cabinet.name or "Неизвестный кабинет",
                "api_key_preview": cabinet.api_key[:10] + "..." if cabinet.api_key and len(cabinet.api_key) > 10 else "N/A"
            }
            
            if not users_data:
                logger.warning(f"No users with telegram_id found for cabinet {cabinet.id}, proceeding with deletion")
            
            # Удаляем кабинет и все связанные данные
            cleanup_result = await self._cleanup_cabinet_data(cabinet)
            
            # КРИТИЧНО: Логируем факт удаления ВСЕГДА, независимо от отправки уведомлений
            deleted_counts = cleanup_result.get("deleted_counts", {})
            logger.error(
                f"🗑️ CABINET REMOVED - ID: {cabinet_info['id']}, "
                f"Name: {cabinet_info['name']}, "
                f"Users affected: {len(users_data)}, "
                f"Deleted data: orders={deleted_counts.get('orders', 0)}, "
                f"products={deleted_counts.get('products', 0)}, "
                f"stocks={deleted_counts.get('stocks', 0)}, "
                f"reviews={deleted_counts.get('reviews', 0)}, "
                f"sales={deleted_counts.get('sales', 0)}, "
                f"Reason: API key invalid (status {validation_result.get('status_code', 'N/A')}), "
                f"Error: {validation_result.get('message', 'N/A')}"
            )
            
            # Отправляем уведомления всем пользователям кабинета
            notification_results = []
            if users_data and cleanup_result.get("success", False):
                for user_data in users_data:
                    try:
                        notification_result = await self._send_cabinet_removal_notification(
                            user_data, 
                            cabinet_info, 
                            validation_result,
                            cleanup_result
                        )
                        notification_results.append(notification_result)
                    except Exception as notify_error:
                        # Логируем ошибку отправки, но не прерываем процесс
                        logger.error(
                            f"Failed to send notification to user {user_data.get('user_id')} "
                            f"(telegram_id: {user_data.get('telegram_id')}): {notify_error}",
                            exc_info=True
                        )
                        notification_results.append({
                            "success": False,
                            "user_id": user_data.get("user_id"),
                            "telegram_id": user_data.get("telegram_id"),
                            "error": str(notify_error)
                        })
            
            # Логируем результаты отправки уведомлений
            successful_notifications = sum(1 for r in notification_results if r.get("success", False))
            logger.info(
                f"📨 Cabinet removal notifications: {successful_notifications}/{len(notification_results)} "
                f"sent successfully for cabinet {cabinet_info['id']}"
            )
            
            return {
                "success": True,
                "valid": False,
                "message": "API key invalid, cabinet removed",
                "attempts": 1,
                "cabinet_removed": cleanup_result["success"],
                "cabinet_id": cabinet_info["id"],
                "cabinet_name": cabinet_info["name"],
                "users_affected": len(users_data),
                "notifications_sent": successful_notifications,
                "notifications_total": len(notification_results),
                "validation_error": validation_result,
                "deleted_counts": cleanup_result.get("deleted_counts", {})
            }
            
        except Exception as e:
            logger.error(
                f"Unexpected error during cabinet validation for cabinet {cabinet.id if hasattr(cabinet, 'id') else 'unknown'}: {e}",
                exc_info=True
            )
            return {
                "success": False,
                "valid": False,
                "message": f"Unexpected validation error: {str(e)}",
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
            logger.error(f"Error cleaning up cabinet {cabinet.id}: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _send_telegram_message_direct(
        self, 
        telegram_id: int, 
        text: str
    ) -> Dict[str, Any]:
        """
        Прямая отправка сообщения через Telegram Bot API
        
        Args:
            telegram_id: Telegram ID пользователя
            text: Текст сообщения
            
        Returns:
            Dict с результатом отправки
        """
        try:
            bot_token = os.getenv("BOT_TOKEN", "").strip()
            if not bot_token:
                logger.warning("BOT_TOKEN not found in environment variables, cannot send Telegram message")
                return {"ok": False, "description": "BOT_TOKEN not configured"}
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    json=data, 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("ok"):
                        logger.info(f"✅ Telegram message sent to {telegram_id}")
                    else:
                        logger.warning(
                            f"❌ Failed to send Telegram message to {telegram_id}: "
                            f"{result.get('description', 'Unknown error')}"
                        )
                    
                    return result
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout sending Telegram message to {telegram_id}")
            return {"ok": False, "description": "Timeout"}
        except Exception as e:
            logger.error(f"Error sending Telegram message to {telegram_id}: {e}", exc_info=True)
            return {"ok": False, "description": str(e)}
    
    async def _send_cabinet_removal_notification(
        self, 
        user_data: Dict[str, Any], 
        cabinet_info: Dict[str, Any],
        validation_result: Dict[str, Any],
        cleanup_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Отправка уведомления пользователю об удалении кабинета напрямую в Telegram
        
        Args:
            user_data: Данные пользователя (user_id, telegram_id, etc.)
            cabinet_info: Информация о кабинете (id, name)
            validation_result: Результат валидации API ключа
            cleanup_result: Результат удаления данных
            
        Returns:
            Dict с результатом отправки
        """
        try:
            telegram_id = user_data.get("telegram_id")
            if not telegram_id:
                logger.warning(f"No telegram_id for user {user_data.get('user_id')}")
                return {"success": False, "error": "No telegram_id"}
            
            # Формируем детальное сообщение с причиной удаления
            from app.features.bot_api.formatter import BotMessageFormatter
            message_formatter = BotMessageFormatter()
            
            # Формируем данные для форматирования
            notification_data = {
                "cabinet_id": cabinet_info.get("id"),
                "cabinet_name": cabinet_info.get("name", "Неизвестный кабинет"),
                "user_id": user_data.get("user_id"),
                "telegram_id": telegram_id,
                "validation_error": validation_result,
                "removal_reason": self._get_removal_reason(validation_result),
                "deleted_counts": cleanup_result.get("deleted_counts", {})
            }
            
            # Формируем сообщение
            message = message_formatter.format_cabinet_removal_notification(notification_data)
            
            # Отправляем напрямую через Telegram Bot API
            result = await self._send_telegram_message_direct(telegram_id, message)
            
            success = result.get("ok", False)
            
            if success:
                logger.info(
                    f"✅ Cabinet removal notification sent to user {user_data.get('user_id')} "
                    f"(telegram_id: {telegram_id}) for cabinet {cabinet_info.get('id')}"
                )
            else:
                logger.warning(
                    f"❌ Failed to send cabinet removal notification to user {user_data.get('user_id')} "
                    f"(telegram_id: {telegram_id}): {result.get('description', 'Unknown error')}"
                )
            
            return {
                "success": success,
                "user_id": user_data.get("user_id"),
                "telegram_id": telegram_id,
                "message": message,
                "telegram_result": result
            }
            
        except Exception as e:
            logger.error(
                f"Error sending cabinet removal notification to user {user_data.get('user_id', 'unknown')}: {e}",
                exc_info=True
            )
            return {
                "success": False,
                "user_id": user_data.get("user_id"),
                "telegram_id": user_data.get("telegram_id"),
                "error": str(e)
            }
    
    def _get_removal_reason(self, validation_result: Dict[str, Any]) -> str:
        """
        Получить понятную причину удаления кабинета
        
        Args:
            validation_result: Результат валидации API ключа
            
        Returns:
            Строка с причиной удаления
        """
        status_code = validation_result.get("status_code")
        message = validation_result.get("message", "")
        error_code = validation_result.get("error_code", "")
        
        if status_code == 401:
            message_lower = message.lower() if message else ""
            if "unauthorized" in message_lower or "invalid" in message_lower:
                return "API ключ недействителен или отозван"
            elif "expired" in message_lower:
                return "API ключ истек"
            else:
                return f"Ошибка авторизации (401): {message}"
        elif error_code:
            return f"Ошибка API: {error_code} - {message}"
        else:
            return f"API ключ недействителен: {message}"
    
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
                    
                    # Сохраняем детали результата
                    results["details"].append({
                        "cabinet_id": result.get("cabinet_id", cabinet.id),
                        "cabinet_name": result.get("cabinet_name", cabinet.name),
                        "users_affected": result.get("users_affected", 0),
                        "notifications_sent": result.get("notifications_sent", 0),
                        "result": result
                    })
                    
                except Exception as e:
                    logger.error(f"Error validating cabinet {cabinet.id}: {e}", exc_info=True)
                    results["errors"] += 1
                    
                    results["details"].append({
                        "cabinet_id": cabinet.id,
                        "cabinet_name": cabinet.name,
                        "error": str(e)
                    })
            
            logger.info(f"Cabinet validation completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during cabinet validation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
