"""
Analysis service endpoints and orchestration.
"""

import os
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from gpt_integration.gpt_client import GPTClient
from gpt_integration.analysis.pipeline import run_analysis
from gpt_integration.analysis.aggregator import aggregate

logger = logging.getLogger(__name__)


async def _fetch_analytics_sales(telegram_id: int, period: str, server_host: str, api_secret_key: str) -> Dict[str, Any]:
    """Получить аналитику продаж с сервера."""
    url = f"{server_host.rstrip('/')}/api/v1/bot/analytics/sales"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "period": period}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return data.get("analytics") or {}


async def _fetch_daily_trends(telegram_id: int, server_host: str, api_secret_key: str) -> Dict[str, Any]:
    """Получить ежедневную динамику событий (новый эндпоинт)."""
    url = f"{server_host.rstrip('/')}/api/v1/bot/analytics/daily-trends"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return data.get("analytics") or {}

async def _fetch_stocks_critical(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    """Получить критические остатки с сервера."""
    url = f"{server_host.rstrip('/')}/api/v1/bot/stocks/critical"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 20, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return (data.get("stocks") or {})


async def _fetch_reviews_summary(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    """Получить сводку отзывов с сервера."""
    url = f"{server_host.rstrip('/')}/api/v1/bot/reviews/summary"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 10, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return (data.get("reviews") or {})


async def _fetch_orders_recent(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    """Получить последние заказы с сервера."""
    url = f"{server_host.rstrip('/')}/api/v1/bot/orders/recent"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 10, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return {
            "orders": data.get("orders") or [],
            "pagination": data.get("pagination") or {},
        }


async def _post_bot_webhook(telegram_id: int, text: str, webhook_base: str) -> None:
    """Отправить текстовый результат в бот через webhook."""
    url = f"{webhook_base.rstrip('/')}/webhook/notifications/{telegram_id}"
    payload = {
        "telegram_id": telegram_id,
        "user_id": telegram_id,
        "type": "analysis_completed",
        "telegram_text": text,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(url, json=payload)


async def _send_photo_to_bot(telegram_id: int, photo_base64: str, caption: str, bot_token: str) -> None:
    """Отправить график (изображение) пользователю через Telegram Bot API."""
    import base64
    from io import BytesIO
    
    try:
        # Декодируем base64 в bytes
        photo_bytes = base64.b64decode(photo_base64)
        
        # Отправляем через Telegram Bot API
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        # Формируем multipart/form-data запрос
        files = {
            "photo": ("chart.png", BytesIO(photo_bytes), "image/png")
        }
        data = {
            "chat_id": telegram_id,
            "caption": caption
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, files=files, data=data)
            if resp.status_code != 200:
                logger.error(f"❌ Failed to send photo: {resp.status_code} {resp.text}")
            else:
                logger.info(f"✅ Photo sent to telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"❌ Error sending photo: {e}")


async def orchestrate_analysis(telegram_id: int, period: str, validate_output: bool) -> None:
    """
    Оркестрация полного процесса анализа:
    1. Сбор данных с сервера
    2. Агрегация данных
    3. Генерация анализа через GPT
    4. Доставка результата в бот
    """
    server_host = os.getenv("SERVER_HOST", "http://server:8000")
    api_secret_key = os.getenv("API_SECRET_KEY", "")
    webhook_base = os.getenv("BOT_WEBHOOK_BASE", "http://bot:8001")

    logger.info(f"🚀 Starting analysis for telegram_id={telegram_id}, period={period}")

    try:
        # 1) Fetch sources concurrently
        logger.info(f"📥 Fetching data from server for telegram_id={telegram_id}")
        # Новый источник вместо /analytics/sales
        daily_trends_task = _fetch_daily_trends(telegram_id, server_host, api_secret_key)
        stocks_task = _fetch_stocks_critical(telegram_id, server_host, api_secret_key)
        reviews_task = _fetch_reviews_summary(telegram_id, server_host, api_secret_key)
        orders_task = _fetch_orders_recent(telegram_id, server_host, api_secret_key)

        fetched = await asyncio.gather(daily_trends_task, stocks_task, reviews_task, orders_task, return_exceptions=True)
        daily_trends, stocks_critical, reviews_summary, recent_orders = fetched

        # Normalize exceptions to None
        if isinstance(daily_trends, Exception):
            logger.warning(f"⚠️ Daily trends fetch failed: {daily_trends}")
            daily_trends = {}
        if isinstance(stocks_critical, Exception):
            logger.warning(f"⚠️ Stocks data fetch failed: {stocks_critical}")
            stocks_critical = None
        if isinstance(reviews_summary, Exception):
            logger.warning(f"⚠️ Reviews data fetch failed: {reviews_summary}")
            reviews_summary = None
        if isinstance(recent_orders, Exception):
            logger.warning(f"⚠️ Orders data fetch failed: {recent_orders}")
            recent_orders = None

        logger.info(f"✅ Data fetched successfully")

        # 2) Aggregate data for the template
        logger.info(f"🔄 Aggregating data...")
        sources = {
            "meta": {"telegram_id": telegram_id, "period": period},
            "daily_trends": daily_trends,
        }
        if stocks_critical:
            sources["stocks_critical"] = stocks_critical
        if reviews_summary:
            sources["reviews_summary"] = reviews_summary
        if recent_orders:
            sources["orders_recent"] = recent_orders

        data = aggregate(sources)
        logger.info(f"✅ Data aggregated, keys: {list(data.keys())}")

        # 3) Run LLM analysis
        logger.info(f"🤖 Calling OpenAI API...")
        client = GPTClient.from_env()
        logger.info(f"🔧 GPT client config: model={client.model}, max_tokens={client.max_tokens}, temperature={client.temperature}")
        template_path = "gpt_integration/analysis/LLM_ANALYSIS_TEMPLATE.md"
        result = run_analysis(client, data=data, template_path=template_path, validate=validate_output)
        
        logger.info(f"✅ LLM analysis completed, result keys: {list(result.keys())}")
        
        # Log raw response for debugging
        raw_response = result.get('raw_response', '')
        logger.info(f"📝 Raw response length: {len(raw_response)} chars")
        logger.info(f"📝 Raw response preview (first 200 chars): {raw_response[:200]}")
        logger.info(f"📝 Raw response preview (last 200 chars): {raw_response[-200:]}")
        
        # Check if JSON was parsed
        parsed_json = result.get('json', {})
        if parsed_json:
            logger.info(f"✅ JSON parsed successfully, keys: {list(parsed_json.keys())}")
        else:
            logger.error(f"❌ JSON parsing failed!")
            logger.error(f"❌ Raw response (full): {raw_response}")
        
        logger.info(f"📊 Result telegram: {result.get('telegram', {})}")

        # 4) Deliver to bot via webhook (send chunks sequentially)
        telegram = result.get("telegram", {})
        chunks = telegram.get("chunks") or []
        if not chunks and isinstance(telegram.get("mdv2"), str):
            chunks = [telegram["mdv2"]]
        if not chunks:
            logger.error(f"❌ NO CHUNKS! Detailed debugging info:")
            logger.error(f"❌ Result keys: {list(result.keys())}")
            logger.error(f"❌ telegram object: {telegram}")
            logger.error(f"❌ telegram type: {type(telegram)}")
            logger.error(f"❌ parsed JSON keys: {list(parsed_json.keys()) if parsed_json else 'None'}")
            logger.error(f"❌ raw_response length: {len(raw_response)} chars")
            logger.error(f"❌ raw_response (first 1000 chars): {raw_response[:1000]}")
            logger.error(f"❌ raw_response (last 1000 chars): {raw_response[-1000:]}")
            
            # Check for markdown blocks
            import re
            markdown_blocks = re.findall(r'```(.*?)```', raw_response, re.DOTALL)
            logger.error(f"❌ Found {len(markdown_blocks)} markdown blocks in response")
            for idx, block in enumerate(markdown_blocks[:3]):  # Log first 3 blocks
                block_preview = block[:200] + "..." if len(block) > 200 else block
                logger.error(f"❌ Markdown block {idx+1} preview: {block_preview}")
            
            # Try to provide more helpful error message
            if len(raw_response) < 100:
                error_msg = f"❌ Ответ от GPT слишком короткий ({len(raw_response)} символов). Возможно, ошибка API или недостаточно токенов."
            elif not parsed_json:
                # JSON extraction completely failed
                if "```json" in raw_response or "```" in raw_response:
                    error_msg = (
                        "❌ Ответ содержит markdown блоки, но не удалось извлечь валидный JSON.\n\n"
                        "Возможные причины:\n"
                        "• JSON содержит синтаксические ошибки\n"
                        "• Ответ был обрезан (недостаточно max_tokens)\n"
                        "• Неожиданный формат markdown блока\n\n"
                        "Попробуйте запустить анализ снова."
                    )
                elif "{" in raw_response:
                    error_msg = (
                        "❌ Ответ содержит JSON, но не в markdown блоке, и парсинг не удался.\n\n"
                        "Попробуйте запустить анализ снова."
                    )
                else:
                    error_msg = (
                        "❌ Ответ от GPT не содержит JSON данных.\n\n"
                        "Возможно, модель вернула текстовый ответ вместо JSON. "
                        "Попробуйте запустить анализ снова."
                    )
            elif "telegram" not in parsed_json:
                error_msg = (
                    "❌ В ответе отсутствует секция 'telegram'.\n\n"
                    f"Найденные секции: {', '.join(parsed_json.keys())}\n\n"
                    "Возможно, ответ был обрезан. Увеличьте max_tokens в настройках."
                )
            elif not isinstance(parsed_json.get("telegram"), dict):
                error_msg = (
                    f"❌ Секция 'telegram' имеет неверный тип: {type(parsed_json.get('telegram')).__name__}\n\n"
                    "Ожидается объект с полем 'chunks' или 'mdv2'."
                )
            else:
                tg_obj = parsed_json.get("telegram", {})
                tg_keys = list(tg_obj.keys()) if isinstance(tg_obj, dict) else []
                error_msg = (
                    f"❌ Секция 'telegram' не содержит данных для отправки.\n\n"
                    f"Найденные поля: {', '.join(tg_keys) if tg_keys else 'нет'}\n\n"
                    "Ожидается поле 'chunks' (список строк) или 'mdv2' (строка)."
                )
            
            chunks = [error_msg]

        # 4.5) Отправка графика (если есть в daily_trends)
        chart_obj = daily_trends.get("chart") if isinstance(daily_trends, dict) else None
        chart_base64_data = chart_obj.get("data") if isinstance(chart_obj, dict) else None
        bot_token = os.getenv("BOT_TOKEN", "")
        
        if isinstance(chart_base64_data, str) and chart_base64_data and bot_token:
            logger.info(f"📊 Sending chart to bot ({len(chart_base64_data)} chars base64)")
            try:
                await _send_photo_to_bot(telegram_id, chart_base64_data, "📊 Динамика за период", bot_token)
                logger.info(f"✅ Chart sent successfully")
            except Exception as chart_err:
                logger.error(f"❌ Failed to send chart: {chart_err}")
        else:
            if not chart_obj:
                logger.warning(f"⚠️ No chart object in daily_trends data")
            elif not chart_base64_data:
                logger.warning(f"⚠️ Chart object present but no 'data' base64 field")
            if not bot_token:
                logger.warning(f"⚠️ BOT_TOKEN not set in environment, cannot send chart")

        logger.info(f"📤 Sending {len(chunks)} text chunks to bot")
        for i, chunk in enumerate(chunks):
            logger.info(f"📤 Sending chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            await _post_bot_webhook(telegram_id, chunk, webhook_base)

        logger.info(f"✅ Analysis completed for telegram_id={telegram_id}")

    except Exception as e:
        logger.error(f"❌ Analysis failed for telegram_id={telegram_id}: {e}", exc_info=True)
        # Fallback: notify user about failure via webhook
        fallback_text = f"❌ Ошибка запуска анализа: {e}"
        try:
            await _post_bot_webhook(telegram_id, fallback_text, webhook_base)
        except Exception as webhook_err:
            logger.error(f"❌ Failed to send fallback webhook: {webhook_err}")
            # Last resort: swallow to avoid crashing the service
            pass

