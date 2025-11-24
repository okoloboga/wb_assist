
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.features.competitors.models import CompetitorSemanticCore, CompetitorLink
from app.features.bot_api.schemas import SemanticCoreOut, SemanticCoreDetailOut
from app.features.bot_api.service import BotAPIService
from app.features.bot_api.routes import get_bot_service

router = APIRouter()

@router.get(
    "/semantic-cores/",
    response_model=List[SemanticCoreOut],
    summary="Получить список доступных семантических ядер",
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
    """
    cabinet = await bot_service.get_user_cabinet(telegram_id)
    if not cabinet:
        raise HTTPException(status_code=404, detail="Кабинет WB не найден для данного пользователя.")

    cores = (
        db.query(
            CompetitorSemanticCore.id,
            CompetitorSemanticCore.category_name,
            CompetitorLink.competitor_name,
        )
        .join(CompetitorLink, CompetitorSemanticCore.competitor_link_id == CompetitorLink.id)
        .filter(
            CompetitorLink.cabinet_id == cabinet.id,
            CompetitorSemanticCore.status == "completed",
        )
        .order_by(CompetitorLink.competitor_name, CompetitorSemanticCore.category_name)
        .all()
    )
    
    # Pydantic V2 requires model_validate for list of objects
    return [SemanticCoreOut.model_validate(core) for core in cores]


@router.get(
    "/semantic-cores/{core_id}/",
    response_model=SemanticCoreDetailOut,
    summary="Получить детали семантического ядра",
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
        raise HTTPException(status_code=404, detail="Кабинет WB не найден для данного пользователя.")

    core = (
        db.query(CompetitorSemanticCore)
        .join(CompetitorLink, CompetitorSemanticCore.competitor_link_id == CompetitorLink.id)
        .filter(
            CompetitorLink.cabinet_id == cabinet.id,
            CompetitorSemanticCore.id == core_id,
            CompetitorSemanticCore.status == "completed",
        )
        .first()
    )

    if not core:
        raise HTTPException(status_code=404, detail="Семантическое ядро не найдено или еще не готово.")

    return SemanticCoreDetailOut.model_validate(core)
