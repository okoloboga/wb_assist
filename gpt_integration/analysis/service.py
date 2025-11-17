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

def _get_env_int(name: str) -> Optional[int]:
    """Безопасно читать целочисленное значение из переменных окружения."""
    raw = os.getenv(name)
    if raw is None:
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None

def _format_money_no_round(value: float) -> str:
    """Форматирование суммы без округления: разделители тысяч пробелами и ₽."""
    try:
        ivalue = int(value)
    except Exception:
        ivalue = 0
    return f"{ivalue:,}".replace(",", " ") + "₽"


def _build_yesterday_header(dt: Dict[str, Any]) -> str:
    """Детерминированный верхний блок: берём вчера из daily_trends,
    при отсутствии — из точки time_series по дате конца диапазона."""
    dt = dt or {}
    meta = dt.get("meta") or {}
    env_window = _get_env_int("ANALYTICS_DAYS_WINDOW")
    # Используем значение из .env приоритетно, затем distill/LLM window, затем original
    N = env_window or meta.get("days_window") or meta.get("original_days_window") or 7
    y = (dt.get("yesterday") or {})
    
    
    # Логируем ОРИГИНАЛЬНЫЕ значения из входных данных (до обработки)
    logger.info(f"📥 ORIGINAL INPUT VALUES (from daily_trends.yesterday):")
    logger.info(f"  yesterday.orders: {y.get('orders')}")
    logger.info(f"  yesterday.orders_amount: {y.get('orders_amount')}")
    logger.info(f"  yesterday.cancellations: {y.get('cancellations')}")
    logger.info(f"  yesterday.cancellations_amount: {y.get('cancellations_amount')}")
    logger.info(f"  yesterday.buyouts: {y.get('buyouts')}")
    logger.info(f"  yesterday.buyouts_amount: {y.get('buyouts_amount')}")
    logger.info(f"  yesterday.returns: {y.get('returns')}")
    logger.info(f"  yesterday.returns_amount: {y.get('returns_amount')}")
    
    # Fallback, если нет yesterday
    if not y or not y.get("date"):
        ts = dt.get("time_series") or []
        target_date = None
        dr = meta.get("date_range") or {}
        if isinstance(dr, dict):
            target_date = dr.get("end")
        picked = None
        if target_date:
            for p in ts:
                if p.get("date") == target_date:
                    picked = p
                    break
        if picked is None and ts:
            picked = ts[-1]
        if picked:
            y = {
                "date": picked.get("date"),
                "orders": picked.get("orders", 0),
                "cancellations": picked.get("cancellations", 0),
                "buyouts": picked.get("buyouts", 0),
                "returns": picked.get("returns", 0),
                "orders_amount": picked.get("orders_amount", 0.0),
                "cancellations_amount": picked.get("cancellations_amount", 0.0),
                "buyouts_amount": picked.get("buyouts_amount", 0.0),
                "returns_amount": picked.get("returns_amount", 0.0),
                "top_products": (dt.get("yesterday") or {}).get("top_products", []),
            }
        else:
            y = y or {}
    date = y.get("date", "")
    orders = int(y.get("orders", 0) or 0)
    cancels = int(y.get("cancellations", 0) or 0)
    buyouts = int(y.get("buyouts", 0) or 0)
    returns = int(y.get("returns", 0) or 0)
    orders_amount = float(y.get("orders_amount", 0.0) or 0.0)
    cancels_amount = float(y.get("cancellations_amount", 0.0) or 0.0)
    buyouts_amount = float(y.get("buyouts_amount", 0.0) or 0.0)
    returns_amount = float(y.get("returns_amount", 0.0) or 0.0)
    avg_check = (orders_amount / orders) if orders > 0 else 0.0

    conv = (dt.get("aggregates") or {}).get("conversion") or {}
    buyout_rate = conv.get("buyout_rate_percent", 0.0)
    return_rate = conv.get("return_rate_percent", 0.0)
    totals = (dt.get("aggregates") or {}).get("totals") or {}
    avg_rating = totals.get("avg_rating")
    if avg_rating is None:
        ts2 = dt.get("time_series") or []
        avg_rating = (ts2[-1].get("avg_rating") if ts2 else 0.0) or 0.0
    
    # Логируем ОРИГИНАЛЬНЫЕ значения из aggregates
    logger.info(f"📊 ORIGINAL AGGREGATES VALUES (from daily_trends.aggregates):")
    logger.info(f"  aggregates.conversion.buyout_rate_percent: {conv.get('buyout_rate_percent')}")
    logger.info(f"  aggregates.conversion.return_rate_percent: {conv.get('return_rate_percent')}")
    logger.info(f"  aggregates.totals.avg_rating: {totals.get('avg_rating')}")


    
    # Получаем топ товары: только из dt.top_products (топ за период N дней)
    top_products = (dt.get("top_products") or [])[:5]
    for i, p in enumerate(top_products, 1):
        logger.info(f"  {i}. {p.get('name', 'N/A')} — {p.get('orders', 0)} заказов")

    lines = [
        "📊 ДИНАМИКА",
        "",
        f"Вчера ({date}):",
        "",
        f"Заказы: {orders} шт. — {_format_money_no_round(orders_amount)}",
        f"Отмены: {cancels} шт. — {_format_money_no_round(cancels_amount)}",
        f"Выкупы: {buyouts} шт. — {_format_money_no_round(buyouts_amount)}",
        f"Возвраты: {returns} шт. — {_format_money_no_round(returns_amount)}",
        "",
        f"Средний чек: {_format_money_no_round(avg_check)}",
        "",
        f"📈 ПОКАЗАТЕЛИ ЗА {N} ДНЕЙ",
        "",
        f"• Коэффициент выкупа: {buyout_rate}%",
        f"• Коэффициент возврата: {return_rate}%",
        f"• Средняя оценка: {avg_rating}",
        "",
        f"🛍️ ТОП ТОВАРОВ ЗА {N} ДНЕЙ",
    ]
    for i, p in enumerate(top_products, 1):
        name = p.get("name", "")
        cnt = int(p.get("orders", 0) or 0)
        lines.append(f"{i}. {name} — {cnt} заказов")
    
    result = "\n".join(lines)
    return result


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
        # Предпочитаем "data", фолбэк на daily_trends/analytics
        return data.get("data") or data.get("daily_trends") or data.get("analytics") or {}

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

        # 4) Отправка графика и составного сообщения
        # Используем обработанный daily_trends из data (с original_days_window), но для графика нужен оригинальный
        processed_daily_trends = data.get("daily_trends") or {}
        # Fallback: если processed_daily_trends пустой, используем оригинальный daily_trends
        if not processed_daily_trends:
            if isinstance(daily_trends, dict):
                processed_daily_trends = daily_trends.copy()
            else:
                processed_daily_trends = {}
        # Добавляем original_days_window из meta, если есть
        if isinstance(processed_daily_trends, dict):
            meta_block = processed_daily_trends.get("meta") or {}
            if not meta_block and isinstance(daily_trends, dict):
                meta_block = daily_trends.get("meta") or {}
                processed_daily_trends["meta"] = meta_block
            if "days_window" in meta_block and "original_days_window" not in meta_block:
                meta_block["original_days_window"] = meta_block.get("days_window")
        
        chart_obj = daily_trends.get("chart") if isinstance(daily_trends, dict) else None
        chart_base64_data = chart_obj.get("data") if isinstance(chart_obj, dict) else None
        bot_token = os.getenv("BOT_TOKEN", "")
        
        # 4.1) Отправка графика
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

        # 4.2) Построение детерминированной шапки
        # Используем обработанный daily_trends из data (с original_days_window)
        # Но нужно добавить yesterday и top_products из оригинального daily_trends, если их нет
        if processed_daily_trends:
            header_yesterday = data.get("yesterday")
            if not header_yesterday and isinstance(daily_trends, dict):
                header_yesterday = daily_trends.get("yesterday")
            if header_yesterday:
                processed_daily_trends["yesterday"] = header_yesterday
            header_top_products = processed_daily_trends.get("top_products")
            if not header_top_products:
                if isinstance(daily_trends, dict) and daily_trends.get("top_products"):
                    header_top_products = daily_trends.get("top_products")
                elif data.get("top_products"):
                    header_top_products = data.get("top_products")
                else:
                    header_top_products = []
                processed_daily_trends["top_products"] = header_top_products
        
        # Логируем для отладки
        daily_trends_meta = (processed_daily_trends.get("meta") or {}) if isinstance(processed_daily_trends, dict) else {}
        
        header_text = _build_yesterday_header(processed_daily_trends)
        
        # Получаем days_window для заголовка инсайтов (соответствует ANALYTICS_DAYS_WINDOW)
        env_window = _get_env_int("ANALYTICS_DAYS_WINDOW")
        analysis_days = env_window or daily_trends_meta.get("days_window") or daily_trends_meta.get("original_days_window") or 7

        # 4.3) Извлечение инсайтов и рекомендаций из GPT
        parsed_json = result.get('json', {}) or {}
        insights = parsed_json.get("insights") or []
        recs = parsed_json.get("recommendations") or []

        logger.info(f"📝 Extracted from GPT: {len(insights)} insights, {len(recs)} recommendations")

        # 4.4) Форматирование инсайтов
        insights_lines = ["", f"💡 ИНСАЙТЫ (анализ за {analysis_days} дней)", ""]
        for insight in insights[:5]:  # Максимум 5 инсайтов
            title = insight.get("title") or ""
            detail = insight.get("detail") or ""
            if title and detail:
                insights_lines.append(f"• {title} — {detail}")
            elif title:
                insights_lines.append(f"• {title}")
            elif detail:
                insights_lines.append(f"• {detail}")

        # 4.5) Форматирование рекомендаций
        rec_lines = ["", "🔍 РЕКОМЕНДАЦИИ", ""]
        for rec in recs[:3]:  # Максимум 3 рекомендации
            action = rec.get("action") or ""
            why = rec.get("why") or ""
            if action and why:
                rec_lines.append(f"• {action} — {why}")
            elif action:
                rec_lines.append(f"• {action}")
            elif why:
                rec_lines.append(f"• {why}")

        # 4.6) Объединение всех частей
        final_text = "\n".join([
            header_text,
            "\n".join(insights_lines),
            "\n".join(rec_lines)
        ])

        logger.info(f"📤 Sending combined message ({len(final_text)} chars)")
        await _post_bot_webhook(telegram_id, final_text, webhook_base)

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

