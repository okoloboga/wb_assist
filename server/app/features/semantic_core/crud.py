"""
CRUD-операции для агрегированного семантического ядра по кабинету.

Этот слой повторяет интерфейс CompetitorSemanticCoreCRUD, но работает
с моделью CabinetSemanticCore (cabinet_id + category_name).
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from .models import CabinetSemanticCore


class CabinetSemanticCoreCRUD:
    """CRUD операции для CabinetSemanticCore."""

    @staticmethod
    def create(
        db: Session,
        cabinet_id: int,
        category_name: str,
        status: str = "pending",
    ) -> CabinetSemanticCore:
        """
        Создать новую запись агрегированного семантического ядра.
        """
        core = CabinetSemanticCore(
            cabinet_id=cabinet_id,
            category_name=category_name,
            status=status,
        )
        db.add(core)
        db.commit()
        db.refresh(core)
        return core

    @staticmethod
    def get_by_id(db: Session, core_id: int) -> Optional[CabinetSemanticCore]:
        """
        Получить запись семантического ядра по ID.
        """
        return db.query(CabinetSemanticCore).filter(CabinetSemanticCore.id == core_id).first()

    @staticmethod
    def get_by_cabinet_and_category(
        db: Session,
        cabinet_id: int,
        category_name: str,
    ) -> Optional[CabinetSemanticCore]:
        """
        Получить запись семантического ядра по кабинету и названию категории.
        """
        return (
            db.query(CabinetSemanticCore)
            .filter(
                and_(
                    CabinetSemanticCore.cabinet_id == cabinet_id,
                    CabinetSemanticCore.category_name == category_name,
                )
            )
            .first()
        )

    @staticmethod
    def list_completed_by_cabinet(
        db: Session,
        cabinet_id: int,
    ) -> List[CabinetSemanticCore]:
        """
        Получить список всех успешно сгенерированных ядер по кабинету.
        """
        return (
            db.query(CabinetSemanticCore)
            .filter(
                CabinetSemanticCore.cabinet_id == cabinet_id,
                CabinetSemanticCore.status == "completed",
            )
            .order_by(CabinetSemanticCore.category_name)
            .all()
        )

    @staticmethod
    def update_status(
        db: Session,
        core_id: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[CabinetSemanticCore]:
        """
        Обновить статус записи семантического ядра.
        """
        core = db.query(CabinetSemanticCore).filter(CabinetSemanticCore.id == core_id).first()
        if not core:
            return None

        core.status = status
        if error_message is not None:
            core.error_message = error_message

        db.commit()
        db.refresh(core)
        return core

    @staticmethod
    def update_core_data(
        db: Session,
        core_id: int,
        core_data: str,
    ) -> Optional[CabinetSemanticCore]:
        """
        Обновить данные семантического ядра и установить статус "completed".
        """
        core = db.query(CabinetSemanticCore).filter(CabinetSemanticCore.id == core_id).first()
        if not core:
            return None

        core.core_data = core_data
        core.status = "completed"
        core.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(core)
        return core

    @staticmethod
    def reset_semantic_core(
        db: Session,
        core_id: int,
    ) -> Optional[CabinetSemanticCore]:
        """
        Сбросить состояние семантического ядра для повторной генерации.
        """
        core = db.query(CabinetSemanticCore).filter(CabinetSemanticCore.id == core_id).first()
        if not core:
            return None

        core.status = "pending"
        core.core_data = None
        core.error_message = None
        core.completed_at = None

        db.commit()
        db.refresh(core)
        return core




