import json
from typing import Any, Dict, List, Optional

from gpt_integration.gpt_client import GPTClient
from gpt_integration.analysis.template_loader import (
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
    """Try to extract the largest JSON object from text.
    Handles markdown code blocks like ```json ... ``` properly.
    """
    import re
    
    # Step 1: Try to extract JSON from markdown code block
    # Pattern: ```json (optional) ... { ... } ... ``` 
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(code_block_pattern, text, re.DOTALL)
    
    if matches:
        # Try each match (usually there's only one)
        for match in matches:
            try:
                return json.loads(match)
            except Exception:
                pass
    
    # Step 2: Remove all markdown code blocks and try again
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```', '', cleaned)
    
    # Step 3: Find the outermost JSON object
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    
    snippet = cleaned[start : end + 1]
    
    # Step 4: Try to parse
    try:
        return json.loads(snippet)
    except Exception:
        # Try with escaped newlines fixed
        try:
            return json.loads(snippet.replace("\\n", "\n"))
        except Exception:
            # Last resort: try to find nested braces
            try:
                # Count braces to find matching closing brace
                brace_count = 0
                end_pos = start
                for i in range(start, len(cleaned)):
                    if cleaned[i] == '{':
                        brace_count += 1
                    elif cleaned[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i
                            break
                if end_pos > start:
                    snippet = cleaned[start : end_pos + 1]
                    return json.loads(snippet)
            except Exception:
                pass
    
    return None


def _prepare_telegram_from_text(text: str) -> Dict[str, Any]:
    # Remove MarkdownV2 escaping if present (bot sends without parse_mode)
    # This handles cases where LLM accidentally escaped text
    unescaped = _unescape_markdown_v2(text)
    chunks = split_telegram_message(unescaped)
    character_count = sum(len(c) for c in chunks)
    return {"chunks": chunks, "character_count": character_count}


def _unescape_markdown_v2(text: str) -> str:
    """Remove MarkdownV2 escaping characters."""
    if not text:
        return ""
    # Remove backslashes before special characters
    import re
    # Pattern matches backslash followed by special MarkdownV2 characters
    specials = r"_\[\]()~`>#+-=|{}.!*\\"
    # Replace \X with X (where X is a special character)
    return re.sub(r'\\([' + re.escape(specials) + r'])', r'\1', text)


def _normalize_telegram(block: Any) -> Dict[str, Any]:
    if isinstance(block, dict):
        chunks = block.get("chunks") or []
        if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks) and chunks:
            # Remove MarkdownV2 escaping since bot sends without parse_mode
            unescaped_chunks = [_unescape_markdown_v2(c) for c in chunks]
            # Split each chunk if it's too long, then flatten
            final_chunks = []
            for chunk in unescaped_chunks:
                split_chunks = split_telegram_message(chunk)
                final_chunks.extend(split_chunks)
            character_count = sum(len(c) for c in final_chunks)
            return {"chunks": final_chunks, "character_count": character_count}
        
        # Check for mdv2 field (MarkdownV2 text from OpenAI)
        mdv2 = block.get("mdv2")
        if isinstance(mdv2, str) and mdv2.strip():
            # Remove escaping and split into chunks
            unescaped = _unescape_markdown_v2(mdv2)
            chunks = split_telegram_message(unescaped)
            character_count = sum(len(c) for c in chunks)
            return {"chunks": chunks, "character_count": character_count}
        
        # Check for text field
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            return _prepare_telegram_from_text(text)
    elif isinstance(block, str) and block.strip():
        return _prepare_telegram_from_text(block)
    return {"chunks": [], "character_count": 0}


def _validate_output(parsed: Dict[str, Any], schema_text: Optional[str]) -> List[str]:
    errors: List[str] = []
    if not isinstance(parsed, dict):
        return ["Output is not a JSON object"]
    expected_keys = ["key_metrics", "anomalies", "insights", "recommendations", "telegram", "sheets"]
    for k in expected_keys:
        if k not in parsed:
            errors.append(f"Missing key: {k}")
    tg = parsed.get("telegram", {})
    if isinstance(tg, dict):
        has_chunks = isinstance(tg.get("chunks"), list)
        has_mdv2 = isinstance(tg.get("mdv2"), str)
        if not (has_chunks or has_mdv2):
            errors.append("telegram must have 'chunks' list or 'mdv2' string")
    else:
        errors.append("telegram must be an object")
    sh = parsed.get("sheets", {})
    if isinstance(sh, dict):
        if not isinstance(sh.get("headers"), list):
            errors.append("sheets.headers must be a list")
        if not isinstance(sh.get("rows"), list):
            errors.append("sheets.rows must be a list")
    else:
        errors.append("sheets must be an object")
    return errors


def run_analysis(
    client: GPTClient, data: Dict[str, Any], template_path: Optional[str] = None, validate: bool = False
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

    # Handle explicit LLM errors (from client retries)
    result_error: Optional[str] = None
    if isinstance(text, str) and text.strip().startswith("ERROR:"):
        result_error = text.strip()

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

    # If still empty, and we have an LLM error, return a readable warning for TG
    if not telegram["chunks"] and result_error:
        # Check if it's a regional restriction error
        error_text = result_error
        if "unsupported_country_region_territory" in error_text or "не available in your region" in error_text.lower():
            error_text = (
                "⚠️ OpenAI API недоступен в вашем регионе.\n\n"
                "Для решения проблемы необходимо настроить альтернативный API endpoint:\n"
                "1. Используйте прокси-сервер для OpenAI API\n"
                "2. Или используйте OpenAI-совместимый провайдер (например, Azure OpenAI, Anyscale и др.)\n"
                "3. Установите переменную окружения OPENAI_BASE_URL с адресом альтернативного endpoint\n\n"
                f"Технические детали:\n{result_error}"
            )
        else:
            error_text = f"⚠️ Ошибка запроса к LLM. Пожалуйста, повторите попытку позже.\n\n{result_error}"
        
        telegram = _prepare_telegram_from_text(error_text)

    sheets = parsed.get("sheets") if isinstance(parsed, dict) else None
    if not isinstance(sheets, dict):
        sheets = {"headers": [], "rows": []}
    if not isinstance(sheets.get("headers"), list):
        sheets["headers"] = []
    if not isinstance(sheets.get("rows"), list):
        sheets["rows"] = []

    result = {
        "messages": messages,
        "raw_response": text,
        "json": parsed,
        "telegram": telegram,
        "sheets": sheets,
    }
    if result_error:
        result["llm_error"] = result_error
    if validate:
        try:
            schema_text = get_output_json_schema(template_path)
        except Exception:
            schema_text = None
        result["validation_errors"] = _validate_output(parsed, schema_text)
    return result