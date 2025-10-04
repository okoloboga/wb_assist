import pytest
from fastapi.testclient import TestClient
from app.features.user.schemas import UserCreate


class TestUserAPI:
    """Интеграционные тесты API пользователей"""

    def test_create_user_success(self, client):
        """Тест успешного создания пользователя через API"""
        user_data = {
            "telegram_id": 123456789,
            "username": "testuser",
            "first_name": "Тест",
            "last_name": "Пользователь"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == user_data["telegram_id"]
        assert data["username"] == user_data["username"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert "id" in data
        assert "created_at" in data

    def test_create_user_minimal_data(self, client):
        """Тест создания пользователя с минимальными данными"""
        user_data = {
            "telegram_id": 987654321,
            "first_name": "Минимум"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == user_data["telegram_id"]
        assert data["first_name"] == user_data["first_name"]
        assert data["username"] is None
        assert data["last_name"] is None

    def test_create_user_validation_error(self, client):
        """Тест валидационной ошибки при создании пользователя"""
        user_data = {
            "telegram_id": -123456789,  # Отрицательный ID
            "first_name": "Тест"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_user_missing_required_field(self, client):
        """Тест ошибки при отсутствии обязательного поля"""
        user_data = {
            "telegram_id": 123456789
            # Отсутствует first_name
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_update_existing_user(self, client, created_user):
        """Тест обновления существующего пользователя"""
        user_data = {
            "telegram_id": created_user.telegram_id,
            "username": "updated_user",
            "first_name": "Обновленное имя",
            "last_name": "Обновленная фамилия"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 200  # Обновление
        data = response.json()
        assert data["id"] == created_user.id
        assert data["username"] == "updated_user"
        assert data["first_name"] == "Обновленное имя"
        assert data["last_name"] == "Обновленная фамилия"

    def test_get_user_success(self, client, created_user):
        """Тест успешного получения пользователя"""
        response = client.get(f"/users/{created_user.telegram_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_user.id
        assert data["telegram_id"] == created_user.telegram_id
        assert data["username"] == created_user.username
        assert data["first_name"] == created_user.first_name

    def test_get_user_not_found(self, client):
        """Тест получения несуществующего пользователя"""
        response = client.get("/users/999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "не найден" in data["detail"]

    def test_get_user_invalid_telegram_id(self, client):
        """Тест получения пользователя с невалидным telegram_id"""
        response = client.get("/users/-123")
        
        assert response.status_code == 400
        data = response.json()
        assert "положительным числом" in data["detail"]

    def test_get_all_users_empty(self, client):
        """Тест получения всех пользователей из пустой БД"""
        response = client.get("/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_all_users_with_data(self, client, multiple_users):
        """Тест получения всех пользователей с данными"""
        response = client.get("/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("telegram_id" in user for user in data)
        assert all("first_name" in user for user in data)

    def test_get_all_users_pagination(self, client, multiple_users):
        """Тест пагинации при получении всех пользователей"""
        # Первая страница
        response = client.get("/users/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Вторая страница
        response = client.get("/users/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        # Третья страница (пустая)
        response = client.get("/users/?skip=3&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_create_user_duplicate_telegram_id(self, client, created_user):
        """Тест создания пользователя с дублирующимся telegram_id"""
        user_data = {
            "telegram_id": created_user.telegram_id,
            "first_name": "Дубликат"
        }
        
        response = client.post("/users/", json=user_data)
        
        # Должно обновить существующего пользователя
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_user.id
        assert data["first_name"] == "Дубликат"

    def test_api_error_handling(self, client):
        """Тест обработки ошибок API"""
        # Тест с некорректным JSON
        response = client.post(
            "/users/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_username_validation_in_api(self, client):
        """Тест валидации username через API"""
        user_data = {
            "telegram_id": 123456789,
            "username": "invalid@user!",
            "first_name": "Тест"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "Username может содержать только буквы" in str(data)

    def test_username_at_removal_in_api(self, client):
        """Тест удаления @ из username через API"""
        user_data = {
            "telegram_id": 123456789,
            "username": "@testuser",
            "first_name": "Тест"
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"

    def test_names_stripping_in_api(self, client):
        """Тест удаления пробелов в именах через API"""
        user_data = {
            "telegram_id": 123456789,
            "first_name": "  Тест  ",
            "last_name": "  Пользователь  "
        }
        
        response = client.post("/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Тест"
        assert data["last_name"] == "Пользователь"