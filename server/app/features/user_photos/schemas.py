"""
Схемы для валидации данных фото пользователей
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserPhotoBase(BaseModel):
    file_path: str
    file_url: Optional[str] = None
    is_active: bool = True


class UserPhotoCreate(UserPhotoBase):
    user_telegram_id: int


class UserPhotoResponse(UserPhotoBase):
    id: int
    user_telegram_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
