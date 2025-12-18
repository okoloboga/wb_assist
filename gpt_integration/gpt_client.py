from typing import List, Dict, Optional
import os
import logging

from gpt_integration.comet_client import comet_client

logger = logging.getLogger(__name__)


class GPTClient:
    """
    A wrapper that provides a consistent interface for chat completions,
    now using CometClient as the backend.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initializes the client. Configuration is now primarily handled by the comet_client singleton.
        """
        self.model = model or os.getenv("COMET_TEXT_MODEL")
        self.temperature = float(os.getenv("COMET_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("COMET_MAX_TOKENS", str(max_tokens)))
        self.system_prompt = system_prompt or os.getenv("OPENAI_SYSTEM_PROMPT") or "You are a helpful assistant."

    @classmethod
    def from_env(cls) -> "GPTClient":
        """Creates an instance of the client from environment variables."""
        return cls()

    async def complete_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Execute chat completion using CometClient and return the text content.
        A system prompt is automatically prepended if not present.
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        logger.info(
            f"🚀 Starting LLM request via CometClient: "
            f"model={self.model}"
        )

        try:
            resp = await comet_client.create_completion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            usage = resp.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                logger.info(
                    f"🧮 Chat tokens: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}"
                )

            choice = resp.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")

            if not content.strip():
                logger.warning("LLM returned an empty response.")
                return "ERROR: LLM returned empty response."

            logger.info(f"✅ LLM request succeeded.")
            return content

        except Exception as e:
            logger.error(f"❌ LLM request failed: {e}", exc_info=True)
            return (
                f"ERROR: LLM request failed.\n"
                f"Error type: {type(e).__name__}\n"
                f"Error: {e}"
            )


