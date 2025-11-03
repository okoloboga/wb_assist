"""
GPT Integration Service

Модули:
- analysis: анализ данных через GPT
- ai_chat: простой чат через GPT  
- card_generation: генерация карточек товаров через GPT
"""

from .gpt_client import GPTClient

# Import main functions from modules
from .analysis import (
    run_analysis,
    aggregate,
    build_from_sources,
    get_system_prompt,
    get_tasks,
    get_output_json_schema,
    get_output_tg_guide,
)
from .ai_chat.service import chat as ai_chat
from .card_generation.service import generate_card

__all__ = [
    "GPTClient",
    "run_analysis",
    "aggregate",
    "build_from_sources",
    "get_system_prompt",
    "get_tasks",
    "get_output_json_schema",
    "get_output_tg_guide",
    "ai_chat",
    "generate_card",
]
