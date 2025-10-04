import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from app.features.user.models import User


class TestUserModel:
    """Тесты модели User"""

    def test_user_creation(self, db_session):
        """Тест создания пользователя с валидными данными"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Тест",
            last_name="Пользователь"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Тест"
        assert user.last_name == "Пользователь"
        assert user.created_at is not None
        assert user.updated_at is None

    def test_user_creation_minimal_data(self, db_session):
        """Тест создания пользователя с минимальными данными"""
        user = User(
            telegram_id=987654321,
            first_name="Минимум"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.telegram_id == 987654321
        assert user.username is None
        assert user.first_name == "Минимум"
        assert user.last_name is None

    def test_user_telegram_id_unique(self, db_session):
        """Тест уникальности telegram_id"""
        # Создаем первого пользователя
        user1 = User(
            telegram_id=123456789,
            first_name="Первый"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Пытаемся создать второго с тем же telegram_id
        user2 = User(
            telegram_id=123456789,
            first_name="Второй"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_repr(self, db_session):
        """Тест строкового представления пользователя"""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Тест"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert "123456789" in repr_str
        assert "testuser" in repr_str

    def test_user_created_at_auto_set(self, db_session):
        """Тест автоматической установки created_at"""
        before_creation = datetime.now(timezone.utc)  # Используем timezone-aware datetime
        
        user = User(
            telegram_id=123456789,
            first_name="Тест"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        after_creation = datetime.now(timezone.utc)  # Используем timezone-aware datetime
        
        assert user.created_at is not None
        # Проверяем что created_at находится в разумных пределах (с запасом в 5 секунд)
        assert before_creation - timedelta(seconds=5) <= user.created_at <= after_creation + timedelta(seconds=1)

    def test_user_updated_at_none_initially(self, db_session):
        """Тест что updated_at изначально None"""
        user = User(
            telegram_id=123456789,
            first_name="Тест"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.updated_at is None

    def test_user_updated_at_auto_set_on_update(self, db_session):
        """Тест автоматической установки updated_at при обновлении"""
        user = User(
            telegram_id=123456789,
            first_name="Тест"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Обновляем пользователя
        user.first_name = "Обновленный"
        db_session.commit()
        db_session.refresh(user)
        
        assert user.updated_at is not None
        assert user.first_name == "Обновленный"