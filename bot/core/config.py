import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""
    
    # Telegram Bot
    bot_token: str
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # Server API
    server_host: str = "http://127.0.0.1:8000"
    api_secret_key: str = ""
    
    # Redis (для кэширования и очередей)
    redis_url: str = "redis://localhost:6379"
    
    # Настройки
    log_level: str = "INFO"
    debug: bool = False
    
    # Retry настройки
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 30
    
    # Уведомления
    enable_notifications: bool = True
    notification_retry_attempts: int = 5
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации"""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        
        if not self.api_secret_key:
            raise ValueError("API_SECRET_KEY не найден в переменных окружения")


def load_config() -> BotConfig:
    """Загрузить конфигурацию из переменных окружения"""
    return BotConfig(
        bot_token=os.getenv("BOT_TOKEN", ""),
        webhook_url=os.getenv("WEBHOOK_URL"),
        webhook_secret=os.getenv("WEBHOOK_SECRET"),
        server_host=os.getenv("SERVER_HOST", "http://127.0.0.1:8000"),
        api_secret_key=os.getenv("API_SECRET_KEY", ""),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        enable_notifications=os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true",
        notification_retry_attempts=int(os.getenv("NOTIFICATION_RETRY_ATTEMPTS", "5"))
    )


# Глобальная конфигурация
config = load_config()