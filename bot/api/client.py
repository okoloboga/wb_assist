import os
import asyncio
import logging
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass

import aiohttp

# Настройка логирования
logger = logging.getLogger(__name__)

# URL сервера и секретный ключ из переменных окружения
SERVER_HOST = os.getenv("SERVER_HOST", "http://127.0.0.1:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")


@dataclass
class BotAPIResponse:
    """Стандартный ответ от Bot API"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    telegram_text: Optional[str] = None
    error: Optional[str] = None
    status_code: int = 200


class BotAPIClient:
    """Клиент для работы с Bot API эндпоинтами"""
    
    def __init__(self):
        self.base_url = f"{SERVER_HOST}/api/v1/bot"
        self.headers = {
            "X-API-SECRET-KEY": API_SECRET_KEY,
            "Content-Type": "application/json"
        }
        
        if not API_SECRET_KEY:
            logger.error("API_SECRET_KEY не найден в переменных окружения.")
            raise ValueError("API_SECRET_KEY не найден в переменных окружения.")

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> BotAPIResponse:
        """Базовый метод для выполнения HTTP запросов"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    try:
                        response_data = await resp.json()
                    except aiohttp.ContentTypeError:
                        response_data = {"error": "Invalid response format"}
                    
                    return BotAPIResponse(
                        success=resp.status < 400,
                        data=response_data.get("data"),
                        telegram_text=response_data.get("telegram_text"),
                        error=response_data.get("error"),
                        status_code=resp.status
                    )

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Ошибка соединения с сервером: {e}")
            return BotAPIResponse(
                success=False,
                error="Service Unavailable",
                status_code=503
            )
        except asyncio.TimeoutError as e:
            logger.error(f"Таймаут запроса: {e}")
            return BotAPIResponse(
                success=False,
                error="Request timeout",
                status_code=408
            )
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при запросе к API: {e}")
            return BotAPIResponse(
                success=False,
                error="Internal client error",
                status_code=500
            )

    # Dashboard и общая информация
    async def get_dashboard(self, user_id: int) -> BotAPIResponse:
        """Получить общую сводку по кабинету WB"""
        return await self._make_request("GET", "/dashboard")

    # Заказы
    async def get_recent_orders(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить последние заказы пользователя"""
        params = {"limit": limit, "offset": offset}
        return await self._make_request("GET", "/orders/recent", params=params)

    async def get_order_details(self, order_id: int) -> BotAPIResponse:
        """Получить детальную информацию о заказе"""
        return await self._make_request("GET", f"/orders/{order_id}")

    # Остатки и товары
    async def get_critical_stocks(
        self, 
        user_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить критичные остатки"""
        params = {"limit": limit, "offset": offset}
        return await self._make_request("GET", "/stocks/critical", params=params)

    # Отзывы и аналитика
    async def get_reviews_summary(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить новые и проблемные отзывы"""
        params = {"limit": limit, "offset": offset}
        return await self._make_request("GET", "/reviews/summary", params=params)

    async def get_analytics_sales(
        self, 
        user_id: int, 
        period: str = "7d"
    ) -> BotAPIResponse:
        """Получить статистику продаж и аналитику"""
        params = {"period": period}
        return await self._make_request("GET", "/analytics/sales", params=params)

    # Синхронизация
    async def start_sync(self, user_id: int) -> BotAPIResponse:
        """Запустить ручную синхронизацию данных"""
        return await self._make_request("POST", "/sync/start")

    async def get_sync_status(self, user_id: int) -> BotAPIResponse:
        """Получить статус синхронизации"""
        return await self._make_request("GET", "/sync/status")

    # WB кабинет подключение
    async def connect_wb_cabinet(
        self, 
        user_id: int, 
        api_key: str
    ) -> BotAPIResponse:
        """Подключить WB кабинет через API ключ"""
        json_data = {"api_key": api_key}
        return await self._make_request("POST", "/cabinets/connect", json_data=json_data)

    async def get_cabinet_status(self, user_id: int) -> BotAPIResponse:
        """Получить статус подключенных кабинетов"""
        return await self._make_request("GET", "/cabinets/status")


# Создаем глобальный экземпляр клиента
bot_api_client = BotAPIClient()


# Обратная совместимость - старые функции
async def register_user_on_server(payload: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
    """
    Отправляет данные для регистрации/обновления пользователя на сервер.

    :param payload: Данные пользователя (telegram_id, username, и т.д.).
    :return: Кортеж (статус_код, json_ответ_или_None).
    """
    register_url = f"{SERVER_HOST}/users/"
    headers = {
        "X-API-SECRET-KEY": API_SECRET_KEY
    }

    if not API_SECRET_KEY:
        logger.error("API_SECRET_KEY не найден в переменных окружения.")
        return 500, {"error": "Client configuration error"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(register_url, json=payload, headers=headers) as resp:
                try:
                    response_json = await resp.json()
                except aiohttp.ContentTypeError:
                    response_json = None
                return resp.status, response_json

    except aiohttp.ClientConnectorError as e:
        logger.error(f"Ошибка соединения с сервером: {e}")
        return 503, {"error": "Service Unavailable"} # 503 Service Unavailable
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при запросе к API: {e}")
        return 500, {"error": "Internal client error"}
