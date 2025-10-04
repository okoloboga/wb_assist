import pytest
from sqlalchemy.orm import Session
from app.features.user.crud import UserCRUD
from app.features.user.models import User
from app.features.user.schemas import UserCreate, UserUpdate


class TestUserCRUD:
    """Тесты CRUD операций для пользователей"""

    def test_get_user_by_telegram_id_existing(self, db_session, created_user):
        """Тест получения существующего пользователя по telegram_id"""
        crud = UserCRUD(db_session)
        
        user = crud.get_user_by_telegram_id(created_user.telegram_id)
        
        assert user is not None
        assert user.id == created_user.id
        assert user.telegram_id == created_user.telegram_id
        assert user.username == created_user.username
        assert user.first_name == created_user.first_name

    def test_get_user_by_telegram_id_not_existing(self, db_session):
        """Тест получения несуществующего пользователя по telegram_id"""
        crud = UserCRUD(db_session)
        
        user = crud.get_user_by_telegram_id(999999999)
        
        assert user is None

    def test_create_user_success(self, db_session, sample_user_create):
        """Тест успешного создания пользователя"""
        crud = UserCRUD(db_session)
        
        user = crud.create_user(sample_user_create)
        
        assert user is not None
        assert user.telegram_id == sample_user_create.telegram_id
        assert user.username == sample_user_create.username
        assert user.first_name == sample_user_create.first_name
        assert user.last_name == sample_user_create.last_name
        assert user.id is not None

    def test_create_user_duplicate_telegram_id(self, db_session, created_user):
        """Тест создания пользователя с дублирующимся telegram_id"""
        crud = UserCRUD(db_session)
        
        duplicate_user_data = UserCreate(
            telegram_id=created_user.telegram_id,
            first_name="Дубликат"
        )
        
        with pytest.raises(Exception):  # IntegrityError или другая ошибка БД
            crud.create_user(duplicate_user_data)

    def test_update_user_existing(self, db_session, created_user):
        """Тест обновления существующего пользователя"""
        crud = UserCRUD(db_session)
        
        update_data = UserUpdate(
            username="updated_user",
            first_name="Обновленное имя"
        )
        
        updated_user = crud.update_user(created_user.telegram_id, update_data)
        
        assert updated_user is not None
        assert updated_user.username == "updated_user"
        assert updated_user.first_name == "Обновленное имя"
        assert updated_user.last_name == created_user.last_name  # Не изменилось
        assert updated_user.updated_at is not None

    def test_update_user_partial(self, db_session, created_user):
        """Тест частичного обновления пользователя"""
        crud = UserCRUD(db_session)
        
        update_data = UserUpdate(username="only_username_updated")
        
        updated_user = crud.update_user(created_user.telegram_id, update_data)
        
        assert updated_user is not None
        assert updated_user.username == "only_username_updated"
        assert updated_user.first_name == created_user.first_name  # Не изменилось
        assert updated_user.last_name == created_user.last_name  # Не изменилось

    def test_update_user_not_existing(self, db_session):
        """Тест обновления несуществующего пользователя"""
        crud = UserCRUD(db_session)
        
        update_data = UserUpdate(first_name="Новое имя")
        
        updated_user = crud.update_user(999999999, update_data)
        
        assert updated_user is None

    def test_create_or_update_user_new(self, db_session, sample_user_create):
        """Тест create_or_update_user для нового пользователя"""
        crud = UserCRUD(db_session)
        
        user, created = crud.create_or_update_user(sample_user_create)
        
        assert created is True
        assert user is not None
        assert user.telegram_id == sample_user_create.telegram_id
        assert user.first_name == sample_user_create.first_name

    def test_create_or_update_user_existing(self, db_session, created_user):
        """Тест create_or_update_user для существующего пользователя"""
        crud = UserCRUD(db_session)
        
        update_data = UserCreate(
            telegram_id=created_user.telegram_id,
            username="updated_username",
            first_name="Обновленное имя",
            last_name="Обновленная фамилия"
        )
        
        user, created = crud.create_or_update_user(update_data)
        
        assert created is False
        assert user is not None
        assert user.id == created_user.id  # Тот же пользователь
        assert user.username == "updated_username"
        assert user.first_name == "Обновленное имя"
        assert user.last_name == "Обновленная фамилия"
        assert user.updated_at is not None

    def test_get_all_users_empty(self, db_session):
        """Тест получения всех пользователей из пустой БД"""
        crud = UserCRUD(db_session)
        
        users = crud.get_all_users()
        
        assert users == []

    def test_get_all_users_with_data(self, db_session, multiple_users):
        """Тест получения всех пользователей с данными"""
        crud = UserCRUD(db_session)
        
        users = crud.get_all_users()
        
        assert len(users) == 3
        assert all(isinstance(user, User) for user in users)

    def test_get_all_users_pagination(self, db_session, multiple_users):
        """Тест пагинации при получении всех пользователей"""
        crud = UserCRUD(db_session)
        
        # Первая страница
        users_page1 = crud.get_all_users(skip=0, limit=2)
        assert len(users_page1) == 2
        
        # Вторая страница
        users_page2 = crud.get_all_users(skip=2, limit=2)
        assert len(users_page2) == 1
        
        # Третья страница (пустая)
        users_page3 = crud.get_all_users(skip=3, limit=2)
        assert len(users_page3) == 0

    def test_get_users_count_empty(self, db_session):
        """Тест подсчета пользователей в пустой БД"""
        crud = UserCRUD(db_session)
        
        count = crud.get_users_count()
        
        assert count == 0

    def test_get_users_count_with_data(self, db_session, multiple_users):
        """Тест подсчета пользователей с данными"""
        crud = UserCRUD(db_session)
        
        count = crud.get_users_count()
        
        assert count == 3

    def test_get_total_users(self, db_session, multiple_users):
        """Тест метода get_total_users"""
        crud = UserCRUD(db_session)
        
        total = crud.get_total_users()
        
        assert total == 3

    def test_crud_rollback_on_error(self, db_session, sample_user_create):
        """Тест отката транзакции при ошибке"""
        crud = UserCRUD(db_session)
        
        # Создаем пользователя
        user1 = crud.create_user(sample_user_create)
        
        # Пытаемся создать пользователя с тем же telegram_id
        duplicate_data = UserCreate(
            telegram_id=sample_user_create.telegram_id,
            first_name="Дубликат"
        )
        
        with pytest.raises(Exception):
            crud.create_user(duplicate_data)
        
        # Проверяем что первый пользователь остался
        db_session.refresh(user1)
        assert user1.id is not None
        assert user1.telegram_id == sample_user_create.telegram_id