from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


# Схема для создания/обновления пользователя
class UserCreate(BaseModel):
    telegram_id: int = Field(
        ..., gt=0, description="Telegram ID пользователя (должен быть положительным)"
    )
    username: Optional[str] = Field(
        None, description="Username в Telegram (без @)"
    )
    first_name: str = Field(
        ..., min_length=1, max_length=64, description="Имя пользователя"
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=64, description="Фамилия пользователя"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is not None and v.strip():  # Проверяем что не None и не пустая строка
            # Убираем @ если он есть в начале
            if v.startswith('@'):
                v = v[1:]
            # Проверяем что username содержит только допустимые символы
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError(
                    'Username может содержать только буквы, цифры, '
                    'подчеркивания и дефисы'
                )
            # Проверяем длину после обработки
            if len(v) < 1 or len(v) > 32:
                raise ValueError("Username должен быть от 1 до 32 символов")
        elif v is not None and not v.strip():
            # Если передана пустая строка, делаем None
            return None
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        if v is not None and v.strip() == '':
            raise ValueError('Имя не может быть пустым')
        return v.strip() if v else v

    @field_validator('telegram_id')
    @classmethod
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

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=32)
    first_name: Optional[str] = Field(None, min_length=1, max_length=64)
    last_name: Optional[str] = Field(None, min_length=1, max_length=64)

    @field_validator('username')
    @classmethod
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

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_names(cls, v):
        if v is not None and v.strip() == '':
            raise ValueError('Имя не может быть пустым')
        return v.strip() if v else v