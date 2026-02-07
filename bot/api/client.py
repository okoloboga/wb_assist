"""
HTTP клиент для взаимодействия с FastAPI
"""
import aiohttp
import logging
import os
import asyncio
from functools import wraps
from typing import Optional, Dict, List, Any, Callable, Coroutine

logger = logging.getLogger(__name__)

API_URL = os.getenv("SERVER_HOST", "http://localhost:8002")

# --- Decorator for Error Handling ---

def _handle_api_exceptions(default_return: Any = None):
    """
    Декоратор для обработки исключений при запросах к API.
    Ловит сетевые ошибки и плохие статусы HTTP.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(self: "APIClient", *args, **kwargs) -> Any:
            method_name = func.__name__
            try:
                session = await self._get_session()
                response: Optional[aiohttp.ClientResponse] = await func(self, session, *args, **kwargs)

                # Успешные статусы (2xx)
                if response and 200 <= response.status < 300:
                    # Если функция должна вернуть bool, успешный запрос означает True
                    if func.__annotations__.get('return') == bool:
                        return True
                    
                    if response.content_type == 'application/json':
                        return await response.json()
                    
                    # Для запросов без тела (например, 204 No Content)
                    if response.status == 204:
                        return None
                        
                    return await response.text()

                # Обработка не-успешных статусов
                error_body = await response.text() if response else "No response object"
                status = response.status if response else "N/A"
                logger.error(
                    f"API Error in {method_name}: "
                    f"status={status}, "
                    f"body='{error_body[:200]}...'"
                )
                return default_return

            except aiohttp.ClientError as e:
                logger.error(f"Network Error in {method_name}: {type(e).__name__} - {e}")
                return default_return
            except asyncio.TimeoutError:
                logger.error(f"Timeout Error in {method_name}")
                return default_return
            except Exception as e:
                logger.error(f"Unexpected Error in {method_name}: {type(e).__name__} - {e}", exc_info=True)
                return default_return
        return wrapper
    return decorator


class APIClient:
    """Клиент для работы с FastAPI backend"""

    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key = os.getenv("API_SECRET_KEY", "CnWvwoDwwGKh")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        if self.session is None or self.session.closed:
            # Устанавливаем разумный таймаут для всех запросов
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {"X-API-SECRET-KEY": self.api_key}
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session

    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    # --- Catalog endpoints ---

    @_handle_api_exceptions(default_return=[])
    async def get_categories(self, session: aiohttp.ClientSession) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/v1/catalog/categories")

    @_handle_api_exceptions(default_return=[])
    async def get_products_by_category(self, session: aiohttp.ClientSession, category: str) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/v1/catalog/products?category={category}")

    @_handle_api_exceptions(default_return=None)
    async def get_product_by_id(self, session: aiohttp.ClientSession, product_id: str) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/v1/catalog/products/{product_id}")

    # --- Favorites endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def add_to_favorites(self, session: aiohttp.ClientSession, user_id: int, product_id: str) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/v1/favorites/",
            json={"user_id": user_id, "product_id": product_id}
        )

    @_handle_api_exceptions(default_return=False)
    async def remove_from_favorites(self, session: aiohttp.ClientSession, user_tg_id: int, product_id: str) -> bool:
        return await session.delete(f"{self.base_url}/api/v1/favorites/{user_tg_id}/{product_id}")

    @_handle_api_exceptions(default_return=[])
    async def get_favorites(self, session: aiohttp.ClientSession, user_tg_id: int) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/v1/favorites/{user_tg_id}")

    @_handle_api_exceptions(default_return={"is_favorite": False})
    async def check_favorite(self, session: aiohttp.ClientSession, user_tg_id: int, product_id: str) -> Dict:
        return await session.get(f"{self.base_url}/api/v1/favorites/{user_tg_id}/check/{product_id}")

    # --- Measurements endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def get_measurements(self, session: aiohttp.ClientSession, user_tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/v1/measurements/{user_tg_id}")

    # --- Size recommendation ---

    @_handle_api_exceptions(default_return=None)
    async def recommend_size(self, session: aiohttp.ClientSession, user_id: int, product_id: str) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/v1/size/recommend",
            json={"user_id": user_id, "product_id": product_id}
        )


# Singleton instance
bot_api_client = APIClient()


# Legacy function for compatibility
async def register_user_on_server(payload: Dict) -> tuple[int, Dict]:
    """Legacy function for user registration compatibility"""
    try:
        session = await bot_api_client._get_session()
        response = await session.post(f"{bot_api_client.base_url}/api/v1/bot/users/register", json=payload)
        data = await response.json() if response.content_type == 'application/json' else {}
        return response.status, data
    except Exception as e:
        logger.error(f"Error in register_user_on_server: {e}")
        return 500, {}