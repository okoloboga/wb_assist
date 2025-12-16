"""
Фоновые задачи для автоматической индексации RAG (Retrieval-Augmented Generation).

Периодическая индексация данных кабинетов в векторную БД для улучшения
ответов AI-ассистента.
"""

import os
import logging
import requests
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.celery_app import celery_app
from app.features.wb_api.models import WBCabinet

logger = logging.getLogger(__name__)


def _get_gpt_service_url() -> str:
    """
    Получить URL AI-сервиса из переменных окружения.

    Returns:
        URL AI-сервиса

    Raises:
        ValueError: Если URL не настроен
    """
    gpt_service_url = os.getenv("GPT_INTEGRATION_URL")
    if not gpt_service_url:
        raise ValueError(
            "Переменная окружения GPT_INTEGRATION_URL не установлена. "
            "Требуется для связи с AI-сервисом."
        )
    return gpt_service_url.rstrip('/')


def _get_api_key() -> str:
    """
    Получить API ключ для обращения к AI-сервису.

    Returns:
        API ключ

    Raises:
        ValueError: Если API ключ не настроен
    """
    api_key = os.getenv("API_SECRET_KEY")
    if not api_key:
        raise ValueError("API_SECRET_KEY не установлен")
    return api_key


@celery_app.task(
    bind=True,
    max_retries=5,  # Увеличено с 3 до 5
    autoretry_for=(requests.RequestException,),
    retry_kwargs={'max_retries': 5, 'countdown': 600},  # 10 минут между попытками (было 5)
    time_limit=1800,  # 30 минут максимум на задачу
    soft_time_limit=1500  # 25 минут soft limit
)
def index_rag_for_cabinet(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Индексация RAG для конкретного кабинета.

    Вызывает API AI-сервиса для запуска индексации данных кабинета
    в векторную БД.

    Args:
        cabinet_id: ID кабинета Wildberries

    Returns:
        Результат индексации:
        {
            'status': 'success' | 'error',
            'cabinet_id': int,
            'message': str,
            'total_chunks': int (если успешно)
        }
    """
    try:
        logger.info(f"🔄 Starting RAG indexing for cabinet {cabinet_id}")

        # Получаем сессию БД
        db = next(get_db())

        try:
            # Проверяем существование кабинета
            cabinet = db.query(WBCabinet).filter(
                WBCabinet.id == cabinet_id,
                WBCabinet.is_active == True
            ).first()

            if not cabinet:
                logger.warning(f"⚠️ Cabinet {cabinet_id} not found or inactive")
                return {
                    "status": "error",
                    "cabinet_id": cabinet_id,
                    "message": "Кабинет не найден или неактивен"
                }

            # Получаем URL и API ключ
            gpt_service_url = _get_gpt_service_url()
            api_key = _get_api_key()

            # Формируем запрос к AI-сервису
            endpoint = f"{gpt_service_url}/v1/rag/index/{cabinet_id}"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }

            logger.info(f"📡 Calling AI service: POST {endpoint}")

            # Отправляем запрос (timeout 10 минут для генерации эмбеддингов)
            response = requests.post(
                endpoint,
                headers=headers,
                timeout=600  # 10 минут
            )

            # Обрабатываем ответ
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✅ RAG indexing completed for cabinet {cabinet_id}: "
                    f"{result.get('total_chunks', 0)} chunks indexed"
                )
                return {
                    "status": "success",
                    "cabinet_id": cabinet_id,
                    "message": result.get('message', 'Индексация завершена'),
                    "total_chunks": result.get('total_chunks', 0)
                }
            else:
                error_detail = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                logger.error(
                    f"❌ RAG indexing failed for cabinet {cabinet_id}: "
                    f"Status {response.status_code}, Detail: {error_detail}"
                )

                # Не повторяем при ошибках валидации (4xx)
                if 400 <= response.status_code < 500:
                    return {
                        "status": "error",
                        "cabinet_id": cabinet_id,
                        "message": f"Ошибка индексации (код {response.status_code})",
                        "detail": error_detail
                    }

                # Повторяем при серверных ошибках (5xx)
                raise requests.RequestException(
                    f"Server error {response.status_code}: {error_detail}"
                )

        finally:
            db.close()

    except requests.Timeout as e:
        logger.error(f"⏱️ Timeout during RAG indexing for cabinet {cabinet_id}: {e}")

        # Повторяем при timeout
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying RAG indexing for cabinet {cabinet_id} after timeout")
            raise self.retry(countdown=300, exc=e)

        return {
            "status": "error",
            "cabinet_id": cabinet_id,
            "message": "Превышено время ожидания индексации"
        }

    except requests.RequestException as e:
        logger.error(f"❌ Request error during RAG indexing for cabinet {cabinet_id}: {e}")

        # Повторяем при сетевых ошибках
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying RAG indexing for cabinet {cabinet_id} after request error")
            raise self.retry(countdown=300, exc=e)

        return {
            "status": "error",
            "cabinet_id": cabinet_id,
            "message": f"Ошибка связи с AI-сервисом: {str(e)}"
        }

    except Exception as e:
        logger.error(
            f"❌ Unexpected error during RAG indexing for cabinet {cabinet_id}: {e}",
            exc_info=True
        )
        return {
            "status": "error",
            "cabinet_id": cabinet_id,
            "message": f"Внутренняя ошибка: {str(e)}"
        }


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60}
)
def index_all_cabinets_rag(self) -> Dict[str, Any]:
    """
    Индексация RAG для всех активных кабинетов.

    Эта задача запускается периодически (по расписанию в beat_schedule)
    и запускает индексацию для каждого активного кабинета.

    Returns:
        Статистика индексации:
        {
            'status': 'success',
            'started': int,  # Количество запущенных индексаций
            'skipped': int,  # Количество пропущенных кабинетов
            'total': int,    # Общее количество активных кабинетов
            'timestamp': str
        }
    """
    try:
        logger.info("🚀 Starting RAG indexing for all active cabinets")

        # Получаем сессию БД
        db = next(get_db())

        try:
            # Получаем все активные кабинеты
            cabinets = db.query(WBCabinet).filter(
                WBCabinet.is_active == True
            ).all()

            total_cabinets = len(cabinets)
            started_count = 0
            skipped_count = 0

            logger.info(f"📊 Found {total_cabinets} active cabinets for RAG indexing")

            # Запускаем индексацию для каждого кабинета
            for cabinet in cabinets:
                try:
                    # Запускаем задачу в фоне (асинхронно)
                    index_rag_for_cabinet.delay(cabinet.id)
                    started_count += 1
                    logger.info(f"✅ RAG indexing started for cabinet {cabinet.id}")

                except Exception as e:
                    logger.error(
                        f"❌ Failed to start RAG indexing for cabinet {cabinet.id}: {e}",
                        exc_info=True
                    )
                    skipped_count += 1

            result = {
                "status": "success",
                "started": started_count,
                "skipped": skipped_count,
                "total": total_cabinets,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(
                f"✅ RAG indexing batch completed: "
                f"{started_count} started, {skipped_count} skipped, "
                f"{total_cabinets} total"
            )

            return result

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error in RAG indexing batch: {e}", exc_info=True)

        # Повторяем при ошибке
        if self.request.retries < self.max_retries:
            logger.info("🔄 Retrying RAG indexing batch")
            raise self.retry(countdown=60, exc=e)

        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@celery_app.task
def check_rag_indexing_status(cabinet_id: int) -> Dict[str, Any]:
    """
    Проверка статуса индексации RAG для кабинета.

    Вызывает API AI-сервиса для получения статуса индексации.

    Args:
        cabinet_id: ID кабинета Wildberries

    Returns:
        Статус индексации
    """
    try:
        logger.info(f"📊 Checking RAG indexing status for cabinet {cabinet_id}")

        # Получаем URL и API ключ
        gpt_service_url = _get_gpt_service_url()
        api_key = _get_api_key()

        # Формируем запрос к AI-сервису
        endpoint = f"{gpt_service_url}/v1/rag/status/{cabinet_id}"
        headers = {
            "X-API-KEY": api_key
        }

        response = requests.get(
            endpoint,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(
                f"✅ RAG status for cabinet {cabinet_id}: "
                f"{result.get('indexing_status', 'unknown')}, "
                f"{result.get('total_chunks', 0)} chunks"
            )
            return result
        else:
            logger.error(
                f"❌ Failed to get RAG status for cabinet {cabinet_id}: "
                f"Status {response.status_code}"
            )
            return {
                "status": "error",
                "message": f"Ошибка получения статуса (код {response.status_code})"
            }

    except Exception as e:
        logger.error(
            f"❌ Error checking RAG status for cabinet {cabinet_id}: {e}",
            exc_info=True
        )
        return {
            "status": "error",
            "message": str(e)
        }
