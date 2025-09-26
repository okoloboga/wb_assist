from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate, UserUpdate
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserCRUD:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_telegram_id(self, telegram_id: int) -> User:
        """Получить пользователя по telegram_id"""
        return self.db.query(User).filter(
            User.telegram_id == telegram_id
        ).first()

    def create_user(self, user_data: UserCreate) -> User:
        """Создать нового пользователя"""
        try:
            user = User(
                telegram_id=user_data.telegram_id,
                username=user_data.username,
                first_name=user_data.first_name,
                last_name=user_data.last_name
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Создан пользователь: {user_data.telegram_id}")
            return user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка создания пользователя: {e}")
            raise

    def update_user(self, telegram_id: int, update_data: UserUpdate) -> User:
        """Обновить данные пользователя"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        # Обновляем только переданные поля
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"Обновлен пользователь: {telegram_id}")
        return user

    def create_or_update_user(
        self, user_data: UserCreate
    ) -> tuple[User, bool]:
        """
        Создать нового пользователя или обновить существующего.
        Возвращает (user, created) где created=True если создан новый
        """
        existing_user = self.get_user_by_telegram_id(user_data.telegram_id)

        if existing_user:
            # Обновляем существующего пользователя
            existing_user.username = user_data.username
            existing_user.first_name = user_data.first_name
            existing_user.last_name = user_data.last_name
            existing_user.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(existing_user)
            logger.info(
                f"Обновлен существующий пользователь: "
                f"{user_data.telegram_id}"
            )
            return existing_user, False
        else:
            # Создаем нового пользователя
            new_user = self.create_user(user_data)
            logger.info(f"Создан новый пользователь: {user_data.telegram_id}")
            return new_user, True

    def get_all_users(self) -> list[User]:
        """Получить всех пользователей"""
        return self.db.query(User).all()

    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        return self.db.query(User).count()

    async def get_total_users(self) -> int:
        """Получить общее количество пользователей (асинхронная версия)"""
        return self.db.query(User).count()


def get_user_crud(db: Session) -> UserCRUD:
    return UserCRUD(db)