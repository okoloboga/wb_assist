import os
from typing import List
import logging


class Settings:
    """
    Настройки приложения
    """

    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    APP_NAME: str = "Telegram Bot Backend API"
    APP_DESCRIPTION: str = "API для управления пользователями Telegram бота"
    APP_VERSION: str = "1.0.0"

    # === НАСТРОЙКИ СЕРВЕРА ===
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./users.db")

    # === НАСТРОЙКИ CORS ===
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = (
        os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
    )
    CORS_ALLOW_METHODS: List[str] = os.getenv(
        "CORS_ALLOW_METHODS", "*"
    ).split(",")
    CORS_ALLOW_HEADERS: List[str] = os.getenv(
        "CORS_ALLOW_HEADERS", "*"
    ).split(",")

    # === НАСТРОЙКИ БЕЗОПАСНОСТИ ===
    TRUSTED_HOSTS: List[str] = os.getenv("TRUSTED_HOSTS", "*").split(",")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY")

    # === НАСТРОЙКИ ЛОГИРОВАНИЯ ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # === НАСТРОЙКИ ПАГИНАЦИИ ===
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "100"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "1000"))

    def setup_logging(self):
        """
        Настройка логирования приложения
        """
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format=self.LOG_FORMAT
        )

        # Настройка логгера для uvicorn (если нужно)
        if self.DEBUG:
            logging.getLogger("uvicorn").setLevel(logging.DEBUG)
            logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)

    def get_cors_config(self) -> dict:
        """
        Получить конфигурацию CORS
        """
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": self.CORS_ALLOW_METHODS,
            "allow_headers": self.CORS_ALLOW_HEADERS,
        }

    def get_trusted_hosts_config(self) -> dict:
        """
        Получить конфигурацию доверенных хостов
        """
        return {
            "allowed_hosts": self.TRUSTED_HOSTS
        }

    def get_app_config(self) -> dict:
        """
        Получить конфигурацию FastAPI приложения
        """
        return {
            "title": self.APP_NAME,
            "description": self.APP_DESCRIPTION,
            "version": self.APP_VERSION,
            "debug": self.DEBUG
        }


# Создаем глобальный экземпляр настроек
settings = Settings()

# Настраиваем логирование при импорте модуля
settings.setup_logging()