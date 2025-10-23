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
from app.features.bot_api.routes_sales import router as bot_sales_router
from app.features.notifications.api.settings import router as notification_settings_router
from app.features.notifications.api.test import router as notification_test_router
from app.features.wb_api.api.cabinet_validation import router as cabinet_validation_router

# Импортируем модели для создания таблиц
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBAnalyticsCache, WBWarehouse, WBSyncLog
from app.features.wb_api.models_sales import WBSales
from app.features.notifications.models import NotificationSettings, NotificationHistory, OrderStatusHistory

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
app.include_router(bot_sales_router, prefix="/api/v1/bot", tags=["Bot Sales"])
app.include_router(notification_settings_router, prefix="/api/v1/notifications", tags=["Notification Settings"])
app.include_router(notification_test_router, prefix="/api/v1/notifications", tags=["Notification Test"])
app.include_router(cabinet_validation_router, prefix="/api/v1/wb/cabinets/validation", tags=["Cabinet Validation"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)