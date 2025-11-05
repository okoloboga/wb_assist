from pathlib import Path
from typing import Optional
import re

_SYSTEM_PROMPT_CACHE: Optional[str] = None
_TASKS_CACHE: Optional[str] = None
_OUTPUT_JSON_SCHEMA_CACHE: Optional[str] = None
_OUTPUT_TG_GUIDE_CACHE: Optional[str] = None


def _load_markdown_section(text: str, section_name: str) -> str:
    pattern = rf"^##\s+{re.escape(section_name)}\s*$"
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    # Find next level-2 header (## but not ###, ####, etc)
    m2 = re.search(r"^##(?!#)\s+", text[start:], flags=re.MULTILINE)
    end = start + m2.start() if m2 else len(text)
    return text[start:end].strip()


def _read_template(template_path: Optional[str]) -> str:
    path = (
        Path(template_path)
        if template_path
        else Path(__file__).with_name("LLM_ANALYSIS_TEMPLATE.md")
    )
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_system_prompt(template_path: Optional[str] = None) -> str:
    """
    Read SYSTEM section from LLM_ANALYSIS_TEMPLATE.md and return its content.
    If the file is missing or the section is not found, return empty string.
    """
    content = _read_template(template_path)
    return _load_markdown_section(content, "SYSTEM")


def get_system_prompt(template_path: Optional[str] = None) -> str:
    """
    Cached accessor for the SYSTEM prompt to avoid repeated disk reads.
    """
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = load_system_prompt(template_path)
    return _SYSTEM_PROMPT_CACHE or ""


def load_tasks(template_path: Optional[str] = None) -> str:
    """Read TASKS section content."""
    content = _read_template(template_path)
    return _load_markdown_section(content, "TASKS")


def get_tasks(template_path: Optional[str] = None) -> str:
    """Cached accessor for TASKS section."""
    global _TASKS_CACHE
    if _TASKS_CACHE is None:
        _TASKS_CACHE = load_tasks(template_path)
    return _TASKS_CACHE or ""


def load_output_json_schema(template_path: Optional[str] = None) -> str:
    """Read OUTPUT_JSON_SCHEMA section content."""
    content = _read_template(template_path)
    return _load_markdown_section(content, "OUTPUT_JSON_SCHEMA")


def get_output_json_schema(template_path: Optional[str] = None) -> str:
    """Cached accessor for OUTPUT_JSON_SCHEMA section."""
    global _OUTPUT_JSON_SCHEMA_CACHE
    if _OUTPUT_JSON_SCHEMA_CACHE is None:
        _OUTPUT_JSON_SCHEMA_CACHE = load_output_json_schema(template_path)
    return _OUTPUT_JSON_SCHEMA_CACHE or ""


def load_output_tg_guide(template_path: Optional[str] = None) -> str:
    """Read OUTPUT_TG_GUIDE section content."""
    content = _read_template(template_path)
    return _load_markdown_section(content, "OUTPUT_TG_GUIDE")


def get_output_tg_guide(template_path: Optional[str] = None) -> str:
    """Cached accessor for OUTPUT_TG_GUIDE section."""
    global _OUTPUT_TG_GUIDE_CACHE
    if _OUTPUT_TG_GUIDE_CACHE is None:
        _OUTPUT_TG_GUIDE_CACHE = load_output_tg_guide(template_path)
    return _OUTPUT_TG_GUIDE_CACHE or ""