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
sync_interval_env = os.getenv("SYNC_INTERVAL")
if not sync_interval_env:
    raise ValueError("SYNC_INTERVAL environment variable is required but not set")
sync_interval = int(sync_interval_env)

# Получаем интервал экспорта в Google Sheets (используем тот же что и для синхронизации)
export_interval = sync_interval

# Получаем время проверки алертов из переменной окружения
stock_alert_check_time = os.getenv("STOCK_ALERT_CHECK_TIME")
if not stock_alert_check_time:
    raise ValueError("STOCK_ALERT_CHECK_TIME environment variable is required but not set")

# Парсим время в формате HH:MM
try:
    hour, minute = map(int, stock_alert_check_time.split(':'))
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        raise ValueError("Invalid time format")
except ValueError as e:
    raise ValueError(f"STOCK_ALERT_CHECK_TIME must be in HH:MM format (e.g., '02:30' or '08:00'), got: {stock_alert_check_time}") from e

logger.info(f"Redis configuration:")
logger.info(f"  Redis URL: {redis_url}")
logger.info(f"Sync configuration:")
logger.info(f"  Sync interval: {sync_interval} seconds ({sync_interval/60:.1f} minutes)")
logger.info(f"  Export interval (same as sync): {export_interval} seconds ({export_interval/60:.1f} minutes)")
logger.info(f"Stock alerts configuration:")
logger.info(f"  Check time: {stock_alert_check_time} MSK")

# Создаем экземпляр Celery с Redis
celery_app = Celery(
    "wb_assist",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.features.sync.tasks",
        "app.features.stock_alerts.tasks",
        "app.features.export.tasks",
        "app.features.digest.tasks",
        "app.features.competitors.tasks",
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
        # Синхронизация - отдельная очередь
        "app.features.sync.tasks.sync_all_cabinets": {"queue": "sync_queue"},
        "app.features.sync.tasks.sync_cabinet_data": {"queue": "sync_queue"},
        
        # Алерты по остаткам - отдельная очередь
        "app.features.stock_alerts.tasks.aggregate_daily_sales_all_cabinets": {"queue": "alerts_queue"},
        "app.features.stock_alerts.tasks.check_stock_alerts_task": {"queue": "alerts_queue"},
        "app.features.stock_alerts.tasks.cleanup_old_analytics_task": {"queue": "alerts_queue"},
        
        # Экспорт в Google Sheets
        "app.features.export.tasks.export_all_to_spreadsheets": {"queue": "export_queue"},
        "app.features.export.tasks.export_cabinet_to_spreadsheet": {"queue": "export_queue"},
        
        # Отправка сводок в каналы
        "app.features.digest.tasks.check_digest_schedule": {"queue": "digest_queue"},
        "app.features.digest.tasks.send_digest_to_channel": {"queue": "digest_queue"},
        
        # Скрапинг конкурентов - отдельная очередь
        "app.features.competitors.tasks.scrape_competitor_task": {"queue": "scraping_queue"},
        "app.features.competitors.tasks.update_all_competitors_task": {"queue": "scraping_queue"},
    },
    
    # Настройки для периодических задач
    beat_schedule={
        "sync-all-cabinets": {
            "task": "app.features.sync.tasks.sync_all_cabinets",
            "schedule": float(sync_interval),  # Используем переменную окружения SYNC_INTERVAL
        },
        "aggregate-daily-sales": {
            "task": "app.features.stock_alerts.tasks.aggregate_daily_sales_all_cabinets",
            "schedule": crontab(hour=hour, minute=minute),  # Настраиваемое время из STOCK_ALERT_CHECK_TIME
        },
        "cleanup-old-analytics": {
            "task": "app.features.stock_alerts.tasks.cleanup_old_analytics_task",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Воскресенье 03:00
        },
        "export-all-to-sheets": {
            "task": "app.features.export.tasks.export_all_to_spreadsheets",
            "schedule": float(export_interval),  # Экспорт в Google Sheets (использует SYNC_INTERVAL)
        },
        "check-digest-schedule": {
            "task": "app.features.digest.tasks.check_digest_schedule",
            "schedule": crontab(minute='*'),  # Каждую минуту проверяем расписание
        },
        "update-all-competitors": {
            "task": "app.features.competitors.tasks.update_all_competitors_task",
            "schedule": crontab(hour=0, minute=0),  # Каждый день в полночь
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
