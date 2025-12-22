"""
CRUD операции для списка игнорируемых nm_id
"""

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from typing import List
import logging

from .models import UserStockIgnoreItem

logger = logging.getLogger(__name__)

class UserStockIgnoreCRUD:
    """CRUD операции для user_stock_ignore_list"""

    @staticmethod
    def get_by_user(db: Session, user_id: int) -> List[int]:
        """Получить список всех nm_id в игнор-листе пользователя."""
        return [item.nm_id for item in db.query(UserStockIgnoreItem.nm_id).filter(UserStockIgnoreItem.user_id == user_id).all()]

    @staticmethod
    def add_items(db: Session, user_id: int, nm_ids: List[int]) -> int:
        """
        Добавляет список nm_id в игнор-лист пользователя, избегая дубликатов.
        Возвращает количество реально добавленных записей.
        """
        if not nm_ids:
            return 0
        
        # Находим nm_id, которые уже есть в списке
        existing_nm_ids = {
            item.nm_id for item in db.query(UserStockIgnoreItem.nm_id).filter(
                UserStockIgnoreItem.user_id == user_id,
                UserStockIgnoreItem.nm_id.in_(nm_ids)
            ).all()
        }
        
        # Определяем новые nm_id, которых еще нет в списке
        new_nm_ids = [nm_id for nm_id in set(nm_ids) if nm_id not in existing_nm_ids]
        
        if not new_nm_ids:
            return 0
            
        # Добавляем только новые
        items_to_insert = [UserStockIgnoreItem(user_id=user_id, nm_id=nm_id) for nm_id in new_nm_ids]
        
        db.bulk_save_objects(items_to_insert)
        db.commit()
        
        return len(new_nm_ids)

    @staticmethod
    def remove_item(db: Session, user_id: int, nm_id: int) -> bool:
        """Удаляет один nm_id из игнор-листа пользователя."""
        item = db.query(UserStockIgnoreItem).filter(
            UserStockIgnoreItem.user_id == user_id,
            UserStockIgnoreItem.nm_id == nm_id
        ).first()

        if item:
            db.delete(item)
            db.commit()
            return True
        return False

    @staticmethod
    def is_ignored(db: Session, user_id: int, nm_id: int) -> bool:
        """Проверяет, находится ли nm_id в игнор-листе пользователя."""
        return db.query(UserStockIgnoreItem).filter(
            UserStockIgnoreItem.user_id == user_id,
            UserStockIgnoreItem.nm_id == nm_id
        ).first() is not None
