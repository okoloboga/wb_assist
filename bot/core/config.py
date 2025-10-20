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

    # OpenAI (LLM)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.2
    openai_max_tokens: int = 800
    openai_timeout: int = 30
    openai_system_prompt: Optional[str] = None
    
    # Google Sheets
    gs_enabled: bool = False
    gs_auth_method: str = "oauth"  # 'oauth' или 'service_account'
    gs_spreadsheet_id: Optional[str] = None
    gs_spreadsheet_title: str = "WB Assist LLM Export"
    gs_credentials_path: str = "config/credentials.json"
    gs_token_path: str = "config/token.json"
    gs_oauth_port: int = 8080
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
        notification_retry_attempts=int(os.getenv("NOTIFICATION_RETRY_ATTEMPTS", "5")),
        # OpenAI (LLM)
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
        openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "800")),
        openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
        openai_system_prompt=os.getenv("OPENAI_SYSTEM_PROMPT"),
        # Google Sheets
        gs_enabled=os.getenv("GS_ENABLED", "false").lower() == "true",
        gs_auth_method=os.getenv("GS_AUTH_METHOD", "oauth"),
        gs_spreadsheet_id=os.getenv("GS_SPREADSHEET_ID"),
        gs_spreadsheet_title=os.getenv("GS_SPREADSHEET_TITLE", "WB Assist LLM Export"),
        gs_credentials_path=os.getenv("GS_CREDENTIALS_PATH", "config/credentials.json"),
        gs_token_path=os.getenv("GS_TOKEN_PATH", "config/token.json"),
        gs_oauth_port=int(os.getenv("GS_OAUTH_PORT", "8080"))
    )


# Глобальная конфигурация
config = load_config()