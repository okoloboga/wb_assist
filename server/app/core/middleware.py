from fastapi import FastAPI, Request, HTTPException, status
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

    # Единая middleware для логирования и проверки ключа
    @app.middleware("http")
    async def main_middleware(request: Request, call_next):
        # 1. Логируем входящий запрос
        start_time = time.time()
        logger.info(f"Входящий запрос: {request.method} {request.url.path}")

        # 2. Проверяем секретный ключ API, пропуская health-check
        if request.url.path not in ['/system/health', '/docs', '/openapi.json']:
            secret_header = request.headers.get("X-API-SECRET-KEY")
            if not secret_header or secret_header != settings.API_SECRET_KEY:
                logger.warning(f"Forbidden access attempt to {request.url.path} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Invalid or missing API Secret Key"}
                )
        
        # 3. Передаем запрос дальше и получаем ответ
        response = await call_next(request)

        # 4. Логируем время выполнения и статус ответа
        process_time = time.time() - start_time
        logger.info(
            f"Запрос 'f{request.method} {request.url.path}' выполнен за {process_time:.4f}s, "
            f"статус: {response.status_code}"
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