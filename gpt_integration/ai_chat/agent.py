from typing import Any, Dict, List
import os
import json
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gpt_integration.core.llm_client import llm_client
from .tools import registry, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Вы — ассистент аналитики WB. Если для ответа нужны данные или вычисления, "
    "используйте инструменты. Никогда не просите пользователя запускать анализ — "
    "сами выполните и предоставьте результат. Отвечайте кратко, с цифрами и выводами."
)

async def _call_llm(
    messages: List[Dict[str, Any]], 
    model: str = "gpt-5.1",
    tools: list | None = None
) -> Dict[str, Any]:
    """
    Call LLM with UniversalLLMClient
    
    Args:
        messages: List of messages
        model: Model ID (gpt-5.1, claude-sonnet-4.5)
        tools: List of tools (not yet supported)
    """
    temperature = float(os.getenv("COMET_TEMPERATURE", "0.7"))
    max_tokens = int(os.getenv("COMET_MAX_TOKENS", "2000"))

    try:
        # Используем UniversalLLMClient
        response_text, tokens_used = await llm_client.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Возвращаем в формате, совместимом с OpenAI
        return {
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "usage": {
                "total_tokens": tokens_used
            }
        }
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        raise

async def run_agent(
    messages: List[Dict[str, Any]], 
    model: str = "gpt-5.1"
) -> Dict[str, Any]:
    """Agent loop with tool-calling.

    1) Call LLM with tools.
    2) If tool_calls present, execute them and feed results back.
    3) Return final answer.
    """
    # Ensure system prompt present
    enriched: List[Dict[str, Any]] = []
    has_system = any(m.get("role") == "system" for m in messages)
    if not has_system:
        enriched.append({"role": "system", "content": SYSTEM_PROMPT})
    enriched.extend(messages)

    # First call with tools
    first = await _call_llm(enriched, model=model, tools=registry)
    msg = first["message"]
    usage = first.get("usage")
    if usage:
        logger.info(
            "🧮 LLM call #1 tokens: prompt=%s, completion=%s, total=%s",
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            usage.get("total_tokens"),
        )

    # If no tool calls — return content
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        return {
            "final": msg.get("content") or "",
            "tokens_used": getattr(usage, "total_tokens", 0) if usage else 0,
        }

    # Execute tools
    tool_messages: List[Dict[str, Any]] = []
    for tc in tool_calls:
        # Handle both dict (CometAPI/JSON) and object (OpenAI SDK) formats
        if isinstance(tc, dict):
            func = tc.get("function", {})
            name = func.get("name", "")
            args_json = func.get("arguments", "{}")
            tool_call_id = tc.get("id", "")
        else:
            # OpenAI SDK object format
            func = tc.function
            name = func.name
            args_json = func.arguments or "{}"
            tool_call_id = tc.id
        try:
            logger.info(f"🔧 Executing tool: {name} with args: {args_json[:200]}")
            result_json = await execute_tool(name, args_json)
            logger.info(f"✅ Tool {name} executed successfully, result length: {len(result_json)}")
        except Exception as e:
            logger.exception(f"❌ Tool execution failed: {name}")
            # Формируем детальное сообщение об ошибке для AI
            error_detail = {
                "error": str(e),
                "error_type": type(e).__name__,
                "tool": name,
                "message": f"Произошла ошибка при выполнении запроса к базе данных. Детали: {str(e)}"
            }
            result_json = json.dumps(error_detail, ensure_ascii=False)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": result_json,
        })

    # Follow-up with tool results
    followup: List[Dict[str, Any]] = []
    if not has_system:
        followup.append({"role": "system", "content": SYSTEM_PROMPT})
    followup.extend(messages)
    # include assistant with tool_calls per API contract
    followup.append({
        "role": "assistant",
        "content": msg.get("content"),
        "tool_calls": msg.get("tool_calls"),
    })
    followup.extend(tool_messages)

    final = await _call_llm(followup, model=model)
    fmsg = final["message"]
    fusage = final.get("usage")
    if fusage:
        logger.info(
            "🧮 LLM call #2 tokens: prompt=%s, completion=%s, total=%s",
            fusage.get("prompt_tokens"),
            fusage.get("completion_tokens"),
            fusage.get("total_tokens"),
        )
    return {
        "final": fmsg.get("content") or "",
        "tokens_used": getattr(fusage, "total_tokens", 0) if fusage else 0,
    }
