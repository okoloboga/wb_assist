from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from typing import List
import logging

from ...core.database import get_db
from .schemas import UserCreate, UserResponse
from .crud import UserCRUD

# Настройка логирования для routes
logger = logging.getLogger(__name__)

# Создаем роутер для пользователей
user_router = APIRouter(prefix="/users", tags=["users"])


# === ПОЛЬЗОВАТЕЛИ ===

@user_router.post(
    "/",
    response_model=UserResponse,
)
async def create_or_update_user(
    user_data: UserCreate,
    response: Response,
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
            response.status_code = status.HTTP_201_CREATED
        else:
            logger.info(
                f"API: Обновлен пользователь "
                f"telegram_id={user_data.telegram_id}"
            )
            response.status_code = status.HTTP_200_OK
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
    users = user_crud.get_all_users(skip=skip, limit=limit)
    return users