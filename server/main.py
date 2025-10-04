from fastapi import FastAPI
from dotenv import load_dotenv

# Загружаем переменные окружения перед импортом настроек
load_dotenv()

from app.core.config import settings
from app.core.middleware import setup_middleware, setup_exception_handlers
from app.core.database import init_db
from app.features.system.routes import system_router
from app.features.user.routes import user_router
from app.features.stats.routes import stats_router
from app.features.wb_api.routes import router as wb_router


# Создаем FastAPI приложение с настройками из config
app = FastAPI(**settings.get_app_config())

# Инициализируем базу данных
init_db()

# Настраиваем middleware
setup_middleware(app)

# Настраиваем обработчики исключений
setup_exception_handlers(app)

# Подключаем роутеры
app.include_router(system_router)
app.include_router(user_router)
app.include_router(stats_router)
app.include_router(wb_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )