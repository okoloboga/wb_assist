from typing import List, Dict, Optional
import os
import time


class GPTClient:
    """Thin wrapper around OpenAI Chat Completions for synchronous text responses.
    Provides a stable interface used by the LLM pipeline and GPT chat handlers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        timeout: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        # Resolve from environment if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "").strip() or None
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(max_tokens)))
        # Timeout is optional; library may not accept it directly
        env_timeout = os.getenv("OPENAI_TIMEOUT")
        self.timeout = int(env_timeout) if env_timeout else (timeout or None)
        self.system_prompt = system_prompt or os.getenv("OPENAI_SYSTEM_PROMPT") or "You are a helpful assistant."

        # Retry config (Stage 5)
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
        self.retry_delay_ms = int(os.getenv("OPENAI_RETRY_DELAY_MS", "500"))
        self.retry_backoff = float(os.getenv("OPENAI_RETRY_BACKOFF", "2"))

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        # Lazily initialize the underlying client to avoid import overhead if unused
        self._client = None

    @classmethod
    def from_env(cls) -> "GPTClient":
        return cls()

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            # Preferred client (OpenAI SDK v2)
            from openai import OpenAI  # type: ignore
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            # Fallback to legacy global client
            import openai  # type: ignore
            openai.api_key = self.api_key
            if self.base_url:
                try:
                    # Some forks use api_base instead of base_url
                    openai.base_url = self.base_url  # type: ignore
                except Exception:
                    openai.api_base = self.base_url  # type: ignore
            self._client = openai
        return self._client

    def _do_completion(self, client, messages: List[Dict[str, str]]) -> str:
        # Try modern client interface
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            choice = getattr(resp, "choices", [None])[0]
            if choice is None:
                return ""
            message = getattr(choice, "message", None)
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
            # Some clients return dict-like structures
            if isinstance(message, dict):
                return message.get("content", "")
            return ""

        # Fallback to legacy global API
        import openai  # type: ignore
        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        choices = resp.get("choices") if isinstance(resp, dict) else getattr(resp, "choices", [])
        if not choices:
            return ""
        first = choices[0]
        msg = first.get("message") if isinstance(first, dict) else getattr(first, "message", {})
        return (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""

    def complete_messages(self, messages: List[Dict[str, str]]) -> str:
        """Execute chat completion and return plain text content.
        If messages do not include a system prompt, prepend one from config/env.
        Implements simple retries with exponential backoff for robustness.
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        client = self._get_client()
        attempt = 0
        delay_ms = self.retry_delay_ms
        last_error: Optional[Exception] = None

        while attempt <= self.max_retries:
            try:
                content = self._do_completion(client, messages)
                # Treat empty content as a transient failure eligible for retry
                if isinstance(content, str) and content.strip():
                    return content
                # If empty and retries remain, wait and retry
                if attempt < self.max_retries:
                    time.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_backoff)
                    attempt += 1
                    continue
                # No content and no retries left
                break
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_backoff)
                    attempt += 1
                    continue
                break

        if last_error is not None:
            return f"ERROR: LLM request failed after {self.max_retries + 1} attempts: {last_error}"
        return "ERROR: LLM returned empty response after retries"