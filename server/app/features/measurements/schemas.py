"""
Схемы для валидации параметров пользователей
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserMeasurementsBase(BaseModel):
    russian_size: Optional[str] = None
    shoulder_length: Optional[float] = None
    back_width: Optional[float] = None
    sleeve_length: Optional[float] = None
    back_length: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    hips: Optional[float] = None
    pants_length: Optional[float] = None
    waist_girth: Optional[float] = None
    rise_height: Optional[float] = None
    back_rise_height: Optional[float] = None


class UserMeasurementsCreate(UserMeasurementsBase):
    user_telegram_id: int


class UserMeasurementsUpdate(UserMeasurementsBase):
    pass


class UserMeasurementsResponse(UserMeasurementsBase):
    id: int
    user_telegram_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
