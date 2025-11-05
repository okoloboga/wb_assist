"""
Analysis module - анализ данных через GPT.
"""

from gpt_integration.analysis.pipeline import run_analysis, compose_messages
from gpt_integration.analysis.aggregator import aggregate, build_from_sources
from gpt_integration.analysis.template_loader import (
    get_system_prompt,
    get_tasks,
    get_output_json_schema,
    get_output_tg_guide,
)

__all__ = [
    "run_analysis",
    "compose_messages",
    "aggregate",
    "build_from_sources",
    "get_system_prompt",
    "get_tasks",
    "get_output_json_schema",
    "get_output_tg_guide",
]

