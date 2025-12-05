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
from .models import CompetitorLink, CompetitorProduct, CompetitorSemanticCore
from ..wb_api.models import CabinetUser
from .crud import CompetitorLinkCRUD, CompetitorProductCRUD, CompetitorSemanticCoreCRUD
from .scraper import scrape_competitor
import requests # New import for making HTTP requests

logger = logging.getLogger(__name__)


def send_semantic_core_completion_notification(semantic_core_id: int, status: str, competitor_name: str, category_name: str, error_message: str = None):
    """Отправляет уведомление о завершении генерации семантического ядра."""
    from ...features.user.crud import UserCRUD
    from ...core.database import get_db

    db = next(get_db())
    try:
        semantic_core_entry = CompetitorSemanticCoreCRUD.get_by_id(db, semantic_core_id)
        if not semantic_core_entry:
            logger.error(f"send_semantic_core_completion_notification: CompetitorSemanticCore with id {semantic_core_id} not found.")
            return

        competitor_link = CompetitorLinkCRUD.get_by_id(db, semantic_core_entry.competitor_link_id)
        if not competitor_link:
            logger.error(f"send_semantic_core_completion_notification: CompetitorLink with id {semantic_core_entry.competitor_link_id} not found.")
            return

        cabinet_user = db.query(CabinetUser).filter(CabinetUser.cabinet_id == competitor_link.cabinet_id).first()
        if not cabinet_user:
            logger.error(f"send_semantic_core_completion_notification: CabinetUser not found for cabinet_id {competitor_link.cabinet_id}")
            return
        user = UserCRUD(db).get_user_by_id(cabinet_user.user_id)
        if not user or not user.bot_webhook_url:
            logger.warning(f"send_semantic_core_completion_notification: User or webhook_url not found for cabinet_id {competitor_link.cabinet_id}")
            return

        if status == "success":
            telegram_text = f"✅ Семантическое ядро для конкурента '{competitor_name}' по категории '{category_name}' готово."
        else:
            telegram_text = f"❌ Ошибка генерации семантического ядра для конкурента '{competitor_name}' по категории '{category_name}'.\n\nПричина: {error_message}"

        payload = {
            "telegram_id": user.telegram_id,
            "type": "semantic_core_ready",
            "telegram_text": telegram_text,
            "data": {
                "semantic_core_id": semantic_core_id,
                "status": status,
                "competitor_name": competitor_name,
                "category_name": category_name,
                "error_message": error_message,
                "core": semantic_core_entry.core_data if status == "success" else None
            }
        }
        
        try:
            requests.post(user.bot_webhook_url, json=payload, timeout=10)
            logger.info(f"Sent semantic core completion notification for semantic_core_id {semantic_core_id} to {user.bot_webhook_url}")
        except requests.RequestException as e:
            logger.error(f"Failed to send semantic core completion notification for semantic_core_id {semantic_core_id}: {e}")

    finally:
        db.close()


def send_scraping_completion_notification(competitor_link_id: int, status: str, competitor_name: str, products_saved: int, error_message: str = None):
    """Отправляет уведомление о завершении скрапинга."""
    from ...features.user.crud import UserCRUD
    from ...core.database import get_db

    db = next(get_db())
    try:
        competitor_link = CompetitorLinkCRUD.get_by_id(db, competitor_link_id)
        if not competitor_link:
            logger.error(f"send_scraping_completion_notification: CompetitorLink with id {competitor_link_id} not found.")
            return

        cabinet_user = db.query(CabinetUser).filter(CabinetUser.cabinet_id == competitor_link.cabinet_id).first()
        if not cabinet_user:
            logger.error(f"send_scraping_completion_notification: CabinetUser not found for cabinet_id {competitor_link.cabinet_id}")
            return
        user = UserCRUD(db).get_user_by_id(cabinet_user.user_id)
        if not user or not user.bot_webhook_url:
            logger.warning(f"send_scraping_completion_notification: User or webhook_url not found for cabinet_id {competitor_link.cabinet_id}")
            return

        if status == "success":
            # Получаем дополнительную информацию для сводки
            categories = CompetitorProductCRUD.get_distinct_categories_by_competitor(db, competitor_link_id)
            price_range = CompetitorProductCRUD.get_price_range_by_competitor(db, competitor_link_id)
            avg_rating = CompetitorProductCRUD.get_average_rating_by_competitor(db, competitor_link_id)

            telegram_text = f"✅ Сбор данных по конкуренту '{competitor_name}' завершен.\n\n"
            telegram_text += f"📊 Краткая сводка:\n"
            telegram_text += f"  - Собрано товаров: {products_saved}\n"
            if categories:
                telegram_text += f"  - Категории: {', '.join(categories[:3])}"
                if len(categories) > 3:
                    telegram_text += f" и еще {len(categories) - 3}\n"
                else:
                    telegram_text += "\n"
            if price_range['min_price'] > 0:
                telegram_text += f"  - Диапазон цен: {price_range['min_price']:.0f} - {price_range['max_price']:.0f} ₽\n"
            if avg_rating > 0:
                telegram_text += f"  - Средний рейтинг: {avg_rating:.1f} ⭐\n"
        else:
            telegram_text = f"❌ Ошибка сбора данных по конкуренту '{competitor_name}'.\n\nПричина: {error_message}"

        payload = {
            "telegram_id": user.telegram_id,
            "type": "scraping_completed",
            "telegram_text": telegram_text,
            "data": {
                "competitor_id": competitor_link_id,
                "status": status,
                "competitor_name": competitor_name,
                "products_saved": products_saved,
                "error_message": error_message
            }
        }
        
        try:
            requests.post(user.bot_webhook_url, json=payload, timeout=10)
            logger.info(f"Sent scraping completion notification for competitor {competitor_link_id} to {user.bot_webhook_url}")
        except requests.RequestException as e:
            logger.error(f"Failed to send scraping completion notification for competitor {competitor_link_id}: {e}")

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 300})
def scrape_competitor_task(self, competitor_link_id: int) -> Dict[str, Any]:
    """
    Задача скрапинга данных конкурента с распределенной блокировкой.
    """
    db = None
    redis_client = None
    lock_key = None
    is_lock_acquired = False

    try:
        logger.info(f"Начало скрапинга конкурента {competitor_link_id}")
        
        # Получаем сессию БД и Redis клиент
        db = next(get_db())
        from ...core.redis import get_redis_client
        redis_client = get_redis_client()

        # Получаем запись конкурента
        competitor = CompetitorLinkCRUD.get_by_id(db, competitor_link_id)
        if not competitor:
            logger.error(f"Конкурент {competitor_link_id} не найден")
            return {"status": "error", "message": "Конкурент не найден"}

        # --- РАСПРЕДЕЛЕННАЯ БЛОКИРОВКА ---
        lock_key = f"lock:scrape_competitor:{competitor.competitor_url}"
        # Устанавливаем блокировку на 30 минут (1800 секунд)
        is_lock_acquired = redis_client.set(lock_key, "1", ex=1800, nx=True)

        if not is_lock_acquired:
            logger.warning(f"Скрапинг конкурента {competitor.competitor_url} (ID: {competitor_link_id}) уже запущен другим процессом. Пропускаем.")
            # Если статус 'pending', меняем на 'completed', т.к. кто-то другой уже работает
            if competitor.status == 'pending':
                 CompetitorLinkCRUD.update_status(db, competitor_link_id, "completed", "Пропущено из-за параллельного запуска")
            return {"status": "skipped", "message": "Скрапинг уже запущен"}
        # --- КОНЕЦ БЛОКИРОВКИ ---

        # Обновляем статус на "scraping"
        CompetitorLinkCRUD.update_status(db, competitor_link_id, "scraping")
        
        # Получаем лимит товаров из env
        max_products = int(os.getenv("COMPETITOR_MAX_PRODUCTS_PER_LINK", "30"))
        
        # Запускаем скрапинг
        logger.info(f"Запуск скрапинга для {competitor.competitor_url}")
        scraping_result = scrape_competitor(competitor.competitor_url, max_products=max_products)
        
        if scraping_result["success_count"] == 0:
            error_msg = f"Не удалось собрать данные: найдено {len(scraping_result.get('products', []))} товаров"
            CompetitorLinkCRUD.update_status(db, competitor_link_id, "error", error_message=error_msg)
            logger.error(f"Скрапинг конкурента {competitor_link_id} завершился с ошибкой: {error_msg}")
            send_scraping_completion_notification(
                competitor_link_id=competitor_link_id, status="error",
                competitor_name=competitor.competitor_name or competitor.competitor_url,
                products_saved=0, error_message=error_msg
            )
            return {"status": "error", "message": error_msg}
        
        # Удаляем старые товары перед добавлением новых
        CompetitorProductCRUD.delete_by_competitor(db, competitor_link_id)
        
        products_saved = 0
        competitor_name = scraping_result.get("competitor_name")
        
        for product_data in scraping_result.get("products", []):
            try:
                CompetitorProductCRUD.create_or_update(db, competitor_link_id, product_data)
                products_saved += 1
            except Exception as e:
                logger.error(f"Ошибка сохранения товара {product_data.get('nm_id')}: {e}")
                continue
        
        CompetitorLinkCRUD.update_after_scraping(db, competitor_link_id, competitor_name or "Неизвестный", products_saved)
        
        logger.info(f"Скрапинг конкурента {competitor_link_id} завершен успешно: {products_saved} товаров")
        
        send_scraping_completion_notification(
            competitor_link_id=competitor_link_id, status="success",
            competitor_name=competitor_name, products_saved=products_saved
        )
        
        return {
            "status": "success", "competitor_id": competitor_link_id,
            "products_saved": products_saved, "competitor_name": competitor_name
        }
        
    except Exception as e:
        logger.error(f"Ошибка скрапинга конкурента {competitor_link_id}: {e}", exc_info=True)
        if db:
            try:
                CompetitorLinkCRUD.update_status(db, competitor_link_id, "error", error_message=str(e))
            except Exception as update_error:
                logger.error(f"Ошибка обновления статуса: {update_error}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300, exc=e)
        
        send_scraping_completion_notification(
            competitor_link_id=competitor_link_id, status="error",
            competitor_name="Неизвестный", products_saved=0, error_message=str(e)
        )
        
        return {"status": "error", "message": str(e)}
    
    finally:
        if is_lock_acquired and redis_client and lock_key:
            redis_client.delete(lock_key)
            logger.info(f"Блокировка {lock_key} снята")
        if db:
            db.close()


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 300})
def generate_semantic_core_task(self, semantic_core_id: int) -> Dict[str, Any]:
    """
    Задача генерации семантического ядра для конкурента по категории.
    """
    db = None
    try:
        logger.info(f"Начало генерации семантического ядра для ID: {semantic_core_id}")
        db = next(get_db())

        # Получаем запись семантического ядра
        semantic_core_entry = CompetitorSemanticCoreCRUD.get_by_id(db, semantic_core_id)
        if not semantic_core_entry:
            logger.error(f"Запись семантического ядра с ID {semantic_core_id} не найдена.")
            return {"status": "error", "message": "Запись семантического ядра не найдена."}

        # Обновляем статус на "processing"
        CompetitorSemanticCoreCRUD.update_status(db, semantic_core_id, "processing")
        
        # Получаем описания товаров
        logger.info(f"Получение описаний товаров для competitor_link_id={semantic_core_entry.competitor_link_id} и категории='{semantic_core_entry.category_name}'")
        product_descriptions_query = db.query(CompetitorProduct.description)\
            .filter(CompetitorProduct.competitor_link_id == semantic_core_entry.competitor_link_id)\
            .filter(CompetitorProduct.category == semantic_core_entry.category_name)\
            .filter(CompetitorProduct.description.isnot(None))
        
        descriptions = [d[0] for d in product_descriptions_query.all()]
        logger.info(f"Найдено {len(descriptions)} описаний товаров.")
        
        descriptions_text = "\n---\n".join(descriptions)

        if not descriptions_text:
            error_msg = "Не найдено описаний товаров для указанной категории."
            CompetitorSemanticCoreCRUD.update_status(db, semantic_core_id, "error", error_message=error_msg)
            logger.warning(f"Семантическое ядро ID {semantic_core_id}: {error_msg}")
            return {"status": "error", "message": error_msg}

        # Контроль токенов: обрезаем текст, если он слишком длинный
        max_text_length = int(os.getenv("SEMANTIC_CORE_MAX_TEXT_LENGTH"))
        if len(descriptions_text) > max_text_length:
            logger.warning(f"Текст описаний для семантического ядра ID {semantic_core_id} превышает лимит ({len(descriptions_text)} > {max_text_length}). Обрезаем.")
            descriptions_text = descriptions_text[:max_text_length]

        # Вызов GPT-сервиса
        gpt_service_url = os.getenv("GPT_INTEGRATION_URL")
        if not gpt_service_url:
            raise ValueError("Переменная окружения GPT_INTEGRATION_URL не установлена.")
        
        gpt_api_key = os.getenv("API_SECRET_KEY")
        if not gpt_api_key:
            raise ValueError("Переменная окружения API_SECRET_KEY не установлена.")

        headers = {"X-API-Key": gpt_api_key}
        payload = {"descriptions_text": descriptions_text}
        
        logger.info(f"Отправка запроса в GPT-сервис для семантического ядра ID {semantic_core_id}...")
        logger.info(f"URL: {gpt_service_url}/v1/semantic-core/generate")
        logger.info(f"Payload: {payload}")
        response = requests.post(f"{gpt_service_url}/v1/semantic-core/generate", json=payload, headers=headers, timeout=300)
        logger.info(f"GPT-сервис ответил с кодом статуса: {response.status_code}")
        response.raise_for_status() # Вызовет исключение для HTTP ошибок
        
        gpt_response = response.json()
        logger.info(f"Ответ от GPT-сервиса: {gpt_response}")

        if gpt_response.get("status") == "success":
            CompetitorSemanticCoreCRUD.update_core_data(db, semantic_core_id, gpt_response.get("core"))
            logger.info(f"Семантическое ядро ID {semantic_core_id} успешно сгенерировано и сохранено.")
            
            send_semantic_core_completion_notification(
                semantic_core_id=semantic_core_id,
                status="success",
                competitor_name=semantic_core_entry.competitor_link.competitor_name,
                category_name=semantic_core_entry.category_name
            )
            
            return {"status": "success", "semantic_core_id": semantic_core_id}
        else:
            error_msg = gpt_response.get("message", "Неизвестная ошибка GPT-сервиса.")
            CompetitorSemanticCoreCRUD.update_status(db, semantic_core_id, "error", error_message=error_msg)
            logger.error(f"Ошибка GPT-сервиса для семантического ядра ID {semantic_core_id}: {error_msg}")
            return {"status": "error", "message": error_msg}

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Ошибка при запросе к GPT-сервису: {req_err}"
        logger.error(f"Семантическое ядро ID {semantic_core_id}: {error_msg}", exc_info=True)
        if db:
            CompetitorSemanticCoreCRUD.update_status(db, semantic_core_id, "error", error_message=error_msg)
        
        send_semantic_core_completion_notification(
            semantic_core_id=semantic_core_id,
            status="error",
            competitor_name=semantic_core_entry.competitor_link.competitor_name,
            category_name=semantic_core_entry.category_name,
            error_message=error_msg
        )
        
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при генерации семантического ядра: {e}"
        logger.error(f"Семантическое ядро ID {semantic_core_id}: {error_msg}", exc_info=True)
        if db:
            CompetitorSemanticCoreCRUD.update_status(db, semantic_core_id, "error", error_message=error_msg)
        
        if self.request.retries < self.max_retries:
            logger.info(f"Повторная попытка генерации семантического ядра ID {semantic_core_id} через 5 минут")
            raise self.retry(countdown=300, exc=e)
        
        send_semantic_core_completion_notification(
            semantic_core_id=semantic_core_id,
            status="error",
            competitor_name=semantic_core_entry.competitor_link.competitor_name,
            category_name=semantic_core_entry.category_name,
            error_message=error_msg
        )
        
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

