"""
Celery-задачи для генерации агрегированного семантического ядра по кабинету.

Логика аналогична generate_semantic_core_task из features.competitors.tasks,
но вместо одного конкурента используется весь кабинет WB и категория.
"""

import logging
import os
from typing import Dict, Any, List

import requests
from celery import current_task  # noqa: F401  # оставляем для отладки при необходимости
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.celery_app import celery_app
from app.features.semantic_core.crud import CabinetSemanticCoreCRUD
from app.features.semantic_core.models import CabinetSemanticCore
from app.features.competitors.models import CompetitorLink, CompetitorProduct
from app.features.wb_api.models import CabinetUser
from app.features.user.crud import UserCRUD

logger = logging.getLogger(__name__)


def send_cabinet_semantic_core_completion_notification(
    core_id: int,
    status: str,
    category_name: str,
    error_message: str | None = None,
) -> None:
    """
    Отправляет webhook-уведомление боту о завершении генерации семантического ядра по кабинету.

    Формат payload совместим с существующим обработчиком semantic_core_ready в боте.
    """
    db: Session = next(get_db())
    try:
        core_entry = CabinetSemanticCoreCRUD.get_by_id(db, core_id)
        if not core_entry:
            logger.error(
                "send_cabinet_semantic_core_completion_notification: "
                "CabinetSemanticCore with id %s not found.",
                core_id,
            )
            return

        cabinet_user = (
            db.query(CabinetUser)
            .filter(CabinetUser.cabinet_id == core_entry.cabinet_id)
            .first()
        )
        if not cabinet_user:
            logger.error(
                "send_cabinet_semantic_core_completion_notification: "
                "CabinetUser not found for cabinet_id %s",
                core_entry.cabinet_id,
            )
            return

        user = UserCRUD(db).get_user_by_id(cabinet_user.user_id)
        if not user or not user.bot_webhook_url:
            logger.warning(
                "send_cabinet_semantic_core_completion_notification: "
                "User or webhook_url not found for cabinet_id %s",
                core_entry.cabinet_id,
            )
            return

        # Для обратной совместимости используем поле competitor_name как "Все конкуренты"
        competitor_name_label = "Все конкуренты"

        if status == "success":
            telegram_text = (
                f"✅ Семантическое ядро по всем конкурентам для категории "
                f"'{category_name}' готово."
            )
        else:
            telegram_text = (
                f"❌ Ошибка генерации семантического ядра по всем конкурентам "
                f"для категории '{category_name}'.\n\nПричина: {error_message}"
            )

        payload: Dict[str, Any] = {
            "telegram_id": user.telegram_id,
            "type": "semantic_core_ready",
            "telegram_text": telegram_text,
            "data": {
                "semantic_core_id": core_id,
                "status": status,
                "competitor_name": competitor_name_label,
                "category_name": category_name,
                "error_message": error_message,
                "core": core_entry.core_data if status == "success" else None,
            },
        }

        try:
            requests.post(user.bot_webhook_url, json=payload, timeout=10)
            logger.info(
                "Sent cabinet semantic core completion notification for id %s to %s",
                core_id,
                user.bot_webhook_url,
            )
        except requests.RequestException as e:
            logger.error(
                "Failed to send cabinet semantic core completion notification "
                "for id %s: %s",
                core_id,
                e,
            )
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 300},
)
def generate_cabinet_semantic_core_task(self, core_id: int) -> Dict[str, Any]:
    """
    Задача генерации агрегированного семантического ядра для кабинета по категории.
    """
    db: Session | None = None

    try:
        logger.info("Начало генерации агрегированного семантического ядра ID: %s", core_id)
        db = next(get_db())

        core_entry = CabinetSemanticCoreCRUD.get_by_id(db, core_id)
        if not core_entry:
            logger.error(
                "Cabinet semantic core entry with ID %s not found. Aborting task.", core_id
            )
            return {"status": "error", "message": "Cabinet semantic core entry not found"}

        # Обновляем статус на "processing"
        CabinetSemanticCoreCRUD.update_status(db, core_id, "processing")

        cabinet_id = core_entry.cabinet_id
        category_name = core_entry.category_name

        logger.info(
            "Сбор описаний товаров для cabinet_id=%s и категории '%s'",
            cabinet_id,
            category_name,
        )

        # Находим всех конкурентов кабинета
        competitors: List[CompetitorLink] = (
            db.query(CompetitorLink)
            .filter(CompetitorLink.cabinet_id == cabinet_id)
            .all()
        )

        if not competitors:
            error_msg = "Не найдены конкуренты для указанного кабинета."
            CabinetSemanticCoreCRUD.update_status(db, core_id, "error", error_msg)
            logger.warning("Cabinet semantic core ID %s: %s", core_id, error_msg)
            send_cabinet_semantic_core_completion_notification(
                core_id=core_id,
                status="error",
                category_name=category_name,
                error_message=error_msg,
            )
            return {"status": "error", "message": error_msg}

        # Сбор описаний по всем конкурентам и товарам нужной категории
        descriptions: List[str] = []
        for competitor in competitors:
            rows = (
                db.query(CompetitorProduct.description)
                .filter(
                    CompetitorProduct.competitor_link_id == competitor.id,
                    CompetitorProduct.category == category_name,
                    CompetitorProduct.description.isnot(None),
                )
                .all()
            )
            descriptions.extend([row[0] for row in rows if row[0]])

        logger.info(
            "Для cabinet_id=%s и категории '%s' найдено %s описаний товаров.",
            cabinet_id,
            category_name,
            len(descriptions),
        )

        if not descriptions:
            error_msg = (
                "Не найдено описаний товаров для указанной категории по всем конкурентам."
            )
            CabinetSemanticCoreCRUD.update_status(db, core_id, "error", error_msg)
            logger.warning("Cabinet semantic core ID %s: %s", core_id, error_msg)
            send_cabinet_semantic_core_completion_notification(
                core_id=core_id,
                status="error",
                category_name=category_name,
                error_message=error_msg,
            )
            return {"status": "error", "message": error_msg}

        descriptions_text = "\n---\n".join(descriptions)

        # Контроль токенов
        max_text_length = int(os.getenv("SEMANTIC_CORE_MAX_TEXT_LENGTH", "15000"))
        if len(descriptions_text) > max_text_length:
            logger.warning(
                "Текст описаний для cabinet semantic core ID %s превышает лимит (%s > %s). "
                "Обрезаем.",
                core_id,
                len(descriptions_text),
                max_text_length,
            )
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

        logger.info(
            "Отправка запроса в GPT-сервис для cabinet semantic core ID %s...", core_id
        )
        response = requests.post(
            f"{gpt_service_url}/v1/semantic-core/generate",
            json=payload,
            headers=headers,
            timeout=300,
        )
        logger.info(
            "GPT-сервис ответил для cabinet semantic core ID %s со статусом %s",
            core_id,
            response.status_code,
        )
        response.raise_for_status()

        gpt_response = response.json()
        logger.info("Ответ GPT-сервиса для cabinet semantic core ID %s: %s", core_id, gpt_response)

        if gpt_response.get("status") == "success":
            CabinetSemanticCoreCRUD.update_core_data(
                db,
                core_id,
                gpt_response.get("core", ""),
            )
            logger.info(
                "Cabinet semantic core ID %s успешно сгенерировано и сохранено.",
                core_id,
            )

            send_cabinet_semantic_core_completion_notification(
                core_id=core_id,
                status="success",
                category_name=category_name,
            )

            return {"status": "success", "semantic_core_id": core_id}

        error_msg = gpt_response.get("message", "Неизвестная ошибка GPT-сервиса.")
        CabinetSemanticCoreCRUD.update_status(db, core_id, "error", error_msg)
        logger.error(
            "Ошибка GPT-сервиса для cabinet semantic core ID %s: %s",
            core_id,
            error_msg,
        )
        send_cabinet_semantic_core_completion_notification(
            core_id=core_id,
            status="error",
            category_name=category_name,
            error_message=error_msg,
        )
        return {"status": "error", "message": error_msg}

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Ошибка при запросе к GPT-сервису: {req_err}"
        logger.error(
            "Cabinet semantic core ID %s: %s",
            core_id,
            error_msg,
            exc_info=True,
        )
        if db:
            CabinetSemanticCoreCRUD.update_status(db, core_id, "error", error_msg)

        send_cabinet_semantic_core_completion_notification(
            core_id=core_id,
            status="error",
            category_name=core_entry.category_name if "core_entry" in locals() else "",
            error_message=error_msg,
        )
        return {"status": "error", "message": error_msg}

    except Exception as e:  # noqa: BLE001
        error_msg = f"Непредвиденная ошибка при генерации семантического ядра: {e}"
        logger.error(
            "Cabinet semantic core ID %s: %s",
            core_id,
            error_msg,
            exc_info=True,
        )
        if db:
            CabinetSemanticCoreCRUD.update_status(db, core_id, "error", error_msg)

        # Повторяем задачу, если лимит попыток не исчерпан
        if self.request.retries < self.max_retries:
            logger.info(
                "Повторная попытка генерации cabinet semantic core ID %s через 5 минут",
                core_id,
            )
            raise self.retry(countdown=300, exc=e)

        send_cabinet_semantic_core_completion_notification(
            core_id=core_id,
            status="error",
            category_name=core_entry.category_name if "core_entry" in locals() else "",
            error_message=error_msg,
        )
        return {"status": "error", "message": str(e)}

    finally:
        if db:
            db.close()






