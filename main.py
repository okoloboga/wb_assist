from fastapi import FastAPI

from config import settings
from middleware import setup_middleware, setup_exception_handlers
from routes import setup_routes


# Создаем FastAPI приложение с настройками из config
app = FastAPI(**settings.get_app_config())

# Настраиваем middleware
setup_middleware(app)

# Настраиваем обработчики исключений
setup_exception_handlers(app)

# Подключаем роутеры
setup_routes(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )