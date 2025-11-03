from typing import Any, Dict, List
import os
import json
import asyncio
import logging
from openai import OpenAI
from .tools import registry, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Вы — ассистент аналитики WB. Если для ответа нужны данные или вычисления, "
    "используйте инструменты. Никогда не просите пользователя запускать анализ — "
    "сами выполните и предоставьте результат. Отвечайте кратко, с цифрами и выводами."
)

def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)

async def _call_llm(messages: List[Dict[str, Any]], tools: list | None = None) -> Dict[str, Any]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "900"))

    def _sync_call():
        client = _get_client()
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools or None,
                tool_choice="auto" if tools else None,
            )
        except Exception as e:
            # Check for regional restriction error (403)
            error_code = None
            error_message = None
            status_code = None
            
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, dict) and 'error' in error_data:
                        error_info = error_data['error']
                        error_code = error_info.get('code')
                        error_message = error_info.get('message', '')
                except Exception:
                    pass
            
            if hasattr(e, 'status_code'):
                status_code = e.status_code
            elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                status_code = e.response.status_code
            
            # If it's a regional restriction, provide helpful message
            is_regional_error = (
                status_code == 403 and 
                (error_code == 'unsupported_country_region_territory' or 
                 'unsupported_country' in str(e).lower() or
                 'region' in str(e).lower() and 'not supported' in str(e).lower())
            )
            
            if is_regional_error:
                raise RuntimeError(
                    f"OpenAI API недоступен в вашем регионе (403: {error_code or 'unsupported_country_region_territory'}). "
                    f"Настройте OPENAI_BASE_URL для использования альтернативного endpoint."
                )
            raise

    try:
        resp = await asyncio.to_thread(_sync_call)
        return {
            "message": resp.choices[0].message,
            "usage": getattr(resp, "usage", None),
        }
    except RuntimeError:
        # Re-raise regional errors as-is
        raise
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        raise RuntimeError(f"Ошибка запроса к LLM: {e}")

async def run_agent(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
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
    first = await _call_llm(enriched, tools=registry)
    msg = first["message"]
    usage = first.get("usage")

    # If no tool calls — return content
    tool_calls = getattr(msg, "tool_calls", None)
    if not tool_calls:
        return {
            "final": msg.content or "",
            "tokens_used": getattr(usage, "total_tokens", 0) if usage else 0,
        }

    # Execute tools
    tool_messages: List[Dict[str, Any]] = []
    for tc in tool_calls:
        func = tc.function
        name = func.name
        args_json = func.arguments or "{}"
        try:
            result_json = await execute_tool(name, args_json)
        except Exception as e:
            logger.exception("Tool execution failed: %s", name)
            result_json = json.dumps({"error": str(e)})
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
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
        "content": msg.content,
        "tool_calls": msg.tool_calls,
    })
    followup.extend(tool_messages)

    final = await _call_llm(followup)
    fmsg = final["message"]
    fusage = final.get("usage")
    return {
        "final": fmsg.content or "",
        "tokens_used": getattr(fusage, "total_tokens", 0) if fusage else 0,
    }
