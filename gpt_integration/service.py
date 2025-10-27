import os
import asyncio
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from gpt_integration.gpt_client import GPTClient
from gpt_integration.pipeline import run_analysis
from gpt_integration.aggregator import aggregate

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

    try:
        # 1) Fetch minimal required sources
        sales_analytics = await _fetch_analytics_sales(telegram_id, period, server_host, api_secret_key)

        # 2) Aggregate data for the template
        sources = {
            "meta": {"telegram_id": telegram_id, "period": period},
            "sales": sales_analytics,
        }
        data = aggregate(sources)

        # 3) Run LLM analysis
        client = GPTClient.from_env()
        template_path = "gpt_integration/LLM_ANALYSIS_TEMPLATE.md"
        result = run_analysis(client, data=data, template_path=template_path, validate=validate_output)

        # 4) Deliver to bot via webhook (send chunks sequentially)
        telegram = result.get("telegram", {})
        chunks = telegram.get("chunks") or []
        if not chunks and isinstance(telegram.get("mdv2"), str):
            chunks = [telegram["mdv2"]]
        if not chunks:
            chunks = ["❌ Не удалось сформировать текст отчёта. Попробуйте позже."]

        for chunk in chunks:
            await _post_bot_webhook(telegram_id, chunk, webhook_base)

    except Exception as e:
        # Fallback: notify user about failure via webhook
        fallback_text = f"❌ Ошибка запуска анализа: {e}"
        try:
            await _post_bot_webhook(telegram_id, fallback_text, webhook_base)
        except Exception:
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