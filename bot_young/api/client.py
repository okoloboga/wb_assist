"""
HTTP клиент для запросов к Server API
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

import aiohttp

from core.config import config

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Стандартный ответ от API"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: int = 200


class ServerAPIClient:
    """Клиент для работы с Server API"""
    
    def __init__(self):
        self.base_url = f"{config.server_host}/api/v1"
        self.headers = {
            "X-API-SECRET-KEY": config.api_secret_key,
            "Content-Type": "application/json"
        }
        self.timeout = 30
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> APIResponse:
        """Базовый метод для HTTP запросов"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    try:
                        response_data = await resp.json()
                    except aiohttp.ContentTypeError:
                        response_data = {"error": "Invalid response format"}
                    
                    return APIResponse(
                        success=resp.status < 400,
                        data=response_data,
                        error=response_data.get("error") or response_data.get("detail"),
                        status_code=resp.status
                    )
        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error: {e}")
            return APIResponse(
                success=False,
                error="Service Unavailable",
                status_code=503
            )
        except Exception as e:
            logger.error(f"Request error: {e}")
            return APIResponse(
                success=False,
                error="Internal client error",
                status_code=500
            )
    
    # === Кабинеты ===
    
    async def get_user_cabinets(self, telegram_id: int) -> APIResponse:
        """Получить кабинеты пользователя"""
        params = {"telegram_id": telegram_id}
        return await self._make_request("GET", "/bot/cabinets/status", params=params)
    
    # === Каналы ===
    
    async def get_user_channels(self, telegram_id: int) -> APIResponse:
        """Получить список каналов пользователя"""
        params = {"telegram_id": telegram_id}
        return await self._make_request("GET", "/channels/", params=params)
    
    async def get_channel_detail(self, channel_id: int, telegram_id: int) -> APIResponse:
        """Получить детальную информацию о канале"""
        params = {"telegram_id": telegram_id}
        return await self._make_request("GET", f"/channels/{channel_id}", params=params)
    
    async def create_channel_report(
        self,
        telegram_id: int,
        cabinet_id: int,
        chat_id: int,
        chat_title: str,
        chat_type: str,
        report_time: str
    ) -> APIResponse:
        """Создать настройку канала"""
        params = {"telegram_id": telegram_id}
        json_data = {
            "user_id": 0,  # Будет заменено на сервере через telegram_id
            "cabinet_id": cabinet_id,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "chat_type": chat_type,
            "report_time": report_time,
            "timezone": "Europe/Moscow"
        }
        return await self._make_request("POST", "/channels/", params=params, json_data=json_data)
    
    async def update_channel(
        self,
        channel_id: int,
        telegram_id: int,
        updates: Dict[str, Any]
    ) -> APIResponse:
        """Обновить настройки канала"""
        params = {"telegram_id": telegram_id}
        return await self._make_request("PUT", f"/channels/{channel_id}", params=params, json_data=updates)
    
    async def delete_channel(self, channel_id: int, telegram_id: int) -> APIResponse:
        """Удалить канал"""
        params = {"telegram_id": telegram_id}
        return await self._make_request("DELETE", f"/channels/{channel_id}", params=params)


# Глобальный экземпляр клиента
api_client = ServerAPIClient()

