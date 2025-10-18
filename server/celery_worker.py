#!/usr/bin/env python3
"""
Скрипт для запуска Celery worker для фоновых задач синхронизации
"""
import os
import sys

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.celery_app import celery_app

if __name__ == "__main__":
    # Запускаем Celery worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=2",  # 2 воркера для обработки задач
        "--queues=sync_queue",  # Очередь для задач синхронизации
    ])
