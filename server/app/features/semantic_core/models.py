"""
Модели базы данных для агрегированного семантического ядра по кабинету.

В отличие от CompetitorSemanticCore, эта сущность привязана не к одному
конкуренту, а к всему кабинету WB и конкретной категории.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Index, func

from app.core.database import Base


class CabinetSemanticCore(Base):
    """
    Агрегированное семантическое ядро по кабинету и категории.

    Одна запись соответствует одному кабинету WB и одной категории, в которую
    входят товары всех конкурентов этого кабинета.
    """

    __tablename__ = "cabinet_semantic_cores"

    id = Column(Integer, primary_key=True, index=True)

    # Кабинет, для которого собрано ядро
    cabinet_id = Column(Integer, ForeignKey("wb_cabinets.id", ondelete="CASCADE"), nullable=False, index=True)

    # Название категории товаров (как в competitor_products / wb_products)
    category_name = Column(String(255), nullable=False)

    # Сырые данные ядра (отформатированный текст от GPT)
    core_data = Column(Text, nullable=True)

    # Статус генерации: pending, processing, completed, error
    status = Column(String(20), nullable=False, default="pending")

    # Описание ошибки (если статус error)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Одно ядро на кабинет + категорию
        UniqueConstraint("cabinet_id", "category_name", name="uq_cabinet_category_semantic_core"),
        # Индекс для быстрых выборок по кабинету и категории
        Index("idx_cabinet_semantic_core_cabinet_category", "cabinet_id", "category_name"),
    )

    def __repr__(self) -> str:
        return f"<CabinetSemanticCore id={self.id} cabinet_id={self.cabinet_id} category='{self.category_name}'>"


