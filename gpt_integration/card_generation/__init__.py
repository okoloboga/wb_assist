"""
Card Generation module - генерация карточек товаров через GPT.
"""

from gpt_integration.card_generation.service import generate_card
from gpt_integration.card_generation.prompt_generator import (
    create_card_prompt,
    format_card_response,
)

__all__ = [
    "generate_card",
    "create_card_prompt",
    "format_card_response",
]

