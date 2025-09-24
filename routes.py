from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from typing import List
import logging

from database import get_db
from schemas import UserCreate, UserResponse
from crud import UserCRUD

# Настройка логирования для routes
logger = logging.getLogger(__name__)

# Создаем роутер для пользователей
user_router = APIRouter(prefix="/users", tags=["users"])

# Создаем роутер для статистики
stats_router = APIRouter(prefix="/stats", tags=["statistics"])

# Создаем роутер для системных эндпоинтов
system_router = APIRouter(tags=["system"])


# === ПОЛЬЗОВАТЕЛИ ===

@user_router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_or_update_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Создать нового пользователя или обновить существующего.
    Ключевое поле - telegram_id.
    """
    try:
        user_crud = UserCRUD(db)
        user, created = user_crud.create_or_update_user(user_data)

        if created:
            logger.info(
                f"API: Создан новый пользователь "
                f"telegram_id={user_data.telegram_id}"
            )
            return user
        else:
            logger.info(
                f"API: Обновлен пользователь "
                f"telegram_id={user_data.telegram_id}"
            )
            # Возвращаем статус 200 для обновления
            return user

    except IntegrityError as e:
        logger.error(
            f"API: Ошибка целостности данных для "
            f"telegram_id={user_data.telegram_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: возможно, пользователь уже существует"
        )
    except SQLAlchemyError as e:
        logger.error(f"API: Ошибка базы данных: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        logger.error(
            f"API: Неожиданная ошибка при создании/обновлении "
            f"пользователя: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@user_router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить пользователя по telegram_id.
    """
    try:
        # Валидация telegram_id
        if telegram_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="telegram_id должен быть положительным числом"
            )

        user_crud = UserCRUD(db)
        user = user_crud.get_user_by_telegram_id(telegram_id)
        if not user:
            logger.warning(
                f"API: Пользователь не найден: telegram_id={telegram_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с telegram_id {telegram_id} не найден"
            )

        logger.info(f"API: Получен пользователь telegram_id={telegram_id}")
        return user

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(
            f"API: Ошибка базы данных при получении пользователя: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных"
        )
    except Exception as e:
        logger.error(
            f"API: Неожиданная ошибка при получении пользователя: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@user_router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получить список всех пользователей с пагинацией.
    """
    user_crud = UserCRUD(db)
    users = user_crud.get_all_users()
    return users


# === СТАТИСТИКА ===

@stats_router.get("/users-count")
async def get_users_count(
    db: Session = Depends(get_db)
):
    """
    Получить общее количество пользователей.
    """
    user_crud = UserCRUD(db)
    count = user_crud.get_users_count()
    return {"total_users": count}


# === СИСТЕМНЫЕ ЭНДПОИНТЫ ===

@system_router.get("/")
async def root():
    """
    Корневой эндпоинт API
    """
    return {"message": "Telegram Bot Backend API", "status": "running"}


@system_router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Проверка здоровья приложения и подключения к БД
    """
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


def setup_routes(app):
    """
    Подключение всех роутеров к FastAPI приложению
    """
    app.include_router(system_router)
    app.include_router(user_router)
    app.include_router(stats_router)