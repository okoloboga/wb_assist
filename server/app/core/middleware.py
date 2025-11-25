from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import os

# Настройка логирования
logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI):
    """
    Настройка middleware для приложения
    """
    from .config import settings

    # Единая middleware для логирования и проверки ключа
    @app.middleware("http")
    async def main_middleware(request: Request, call_next):
        # 1. Логируем входящий запрос
        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Входящий запрос: {request.method} {request.url.path} от {client_host}")

        # 2. Проверяем секретный ключ API, пропуская health-check и документацию
        public_paths = ['/system/health', '/docs', '/openapi.json', '/redoc']
        if request.url.path not in public_paths and not request.url.path.startswith('/docs'):
            secret_header = request.headers.get("X-API-SECRET-KEY")
            # Используем ключ из переменной окружения напрямую
            expected_key = os.getenv('API_SECRET_KEY') or settings.API_SECRET_KEY
            
            if not secret_header:
                logger.warning(
                    f"❌ Неудачная попытка аутентификации: отсутствует API ключ | "
                    f"Путь: {request.url.path} | IP: {client_host} | "
                    f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Missing API Secret Key"}
                )
            
            if secret_header != expected_key:
                logger.warning(
                    f"❌ Неудачная попытка аутентификации: неверный API ключ | "
                    f"Путь: {request.url.path} | IP: {client_host} | "
                    f"Предоставленный ключ: {secret_header[:8]}... | "
                    f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid API Secret Key"}
                )
            
            logger.debug(f"✅ Аутентификация успешна для {request.url.path}")
        
        # 3. Передаем запрос дальше и получаем ответ
        response = await call_next(request)

        # 4. Логируем время выполнения и статус ответа
        process_time = time.time() - start_time
        
        # Разный уровень логирования в зависимости от статуса
        if response.status_code >= 500:
            logger.error(
                f"❌ Запрос {request.method} {request.url.path} завершился с ошибкой | "
                f"Статус: {response.status_code} | Время: {process_time:.4f}s"
            )
        elif response.status_code >= 400:
            logger.warning(
                f"⚠️ Запрос {request.method} {request.url.path} завершился с ошибкой клиента | "
                f"Статус: {response.status_code} | Время: {process_time:.4f}s"
            )
        else:
            logger.info(
                f"✅ Запрос {request.method} {request.url.path} выполнен успешно | "
                f"Статус: {response.status_code} | Время: {process_time:.4f}s"
            )

        return response

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        **settings.get_cors_config()
    )

    # Trusted hosts middleware
    app.add_middleware(
        TrustedHostMiddleware,
        **settings.get_trusted_hosts_config()
    )


def setup_exception_handlers(app: FastAPI):
    """
    Настройка глобальных обработчиков исключений
    """

    # Глобальный обработчик исключений
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Необработанная ошибка: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"}
        )