"""
AI Chat service endpoints.
"""

import logging
from typing import Dict, List, Optional

from gpt_integration.gpt_client import GPTClient

logger = logging.getLogger(__name__)


def chat(messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
    """
    Обработка запроса чата.
    
    Args:
        messages: Список сообщений в формате OpenAI
        system_prompt: Опциональный системный промпт
        
    Returns:
        str: Ответ от GPT
    """
    # Instantiate client on each request to pick up latest envs
    client = GPTClient.from_env()
    if system_prompt:
        client.system_prompt = system_prompt
    text = client.complete_messages(messages)
    return text

