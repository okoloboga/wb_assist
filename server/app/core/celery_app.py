"""
Celery конфигурация для фоновых задач синхронизации с Redis
"""
from celery import Celery
from celery.schedules import crontab
import os
import logging

logger = logging.getLogger(__name__)

# Получаем конфигурацию Redis
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Получаем интервал синхронизации из переменной окружения
sync_interval = int(os.getenv("SYNC_INTERVAL", "600"))  # По умолчанию 10 минут

logger.info(f"Redis configuration:")
logger.info(f"  Redis URL: {redis_url}")
logger.info(f"Sync configuration:")
logger.info(f"  Sync interval: {sync_interval} seconds ({sync_interval/60:.1f} minutes)")

# Создаем экземпляр Celery с Redis
celery_app = Celery(
    "wb_assist",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.features.sync.tasks",
    ]
)

# Конфигурация Celery с Redis (упрощенная версия)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Redis конфигурация (без Sentinel)
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_connection_retry_delay=1.0,
    
    # Настройки очередей
    task_routes={
        "app.features.sync.tasks.sync_all_cabinets": {"queue": "sync_queue"},
        "app.features.sync.tasks.sync_cabinet_data": {"queue": "sync_queue"},
    },
    
    # Настройки для периодических задач
    beat_schedule={
        "sync-all-cabinets": {
            "task": "app.features.sync.tasks.sync_all_cabinets",
            "schedule": float(sync_interval),  # Используем переменную окружения SYNC_INTERVAL
        },
    },
    
    # Настройки для повторных попыток
    task_default_retry_delay=60,  # 1 минута между попытками
    task_max_retries=3,
    
    # Настройки для работы с Redis
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=True,
    
    # Логирование
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)
