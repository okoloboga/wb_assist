import json
from typing import Any, Dict, List, Optional

from gpt_integration.gpt_client import GPTClient
from gpt_integration.template_loader import (
    get_system_prompt,
    get_tasks,
    get_output_json_schema,
    get_output_tg_guide,
)
from utils.formatters import escape_markdown_v2, split_telegram_message


def compose_messages(data: Dict[str, Any], template_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Compose LLM messages using SYSTEM + DATA + TASKS (+ optional schema/guides).
    Returns OpenAI chat messages list.
    """
    system = get_system_prompt(template_path) or (
        "Ты аналитик e‑commerce. Пиши кратко, по делу, на русском."
    )
    tasks = get_tasks(template_path)
    schema = get_output_json_schema(template_path)
    tg_guide = get_output_tg_guide(template_path)

    data_json = json.dumps(data, ensure_ascii=False, indent=2)
    sections: List[str] = [f"## DATA\n{data_json}"]
    if tasks:
        sections.append(f"## TASKS\n{tasks}")
    if schema:
        sections.append(f"## OUTPUT_JSON_SCHEMA\n{schema}")
    if tg_guide:
        sections.append(f"## OUTPUT_TG_GUIDE\n{tg_guide}")
    sections.append(
        "Верни ответ строго в формате OUTPUT_JSON и OUTPUT_TG, \n"
        "соблюдая описанные схемы и правила."
    )
    user_content = "\n\n".join(sections)

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def _safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """Try to extract the largest JSON object from text."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except Exception:
        try:
            return json.loads(snippet.replace("\\n", "\n"))
        except Exception:
            return None


def _prepare_telegram_from_text(text: str) -> Dict[str, Any]:
    escaped = escape_markdown_v2(text)
    chunks = split_telegram_message(escaped)
    character_count = sum(len(c) for c in chunks)
    return {"chunks": chunks, "character_count": character_count}


def _normalize_telegram(block: Any) -> Dict[str, Any]:
    if isinstance(block, dict):
        chunks = block.get("chunks") or []
        if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks) and chunks:
            escaped_chunks = [escape_markdown_v2(c) for c in chunks]
            character_count = sum(len(c) for c in escaped_chunks)
            return {"chunks": escaped_chunks, "character_count": character_count}
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            return _prepare_telegram_from_text(text)
    elif isinstance(block, str) and block.strip():
        return _prepare_telegram_from_text(block)
    return {"chunks": [], "character_count": 0}


def run_analysis(
    client: GPTClient, data: Dict[str, Any], template_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrate LLM analysis:
    - compose messages
    - call LLM
    - parse JSON and prepare telegram/sheets outputs
    Returns dict with keys: messages, raw_response, json, telegram, sheets
    """
    messages = compose_messages(data, template_path)
    text = client.complete_messages(messages)
    parsed = _safe_json_extract(text) or {}

    telegram = _normalize_telegram(parsed.get("telegram")) if parsed else {"chunks": [], "character_count": 0}
    if not telegram["chunks"]:
        # Fallback: try extract text after 'OUTPUT_TG'
        lower = text.lower()
        idx = lower.find("output_tg")
        if idx != -1:
            tg_text = text[idx + len("output_tg") :].strip()
            if tg_text:
                telegram = _prepare_telegram_from_text(tg_text)

    sheets = parsed.get("sheets") if isinstance(parsed, dict) else None
    if not isinstance(sheets, dict):
        sheets = {"headers": [], "rows": []}
    if not isinstance(sheets.get("headers"), list):
        sheets["headers"] = []
    if not isinstance(sheets.get("rows"), list):
        sheets["rows"] = []

    return {
        "messages": messages,
        "raw_response": text,
        "json": parsed,
        "telegram": telegram,
        "sheets": sheets,
    }