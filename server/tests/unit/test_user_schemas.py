import pytest
from pydantic import ValidationError
from app.features.user.schemas import UserCreate, UserUpdate, UserResponse


class TestUserCreateSchema:
    """Тесты схемы UserCreate"""

    def test_valid_user_create(self):
        """Тест создания валидного UserCreate"""
        user_data = {
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Тест",
            "last_name": "Пользователь"
        }
        
        user = UserCreate(**user_data)
        
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Тест"
        assert user.last_name == "Пользователь"

    def test_user_create_minimal_data(self):
        """Тест создания UserCreate с минимальными данными"""
        user_data = {
            "telegram_id": 987654321,
            "first_name": "Минимум"
        }
        
        user = UserCreate(**user_data)
        
        assert user.telegram_id == 987654321
        assert user.username is None
        assert user.first_name == "Минимум"
        assert user.last_name is None

    def test_username_with_at_removal(self):
        """Тест удаления @ из username"""
        user_data = {
            "telegram_id": 123456789,
            "username": "@testuser",
            "first_name": "Тест"
        }
        
        user = UserCreate(**user_data)
        assert user.username == "testuser"

    def test_username_validation_invalid_chars(self):
        """Тест валидации username с недопустимыми символами"""
        user_data = {
            "telegram_id": 123456789,
            "username": "test@user!",
            "first_name": "Тест"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "Username может содержать только буквы, цифры" in str(exc_info.value)

    def test_username_validation_valid_chars(self):
        """Тест валидации username с допустимыми символами"""
        valid_usernames = ["testuser", "test_user", "test-user", "test123", "TestUser"]
        
        for username in valid_usernames:
            user_data = {
                "telegram_id": 123456789,
                "username": username,
                "first_name": "Тест"
            }
            
            user = UserCreate(**user_data)
            assert user.username == username

    def test_telegram_id_validation_positive(self):
        """Тест валидации положительного telegram_id"""
        user_data = {
            "telegram_id": 123456789,
            "first_name": "Тест"
        }
        
        user = UserCreate(**user_data)
        assert user.telegram_id == 123456789

    def test_telegram_id_validation_negative(self):
        """Тест валидации отрицательного telegram_id"""
        user_data = {
            "telegram_id": -123456789,
            "first_name": "Тест"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_telegram_id_validation_zero(self):
        """Тест валидации нулевого telegram_id"""
        user_data = {
            "telegram_id": 0,
            "first_name": "Тест"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_first_name_required(self):
        """Тест обязательности поля first_name"""
        user_data = {
            "telegram_id": 123456789
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "first_name" in str(exc_info.value)

    def test_first_name_empty_string(self):
        """Тест валидации пустой строки first_name"""
        user_data = {
            "telegram_id": 123456789,
            "first_name": "   "
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**user_data)
        
        assert "Имя не может быть пустым" in str(exc_info.value)

    def test_names_stripping(self):
        """Тест удаления пробелов в именах"""
        user_data = {
            "telegram_id": 123456789,
            "first_name": "  Тест  ",
            "last_name": "  Пользователь  "
        }
        
        user = UserCreate(**user_data)
        assert user.first_name == "Тест"
        assert user.last_name == "Пользователь"


class TestUserUpdateSchema:
    """Тесты схемы UserUpdate"""

    def test_valid_user_update(self):
        """Тест создания валидного UserUpdate"""
        update_data = {
            "username": "newuser",
            "first_name": "Новое имя"
        }
        
        user_update = UserUpdate(**update_data)
        
        assert user_update.username == "newuser"
        assert user_update.first_name == "Новое имя"
        assert user_update.last_name is None

    def test_user_update_empty(self):
        """Тест создания пустого UserUpdate"""
        user_update = UserUpdate()
        
        assert user_update.username is None
        assert user_update.first_name is None
        assert user_update.last_name is None

    def test_user_update_username_validation(self):
        """Тест валидации username в UserUpdate"""
        update_data = {
            "username": "invalid@user!"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**update_data)
        
        assert "Username может содержать только буквы, цифры" in str(exc_info.value)

    def test_user_update_names_stripping(self):
        """Тест удаления пробелов в именах в UserUpdate"""
        update_data = {
            "first_name": "  Новое имя  ",
            "last_name": "  Новая фамилия  "
        }
        
        user_update = UserUpdate(**update_data)
        assert user_update.first_name == "Новое имя"
        assert user_update.last_name == "Новая фамилия"


class TestUserResponseSchema:
    """Тесты схемы UserResponse"""

    def test_user_response_from_model(self, created_user):
        """Тест создания UserResponse из модели User"""
        user_response = UserResponse.model_validate(created_user)
        
        assert user_response.id == created_user.id
        assert user_response.telegram_id == created_user.telegram_id
        assert user_response.username == created_user.username
        assert user_response.first_name == created_user.first_name
        assert user_response.last_name == created_user.last_name
        assert user_response.created_at == created_user.created_at
        assert user_response.updated_at == created_user.updated_at

    def test_user_response_serialization(self, created_user):
        """Тест сериализации UserResponse в словарь"""
        user_response = UserResponse.model_validate(created_user)
        user_dict = user_response.model_dump()
        
        assert isinstance(user_dict, dict)
        assert "id" in user_dict
        assert "telegram_id" in user_dict
        assert "username" in user_dict
        assert "first_name" in user_dict
        assert "last_name" in user_dict
        assert "created_at" in user_dict
        assert "updated_at" in user_dict