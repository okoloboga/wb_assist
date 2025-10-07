"""
Модуль автоматической синхронизации данных
"""
from .tasks import sync_cabinet_data, sync_all_cabinets, schedule_cabinet_sync

__all__ = ["sync_cabinet_data", "sync_all_cabinets", "schedule_cabinet_sync"]
