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


def _log_data_summary(data: Dict[str, Any]) -> None:
    """Логирует краткую сводку данных, отправляемых в GPT."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"  data keys: {list(data.keys())}")
    
    # Meta
    meta = data.get("meta") or {}
    logger.debug(f"  meta: telegram_id={meta.get('telegram_id')}, period={meta.get('period')}, days_window={meta.get('days_window')}")
    
    # Yesterday
    yesterday = data.get("yesterday") or {}
    if yesterday:
        logger.debug(f"  yesterday: date={yesterday.get('date')}, orders={yesterday.get('orders')}, "
                    f"orders_amount={yesterday.get('orders_amount')}, top_products_count={len(yesterday.get('top_products', []))}")
    else:
        logger.debug(f"  yesterday: отсутствует")
    
    # Daily trends
    daily_trends = data.get("daily_trends") or {}
    if daily_trends:
        dt_meta = daily_trends.get("meta") or {}
        dt_agg = daily_trends.get("aggregates") or {}
        ts = daily_trends.get("time_series") or []
        logger.debug(f"  daily_trends: days_window={dt_meta.get('days_window')}, time_series_len={len(ts)}")
        logger.debug(f"    aggregates: buyout_rate={dt_agg.get('conversion', {}).get('buyout_rate_percent')}%, "
                    f"return_rate={dt_agg.get('conversion', {}).get('return_rate_percent')}%")
        if ts:
            logger.debug(f"    time_series: первая дата={ts[0].get('date')}, последняя дата={ts[-1].get('date')}")
    else:
        logger.debug(f"  daily_trends: отсутствует")
    
    # Other sources
    for key in ["stocks_critical", "reviews_summary", "orders_recent", "sales"]:
        val = data.get(key)
        if val:
            if isinstance(val, dict):
                logger.debug(f"  {key}: присутствует (keys: {list(val.keys())[:5]})")
            elif isinstance(val, list):
                logger.debug(f"  {key}: присутствует (len={len(val)})")
            else:
                logger.debug(f"  {key}: присутствует (type={type(val).__name__})")
        else:
            logger.debug(f"  {key}: отсутствует")
    
    # Размер JSON
    try:
        data_json = json.dumps(data, ensure_ascii=False)
        logger.debug(f"  JSON size: {len(data_json)} символов (~{len(data_json.encode('utf-8'))} bytes)")
    except Exception as e:
        logger.debug(f"  JSON size: не удалось вычислить ({e})")


def compose_messages(data: Dict[str, Any], template_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Compose LLM messages using SYSTEM + DATA + TASKS (+ optional schema/guides).
    Returns OpenAI chat messages list.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Логируем краткую сводку данных
    _log_data_summary(data)
    
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
        "Верни ответ СТРОГО в формате OUTPUT_JSON и OUTPUT_TG, \n"
        "соблюдая описанные схемы и правила.\n\n"
        "КРИТИЧЕСКИ ВАЖНО: Верни JSON БЕЗ markdown блоков (без ```json и ```). "
        "Начни ответ сразу с открывающей фигурной скобки { и закончи закрывающей }."
    )
    user_content = "\n\n".join(sections)
    
    # Логируем размер промпта
    total_size = len(system) + len(user_content)

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def _safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """Извлекает JSON объект из текста.
    Теперь ожидает чистый JSON без markdown блоков, но поддерживает fallback для markdown.
    """
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not text or not isinstance(text, str):
        return None
    
    # Удаляем лишние пробелы в начале и конце
    cleaned = text.strip()
    
    def _sanitize_numeric_underscores(s: str) -> str:
        """
        Удаляет подчёркивания внутри чисел (например, 40_000.0 -> 40000.0), не затрагивая строки.
        """
        # Заменяем только вне строк JSON (грубая, но эффективная стратегия):
        out = []
        in_string_local = False
        escape = False
        for ch in s:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == '\\\\':
                out.append(ch)
                escape = True
                continue
            if ch == '\"':
                in_string_local = not in_string_local
                out.append(ch)
                continue
            if not in_string_local and ch == '_':
                # пропускаем подчёркивания вне строк
                continue
            out.append(ch)
        return ''.join(out)
    
    def _sanitize_numeric_currency(s: str) -> str:
        """
        Удаляет символы валюты после чисел (например, 112500₽ -> 112500, 1071.43₽ -> 1071.43, -13000₽ -> -13000), не затрагивая строки.
        """
        # Паттерн для поиска чисел с символом валюты после них
        # Поддерживаем отрицательные числа и числа с плавающей точкой
        currency_chars = r'₽\$\€£¥'
        
        # Паттерн: опциональный минус + число (с точкой или без) + валюта + запятая/закрывающая скобка/закрывающая фигурная скобка/конец строки
        # Примеры: "112500₽,", "-13000₽,", "1071.43₽,", "112500₽}"
        # Экранируем } в f-string, удваивая его
        pattern = rf'(-?\d+\.?\d*)([{currency_chars}]+)(\s*[,}}\]]|\s*$)'
        
        def replace_currency(match):
            number = match.group(1)
            after = match.group(3)
            return number + after
        
        # Применяем замену
        result = re.sub(pattern, replace_currency, s)
        return result
    
    def extract_json_from_text(text_to_parse: str, description: str) -> Optional[Dict[str, Any]]:
        """Вспомогательная функция для извлечения JSON из текста."""
        start = text_to_parse.find("{")
        if start == -1:
            return None
        
        # Считаем скобки для поиска соответствующей закрывающей скобки
        brace_count = 0
        end_pos = -1
        in_string = False
        escape_next = False
        
        for i in range(start, len(text_to_parse)):
            char = text_to_parse[i]
            
            # Обработка экранирования
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            
            # Считаем скобки только вне строк
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
        
        if end_pos <= start:
            return None
        
        snippet = text_to_parse[start : end_pos + 1]
        
        # Пробуем несколько стратегий исправления
        fixing_strategies = [
            lambda s: s,  # Оригинал
            lambda s: _sanitize_numeric_underscores(s),  # Удаляем подчёркивания в числах
            lambda s: _sanitize_numeric_currency(s),  # Удаляем символы валюты из чисел
            lambda s: _sanitize_numeric_underscores(_sanitize_numeric_currency(s)),  # Комбинация: валюта + подчёркивания
            lambda s: re.sub(r',(\s*[}\]])', r'\\1', s),  # Удаляем trailing commas
            lambda s: re.sub(r',(\s*[}\]])', r'\\1', s).replace('\\\\n', '\\n'),  # Исправляем newlines
        ]
        
        for strategy_idx, strategy in enumerate(fixing_strategies):
            try:
                fixed = strategy(snippet)
                parsed = json.loads(fixed)
                if isinstance(parsed, dict):
                    if strategy_idx == 0:
                        logger.info(f"✅ Успешно извлечен JSON из {description} ({len(snippet)} символов)")
                    else:
                        logger.info(f"✅ Успешно извлечен JSON из {description} после исправления стратегией #{strategy_idx}")
                    return parsed
            except json.JSONDecodeError as e:
                if strategy_idx == 0:
                    logger.debug(f"Ошибка декодирования JSON в {description} на позиции {e.pos}: {e.msg}")
                    error_pos = e.pos if hasattr(e, 'pos') else 0
                    logger.debug(f"Проблемная область: {snippet[max(0, error_pos-50):error_pos+50]}")
                continue
            except Exception as e:
                logger.debug(f"Стратегия #{strategy_idx} не удалась для {description}: {e}")
                continue
        
        return None
    
    # Шаг 1: Пытаемся найти чистый JSON (начинающийся сразу с {)
    # Это основной случай - чистый JSON без markdown
    result = extract_json_from_text(cleaned, "чистого текста")
    if result:
        return result
    
    # Шаг 2: Fallback - если не нашли чистый JSON, пробуем найти в markdown блоках
    # (на случай, если GPT все еще вернул markdown)
    logger.debug("Чистый JSON не найден, пробуем markdown блоки как fallback...")
    
    code_block_patterns = [
        r'```json\s*(.*?)\s*```',  # ```json ... ```
        r'```JSON\s*(.*?)\s*```',  # ```JSON ... ```
        r'```\s*(.*?)\s*```',      # ``` ... ``` (fallback)
    ]
    
    for pattern in code_block_patterns:
        code_blocks = re.findall(pattern, cleaned, re.DOTALL | re.IGNORECASE)
        
        for block_content in code_blocks:
            if not block_content.strip():
                continue
            
            result = extract_json_from_text(block_content.strip(), "markdown блока")
            if result:
                return result
    
    # Шаг 3: Удаляем markdown блоки и пробуем найти JSON в оставшемся тексте
    cleaned_no_markdown = re.sub(r'```(?:json|JSON)?\s*.*?\s*```', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    if cleaned_no_markdown != cleaned:
        result = extract_json_from_text(cleaned_no_markdown.strip(), "текста без markdown")
        if result:
            return result
    
    # Логируем проблему для отладки
    logger.error("❌ Не удалось извлечь JSON из текста после всех стратегий")
    # Логируем образец текста для помощи в отладке
    if len(text) > 500:
        logger.error(f"Образец текста (первые 500 символов): {text[:500]}")
        logger.error(f"Образец текста (последние 500 символов): {text[-500:]}")
    else:
        logger.error(f"Полный текст: {text}")
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
    import logging
    logger = logging.getLogger(__name__)
    
    messages = compose_messages(data, template_path)
    text = client.complete_messages(messages)
    
    # Save raw response to file for debugging
    try:
        import os
        debug_dir = os.path.join(os.path.dirname(__file__), "debug")
        os.makedirs(debug_dir, exist_ok=True)
        debug_file = os.path.join(debug_dir, "last_gpt_response.txt")
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(f"=== RAW GPT RESPONSE ({len(text)} chars) ===\n\n")
            f.write(text)
            f.write("\n\n=== END ===\n")
        logger.info(f"💾 Saved raw response to {debug_file}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save debug file: {e}")

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
        error_lower = error_text.lower()
        
        if "unsupported_country_region_territory" in error_text or "не available in your region" in error_lower:
            error_text = (
                "⚠️ OpenAI API недоступен в вашем регионе.\n\n"
                "Для решения проблемы необходимо настроить альтернативный API endpoint:\n"
                "1. Используйте прокси-сервер для OpenAI API\n"
                "2. Или используйте OpenAI-совместимый провайдер (например, Azure OpenAI, Anyscale и др.)\n"
                "3. Установите переменную окружения OPENAI_BASE_URL с адресом альтернативного endpoint\n\n"
                f"Технические детали:\n{result_error}"
            )
        elif "connection error" in error_lower or "connection" in error_lower:
            # Connection error - provide helpful message
            error_text = (
                "⚠️ Ошибка соединения с API.\n\n"
                "Не удалось установить соединение с сервисом. Возможные причины:\n"
                "• Проблемы с интернет-соединением\n"
                "• Временная недоступность сервера\n"
                "• Неправильная настройка прокси или DNS\n"
                "• Блокировка файрволом\n\n"
                "Попробуйте:\n"
                "1. Проверить интернет-соединение\n"
                "2. Подождать несколько минут и повторить попытку\n"
                "3. Проверить настройки сети и прокси\n\n"
                f"Техническая информация:\n{result_error}"
            )
        elif "timeout" in error_lower:
            error_text = (
                "⚠️ Превышено время ожидания ответа от API.\n\n"
                "Сервер не ответил в течение установленного времени. "
                "Это может быть временная проблема с сетью или высокая загрузка сервера.\n\n"
                "Попробуйте:\n"
                "1. Подождать несколько минут и повторить попытку\n"
                "2. Проверить скорость интернет-соединения\n\n"
                f"Техническая информация:\n{result_error}"
            )
        else:
            # Generic error - provide helpful message
            error_text = (
                "⚠️ Ошибка запроса к LLM.\n\n"
                "Произошла ошибка при обращении к сервису анализа. "
                "Пожалуйста, повторите попытку через несколько минут.\n\n"
                f"Техническая информация:\n{result_error}"
            )
        
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