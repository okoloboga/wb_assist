from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Настройка логирования
logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI):
    """
    Настройка middleware для приложения
    """
    from .config import settings

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

    # Middleware для логирования запросов
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()

        # Логируем входящий запрос
        logger.info(
            f"Входящий запрос: {request.method} {request.url.path}"
        )

        response = await call_next(request)

        # Логируем время выполнения
        process_time = time.time() - start_time
        logger.info(
            f"Запрос выполнен за {process_time:.4f}s, "
            f"статус: {response.status_code}"
        )

        return response


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