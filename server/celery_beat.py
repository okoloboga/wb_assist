#!/usr/bin/env python3
"""
Скрипт для запуска Celery beat (планировщик) для периодических задач
"""
import os
import sys

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.celery_app import celery_app

if __name__ == "__main__":
    # Запускаем Celery beat
    celery_app.start([
        "beat",
        "--loglevel=info",
        "--scheduler=celery.beat:PersistentScheduler",  # Постоянное хранение расписания
        "--schedule=/app/beat_data/celerybeat-schedule",  # Путь к файлу расписания
    ])
