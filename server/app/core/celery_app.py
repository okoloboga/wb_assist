"""
Celery конфигурация для фоновых задач синхронизации
"""
from celery import Celery
from celery.schedules import crontab
import os

# Создаем экземпляр Celery
celery_app = Celery(
    "wb_assist",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "app.features.sync.tasks",
    ]
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Настройки для периодических задач
    beat_schedule={
        "sync-all-cabinets": {
            "task": "app.features.sync.tasks.sync_all_cabinets",
            "schedule": 60.0,  # Каждую минуту проверяем, кого нужно синхронизировать
        },
    },
    # Настройки для повторных попыток
    task_default_retry_delay=60,  # 1 минута между попытками
    task_max_retries=3,
)
