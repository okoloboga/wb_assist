import os
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    system_prompt: Optional[str]

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "800")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            system_prompt=os.getenv("OPENAI_SYSTEM_PROMPT"),
        )


class GPTClient:
    """
    Минимальный клиент для вызова GPT.
    Использует chat.completions API и возвращает текст ответа ассистента.
    """
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY отсутствует. Укажите ключ в окружении.")

        client_kwargs = {"api_key": self.config.api_key}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        # Настройка таймаута на уровне клиента
        client_kwargs["timeout"] = self.config.timeout

        self.client = OpenAI(**client_kwargs)

    def complete_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Выполнить завершение диалога.
        messages: список словарей [{'role': 'user' | 'assistant', 'content': '...'}]
        Возвращает контент первого варианта ответа.
        """
        if not isinstance(messages, list):
            raise ValueError("messages должен быть списком сообщений.")

        chat_messages: List[Dict[str, str]] = []
        if self.config.system_prompt:
            chat_messages.append({"role": "system", "content": self.config.system_prompt})
        chat_messages.extend(messages)

        try:
            resp = self.client.chat.completions.create(
                model=self.config.model,
                messages=chat_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            content = resp.choices[0].message.content or ""
            return content.strip()
        except Exception as e:
            logger.error("Ошибка запроса к LLM: %r", e)
            raise
