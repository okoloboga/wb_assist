"""
CRUD операции для работы с конкурентами
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func as sql_func
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import logging
import os

from .models import CompetitorLink, CompetitorProduct, CompetitorSemanticCore

logger = logging.getLogger(__name__)


class CompetitorLinkCRUD:
    """CRUD операции для competitor_links"""
    
    @staticmethod
    def create(
        db: Session,
        cabinet_id: int,
        competitor_url: str
    ) -> CompetitorLink:
        """Создать новую ссылку конкурента"""
        competitor = CompetitorLink(
            cabinet_id=cabinet_id,
            competitor_url=competitor_url,
            status='pending'
        )
        db.add(competitor)
        db.commit()
        db.refresh(competitor)
        return competitor
    
    @staticmethod
    def get_by_id(db: Session, competitor_id: int) -> Optional[CompetitorLink]:
        """Получить конкурента по ID"""
        return db.query(CompetitorLink).filter(CompetitorLink.id == competitor_id).first()
    
    @staticmethod
    def get_by_cabinet(
        db: Session,
        cabinet_id: int,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 10
    ) -> List[CompetitorLink]:
        """Получить список конкурентов кабинета с пагинацией"""
        query = db.query(CompetitorLink).filter(CompetitorLink.cabinet_id == cabinet_id)
        
        if status:
            query = query.filter(CompetitorLink.status == status)
        
        return query.order_by(desc(CompetitorLink.created_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def count_by_cabinet(db: Session, cabinet_id: int, status: Optional[str] = None) -> int:
        """Подсчитать количество конкурентов кабинета"""
        query = db.query(CompetitorLink).filter(CompetitorLink.cabinet_id == cabinet_id)
        
        if status:
            query = query.filter(CompetitorLink.status == status)
        
        return query.count()
    
    @staticmethod
    def check_duplicate(db: Session, cabinet_id: int, competitor_url: str) -> bool:
        """Проверить, существует ли уже такой конкурент в кабинете"""
        existing = db.query(CompetitorLink).filter(
            and_(
                CompetitorLink.cabinet_id == cabinet_id,
                CompetitorLink.competitor_url == competitor_url
            )
        ).first()
        return existing is not None
    
    @staticmethod
    def check_limit(db: Session, cabinet_id: int) -> bool:
        """Проверить, не превышен ли лимит конкурентов для кабинета"""
        max_links = int(os.getenv("COMPETITOR_MAX_LINKS_PER_CABINET", "10"))
        current_count = db.query(CompetitorLink).filter(
            CompetitorLink.cabinet_id == cabinet_id
        ).count()
        return current_count < max_links
    
    @staticmethod
    def update_status(
        db: Session,
        competitor_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[CompetitorLink]:
        """Обновить статус конкурента"""
        competitor = db.query(CompetitorLink).filter(CompetitorLink.id == competitor_id).first()
        if not competitor:
            return None
        
        competitor.status = status
        if error_message:
            competitor.error_message = error_message
        competitor.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(competitor)
        return competitor
    
    @staticmethod
    def update_after_scraping(
        db: Session,
        competitor_id: int,
        competitor_name: str,
        products_count: int
    ) -> Optional[CompetitorLink]:
        """Обновить данные конкурента после успешного скрапинга"""
        competitor = db.query(CompetitorLink).filter(CompetitorLink.id == competitor_id).first()
        if not competitor:
            return None
        
        competitor.competitor_name = competitor_name
        competitor.products_count = products_count
        competitor.status = 'completed'
        competitor.last_scraped_at = datetime.now(timezone.utc)
        competitor.updated_at = datetime.now(timezone.utc)
        
        # Вычисляем время следующего обновления
        competitor.next_update_at = CompetitorLinkCRUD._calculate_next_update_time(competitor.cabinet_id)
        
        db.commit()
        db.refresh(competitor)
        return competitor
    
    @staticmethod
    def _calculate_next_update_time(cabinet_id: int) -> datetime:
        """Вычислить время следующего обновления на основе cabinet_id"""
        import hashlib
        
        # Используем хеш cabinet_id для получения смещения
        hash_value = int(hashlib.md5(str(cabinet_id).encode()).hexdigest(), 16)
        spread_hours = int(os.getenv("COMPETITOR_UPDATE_SPREAD_HOURS", "2"))
        base_hour = int(os.getenv("COMPETITOR_UPDATE_BASE_HOUR", "0"))
        
        # Смещение в часах от базового времени
        offset_hours = hash_value % spread_hours
        
        next_update = datetime.now(timezone.utc).replace(hour=base_hour, minute=0, second=0, microsecond=0)
        next_update += timedelta(hours=offset_hours, days=1)
        
        return next_update
    
    @staticmethod
    def get_ready_for_update(db: Session, limit: int = 10) -> List[CompetitorLink]:
        """Получить конкурентов, готовых к обновлению"""
        now = datetime.now(timezone.utc)
        return db.query(CompetitorLink).filter(
            and_(
                CompetitorLink.status == 'completed',
                CompetitorLink.next_update_at <= now
            )
        ).limit(limit).all()

    @staticmethod
    def delete(db: Session, competitor_id: int) -> bool:
        """Удалить конкурента по ID"""
        competitor = db.query(CompetitorLink).filter(CompetitorLink.id == competitor_id).first()
        if competitor:
            db.delete(competitor)
            db.commit()
            return True
        return False


class CompetitorProductCRUD:
    """CRUD операции для competitor_products"""

    @staticmethod
    def get_by_id(db: Session, product_id: int) -> Optional[CompetitorProduct]:
        """Получить товар по его уникальному ID"""
        return db.query(CompetitorProduct).filter(CompetitorProduct.id == product_id).first()
    
    @staticmethod
    def create_or_update(
        db: Session,
        competitor_link_id: int,
        product_data: Dict[str, Any]
    ) -> CompetitorProduct:
        """Создать или обновить товар конкурента"""
        nm_id = str(product_data.get('nm_id', ''))
        
        existing = db.query(CompetitorProduct).filter(
            and_(
                CompetitorProduct.competitor_link_id == competitor_link_id,
                CompetitorProduct.nm_id == nm_id
            )
        ).first()
        
        if existing:
            # Обновляем существующий товар
            existing.product_url = product_data.get('product_url', existing.product_url)
            existing.name = product_data.get('name')
            existing.current_price = product_data.get('current_price')
            existing.original_price = product_data.get('original_price')
            existing.brand = product_data.get('brand')
            existing.category = product_data.get('category')
            existing.rating = product_data.get('rating')
            existing.description = product_data.get('description')
            existing.scraped_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Создаем новый товар
            new_product = CompetitorProduct(
                competitor_link_id=competitor_link_id,
                nm_id=nm_id,
                product_url=product_data.get('product_url', ''),
                name=product_data.get('name'),
                current_price=product_data.get('current_price'),
                original_price=product_data.get('original_price'),
                brand=product_data.get('brand'),
                category=product_data.get('category'),
                rating=product_data.get('rating'),
                description=product_data.get('description'),
                scraped_at=datetime.now(timezone.utc)
            )
            db.add(new_product)
            db.commit()
            db.refresh(new_product)
            return new_product
    
    @staticmethod
    def get_by_competitor(
        db: Session,
        competitor_link_id: int,
        offset: int = 0,
        limit: int = 10
    ) -> List[CompetitorProduct]:
        """Получить товары конкурента с пагинацией"""
        return db.query(CompetitorProduct).filter(
            CompetitorProduct.competitor_link_id == competitor_link_id
        ).order_by(desc(CompetitorProduct.scraped_at)).offset(offset).limit(limit).all()
    
    @staticmethod
    def count_by_competitor(db: Session, competitor_link_id: int) -> int:
        """Подсчитать количество товаров конкурента"""
        return db.query(CompetitorProduct).filter(
            CompetitorProduct.competitor_link_id == competitor_link_id
        ).count()
    
    @staticmethod
    def delete_by_competitor(db: Session, competitor_link_id: int) -> int:
        """Удалить все товары конкурента (перед обновлением)"""
        deleted = db.query(CompetitorProduct).filter(
            CompetitorProduct.competitor_link_id == competitor_link_id
        ).delete()
        db.commit()
        return deleted

    @staticmethod
    def get_distinct_categories_by_competitor(db: Session, competitor_link_id: int) -> List[str]:
        """Получить список уникальных категорий для товаров конкурента"""
        categories = db.query(CompetitorProduct.category)\
            .filter(CompetitorProduct.competitor_link_id == competitor_link_id)\
            .filter(CompetitorProduct.category.isnot(None))\
            .distinct()\
            .order_by(CompetitorProduct.category)\
            .all()
        return [c[0] for c in categories if c[0]] # Фильтруем пустые строки

    @staticmethod
    def get_price_range_by_competitor(db: Session, competitor_link_id: int) -> Dict[str, float]:
        """Получить диапазон цен (min, max) для товаров конкурента"""
        price_range = db.query(
            sql_func.min(CompetitorProduct.current_price),
            sql_func.max(CompetitorProduct.current_price)
        ).filter(
            CompetitorProduct.competitor_link_id == competitor_link_id
        ).first()
        
        return {
            "min_price": float(price_range[0]) if price_range and price_range[0] is not None else 0.0,
            "max_price": float(price_range[1]) if price_range and price_range[1] is not None else 0.0
        }

    @staticmethod
    def get_average_rating_by_competitor(db: Session, competitor_link_id: int) -> float:
        """Получить средний рейтинг для товаров конкурента"""
        avg_rating = db.query(
            sql_func.avg(CompetitorProduct.rating)
        ).filter(
            CompetitorProduct.competitor_link_id == competitor_link_id,
            CompetitorProduct.rating.isnot(None)
        ).scalar()
        
        return float(avg_rating) if avg_rating is not None else 0.0


class CompetitorSemanticCoreCRUD:
    """CRUD операции для CompetitorSemanticCore"""

    @staticmethod
    def create(
        db: Session,
        competitor_link_id: int,
        category_name: str,
        status: str = 'pending'
    ) -> CompetitorSemanticCore:
        """Создать новую запись семантического ядра"""
        semantic_core = CompetitorSemanticCore(
            competitor_link_id=competitor_link_id,
            category_name=category_name,
            status=status
        )
        db.add(semantic_core)
        db.commit()
        db.refresh(semantic_core)
        return semantic_core

    @staticmethod
    def get_by_id(db: Session, semantic_core_id: int) -> Optional[CompetitorSemanticCore]:
        """Получить запись семантического ядра по ID"""
        return db.query(CompetitorSemanticCore).filter(CompetitorSemanticCore.id == semantic_core_id).first()

    @staticmethod
    def update_status(
        db: Session,
        semantic_core_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[CompetitorSemanticCore]:
        """Обновить статус записи семантического ядра"""
        semantic_core = db.query(CompetitorSemanticCore).filter(CompetitorSemanticCore.id == semantic_core_id).first()
        if not semantic_core:
            return None
        
        semantic_core.status = status
        if error_message:
            semantic_core.error_message = error_message
        db.commit()
        db.refresh(semantic_core)
        return semantic_core

    @staticmethod
    def update_core_data(
        db: Session,
        semantic_core_id: int,
        core_data: str
    ) -> Optional[CompetitorSemanticCore]:
        """Обновить данные семантического ядра и установить статус "completed" """
        semantic_core = db.query(CompetitorSemanticCore).filter(CompetitorSemanticCore.id == semantic_core_id).first()
        if not semantic_core:
            return None
        
        semantic_core.core_data = core_data
        semantic_core.status = "completed"
        semantic_core.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(semantic_core)
        return semantic_core


