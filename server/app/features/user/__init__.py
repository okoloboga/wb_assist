"""
Управление пользователями.

Этот модуль содержит:
- models: модели базы данных (SQLAlchemy)
- schemas: схемы API (Pydantic)
- crud: операции с БД (CRUD - Create, Read, Update, Delete)
- routes: маршруты для работы с пользователями (/users, /users/{id})
"""

from .models import User
from .crud import UserCRUD, get_user_crud
from .routes import user_router

__all__ = [
    "User",
    "UserCRUD",
    "get_user_crud", 
    "user_router"
]