"""
Пакет для работы с агрегированным семантическим ядром по кабинету.

Сейчас содержит только модель и CRUD-слой. Интеграция с Bot API и Celery
будет добавлена на следующих этапах миграции.
"""

from .models import CabinetSemanticCore

__all__ = ["CabinetSemanticCore"]




