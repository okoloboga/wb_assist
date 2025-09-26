from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


# Схема для создания/обновления пользователя
class UserCreate(BaseModel):
    telegram_id: int = Field(
        ..., gt=0, description="Telegram ID пользователя (должен быть положительным)"
    )
    username: Optional[str] = Field(
        None, min_length=1, max_length=32, description="Username в Telegram (без @)"
    )
    first_name: str = Field(
        ..., min_length=1, max_length=64, description="Имя пользователя"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=64, description="Фамилия пользователя"
    )

    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            # Убираем @ если он есть в начале
            if v.startswith('@'):
                v = v[1:]
            # Проверяем что username содержит только допустимые символы
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError(
                    'Username может содержать только буквы, цифры, '
                    'подчеркивания и дефисы'
                )
        return v

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and v.strip() == '':
            raise ValueError('Имя не может быть пустым')
        return v.strip() if v else v

    @validator('telegram_id')
    def validate_telegram_id(cls, v):
        if v <= 0:
            raise ValueError('Telegram ID должен быть положительным числом')
        return v


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=32)
    first_name: Optional[str] = Field(None, min_length=1, max_length=64)
    last_name: Optional[str] = Field(None, min_length=1, max_length=64)

    @validator('username')
    def validate_username(cls, v):
        if v is not None:
            if v.startswith('@'):
                v = v[1:]
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError(
                    'Username может содержать только буквы, цифры, '
                    'подчеркивания и дефисы'
                )
        return v

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and v.strip() == '':
            raise ValueError('Имя не может быть пустым')
        return v.strip() if v else v