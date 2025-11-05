"""
Photo Processing module - обработка фотографий через нейронную сеть.

Модуль предоставляет:
- REST API для обработки фотографий по промпту
- Интеграцию с сервисом генерации изображений
- Сохранение результатов обработки
- Историю обработанных фотографий
"""

from .database import Base, engine, SessionLocal, get_db, init_db
from .models import PhotoProcessingResult
from .service import process_photo, save_processing_result, get_processing_history
from .image_client import ImageGenerationClient

__all__ = [
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    # Models
    "PhotoProcessingResult",
    # Service
    "process_photo",
    "save_processing_result",
    "get_processing_history",
    # Clients
    "ImageGenerationClient",
]

