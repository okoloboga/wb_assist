"""
RAG API endpoints for indexing and status management.

Provides REST API for triggering RAG indexing and checking status.
"""

import logging
import asyncio
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import os

from .indexer import RAGIndexer
from .database import RAGSessionLocal
from .models import RAGIndexStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["rag"])


class IndexRequest(BaseModel):
    """Request body для индексации."""
    changed_ids: Optional[Dict[str, List[int]]] = None


def _verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-KEY")) -> None:
    """
    Verify API key from request headers.

    Args:
        x_api_key: API key from X-API-KEY header

    Raises:
        HTTPException: If API key is invalid or missing
    """
    expected_key = os.getenv("API_SECRET_KEY")
    if not expected_key:
        logger.error("❌ API_SECRET_KEY not configured on server")
        raise HTTPException(
            status_code=500,
            detail="API authentication not configured on server"
        )

    if not x_api_key or x_api_key != expected_key:
        logger.warning(f"⛔ Invalid API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )


async def _background_indexing(
    cabinet_id: int,
    full_rebuild: bool,
    changed_ids: Optional[Dict[str, List[int]]]
) -> None:
    """
    Фоновая задача индексации.

    Выполняется асинхронно, не блокируя основной поток.
    Все ошибки логируются и записываются в статус.

    Args:
        cabinet_id: ID кабинета
        full_rebuild: Полная переиндексация
        changed_ids: Дельта изменений (для incremental)
    """
    indexing_mode = 'full_rebuild' if full_rebuild else 'incremental'

    try:
        indexer = RAGIndexer()
        result = await indexer.index_cabinet(
            cabinet_id=cabinet_id,
            full_rebuild=full_rebuild,
            changed_ids=changed_ids
        )

        if result['success']:
            logger.info(
                f"✅ Background {indexing_mode} indexing completed for cabinet {cabinet_id}: "
                f"{result['total_chunks']} chunks indexed"
            )
        else:
            errors = result.get('errors', [])
            logger.error(
                f"❌ Background {indexing_mode} indexing failed for cabinet {cabinet_id}: {errors}"
            )

    except Exception as e:
        logger.error(
            f"❌ Unexpected error in background indexing for cabinet {cabinet_id}: {e}",
            exc_info=True
        )


@router.post("/index/{cabinet_id}", status_code=202)
async def trigger_indexing(
    cabinet_id: int,
    full_rebuild: bool = False,
    request_body: Optional[IndexRequest] = None,
    _: None = Depends(_verify_api_key)
):
    """
    Запуск асинхронной индексации для кабинета.

    Индексация выполняется в фоне, endpoint сразу возвращает 202 Accepted.
    Для проверки статуса используйте GET /v1/rag/status/{cabinet_id}.

    Поддерживает два режима:
    1. Event-driven (changed_ids): Индексация только измененных записей
    2. Full rebuild: Полная переиндексация с очисткой устаревших данных

    Args:
        cabinet_id: ID кабинета Wildberries
        full_rebuild: Полная переиндексация (weekly cleanup)
        request_body: Дельта изменений от WB sync (Event-driven)

    Returns:
        202 Accepted: Индексация запущена
        409 Conflict: Индексация уже выполняется
    """
    indexing_mode = 'full_rebuild' if full_rebuild else 'incremental'
    changed_ids = request_body.changed_ids if request_body else None

    logger.info(
        f"🚀 Triggering background {indexing_mode} RAG indexing for cabinet {cabinet_id}"
        + (f" with {sum(len(ids) for ids in changed_ids.values())} changed IDs" if changed_ids else "")
    )

    # Проверяем, не выполняется ли уже индексация
    db = RAGSessionLocal()
    try:
        status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()

        if status and status.indexing_status == 'in_progress':
            logger.warning(
                f"⚠️ Concurrent indexing detected for cabinet {cabinet_id}. Skipping."
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "status": "conflict",
                    "message": f"Индексация кабинета {cabinet_id} уже выполняется",
                    "cabinet_id": cabinet_id,
                    "current_status": "in_progress"
                }
            )
    finally:
        db.close()

    # Запускаем индексацию в фоне
    asyncio.create_task(
        _background_indexing(
            cabinet_id=cabinet_id,
            full_rebuild=full_rebuild,
            changed_ids=changed_ids
        )
    )

    logger.info(
        f"✅ Background {indexing_mode} indexing task created for cabinet {cabinet_id}"
    )

    return {
        "status": "accepted",
        "message": f"Индексация кабинета {cabinet_id} запущена в фоне",
        "cabinet_id": cabinet_id,
        "indexing_mode": indexing_mode,
        "note": "Используйте GET /v1/rag/status/{cabinet_id} для проверки статуса"
    }


@router.get("/status/{cabinet_id}")
async def get_indexing_status(
    cabinet_id: int,
    _: None = Depends(_verify_api_key)
):
    """
    Получить детальный статус индексации для кабинета.

    Возвращает текущий статус, время последней индексации,
    количество проиндексированных чанков и другую информацию.

    Args:
        cabinet_id: ID кабинета Wildberries

    Returns:
        Детальный статус индексации
    """
    logger.info(f"📊 Getting RAG indexing status for cabinet {cabinet_id}")

    db = RAGSessionLocal()

    try:
        status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()

        if not status:
            return {
                "status": "not_found",
                "message": f"Индексация для кабинета {cabinet_id} еще не запускалась",
                "cabinet_id": cabinet_id,
                "indexing_status": None,
                "last_indexed_at": None,
                "last_incremental_at": None,
                "total_chunks": 0,
                "is_indexing": False
            }

        is_indexing = status.indexing_status == 'in_progress'

        return {
            "status": "success",
            "cabinet_id": cabinet_id,
            "indexing_status": status.indexing_status,
            "is_indexing": is_indexing,
            "last_indexed_at": status.last_indexed_at.isoformat() if status.last_indexed_at else None,
            "last_incremental_at": status.last_incremental_at.isoformat() if status.last_incremental_at else None,
            "total_chunks": status.total_chunks or 0,
            "created_at": status.created_at.isoformat() if status.created_at else None,
            "updated_at": status.updated_at.isoformat() if status.updated_at else None,
            "message": (
                "Индексация выполняется..." if is_indexing
                else f"Последняя индексация: {status.indexing_status}"
            )
        }

    except Exception as e:
        logger.error(f"❌ Error getting indexing status for cabinet {cabinet_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Ошибка получения статуса: {str(e)}"
            }
        )
    finally:
        db.close()


@router.get("/health")
async def health_check():
    """
    Health check для RAG сервиса.
    """
    return {
        "status": "ok",
        "service": "rag",
        "version": "1.0.0"
    }
