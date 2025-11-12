import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Загружаем переменные окружения только если .env файл существует
# В Docker переменные окружения уже установлены через docker-compose.yml
env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    # Пробуем загрузить из текущей директории (для локального запуска)
    load_dotenv(override=False)  # override=False означает, что не перезаписываем существующие переменные


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
    request_timeout: int = 300  # 5 минут для синхронизации
    
    # Уведомления
    enable_notifications: bool = True
    notification_retry_attempts: int = 5
    
    # Webhook настройки
    webhook_port: int = 8001  # Порт для webhook сервера

    # Адрес GPT сервиса
    gpt_service_url: str = "http://127.0.0.1:9000"
    
    # Адрес AI Chat сервиса
    ai_chat_service_url: str = "http://127.0.0.1:9001"
    
    # LLM (GPT) настройки
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 800
    openai_timeout: int = 30
    openai_system_prompt: Optional[str] = None
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации"""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        
        if not self.api_secret_key:
            raise ValueError("API_SECRET_KEY не найден в переменных окружения")


def load_config() -> BotConfig:
    """Загрузить конфигурацию из переменных окружения"""
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    return BotConfig(
        bot_token=bot_token,
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
        notification_retry_attempts=int(os.getenv("NOTIFICATION_RETRY_ATTEMPTS", "5")),
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8001")),
        # GPT Service URL
        gpt_service_url=os.getenv("GPT_SERVICE_URL", "http://127.0.0.1:9000"),
        # AI Chat Service URL
        ai_chat_service_url=os.getenv("AI_CHAT_SERVICE_URL", "http://127.0.0.1:9001"),
        # LLM (GPT)
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "800")),
        openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
        openai_system_prompt=os.getenv("OPENAI_SYSTEM_PROMPT")
    )


# Глобальная конфигурация
config = load_config()