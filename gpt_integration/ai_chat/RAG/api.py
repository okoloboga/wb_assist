"""
RAG API endpoints for indexing and status management.

Provides REST API for triggering RAG indexing and checking status.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
import os

from .indexer import RAGIndexer
from .database import RAGSessionLocal
from .models import RAGIndexStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["rag"])


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


@router.post("/index/{cabinet_id}")
async def trigger_indexing(
    cabinet_id: int,
    _: None = Depends(_verify_api_key)
):
    """
    Запуск индексации для кабинета вручную или через Celery.

    Args:
        cabinet_id: ID кабинета Wildberries

    Returns:
        Результат индексации
    """
    logger.info(f"🚀 Starting RAG indexing for cabinet {cabinet_id}")

    try:
        indexer = RAGIndexer()
        result = await indexer.index_cabinet(cabinet_id)

        if result['success']:
            logger.info(
                f"✅ RAG indexing completed for cabinet {cabinet_id}: "
                f"{result['total_chunks']} chunks indexed"
            )
            return {
                "status": "success",
                "message": f"Индексация кабинета {cabinet_id} завершена успешно",
                "cabinet_id": cabinet_id,
                "total_chunks": result['total_chunks']
            }
        else:
            logger.error(
                f"❌ RAG indexing failed for cabinet {cabinet_id}: "
                f"{result.get('errors', [])}"
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Ошибка индексации кабинета {cabinet_id}",
                    "errors": result.get('errors', [])
                }
            )

    except Exception as e:
        logger.error(f"❌ Unexpected error during indexing cabinet {cabinet_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Внутренняя ошибка при индексации: {str(e)}"
            }
        )


@router.get("/status/{cabinet_id}")
async def get_indexing_status(
    cabinet_id: int,
    _: None = Depends(_verify_api_key)
):
    """
    Получить статус индексации для кабинета.

    Args:
        cabinet_id: ID кабинета Wildberries

    Returns:
        Статус индексации
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
                "total_chunks": 0
            }

        return {
            "status": "success",
            "cabinet_id": cabinet_id,
            "indexing_status": status.indexing_status,
            "last_indexed_at": status.last_indexed_at.isoformat() if status.last_indexed_at else None,
            "total_chunks": status.total_chunks or 0,
            "updated_at": status.updated_at.isoformat() if status.updated_at else None
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
