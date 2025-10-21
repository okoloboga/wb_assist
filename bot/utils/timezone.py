"""
Утилиты для работы с временными зонами
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# Московское время (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))


class TimezoneUtils:
    """Утилиты для работы с временными зонами"""
    
    @staticmethod
    def now_utc() -> datetime:
        """Текущее время в UTC"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def now_msk() -> datetime:
        """Текущее время в МСК"""
        return datetime.now(MSK_TZ)
    
    @staticmethod
    def to_msk(dt: datetime) -> datetime:
        """Конвертация datetime в МСК"""
        if dt.tzinfo is None:
            # Если timezone не указан, считаем что это UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MSK_TZ)
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Конвертация datetime в UTC"""
        if dt.tzinfo is None:
            # Если timezone не указан, считаем что это МСК
            dt = dt.replace(tzinfo=MSK_TZ)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def parse_wb_datetime(date_str: str) -> Optional[datetime]:
        """Парсинг даты из WB API (предполагается МСК)"""
        try:
            if not date_str:
                return None
            
            # Парсим ISO формат
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Если timezone не указан, считаем что это МСК
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ)
            
            # Конвертируем в UTC для хранения в БД
            return dt.astimezone(timezone.utc)
            
        except Exception:
            return None
    
    @staticmethod
    def format_for_user(dt: datetime) -> str:
        """Форматирование даты для пользователя в МСК"""
        msk_dt = TimezoneUtils.to_msk(dt)
        return msk_dt.strftime("%d.%m.%Y %H:%M")
    
    @staticmethod
    def format_time_only(dt: datetime) -> str:
        """Форматирование только времени в МСК"""
        msk_dt = TimezoneUtils.to_msk(dt)
        return msk_dt.strftime("%H:%M:%S")
    
    @staticmethod
    def get_today_start_msk() -> datetime:
        """Начало сегодняшнего дня в МСК"""
        today = TimezoneUtils.now_msk().date()
        return datetime.combine(today, datetime.min.time()).replace(tzinfo=MSK_TZ)
    
    @staticmethod
    def get_yesterday_start_msk() -> datetime:
        """Начало вчерашнего дня в МСК"""
        yesterday = TimezoneUtils.now_msk().date() - timedelta(days=1)
        return datetime.combine(yesterday, datetime.min.time()).replace(tzinfo=MSK_TZ)
    
    @staticmethod
    def get_week_start_msk() -> datetime:
        """Начало текущей недели в МСК"""
        today = TimezoneUtils.now_msk()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_month_start_msk() -> datetime:
        """Начало текущего месяца в МСК"""
        today = TimezoneUtils.now_msk()
        return today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
