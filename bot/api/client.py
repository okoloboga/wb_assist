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
    # Дополнительные поля для совместимости с новой структурой API
    orders: Optional[List[Dict[str, Any]]] = None
    pagination: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    stocks: Optional[Dict[str, Any]] = None
    competitors: Optional[List[Dict[str, Any]]] = None
    products: Optional[List[Dict[str, Any]]] = None


class BotAPIClient:
    """Клиент для работы с Bot API эндпоинтами"""
    
    def __init__(self):
        self.base_url = f"{SERVER_HOST}/api/v1/bot"
        self.headers = {
            "X-API-SECRET-KEY": API_SECRET_KEY,
            "Content-Type": "application/json"
        }
        self.max_retries = 3
        self.retry_delay = 1  # секунды
        self.timeout = 30  # секунды
        
        # Отладочные логи инициализации
        logger.info(f"🔧 Инициализация BotAPIClient:")
        logger.info(f"   🌐 SERVER_HOST: {SERVER_HOST}")
        logger.info(f"   🔗 Base URL: {self.base_url}")
        logger.info(f"   🔑 API_SECRET_KEY: {'***' + API_SECRET_KEY[-4:] if API_SECRET_KEY else 'НЕ НАЙДЕН'}")
        logger.info(f"   📋 Headers: {self.headers}")
        logger.info(f"   🔄 Max retries: {self.max_retries}")
        logger.info(f"   ⏰ Timeout: {self.timeout}s")
        
        if not API_SECRET_KEY:
            logger.error("❌ API_SECRET_KEY не найден в переменных окружения.")
            raise ValueError("API_SECRET_KEY не найден в переменных окружения.")

    async def _make_request_with_retry(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> BotAPIResponse:
        """HTTP запрос с retry логикой"""
        timeout = timeout or self.timeout
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                    url = f"{self.base_url}{endpoint}"
                    async with session.request(
                        method=method.upper(),
                        url=url,
                        headers=self.headers,
                        params=params,
                        json=data
                    ) as response:
                        return await self._handle_response(response)
                            
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout на попытке {attempt + 1}/{self.max_retries} для {endpoint}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    return BotAPIResponse(
                        success=False,
                        error="Request timeout",
                        status_code=408
                    )
                    
            except aiohttp.ClientError as e:
                logger.warning(f"🌐 Network error на попытке {attempt + 1}/{self.max_retries} для {endpoint}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                else:
                    return BotAPIResponse(
                        success=False,
                        error=f"Network error: {str(e)}",
                        status_code=500
                    )
            except Exception as e:
                logger.error(f"💥 Непредвиденная ошибка при запросе: {e}")
                return BotAPIResponse(
                    success=False,
                    error="Internal client error",
                    status_code=500
                )
        
        return BotAPIResponse(
            success=False,
            error=f"Failed after {self.max_retries} attempts",
            status_code=500
        )

    async def _handle_response(self, response: aiohttp.ClientResponse) -> BotAPIResponse:
        """Обработка HTTP ответа с детальным логированием"""
        try:
            data = await response.json()
            if response.status == 200:
                # Для dashboard эндпоинта данные находятся в корне ответа
                if "dashboard" in data:
                    return BotAPIResponse(
                        success=True,
                        data=data,  # Передаем весь ответ как data
                        telegram_text=data.get("telegram_text"),
                        status_code=response.status
                    )
                else:
                    return BotAPIResponse(
                        success=True,
                        data=data.get("data"),
                        telegram_text=data.get("telegram_text"),
                        status_code=response.status,
                        # Единообразная структура - поля в корне ответа
                        orders=data.get("orders"),
                        pagination=data.get("pagination"),
                        order=data.get("order"),
                        stocks=data.get("stocks"),
                        competitors=data.get("competitors"),
                        products=data.get("products")
                    )
            elif response.status == 404:
                logger.warning(f"🔍 Resource not found: {response.url}")
                return BotAPIResponse(
                    success=False,
                    error="Ресурс не найден",
                    status_code=response.status
                )
            elif response.status == 429:
                logger.warning(f"⏰ Rate limit exceeded: {response.url}")
                return BotAPIResponse(
                    success=False,
                    error="Превышен лимит запросов, попробуйте позже",
                    status_code=response.status
                )
            elif response.status >= 500:
                logger.error(f"🔥 Server error {response.status}: {response.url}")
                return BotAPIResponse(
                    success=False,
                    error="Ошибка сервера, попробуйте позже",
                    status_code=response.status
                )
            else:
                error_msg = data.get("error") or data.get("detail") or f"HTTP {response.status}"
                return BotAPIResponse(
                    success=False,
                    error=error_msg,
                    status_code=response.status
                )
                
        except Exception as e:
            logger.error(f"💥 Error parsing response: {e}")
            return BotAPIResponse(
                success=False,
                error="Ошибка обработки ответа сервера",
                status_code=response.status
            )

    async def _make_request_with_timeout(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 300
    ) -> BotAPIResponse:
        """Базовый метод для выполнения HTTP запросов с настраиваемым таймаутом"""
        url = f"{self.base_url}{endpoint}"
        
        # Отладочные логи
        logger.info(f"🚀 Отправляем запрос к серверу (таймаут: {timeout}s):")
        logger.info(f"   📍 URL: {url}")
        logger.info(f"   🔧 Method: {method}")
        logger.info(f"   📋 Params: {params}")
        logger.info(f"   📦 JSON: {json_data}")
        logger.info(f"   🔑 Headers: {self.headers}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    logger.info(f"📡 Получен ответ от сервера:")
                    logger.info(f"   📊 Status: {resp.status}")
                    
                    try:
                        response_data = await resp.json()
                        logger.info(f"   📦 Response data: {response_data}")
                    except aiohttp.ContentTypeError:
                        response_data = {"error": "Invalid response format"}
                        logger.error(f"   ❌ Ошибка парсинга JSON: Invalid response format")
                    
                    # Логируем структуру ответа для отладки
                    
                    result = BotAPIResponse(
                        success=resp.status < 400,
                        data=response_data,
                        telegram_text=response_data.get("telegram_text") if isinstance(response_data, dict) else None,
                        error=response_data.get("error") if isinstance(response_data, dict) else None,
                        status_code=resp.status,
                        # Заполняем новые поля для совместимости
                        orders=response_data.get("orders") if isinstance(response_data, dict) else None,
                        pagination=response_data.get("pagination") if isinstance(response_data, dict) else None
                    )
                    
                    logger.info(f"✅ Запрос выполнен успешно: {result.success}")
                    return result
                    
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут запроса:")
            logger.error(f"   🔗 Таймаут при запросе к {url}")
            return BotAPIResponse(
                success=False,
                error="Request timeout",
                status_code=408
            )
        except aiohttp.ClientConnectorError as e:
            logger.error(f"🔌 Ошибка соединения с сервером:")
            logger.error(f"   🔗 URL: {url}")
            logger.error(f"   ❌ Ошибка: {e}")
            return BotAPIResponse(
                success=False,
                error="Connection error",
                status_code=503
            )
        except Exception as e:
            logger.error(f"💥 Непредвиденная ошибка при запросе к API:")
            logger.error(f"   🔗 URL: {url}")
            logger.error(f"   ❌ Ошибка: {e}")
            return BotAPIResponse(
                success=False,
                error="Internal error",
                status_code=500
            )

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> BotAPIResponse:
        """Базовый метод для выполнения HTTP запросов"""
        url = f"{self.base_url}{endpoint}"
        
        # Отладочные логи
        logger.info(f"🚀 Отправляем запрос к серверу:")
        logger.info(f"   📍 URL: {url}")
        logger.info(f"   🔧 Method: {method}")
        logger.info(f"   📋 Params: {params}")
        logger.info(f"   📦 JSON: {json_data}")
        logger.info(f"   🔑 Headers: {self.headers}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 минут для синхронизации
                ) as resp:
                    logger.info(f"📡 Получен ответ от сервера:")
                    logger.info(f"   📊 Status: {resp.status}")
                    
                    try:
                        response_data = await resp.json()
                        logger.info(f"   📦 Response data: {response_data}")
                    except aiohttp.ContentTypeError:
                        response_data = {"error": "Invalid response format"}
                        logger.error(f"   ❌ Ошибка парсинга JSON: Invalid response format")
                    
                    result = BotAPIResponse(
                        success=resp.status < 400,
                        data=response_data,
                        telegram_text=response_data.get("telegram_text"),
                        error=response_data.get("error"),
                        status_code=resp.status,
                        # Единообразная структура - поля в корне ответа
                        competitors=response_data.get("competitors"),
                        products=response_data.get("products"),
                        pagination=response_data.get("pagination")
                    )
                    
                    logger.info(f"✅ Результат запроса: success={result.success}, status_code={result.status_code}")
                    return result

        except aiohttp.ClientConnectorError as e:
            logger.error(f"❌ Ошибка соединения с сервером: {e}")
            logger.error(f"   🔗 Не удается подключиться к {url}")
            return BotAPIResponse(
                success=False,
                error="Service Unavailable",
                status_code=503
            )
        except asyncio.TimeoutError as e:
            logger.error(f"⏰ Таймаут запроса: {e}")
            logger.error(f"   🔗 Таймаут при запросе к {url}")
            return BotAPIResponse(
                success=False,
                error="Request timeout",
                status_code=408
            )
        except Exception as e:
            logger.error(f"💥 Непредвиденная ошибка при запросе к API: {e}")
            logger.error(f"   🔗 Ошибка при запросе к {url}")
            return BotAPIResponse(
                success=False,
                error="Internal client error",
                status_code=500
            )

    # Dashboard и общая информация
    async def get_dashboard(self, user_id: int) -> BotAPIResponse:
        """Получить общую сводку по кабинету WB"""
        params = {"telegram_id": user_id}
        return await self._make_request_with_retry("GET", "/dashboard", params=params)

    # Заказы
    async def get_recent_orders(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0,
        status: Optional[str] = None
    ) -> BotAPIResponse:
        """Получить последние заказы пользователя с фильтрацией по статусу"""
        logger.info(f"📦 Получение заказов для пользователя {user_id}, limit={limit}, offset={offset}, status={status}")
        params = {"telegram_id": user_id, "limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._make_request_with_retry("GET", "/orders/recent", params=params)

    async def get_order_details(self, order_id: int, user_id: int) -> BotAPIResponse:
        """Получить детальную информацию о заказе"""
        params = {"telegram_id": user_id}
        return await self._make_request_with_retry("GET", f"/orders/{order_id}", params=params)

    # Остатки и товары
    async def get_critical_stocks(
        self, 
        user_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить критичные остатки"""
        params = {"telegram_id": user_id, "limit": limit, "offset": offset}
        return await self._make_request_with_retry("GET", "/stocks/critical", params=params)

    # Остатки и товары
    async def get_dynamic_critical_stocks(
        self, 
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить критичные остатки на основе динамики затрат с пагинацией"""
        params = {
            "telegram_id": user_id,
            "limit": limit,
            "offset": offset
        }
        return await self._make_request_with_retry("GET", "/stocks/dynamic-critical", params=params)

    async def get_all_stocks_report(
        self, 
        user_id: int,
        limit: int = 15,
        offset: int = 0
    ) -> BotAPIResponse:
        """Получить отчет по всем остаткам с группировкой по товарам, складам и размерам"""
        params = {
            "telegram_id": user_id,
            "limit": limit,
            "offset": offset
        }
        return await self._make_request_with_retry("GET", "/stocks/all", params=params)

    # Отзывы и аналитика
    async def get_reviews_summary(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0,
        rating_threshold: Optional[int] = None
    ) -> BotAPIResponse:
        """Получить новые и проблемные отзывы с фильтрацией по рейтингу"""
        params = {"telegram_id": user_id, "limit": limit, "offset": offset}
        if rating_threshold is not None:
            params["rating_threshold"] = rating_threshold
        return await self._make_request("GET", "/reviews/summary", params=params)

    async def get_analytics_sales(
        self, 
        user_id: int, 
        period: str = "7d"
    ) -> BotAPIResponse:
        """Получить статистику продаж и аналитику"""
        params = {"telegram_id": user_id, "period": period}
        return await self._make_request("GET", "/analytics/sales", params=params)

    # Синхронизация
    async def start_sync(self, user_id: int) -> BotAPIResponse:
        """Запустить ручную синхронизацию данных"""
        params = {"telegram_id": user_id}
        return await self._make_request("POST", "/sync/start", params=params)
    
    async def start_initial_sync(self, user_id: int) -> BotAPIResponse:
        """Запустить первичную синхронизацию с увеличенным таймаутом"""
        params = {"telegram_id": user_id}
        return await self._make_request_with_retry("POST", "/sync/start", params=params, timeout=600)  # 10 минут

    async def get_sync_status(self, user_id: int) -> BotAPIResponse:
        """Получить статус синхронизации"""
        params = {"telegram_id": user_id}
        return await self._make_request("GET", "/sync/status", params=params)

    # WB кабинет подключение
    async def connect_wb_cabinet(
        self, 
        user_id: int, 
        api_key: str
    ) -> BotAPIResponse:
        """Подключить WB кабинет через API ключ"""
        params = {"telegram_id": user_id}
        json_data = {"api_key": api_key}
        return await self._make_request("POST", "/cabinets/connect", params=params, json_data=json_data)


    # ===== УВЕДОМЛЕНИЯ (S3) =====

    async def get_notification_settings(self, user_id: int) -> BotAPIResponse:
        """Получить настройки уведомлений пользователя"""
        logger.info(f"🔔 Получение настроек уведомлений для пользователя {user_id}")
        params = {"telegram_id": user_id}
        return await self._make_request("GET", "/notifications/settings", params=params)

    async def update_notification_settings(self, user_id: int, updates: Dict[str, Any]) -> BotAPIResponse:
        """Обновить настройки уведомлений пользователя (частично)"""
        logger.info(f"🛠 Обновление настроек уведомлений для пользователя {user_id}: {updates}")
        params = {"telegram_id": user_id}
        return await self._make_request("POST", "/notifications/settings", params=params, json_data=updates)

    async def update_user_webhook(self, user_id: int, webhook_url: str) -> BotAPIResponse:
        """Обновить webhook URL пользователя"""
        logger.info(f"🔗 Обновление webhook URL для пользователя {user_id}: {webhook_url}")
        params = {"telegram_id": user_id}
        json_data = {"bot_webhook_url": webhook_url}
        return await self._make_request("POST", "/users/webhook", params=params, json_data=json_data)

    # ===== НОВЫЕ МЕТОДЫ ДЛЯ СТАТИСТИКИ ЗАКАЗОВ =====

    async def get_orders_statistics(self, user_id: int) -> BotAPIResponse:
        """Получить полную статистику по заказам"""
        logger.info(f"📊 Получение статистики заказов для пользователя {user_id}")
        params = {"telegram_id": user_id}
        return await self._make_request("GET", "/orders/statistics", params=params)

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ПРОДАЖАМИ =====

    async def get_recent_sales(
        self, 
        user_id: int, 
        limit: int = 10, 
        offset: int = 0,
        sale_type: Optional[str] = None
    ) -> BotAPIResponse:
        """Получить последние продажи и возвраты"""
        logger.info(f"💰 Получение продаж для пользователя {user_id}, limit={limit}, offset={offset}, type={sale_type}")
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        if sale_type:
            params["sale_type"] = sale_type
        return await self._make_request("GET", "/sales/recent", params=params)

    async def get_buyouts(
        self, 
        user_id: int, 
        limit: int = 10,
        date_from: Optional[str] = None
    ) -> BotAPIResponse:
        """Получить только выкупы"""
        logger.info(f"✅ Получение выкупов для пользователя {user_id}, limit={limit}, date_from={date_from}")
        params = {"user_id": user_id, "limit": limit}
        if date_from:
            params["date_from"] = date_from
        return await self._make_request("GET", "/sales/buyouts", params=params)

    async def get_returns(
        self, 
        user_id: int, 
        limit: int = 10,
        date_from: Optional[str] = None
    ) -> BotAPIResponse:
        """Получить только возвраты"""
        logger.info(f"↩️ Получение возвратов для пользователя {user_id}, limit={limit}, date_from={date_from}")
        params = {"user_id": user_id, "limit": limit}
        if date_from:
            params["date_from"] = date_from
        return await self._make_request("GET", "/sales/returns", params=params)

    async def get_sales_statistics(
        self, 
        user_id: int,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> BotAPIResponse:
        """Получить статистику продаж"""
        logger.info(f"📈 Получение статистики продаж для пользователя {user_id}, from={date_from}, to={date_to}")
        params = {"user_id": user_id}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return await self._make_request("GET", "/sales/statistics", params=params)

    # ===== НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С КАБИНЕТАМИ =====

    async def create_or_connect_cabinet(
        self, 
        user_id: int, 
        api_key: str,
        name: str
    ) -> BotAPIResponse:
        """Создать новый кабинет или подключиться к существующему"""
        logger.info(f"🏢 Создание/подключение кабинета для пользователя {user_id}, name={name}")
        params = {"user_id": user_id, "api_key": api_key, "name": name}
        return await self._make_request("POST", "/wb/cabinets/", params=params)

    async def get_user_cabinets(self, user_id: int) -> BotAPIResponse:
        """Получить кабинеты пользователя"""
        logger.info(f"📋 Получение кабинетов пользователя {user_id}")
        params = {"user_id": user_id}
        return await self._make_request("GET", "/wb/cabinets/", params=params)

    async def validate_all_cabinets(self) -> BotAPIResponse:
        """Валидация всех кабинетов"""
        logger.info("🔍 Валидация всех кабинетов")
        return await self._make_request("POST", "/api/v1/wb/cabinets/validation/validate-all")

    # ===== DEPRECATED МЕТОДЫ (для обратной совместимости) =====

    async def connect_wb_cabinet(
        self, 
        user_id: int, 
        api_key: str
    ) -> BotAPIResponse:
        """Подключить WB кабинет через API ключ (DEPRECATED)"""
        logger.warning("⚠️ DEPRECATED: connect_wb_cabinet устарел, используйте create_or_connect_cabinet")
        params = {"telegram_id": user_id}
        json_data = {"api_key": api_key}
        return await self._make_request("POST", "/cabinets/connect", params=params, json_data=json_data)

    async def get_cabinet_status(self, user_id: int) -> BotAPIResponse:
        """Получить статус подключенных кабинетов (DEPRECATED)"""
        logger.warning("⚠️ DEPRECATED: get_cabinet_status устарел, используйте get_user_cabinets")
        params = {"telegram_id": user_id}
        return await self._make_request("GET", "/cabinets/status", params=params)

    # ===== МЕТОДЫ ЭКСПОРТА В GOOGLE SHEETS (S4) =====

    async def set_cabinet_spreadsheet(self, cabinet_id: int, spreadsheet_url: str) -> BotAPIResponse:
        """Сохраняет spreadsheet_id для кабинета"""
        logger.info(f"📊 Сохранение spreadsheet для кабинета {cabinet_id}")
        
        url = f"{SERVER_HOST}/api/export/cabinet/{cabinet_id}/spreadsheet"
        params = {"spreadsheet_url": spreadsheet_url}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    response_data = await resp.json()
                    
                    if resp.status == 200:
                        logger.info(f"✅ Spreadsheet сохранен: {response_data.get('spreadsheet_id', 'N/A')}")
                        return BotAPIResponse(
                            success=True,
                            data=response_data,
                            status_code=resp.status
                        )
                    else:
                        error_msg = response_data.get("detail", "Ошибка сохранения spreadsheet")
                        logger.error(f"❌ Ошибка сохранения spreadsheet: {error_msg}")
                        return BotAPIResponse(
                            success=False,
                            error=error_msg,
                            status_code=resp.status
                        )
                        
        except Exception as e:
            logger.error(f"💥 Ошибка сохранения spreadsheet: {e}")
            return BotAPIResponse(
                success=False,
                error=f"Ошибка сохранения: {str(e)}",
                status_code=500
            )

    async def get_cabinet_spreadsheet(self, cabinet_id: int) -> BotAPIResponse:
        """Получить привязанную Google Sheet кабинета"""
        url = f"{SERVER_HOST}/api/export/cabinet/{cabinet_id}/spreadsheet"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        return BotAPIResponse(success=True, data=data, status_code=resp.status)
                    else:
                        return BotAPIResponse(success=False, error=data.get("detail", "Not found"), status_code=resp.status)
        except Exception as e:
            logger.error(f"Ошибка получения spreadsheet: {e}")
            return BotAPIResponse(success=False, error=str(e), status_code=500)

    async def update_cabinet_spreadsheet(self, cabinet_id: int) -> BotAPIResponse:
        """Обновляет Google Sheets таблицу кабинета"""
        logger.info(f"🔄 Обновление таблицы кабинета {cabinet_id}")
        
        url = f"{SERVER_HOST}/api/export/cabinet/{cabinet_id}/update"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    # Даем серверу достаточно времени на экспорт больших таблиц
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as resp:
                    response_data = await resp.json()
                    
                    if resp.status == 200:
                        logger.info(f"✅ Таблица обновлена для кабинета {cabinet_id}")
                        return BotAPIResponse(
                            success=True,
                            data=response_data,
                            status_code=resp.status
                        )
                    else:
                        error_msg = response_data.get("detail", "Ошибка обновления таблицы")
                        logger.error(f"❌ Ошибка обновления таблицы: {error_msg}")
                        return BotAPIResponse(
                            success=False,
                            error=error_msg,
                            status_code=resp.status
                        )
                        
        except asyncio.TimeoutError:
            # Сервер продолжает обновление, но клиент дождаться не смог
            msg = "Таймаут ожидания ответа. Экспорт на сервере продолжится — проверьте таблицу через минуту."
            logger.warning(f"⏰ {msg}")
            return BotAPIResponse(
                success=False,
                error=msg,
                status_code=408
            )
        except Exception as e:
            logger.error(f"💥 Ошибка обновления таблицы: {e}")
            return BotAPIResponse(
                success=False,
                error=f"Ошибка обновления: {str(e)}",
                status_code=500
            )

    async def create_export_token(self, user_id: int, cabinet_id: int) -> BotAPIResponse:
        """Создает токен экспорта для кабинета"""
        logger.info(f"🔑 Создание токена экспорта для кабинета {cabinet_id}, пользователя {user_id}")
        
        # Используем правильный URL и метод
        url = f"{SERVER_HOST}/api/export/token"
        json_data = {
            "user_id": user_id,
            "cabinet_id": cabinet_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=json_data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    response_data = await resp.json()
                    
                    if resp.status == 200:
                        logger.info(f"✅ Токен экспорта создан: {response_data.get('token', 'N/A')}")
                        return BotAPIResponse(
                            success=True,
                            data=response_data,
                            status_code=resp.status
                        )
                    else:
                        error_msg = response_data.get("detail", "Ошибка создания токена")
                        logger.error(f"❌ Ошибка создания токена: {error_msg}")
                        return BotAPIResponse(
                            success=False,
                            error=error_msg,
                            status_code=resp.status
                        )
                        
        except Exception as e:
            logger.error(f"💥 Ошибка создания токена экспорта: {e}")
            return BotAPIResponse(
                success=False,
                error=f"Ошибка создания токена: {str(e)}",
                status_code=500
            )

    async def create_google_sheets_template(self, cabinet_name: str) -> BotAPIResponse:
        """Создает шаблон Google Sheets"""
        logger.info(f"📊 Создание шаблона Google Sheets для {cabinet_name}")
        
        # Используем правильный URL и метод
        url = f"{SERVER_HOST}/api/export/template/create"
        params = {
            "template_name": f"WB Assist - {cabinet_name}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as resp:
                    response_data = await resp.json()
                    
                    if resp.status == 200:
                        logger.info(f"✅ Шаблон создан: {response_data.get('template_id', 'N/A')}")
                        return BotAPIResponse(
                            success=True,
                            data=response_data,
                            status_code=resp.status
                        )
                    else:
                        error_msg = response_data.get("detail", "Ошибка создания шаблона")
                        logger.error(f"❌ Ошибка создания шаблона: {error_msg}")
                        return BotAPIResponse(
                            success=False,
                            error=error_msg,
                            status_code=resp.status
                        )
                        
        except Exception as e:
            logger.error(f"💥 Ошибка создания шаблона Google Sheets: {e}")
            return BotAPIResponse(
                success=False,
                error=f"Ошибка создания шаблона: {str(e)}",
                status_code=500
            )


# Создаем глобальный экземпляр клиента
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С КОНКУРЕНТАМИ =====

    async def add_competitor(
        self,
        user_id: int,
        competitor_url: str
    ) -> BotAPIResponse:
        """Добавить ссылку конкурента"""
        logger.info(f"➕ Добавление конкурента для пользователя {user_id}")
        
        endpoint = "/competitors/add"
        params = {"telegram_id": user_id}
        json_data = {"competitor_url": competitor_url}
        
        return await self._make_request("POST", endpoint, params=params, json_data=json_data)

    async def get_competitors(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 10
    ) -> BotAPIResponse:
        """Получить список конкурентов с пагинацией"""
        logger.info(f"📊 Получение конкурентов для пользователя {user_id}, offset={offset}, limit={limit}")
        
        endpoint = "/competitors"
        params = {
            "telegram_id": user_id,
            "offset": offset,
            "limit": limit
        }
        
        return await self._make_request("GET", endpoint, params=params)

    async def get_competitor_products(
        self,
        competitor_id: int,
        user_id: int,
        offset: int = 0,
        limit: int = 10
    ) -> BotAPIResponse:
        """Получить товары конкурента с пагинацией"""
        logger.info(f"🛍️ Получение товаров конкурента {competitor_id} для пользователя {user_id}")
        
        endpoint = f"/competitors/{competitor_id}/products"
        params = {
            "telegram_id": user_id,
            "offset": offset,
            "limit": limit
        }
        
        return await self._make_request("GET", endpoint, params=params)

    async def get_competitor_product_detail(
        self,
        product_id: int,
        user_id: int
    ) -> BotAPIResponse:
        """Получить детальную информацию о товаре конкурента"""
        logger.info(f"📦 Получение деталей товара {product_id} для пользователя {user_id}")
        
        endpoint = f"/competitors/products/{product_id}"
        params = {"telegram_id": user_id}
        
        return await self._make_request("GET", endpoint, params=params)

    async def delete_competitor(
        self,
        competitor_id: int,
        user_id: int
    ) -> BotAPIResponse:
        """Удалить конкурента"""
        logger.info(f"🗑️ Удаление конкурента {competitor_id} для пользователя {user_id}")
        
        endpoint = f"/competitors/{competitor_id}"
        params = {"telegram_id": user_id}
        
        return await self._make_request("DELETE", endpoint, params=params)


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

    async def get_cabinet_id(self, user_id: int) -> BotAPIResponse:
        """Получает ID кабинета пользователя"""
        try:
            url = f"{SERVER_HOST}/api/v1/wb/cabinets/status"
            params = {"telegram_id": user_id}
            
            logger.info(f"🔍 Получение ID кабинета для пользователя {user_id}")
            
            status_code, response_data = await self._make_request_with_retry("GET", url, params=params)
            
            if status_code == 200:
                return BotAPIResponse(
                    success=True,
                    data=response_data,
                    cabinet_id=response_data.get("cabinet_id")
                )
            else:
                return BotAPIResponse(
                    success=False,
                    error=response_data.get("detail", "Ошибка получения ID кабинета"),
                    status_code=status_code
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения ID кабинета: {e}")
            return BotAPIResponse(
                success=False,
                error=f"Ошибка получения ID кабинета: {str(e)}",
                status_code=500
            )
