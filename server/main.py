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
from app.features.bot_api.routes import router as bot_router

# Импортируем модели для создания таблиц
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBAnalyticsCache, WBWarehouse, WBSyncLog

# Создаем FastAPI приложение с настройками из config
app = FastAPI(**settings.get_app_config())

# Инициализируем базу данных ПОСЛЕ импорта всех моделей
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
app.include_router(bot_router, prefix="/api/v1/bot", tags=["Bot API"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)