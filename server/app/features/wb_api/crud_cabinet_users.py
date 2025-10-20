from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from .models_cabinet_users import CabinetUser
from .models import WBCabinet


class CabinetUserCRUD:
    """CRUD операции для связи пользователей с кабинетами"""
    
    def add_user_to_cabinet(self, db: Session, cabinet_id: int, user_id: int) -> CabinetUser:
        """Добавить пользователя к кабинету"""
        cabinet_user = CabinetUser(
            cabinet_id=cabinet_id,
            user_id=user_id,
            is_active=True
        )
        db.add(cabinet_user)
        db.commit()
        db.refresh(cabinet_user)
        return cabinet_user
    
    def get_cabinet_users(self, db: Session, cabinet_id: int) -> List[int]:
        """Получить всех пользователей кабинета"""
        cabinet_users = db.query(CabinetUser).filter(
            and_(
                CabinetUser.cabinet_id == cabinet_id,
                CabinetUser.is_active == True
            )
        ).all()
        return [cu.user_id for cu in cabinet_users]
    
    def get_user_cabinets(self, db: Session, user_id: int) -> List[int]:
        """Получить все кабинеты пользователя"""
        cabinet_users = db.query(CabinetUser).filter(
            and_(
                CabinetUser.user_id == user_id,
                CabinetUser.is_active == True
            )
        ).all()
        return [cu.cabinet_id for cu in cabinet_users]
    
    def is_user_in_cabinet(self, db: Session, cabinet_id: int, user_id: int) -> bool:
        """Проверить, есть ли пользователь в кабинете"""
        cabinet_user = db.query(CabinetUser).filter(
            and_(
                CabinetUser.cabinet_id == cabinet_id,
                CabinetUser.user_id == user_id,
                CabinetUser.is_active == True
            )
        ).first()
        return cabinet_user is not None
    
    def find_cabinet_by_api_key(self, db: Session, api_key: str) -> Optional[WBCabinet]:
        """Найти кабинет по API ключу"""
        return db.query(WBCabinet).filter(WBCabinet.api_key == api_key).first()
    
    def remove_user_from_cabinet(self, db: Session, cabinet_id: int, user_id: int) -> bool:
        """Удалить пользователя из кабинета"""
        cabinet_user = db.query(CabinetUser).filter(
            and_(
                CabinetUser.cabinet_id == cabinet_id,
                CabinetUser.user_id == user_id
            )
        ).first()
        
        if cabinet_user:
            cabinet_user.is_active = False
            db.commit()
            return True
        return False
