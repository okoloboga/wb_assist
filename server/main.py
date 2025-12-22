from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из корневого .env файла
# В Docker переменные окружения уже установлены через docker-compose.yml
env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    # Пробуем загрузить из текущей директории (для обратной совместимости)
    load_dotenv(override=False)

from app.core.config import settings
from app.core.middleware import setup_middleware, setup_exception_handlers
from app.core.database import init_db
from app.features.system.routes import system_router
from app.features.user.routes import user_router
from app.features.stats.routes import stats_router
from app.features.wb_api.routes import router as wb_router
from app.features.bot_api.routes import router as bot_router
from app.features.bot_api.routes_sales import router as bot_sales_router
from app.features.bot_api.routes_semantic_core import router as bot_semantic_core_router
from app.features.notifications.api.settings import router as notification_settings_router
from app.features.notifications.api.test import router as notification_test_router
from app.features.wb_api.api.cabinet_validation import router as cabinet_validation_router
from app.features.export import router as export_router, template_router
from app.features.digest.router import router as digest_router
from app.features.competitors.routes import router as competitors_router

# Импортируем модели для создания таблиц
from app.features.user.models import User
from app.features.wb_api.models import WBCabinet, WBProduct, WBOrder, WBStock, WBReview, WBAnalyticsCache, WBWarehouse, WBSyncLog
from app.features.wb_api.models_sales import WBSales
from app.features.notifications.models import NotificationSettings, NotificationHistory, OrderStatusHistory
from app.features.stock_alerts.models import DailySalesAnalytics, StockAlertHistory
from app.features.export.models import ExportToken, ExportLog
from app.features.digest.models import ChannelReport, DigestHistory
from app.features.competitors.models import CompetitorLink, CompetitorProduct, CompetitorSemanticCore
from app.features.semantic_core.models import CabinetSemanticCore

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
app.include_router(bot_semantic_core_router, prefix="/api/v1/bot", tags=["Bot API"])
app.include_router(notification_settings_router, prefix="/api/v1/notifications", tags=["Notification Settings"])
app.include_router(notification_test_router, prefix="/api/v1/notifications", tags=["Notification Test"])
app.include_router(cabinet_validation_router, prefix="/api/v1/wb/cabinets/validation", tags=["Cabinet Validation"])
app.include_router(export_router, tags=["Export"])
app.include_router(template_router, tags=["Export Templates"])
app.include_router(digest_router, prefix="/api/v1", tags=["Digest"])
app.include_router(competitors_router, prefix="/api/v1/bot", tags=["Competitors"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)