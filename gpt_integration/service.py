import os
import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from gpt_integration.gpt_client import GPTClient
from gpt_integration.pipeline import run_analysis
from gpt_integration.aggregator import aggregate

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="GPT Integration Service", version="1.0.0")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    text: str


class AnalysisRequest(BaseModel):
    data: Dict[str, Any]
    template_path: Optional[str] = None
    validate_output: bool = False


class AnalysisStartRequest(BaseModel):
    telegram_id: int
    period: str = "7d"
    validate_output: bool = True


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # Instantiate client on each request to pick up latest envs
    client = GPTClient.from_env()
    if req.system_prompt:
        client.system_prompt = req.system_prompt
    text = client.complete_messages(req.messages)
    return ChatResponse(text=text)


@app.post("/v1/analysis")
def analysis(req: AnalysisRequest) -> Dict[str, Any]:
    client = GPTClient.from_env()
    result = run_analysis(client, data=req.data, template_path=req.template_path, validate=req.validate_output)
    return result


async def _fetch_analytics_sales(telegram_id: int, period: str, server_host: str, api_secret_key: str) -> Dict[str, Any]:
    url = f"{server_host.rstrip('/')}/api/v1/bot/analytics/sales"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "period": period}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        # Expecting schema AnalyticsSalesAPIResponse
        return data.get("analytics") or {}


async def _fetch_stocks_critical(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    url = f"{server_host.rstrip('/')}/api/v1/bot/stocks/critical"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 20, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        # Expecting schema CriticalStocksAPIResponse
        return (data.get("stocks") or {})

async def _fetch_reviews_summary(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    url = f"{server_host.rstrip('/')}/api/v1/bot/reviews/summary"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 10, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        # Expecting schema ReviewsSummaryAPIResponse
        return (data.get("reviews") or {})

async def _fetch_orders_recent(telegram_id: int, server_host: str, api_secret_key: str) -> Any:
    url = f"{server_host.rstrip('/')}/api/v1/bot/orders/recent"
    headers = {"X-API-SECRET-KEY": api_secret_key}
    params = {"telegram_id": telegram_id, "limit": 10, "offset": 0}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        # Expecting schema OrdersResponse
        return {
            "orders": data.get("orders") or [],
            "pagination": data.get("pagination") or {},
        }


async def _post_bot_webhook(telegram_id: int, text: str, webhook_base: str) -> None:
    url = f"{webhook_base.rstrip('/')}/webhook/notifications/{telegram_id}"
    payload = {
        "telegram_id": telegram_id,
        "user_id": telegram_id,
        "type": "analysis_completed",
        "telegram_text": text,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(url, json=payload)


async def _orchestrate_analysis(telegram_id: int, period: str, validate_output: bool) -> None:
    server_host = os.getenv("SERVER_HOST", "http://server:8000")
    api_secret_key = os.getenv("API_SECRET_KEY", "")
    webhook_base = os.getenv("BOT_WEBHOOK_BASE", "http://bot:8001")

    logger.info(f"🚀 Starting analysis for telegram_id={telegram_id}, period={period}")

    try:
        # 1) Fetch sources concurrently
        logger.info(f"📥 Fetching data from server for telegram_id={telegram_id}")
        sales_task = _fetch_analytics_sales(telegram_id, period, server_host, api_secret_key)
        stocks_task = _fetch_stocks_critical(telegram_id, server_host, api_secret_key)
        reviews_task = _fetch_reviews_summary(telegram_id, server_host, api_secret_key)
        orders_task = _fetch_orders_recent(telegram_id, server_host, api_secret_key)

        fetched = await asyncio.gather(sales_task, stocks_task, reviews_task, orders_task, return_exceptions=True)
        sales_analytics, stocks_critical, reviews_summary, recent_orders = fetched

        # Normalize exceptions to None
        if isinstance(sales_analytics, Exception):
            logger.warning(f"⚠️ Sales data fetch failed: {sales_analytics}")
            sales_analytics = {}
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
            "sales": sales_analytics,
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
        template_path = "gpt_integration/LLM_ANALYSIS_TEMPLATE.md"
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
            logger.error(f"❌ parsed JSON: {parsed_json}")
            logger.error(f"❌ raw_response (first 1000 chars): {raw_response[:1000]}")
            logger.error(f"❌ raw_response (last 1000 chars): {raw_response[-1000:]}")
            
            # Try to provide more helpful error message
            if "```json" in raw_response or "```" in raw_response:
                error_msg = "❌ Не удалось извлечь JSON из markdown блока. Проверьте формат ответа."
            elif len(raw_response) < 100:
                error_msg = f"❌ Ответ слишком короткий ({len(raw_response)} символов). Возможно, ошибка API."
            elif "telegram" not in parsed_json:
                error_msg = "❌ В ответе отсутствует секция 'telegram'. Увеличьте max_tokens."
            else:
                error_msg = "❌ Не удалось сформировать текст отчёта. Попробуйте позже."
            
            chunks = [error_msg]

        logger.info(f"📤 Sending {len(chunks)} chunks to bot")
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


@app.post("/v1/analysis/start")
async def analysis_start(req: AnalysisStartRequest, x_api_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    expected_key = os.getenv("API_SECRET_KEY", "")
    # Simple header check to avoid public triggering
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    # Fire-and-forget orchestration
    asyncio.create_task(_orchestrate_analysis(req.telegram_id, req.period, req.validate_output))
    return {"status": "accepted", "message": "analysis started"}


if __name__ == "__main__":
    port_str = os.getenv("GPT_PORT") or "9000"
    port = int(port_str)
    import uvicorn
    uvicorn.run("gpt_integration.service:app", host="0.0.0.0", port=port)