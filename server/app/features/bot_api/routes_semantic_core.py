
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.bot_api.routes import get_bot_service
from app.features.bot_api.schemas import SemanticCoreOut, SemanticCoreDetailOut
from app.features.bot_api.service import BotAPIService
from app.features.competitors.models import CompetitorProduct, CompetitorLink
from app.features.semantic_core.crud import CabinetSemanticCoreCRUD
from app.features.semantic_core.models import CabinetSemanticCore
from app.features.semantic_core.tasks import generate_cabinet_semantic_core_task

router = APIRouter()


class CabinetSemanticCoreGenerateRequest(BaseModel):
    """Тело запроса для запуска генерации семантического ядра по кабинету."""

    category_name: str


@router.get(
    "/semantic-cores/categories",
    summary="Получить список категорий для агрегированного семантического ядра",
    tags=["Bot API"],
)
async def list_semantic_core_categories(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db),
    bot_service: BotAPIService = Depends(get_bot_service),
):
    """
    Возвращает список уникальных категорий товаров по всем конкурентам кабинета.
    """
    cabinet = await bot_service.get_user_cabinet(telegram_id)
    if not cabinet:
        raise HTTPException(
            status_code=404,
            detail="Кабинет WB не найден для данного пользователя.",
        )

    categories_query = (
        db.query(CompetitorProduct.category)
        .join(CompetitorLink, CompetitorProduct.competitor_link_id == CompetitorLink.id)
        .filter(
            CompetitorLink.cabinet_id == cabinet.id,
            CompetitorProduct.category.isnot(None),
        )
        .distinct()
        .order_by(CompetitorProduct.category)
        .all()
    )

    categories = [c[0] for c in categories_query if c[0]]

    return {
        "status": "success",
        "categories": categories,
    }


@router.get(
    "/semantic-cores/",
    response_model=List[SemanticCoreOut],
    summary="Получить список доступных семантических ядер по кабинету",
    tags=["Bot API"],
)
async def list_semantic_cores(
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db),
    bot_service: BotAPIService = Depends(get_bot_service),
):
    """
    Возвращает список всех успешно сгенерированных семантических ядер,
    доступных для текущего кабинета пользователя.

    Использует агрегированную модель CabinetSemanticCore (по кабинету и категории).
    """
    cabinet = await bot_service.get_user_cabinet(telegram_id)
    if not cabinet:
        raise HTTPException(
            status_code=404,
            detail="Кабинет WB не найден для данного пользователя.",
        )

    cores: List[CabinetSemanticCore] = (
        db.query(CabinetSemanticCore)
        .filter(
            CabinetSemanticCore.cabinet_id == cabinet.id,
            CabinetSemanticCore.status == "completed",
        )
        .order_by(CabinetSemanticCore.category_name)
        .all()
    )

    # Для обратной совместимости поле competitor_name заполняем значением "Все конкуренты"
    return [
        SemanticCoreOut(
            id=core.id,
            competitor_name="Все конкуренты",
            category_name=core.category_name,
        )
        for core in cores
    ]


@router.get(
    "/semantic-cores/{core_id}/",
    response_model=SemanticCoreDetailOut,
    summary="Получить детали семантического ядра по кабинету",
    tags=["Bot API"],
)
async def get_semantic_core_detail(
    core_id: int,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    db: Session = Depends(get_db),
    bot_service: BotAPIService = Depends(get_bot_service),
):
    """
    Возвращает полное содержимое (core_data) указанного семантического ядра.
    Проверяет, что ядро принадлежит кабинету текущего пользователя.
    """
    cabinet = await bot_service.get_user_cabinet(telegram_id)
    if not cabinet:
        raise HTTPException(
            status_code=404,
            detail="Кабинет WB не найден для данного пользователя.",
        )

    core = (
        db.query(CabinetSemanticCore)
        .filter(
            CabinetSemanticCore.cabinet_id == cabinet.id,
            CabinetSemanticCore.id == core_id,
            CabinetSemanticCore.status == "completed",
        )
        .first()
    )

    if not core:
        raise HTTPException(
            status_code=404,
            detail="Семантическое ядро не найдено или еще не готово.",
        )

    return SemanticCoreDetailOut.model_validate(core)


@router.post(
    "/semantic-cores/generate",
    summary="Запустить генерацию семантического ядра по категории для всех конкурентов кабинета",
    tags=["Bot API"],
)
async def generate_cabinet_semantic_core(
    request: CabinetSemanticCoreGenerateRequest,
    telegram_id: int = Query(..., description="Telegram ID пользователя"),
    force: bool = Query(
        False,
        description="Принудительно перезаписать существующее ядро, если оно уже сгенерировано",
    ),
    db: Session = Depends(get_db),
    bot_service: BotAPIService = Depends(get_bot_service),
):
    """
    Запускает генерацию агрегированного семантического ядра для кабинета по выбранной категории.

    Если ядро уже существует и `force=false`, возвращает готовое ядро без запуска новой задачи.
    """
    cabinet = await bot_service.get_user_cabinet(telegram_id)
    if not cabinet:
        raise HTTPException(
            status_code=404,
            detail="Кабинет WB не найден для данного пользователя.",
        )

    existing_core = CabinetSemanticCoreCRUD.get_by_cabinet_and_category(
        db,
        cabinet_id=cabinet.id,
        category_name=request.category_name,
    )

    if existing_core and not force:
        # Если ядро существует и не требуется перезапись, возвращаем его
        return {
            "status": "already_exists",
            "message": "Семантическое ядро для этой категории уже было сгенерировано.",
            "semantic_core": {
                "id": existing_core.id,
                "core_data": existing_core.core_data,
                "created_at": existing_core.created_at,
                # Для совместимости с текущей схемой
                "competitor_name": "Все конкуренты",
                "category_name": existing_core.category_name,
            },
        }

    if existing_core and force:
        logger_msg = (
            "Сброс существующего агрегированного семантического ядра "
            f"(id={existing_core.id}) для перезаписи."
        )
        logging.getLogger(__name__).info(logger_msg)
        CabinetSemanticCoreCRUD.reset_semantic_core(db, existing_core.id)
        core_id_to_process = existing_core.id
    else:
        new_core = CabinetSemanticCoreCRUD.create(
            db,
            cabinet_id=cabinet.id,
            category_name=request.category_name,
            status="pending",
        )
        core_id_to_process = new_core.id

    # Запускаем Celery-задачу на той же очереди, что и скрапинг конкурентов
    generate_cabinet_semantic_core_task.apply_async(
        args=[core_id_to_process],
        queue="scraping_queue",
    )

    logging.getLogger(__name__).info(
        "Запущена генерация агрегированного семантического ядра для cabinet_id=%s, "
        "категория '%s'. ID задачи: %s",
        cabinet.id,
        request.category_name,
        core_id_to_process,
    )

    return {
        "status": "accepted",
        "message": "Генерация семантического ядра запущена. Результат будет отправлен по завершении.",
        "semantic_core_id": core_id_to_process,
    }
