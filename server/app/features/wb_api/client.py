import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from .models import WBCabinet

logger = logging.getLogger(__name__)


class WBAPIClient:
    """Клиент для работы с Wildberries API"""
    
    def __init__(self, cabinet: WBCabinet):
        self.cabinet = cabinet
        self.api_key = cabinet.api_key
        
        # Базовые URL для разных API
        self.base_urls = {
            "marketplace": "https://marketplace-api.wildberries.ru",
            "statistics": "https://statistics-api.wildberries.ru", 
            "content": "https://content-api.wildberries.ru",
            "feedbacks": "https://feedbacks-api.wildberries.ru",
            "common": "https://common-api.wildberries.ru"
        }
        
        # Rate limits для разных эндпоинтов
        self.rate_limits = {
            "orders": {"requests_per_minute": 300, "interval_ms": 200, "burst": 20},
            "stocks": {"requests_per_minute": 100, "interval_ms": 600, "burst": 20},
            "products": {"requests_per_minute": 10, "interval_ms": 6000, "burst": 5},
            "feedbacks": {"requests_per_minute": 60, "interval_ms": 1000, "burst": 10},
            "common": {"requests_per_minute": 300, "interval_ms": 200, "burst": 20}
        }
        
        # Текущие счетчики запросов
        self.request_counters = {key: 0 for key in self.rate_limits.keys()}
        self.last_reset = {key: datetime.now(timezone.utc) for key in self.rate_limits.keys()}

    async def validate_api_key(self) -> Dict[str, Any]:
        """Валидация API ключа через простой запрос к WB API"""
        try:
            # Используем простой запрос к orders API для проверки валидности ключа
            url = f"{self.base_urls['statistics']}/api/v1/supplier/orders"
            params = {
                "dateFrom": "2024-01-01",
                "limit": 1  # Минимальный запрос
            }
            
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Validating API key for cabinet {self.cabinet.id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"API key validation successful for cabinet {self.cabinet.id}")
                    return {
                        "valid": True,
                        "status_code": response.status_code,
                        "message": "API key is valid"
                    }
                elif response.status_code == 401:
                    # API ключ невалиден
                    error_data = response.json() if response.content else {}
                    logger.warning(f"API key validation failed for cabinet {self.cabinet.id}: {error_data}")
                    return {
                        "valid": False,
                        "status_code": response.status_code,
                        "message": error_data.get("detail", "API access token not valid"),
                        "error_code": error_data.get("code", ""),
                        "title": error_data.get("title", "unauthorized")
                    }
                else:
                    # Другие ошибки (не связанные с валидностью ключа)
                    logger.warning(f"API key validation returned status {response.status_code} for cabinet {self.cabinet.id}")
                    return {
                        "valid": True,  # Считаем валидным, если не 401
                        "status_code": response.status_code,
                        "message": f"API returned status {response.status_code}",
                        "warning": True
                    }
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_data = e.response.json() if e.response.content else {}
                logger.warning(f"API key validation failed for cabinet {self.cabinet.id}: {error_data}")
                return {
                    "valid": False,
                    "status_code": e.response.status_code,
                    "message": error_data.get("detail", "API access token not valid"),
                    "error_code": error_data.get("code", ""),
                    "title": error_data.get("title", "unauthorized")
                }
            else:
                logger.error(f"HTTP error during API key validation for cabinet {self.cabinet.id}: {e.response.status_code}")
                return {
                    "valid": True,  # Считаем валидным, если не 401
                    "status_code": e.response.status_code,
                    "message": f"HTTP error: {e.response.status_code}",
                    "warning": True
                }
        except Exception as e:
            logger.error(f"Error validating API key for cabinet {self.cabinet.id}: {e}")
            return {
                "valid": True,  # Считаем валидным при других ошибках
                "status_code": 0,
                "message": f"Validation error: {str(e)}",
                "warning": True
            }

    async def _make_request(
        self, 
        method: str, 
        url: str, 
        headers: Dict[str, str] = None,
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        api_type: str = "statistics",
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Базовый метод для выполнения HTTP запросов с retry логикой"""
        
        if headers is None:
            headers = {}
        
        # Добавляем авторизацию
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        
        # Проверяем rate limits
        await self._check_rate_limit(api_type)
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=headers, params=params)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=headers, params=params, json=json_data)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Обработка успешного ответа
                    if response.status_code == 200:
                        self.request_counters[api_type] += 1
                        return response.json()
                    
                    # Обработка ошибок
                    elif response.status_code == 401:
                        logger.error(f"Unauthorized: Invalid API key for cabinet {self.cabinet.id}")
                        raise Exception("Invalid API key")
                    
                    elif response.status_code == 429:
                        logger.warning(f"Rate limit exceeded for {api_type}, attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise Exception("Rate limit exceeded")
                    
                    elif response.status_code >= 500:
                        logger.warning(f"Server error {response.status_code}, attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        else:
                            raise Exception(f"Server error: {response.status_code}")
                    
                    else:
                        logger.error(f"Unexpected status code: {response.status_code}")
                        raise Exception(f"Unexpected status code: {response.status_code}")
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout for {url}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception("Request timeout")
            
            except Exception as e:
                logger.error(f"Request failed: {str(e)}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise e
        
        return None

    async def _check_rate_limit(self, api_type: str):
        """Проверка и соблюдение rate limits"""
        if api_type not in self.rate_limits:
            return
        
        now = datetime.now(timezone.utc)
        rate_limit = self.rate_limits[api_type]
        
        # Сброс счетчика каждую минуту
        if (now - self.last_reset[api_type]).total_seconds() >= 60:
            self.request_counters[api_type] = 0
            self.last_reset[api_type] = now
        
        # Проверка лимита
        if self.request_counters[api_type] >= rate_limit["requests_per_minute"]:
            sleep_time = 60 - (now - self.last_reset[api_type]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit reached for {api_type}, sleeping {sleep_time}s")
                await asyncio.sleep(sleep_time)
                self.request_counters[api_type] = 0
                self.last_reset[api_type] = datetime.now(timezone.utc)
        
        # Небольшая задержка между запросами
        await asyncio.sleep(rate_limit["interval_ms"] / 1000)

    async def validate_api_key(self) -> Dict[str, Any]:
        """Валидация API ключа через запрос к складам"""
        try:
            url = f"{self.base_urls['marketplace']}/api/v3/warehouses"
            result = await self._make_request("GET", url, api_type="common")
            
            if result is not None:
                return {
                    "valid": True,
                    "message": "API key is valid",
                    "status_code": 200
                }
            else:
                return {
                    "valid": False,
                    "message": "API request returned no data",
                    "status_code": None
                }
        except Exception as e:
            logger.error(f"API key validation failed: {str(e)}")
            # Проверяем, если это 401 ошибка
            if "401" in str(e) or "Unauthorized" in str(e):
                return {
                    "valid": False,
                    "message": "Invalid API key (401 Unauthorized)",
                    "status_code": 401
                }
            else:
                return {
                    "valid": False,
                    "message": f"API validation error: {str(e)}",
                    "status_code": None
                }

    async def get_warehouses(self) -> List[Dict[str, Any]]:
        """Получение списка складов"""
        url = f"{self.base_urls['marketplace']}/api/v3/warehouses"
        result = await self._make_request("GET", url, api_type="common")
        return result or []


    async def get_products(self) -> List[Dict[str, Any]]:
        """Получение списка товаров"""
        url = f"{self.base_urls['content']}/content/v2/get/cards/list"
        
        # Параметры для получения товаров - БЕЗ ЛИМИТОВ
        json_data = {
            "sort": {
                "filter": {"withPhoto": -1, "visible": "ALL"}
            }
        }
        
        result = await self._make_request("POST", url, json_data=json_data, api_type="products")
        
        if result and "cards" in result:
            return result["cards"]
        return []

    async def get_orders(
        self, 
        date_from: str, 
        date_to: str = None,
        nm_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Получение заказов за период"""
        url = f"{self.base_urls['statistics']}/api/v1/supplier/orders"
        
        params = {"dateFrom": date_from}
        if date_to:
            params["dateTo"] = date_to
        if nm_id:
            params["nmId"] = nm_id
        
        result = await self._make_request("GET", url, params=params, api_type="orders")
        return result or []

    async def get_stocks(
        self, 
        date_from: str, 
        date_to: str = None
    ) -> List[Dict[str, Any]]:
        """Получение остатков за период"""
        url = f"{self.base_urls['statistics']}/api/v1/supplier/stocks"
        
        params = {"dateFrom": date_from}
        if date_to:
            params["dateTo"] = date_to
        
        result = await self._make_request("GET", url, params=params, api_type="stocks")
        return result or []

    async def get_reviews(
        self, 
        is_answered: bool = False,
        take: int = 1000,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Получение отзывов"""
        url = f"{self.base_urls['feedbacks']}/api/v1/feedbacks"
        
        params = {
            "isAnswered": is_answered,
            "take": take,
            "skip": skip
        }
        
        result = await self._make_request("GET", url, params=params, api_type="feedbacks")
        return result or {"data": {"feedbacks": []}}

    async def get_questions(
        self, 
        is_answered: bool = False,
        take: int = 1000,
        skip: int = 0
    ) -> Dict[str, Any]:
        """Получение вопросов"""
        url = f"{self.base_urls['feedbacks']}/api/v1/questions"
        
        params = {
            "isAnswered": is_answered,
            "take": take,
            "skip": skip
        }
        
        result = await self._make_request("GET", url, params=params, api_type="feedbacks")
        return result or {"data": {"questions": []}}

    async def get_sales(
        self, 
        date_from: str,
        flag: int = 0,
        nm_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Получение статистики продаж"""
        url = f"{self.base_urls['statistics']}/api/v1/supplier/sales"
        
        params = {
            "dateFrom": date_from,
            "flag": flag
        }
        if nm_id:
            params["nmId"] = nm_id
        
        result = await self._make_request("GET", url, params=params, api_type="orders")
        return result or []

    async def get_commissions(self) -> List[Dict[str, Any]]:
        """Получение комиссий WB по категориям товаров"""
        url = f"{self.base_urls['common']}/api/v1/tariffs/commission"
        
        params = {"locale": "ru"}
        
        result = await self._make_request("GET", url, params=params, api_type="common")
        
        # Извлекаем данные из ответа
        if result and isinstance(result, dict):
            if "data" in result:
                return result["data"]
            elif "response" in result and "data" in result["response"]:
                return result["response"]["data"]
            else:
                # Если это словарь, но нет ключа data, возможно это сам список
                return [result] if result else []
        elif result and isinstance(result, list):
            return result
        else:
            return []

    async def get_box_tariffs(self, date: str) -> Dict[str, Any]:
        """Получение тарифов для коробов"""
        url = f"{self.base_urls['common']}/api/v1/tariffs/box"
        
        params = {"date": date}
        
        result = await self._make_request("GET", url, params=params, api_type="common")
        return result or {"data": []}

    async def get_pallet_tariffs(self, date: str) -> Dict[str, Any]:
        """Получение тарифов для монопаллет"""
        url = f"{self.base_urls['common']}/api/v1/tariffs/pallet"
        
        params = {"date": date}
        
        result = await self._make_request("GET", url, params=params, api_type="common")
        return result or {"data": []}

    async def get_return_tariffs(self, date: str) -> Dict[str, Any]:
        """Получение тарифов на возврат"""
        url = f"{self.base_urls['common']}/api/v1/tariffs/return"
        
        params = {"date": date}
        
        result = await self._make_request("GET", url, params=params, api_type="common")
        return result or {"data": []}

    async def get_claims(self, is_archive: bool = False) -> List[Dict[str, Any]]:
        """Получение возвратов покупателей (Claims API)"""
        try:
            url = "https://returns-api.wildberries.ru/api/v1/claims"
            
            params = {
                "is_archive": str(is_archive).lower()
            }
            
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Fetching claims data (archive={is_archive}) for cabinet {self.cabinet.id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if not data or "claims" not in data:
                    logger.warning(f"No claims data received for cabinet {self.cabinet.id}")
                    return []
                
                claims = data.get("claims", [])
                logger.info(f"Received {len(claims)} claims for cabinet {self.cabinet.id}")
                return claims
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching claims for cabinet {self.cabinet.id}: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching claims for cabinet {self.cabinet.id}: {e}")
            return []

    async def get_all_data(
        self, 
        date_from: str, 
        date_to: str = None
    ) -> Dict[str, Any]:
        """Получение всех данных параллельно"""
        tasks = [
            self.get_warehouses(),
            self.get_products(),
            self.get_orders(date_from, date_to),
            self.get_stocks(date_from, date_to),
            self.get_reviews(),
            self.get_questions(),
            self.get_sales(date_from),
            self.get_commissions()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "warehouses": results[0] if not isinstance(results[0], Exception) else [],
            "products": results[1] if not isinstance(results[1], Exception) else [],
            "orders": results[2] if not isinstance(results[2], Exception) else [],
            "stocks": results[3] if not isinstance(results[3], Exception) else [],
            "reviews": results[4] if not isinstance(results[4], Exception) else {"data": {"feedbacks": []}},
            "questions": results[5] if not isinstance(results[5], Exception) else {"data": {"questions": []}},
            "sales": results[6] if not isinstance(results[6], Exception) else [],
            "commissions": results[7] if not isinstance(results[7], Exception) else []
        }

    async def get_sales(self, date_from: str, flag: int = 0) -> List[Dict[str, Any]]:
        """Получение данных о продажах и возвратах"""
        try:
            url = f"{self.base_urls['statistics']}/api/v1/supplier/sales"
            
            params = {
                "dateFrom": date_from,
                "flag": flag
            }
            
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Fetching sales data from {date_from} for cabinet {self.cabinet.id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if not data:
                    logger.warning(f"No sales data received for cabinet {self.cabinet.id}")
                    return []
                
                logger.info(f"Received {len(data)} sales records for cabinet {self.cabinet.id}")
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching sales for cabinet {self.cabinet.id}: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching sales for cabinet {self.cabinet.id}: {e}")
            return []