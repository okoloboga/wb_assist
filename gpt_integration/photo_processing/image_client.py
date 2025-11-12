"""
Клиент для работы с API генерации изображений.

Функциональность:
- Инициализация с API ключом и базовым URL
- Обработка изображения по промпту
- Обработка ошибок и таймаутов
- Retry логика при ошибках
"""

import os
import logging
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageGenerationClient:
    """Клиент для работы с API генерации изображений"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Инициализация клиента.
        
        Args:
            api_key: API ключ для сервиса генерации изображений
            base_url: Базовый URL API сервиса
            timeout: Таймаут запросов в секундах
            max_retries: Максимальное количество попыток при ошибках
        """
        self.api_key = api_key or os.getenv("IMAGE_GEN_API_KEY")
        self.base_url = base_url or os.getenv("IMAGE_GEN_BASE_URL", "")
        self.timeout = timeout or int(os.getenv("IMAGE_GEN_TIMEOUT", "60"))
        self.max_retries = max_retries or int(os.getenv("IMAGE_GEN_MAX_RETRIES", "3"))
        
        if not self.api_key:
            logger.warning("IMAGE_GEN_API_KEY not set")
        if not self.base_url:
            logger.warning("IMAGE_GEN_BASE_URL not set")
    
    async def process_image(
        self,
        image_url: str,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Обработать изображение по промпту.
        
        Args:
            image_url: URL исходного изображения
            prompt: Текстовое описание желаемого результата
        
        Returns:
            Dict с результатом:
            - photo_url: URL обработанного изображения
            - processing_time: Время обработки в секундах
            - metadata: Дополнительные метаданные
        
        Raises:
            ValueError: Если API key или base URL не установлены
            aiohttp.ClientError: При сетевых ошибках
            Exception: При ошибках API или таймаутах
        """
        if not self.api_key or not self.base_url:
            raise ValueError("API key and base URL must be set")
        
        start_time = datetime.now()
        
        logger.info(f"Processing image: {image_url[:50]}... with prompt: {prompt[:50]}...")
        
        # Формируем данные запроса
        request_data = {
            "image_url": image_url,
            "prompt": prompt
        }
        
        try:
            # Вызываем API с retry логикой
            result = await self._make_request(
                endpoint="/process",
                method="POST",
                data=request_data
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Извлекаем URL обработанного изображения
            photo_url = result.get("result_url") or result.get("image_url") or result.get("url", "")
            
            if not photo_url:
                raise ValueError("No image URL in API response")
            
            logger.info(f"✅ Image processed successfully in {processing_time:.2f}s")
            
            return {
                "photo_url": photo_url,
                "processing_time": processing_time,
                "metadata": result.get("metadata", {})
            }
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Image processing failed after {processing_time:.2f}s: {e}")
            raise
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Выполнить HTTP запрос к API с retry логикой.
        
        Args:
            endpoint: Endpoint API
            method: HTTP метод
            data: Данные запроса
            retry_count: Текущий номер попытки
        
        Returns:
            Ответ API в виде словаря
        
        Raises:
            aiohttp.ClientError: При сетевых ошибках после всех попыток
            Exception: При ошибках API после всех попыток
        """
        url = f"{self.base_url.rstrip('/')}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method, url, json=data, headers=headers) as response:
                    
                    # Успешный ответ
                    if response.status == 200:
                        result = await response.json()
                        return result
                    
                    # Ошибки клиента (4xx)
                    elif 400 <= response.status < 500:
                        error_text = await response.text()
                        logger.error(f"Client error {response.status}: {error_text}")
                        
                        if response.status == 400:
                            raise ValueError(f"Bad request: {error_text}")
                        elif response.status == 403:
                            raise PermissionError(f"Access denied: {error_text}")
                        else:
                            raise Exception(f"Client error {response.status}: {error_text}")
                    
                    # Ошибки сервера (5xx) - можно повторить
                    elif response.status >= 500:
                        error_text = await response.text()
                        logger.warning(f"Server error {response.status}: {error_text}")
                        
                        # Повторяем запрос при ошибках сервера
                        if retry_count < self.max_retries:
                            delay = 2 ** retry_count  # Экспоненциальная задержка: 1s, 2s, 4s
                            logger.info(f"Retrying in {delay}s... (attempt {retry_count + 1}/{self.max_retries})")
                            await asyncio.sleep(delay)
                            return await self._make_request(endpoint, method, data, retry_count + 1)
                        else:
                            raise Exception(f"Service unavailable after {self.max_retries} retries: {error_text}")
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"Unexpected status {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout after {self.timeout}s")
            
            # Повторяем запрос при таймауте
            if retry_count < self.max_retries:
                delay = 2 ** retry_count
                logger.info(f"Retrying after timeout in {delay}s... (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                return await self._make_request(endpoint, method, data, retry_count + 1)
            else:
                raise Exception(f"Request timeout after {self.max_retries} retries")
        
        except aiohttp.ClientError as e:
            logger.warning(f"Network error: {e}")
            
            # Повторяем запрос при сетевых ошибках
            if retry_count < self.max_retries:
                delay = 2 ** retry_count
                logger.info(f"Retrying after network error in {delay}s... (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                return await self._make_request(endpoint, method, data, retry_count + 1)
            else:
                raise Exception(f"Network error after {self.max_retries} retries: {e}")












async def download_telegram_photo(bot_token: str, file_id: str) -> str:
    """
    Загрузить фото из Telegram и получить URL для обработки.
    
    Args:
        bot_token: Токен Telegram бота
        file_id: file_id фотографии в Telegram
    
    Returns:
        URL фотографии для передачи в API генерации изображений
    
    Raises:
        Exception: При ошибках загрузки
    """
    try:
        # Получаем информацию о файле
        file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_info_url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to get file info: {error_text}")
                
                result = await response.json()
                
                if not result.get("ok"):
                    raise Exception(f"Telegram API error: {result.get('description', 'Unknown error')}")
                
                file_path = result["result"]["file_path"]
                
                # Формируем URL для скачивания
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                
                logger.info(f"✅ Got Telegram photo URL: {file_url[:50]}...")
                
                return file_url
    
    except Exception as e:
        logger.error(f"❌ Failed to download Telegram photo: {e}")
        raise
