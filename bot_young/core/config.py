"""
Конфигурация bot_young
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""
    
    # Telegram Bot
    bot_token: str
    
    # Server API
    server_host: str = "http://127.0.0.1:8000"
    api_secret_key: str = ""
    
    # Main Bot (для ссылок)
    main_bot_username: str = ""
    
    # Настройки
    log_level: str = "INFO"
    
    # Timezone
    default_timezone: str = "Europe/Moscow"
    
    def __post_init__(self):
        """Валидация конфигурации"""
        if not self.bot_token:
            raise ValueError("BOT_YOUNG_TOKEN не найден в переменных окружения")
        
        if not self.api_secret_key:
            raise ValueError("API_SECRET_KEY не найден в переменных окружения")


def load_config() -> BotConfig:
    """Загрузить конфигурацию из переменных окружения"""
    return BotConfig(
        bot_token=os.getenv("BOT_YOUNG_TOKEN", ""),
        server_host=os.getenv("SERVER_HOST", "http://127.0.0.1:8000"),
        api_secret_key=os.getenv("API_SECRET_KEY", ""),
        main_bot_username=os.getenv("MAIN_BOT_USERNAME", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow"),
    )


# Глобальная конфигурация
config = load_config()

