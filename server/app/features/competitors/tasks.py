"""
Celery задачи для скрапинга конкурентов Wildberries
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime
from celery import current_task
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.celery_app import celery_app
from .models import CompetitorLink
from .crud import CompetitorLinkCRUD, CompetitorProductCRUD
from .scraper import scrape_competitor

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 300})
def scrape_competitor_task(self, competitor_link_id: int) -> Dict[str, Any]:
    """
    Задача скрапинга данных конкурента.
    
    Args:
        competitor_link_id: ID записи CompetitorLink
        
    Returns:
        Словарь с результатом выполнения
    """
    db = None
    try:
        logger.info(f"Начало скрапинга конкурента {competitor_link_id}")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем запись конкурента
        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_link_id)
        if not competitor:
            logger.error(f"Конкурент {competitor_link_id} не найден")
            return {"status": "error", "message": "Конкурент не найден"}
        
        # Обновляем статус на "scraping"
        CompetitorLinkCRUD.update_status(db, competitor_link_id, "scraping")
        
        # Получаем лимит товаров из env
        max_products = int(os.getenv("COMPETITOR_MAX_PRODUCTS_PER_LINK", "30"))
        
        # Запускаем скрапинг
        logger.info(f"Запуск скрапинга для {competitor.competitor_url}")
        scraping_result = scrape_competitor(competitor.competitor_url, max_products=max_products)
        
        if scraping_result["success_count"] == 0:
            # Если не удалось собрать ни одного товара
            error_msg = f"Не удалось собрать данные: найдено {len(scraping_result.get('products', []))} товаров"
            CompetitorLinkCRUD.update_status(
                db, 
                competitor_link_id, 
                "error",
                error_message=error_msg
            )
            logger.error(f"Скрапинг конкурента {competitor_link_id} завершился с ошибкой: {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # Удаляем старые товары перед добавлением новых (полное обновление)
        CompetitorProductCRUD.delete_by_competitor(db, competitor_link_id)
        
        # Сохраняем товары в БД
        products_saved = 0
        competitor_name = scraping_result.get("competitor_name")
        
        for product_data in scraping_result.get("products", []):
            try:
                CompetitorProductCRUD.create_or_update(db, competitor_link_id, product_data)
                products_saved += 1
            except Exception as e:
                logger.error(f"Ошибка сохранения товара {product_data.get('nm_id')}: {e}")
                continue
        
        # Обновляем данные конкурента после успешного скрапинга
        CompetitorLinkCRUD.update_after_scraping(
            db,
            competitor_link_id,
            competitor_name or "Неизвестный",
            products_saved
        )
        
        logger.info(f"Скрапинг конкурента {competitor_link_id} завершен успешно: {products_saved} товаров")
        return {
            "status": "success",
            "competitor_id": competitor_link_id,
            "products_saved": products_saved,
            "competitor_name": competitor_name
        }
        
    except Exception as e:
        logger.error(f"Ошибка скрапинга конкурента {competitor_link_id}: {e}", exc_info=True)
        
        # Обновляем статус на "error"
        if db:
            try:
                CompetitorLinkCRUD.update_status(
                    db,
                    competitor_link_id,
                    "error",
                    error_message=str(e)
                )
            except Exception as update_error:
                logger.error(f"Ошибка обновления статуса: {update_error}")
        
        # Retry логика
        if self.request.retries < self.max_retries:
            logger.info(f"Повторная попытка скрапинга конкурента {competitor_link_id} через 5 минут")
            raise self.retry(countdown=300, exc=e)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if db:
            db.close()


@celery_app.task(bind=True, max_retries=3)
def update_all_competitors_task(self) -> Dict[str, Any]:
    """
    Периодическая задача обновления всех конкурентов.
    Запускается раз в сутки через Celery Beat.
    Распределяет время обновления по cabinet_id.
    
    Returns:
        Словарь с результатом выполнения
    """
    db = None
    try:
        logger.info("Начало обновления всех конкурентов")
        
        # Получаем сессию БД
        db = next(get_db())
        
        # Получаем конкурентов, готовых к обновлению
        competitors = CompetitorLinkCRUD.get_ready_for_update(db, limit=50)
        
        if not competitors:
            logger.info("Нет конкурентов, готовых к обновлению")
            return {
                "status": "success",
                "updated_count": 0,
                "message": "Нет конкурентов для обновления"
            }
        
        logger.info(f"Найдено {len(competitors)} конкурентов для обновления")
        
        # Запускаем скрапинг для каждого конкурента
        updated_count = 0
        for competitor in competitors:
            try:
                scrape_competitor_task.delay(competitor.id)
                updated_count += 1
                logger.info(f"Запущено обновление конкурента {competitor.id}")
            except Exception as e:
                logger.error(f"Ошибка запуска обновления конкурента {competitor.id}: {e}")
                continue
        
        logger.info(f"Обновление конкурентов: запущено {updated_count} задач")
        return {
            "status": "success",
            "updated_count": updated_count,
            "total_found": len(competitors)
        }
        
    except Exception as e:
        logger.error(f"Ошибка обновления конкурентов: {e}", exc_info=True)
        
        if self.request.retries < self.max_retries:
            logger.info("Повторная попытка обновления конкурентов через 1 час")
            raise self.retry(countdown=3600, exc=e)
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if db:
            db.close()

