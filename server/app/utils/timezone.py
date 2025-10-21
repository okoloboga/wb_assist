"""
Утилиты для работы с timezone - всё по МСК (UTC+3)
WB отдаёт данные в МСК, поэтому всё храним и отображаем в МСК
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# МСК timezone (UTC+3)
try:
    from zoneinfo import ZoneInfo
    MSK_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    # Fallback для старых версий Python
    MSK_TZ = timezone(timedelta(hours=3))


class TimezoneUtils:
    """Утилиты для работы с timezone - всё по МСК"""
    
    @staticmethod
    def now_msk() -> datetime:
        """Текущее время в МСК"""
        return datetime.now(MSK_TZ)
    
    @staticmethod
    def now_utc() -> datetime:
        """Текущее время в UTC"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def parse_wb_datetime(date_str: str) -> Optional[datetime]:
        """
        Парсинг даты из WB API
        WB отдаёт данные в МСК, поэтому парсим как МСК
        """
        if not date_str:
            return None
        
        try:
            # Пробуем разные форматы дат от WB API
            formats = [
                "%Y-%m-%dT%H:%M:%S%z",  # С timezone
                "%Y-%m-%d %H:%M:%S%z",  # С timezone
                "%Y-%m-%dT%H:%M:%S",    # Без timezone - считаем МСК
                "%Y-%m-%d %H:%M:%S",    # Без timezone - считаем МСК
                "%Y-%m-%d"              # Только дата - считаем МСК
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    
                    if dt.tzinfo is None:
                        # Без timezone - считаем МСК
                        dt = dt.replace(tzinfo=MSK_TZ)
                    else:
                        # С timezone - конвертируем в МСК
                        dt = dt.astimezone(MSK_TZ)
                    
                    return dt
                except ValueError:
                    continue
            
            logger.warning(f"Не удалось распарсить дату: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка парсинга даты {date_str}: {e}")
            return None
    
    @staticmethod
    def format_for_user(dt: datetime) -> str:
        """
        Форматирование времени для пользователя в МСК
        """
        if not dt:
            return "N/A"
        
        try:
            # Если время без timezone, считаем МСК
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ)
            else:
                # Конвертируем в МСК
                dt = dt.astimezone(MSK_TZ)
            
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception as e:
            logger.error(f"Ошибка форматирования времени {dt}: {e}")
            return "N/A"
    
    @staticmethod
    def format_time_only(dt: datetime) -> str:
        """Форматирование только времени в МСК"""
        if not dt:
            return "N/A"
        
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ)
            else:
                dt = dt.astimezone(MSK_TZ)
            
            return dt.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Ошибка форматирования времени {dt}: {e}")
            return "N/A"
    
    @staticmethod
    def format_date_only(dt: datetime) -> str:
        """Форматирование только даты в МСК"""
        if not dt:
            return "N/A"
        
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK_TZ)
            else:
                dt = dt.astimezone(MSK_TZ)
            
            return dt.strftime("%d.%m.%Y")
        except Exception as e:
            logger.error(f"Ошибка форматирования даты {dt}: {e}")
            return "N/A"
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Конвертация МСК времени в UTC для хранения в БД"""
        if dt.tzinfo is None:
            # Если без timezone, считаем МСК
            dt = dt.replace(tzinfo=MSK_TZ)
        
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def from_utc(dt: datetime) -> datetime:
        """Конвертация UTC времени в МСК для отображения"""
        if dt.tzinfo is None:
            # Если без timezone, считаем UTC
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone(MSK_TZ)
    
    @staticmethod
    def get_today_start_msk() -> datetime:
        """Начало сегодняшнего дня в МСК"""
        now = TimezoneUtils.now_msk()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_yesterday_start_msk() -> datetime:
        """Начало вчерашнего дня в МСК"""
        today = TimezoneUtils.get_today_start_msk()
        return today - timedelta(days=1)
    
    @staticmethod
    def get_week_start_msk() -> datetime:
        """Начало текущей недели (понедельник) в МСК"""
        today = TimezoneUtils.get_today_start_msk()
        days_since_monday = today.weekday()
        return today - timedelta(days=days_since_monday)
    
    @staticmethod
    def get_month_start_msk() -> datetime:
        """Начало текущего месяца в МСК"""
        now = TimezoneUtils.now_msk()
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
