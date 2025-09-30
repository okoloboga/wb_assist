import os
import logging
from typing import Tuple, Optional, Dict, Any

import aiohttp

# Настройка логирования
logger = logging.getLogger(__name__)

# URL сервера и секретный ключ из переменных окружения
SERVER_HOST = os.getenv("SERVER_HOST", "http://127.0.0.1:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")


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
