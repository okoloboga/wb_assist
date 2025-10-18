import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI


@dataclass
class LLMConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 800
    timeout: int = 30
    system_prompt: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "800")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            system_prompt=os.getenv("OPENAI_SYSTEM_PROMPT", None),
        )


class GPTClient:
    """Минимальный клиент для обращения к LLM через OpenAI SDK.

    Использование:
        from dotenv import load_dotenv
        load_dotenv(".env")
        client = GPTClient()  # конфиг берётся из переменных окружения
        answer = client.complete("Скажи 'pong'.")
        print(answer)
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        if not self.config.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
        # Настраиваем таймаут через with_options; будет применён ко всем вызовам
        self.client_timed = self.client.with_options(timeout=self.config.timeout)

    def _build_messages(self, user_text: str, history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        return messages

    def complete(
        self,
        user_text: str,
        history: Optional[List[Dict[str, str]]] = None,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Сгенерировать ответ на пользовательский текст.

        Возвращает чистый текст ответа модели.
        """
        messages = self._build_messages(user_text, history)
        try:
            completion = self.client_timed.chat.completions.create(
                model=model or self.config.model,
                messages=messages,
                temperature=self.config.temperature if temperature is None else temperature,
                max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
            )
            text = completion.choices[0].message.content
            return (text or "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM request failed: {e.__class__.__name__}: {e}") from e

    def complete_messages(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Сгенерировать ответ по готовому списку messages.
        Полезно, если вы сами собираете историю диалога.
        """
        msgs = list(messages)
        if self.config.system_prompt and (not msgs or msgs[0].get("role") != "system"):
            msgs = [{"role": "system", "content": self.config.system_prompt}] + msgs
        try:
            completion = self.client_timed.chat.completions.create(
                model=model or self.config.model,
                messages=msgs,
                temperature=self.config.temperature if temperature is None else temperature,
                max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
            )
            text = completion.choices[0].message.content
            return (text or "").strip()
        except Exception as e:
            raise RuntimeError(f"LLM request failed: {e.__class__.__name__}: {e}") from e

    def health_check(self) -> bool:
        """Проверка доступности LLM."""
        try:
            out = self.complete("ping")
            return bool(out)
        except Exception:
            return False


__all__ = ["LLMConfig", "GPTClient"]