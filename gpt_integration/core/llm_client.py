"""
Universal LLM Client для работы с разными AI моделями
Поддерживает GPT-5.1 (OpenAI) и Claude Sonnet 4.5 (Google Vertex AI)
"""
import os
import logging
from typing import List, Dict, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class UniversalLLMClient:
    """Универсальный клиент для работы с разными LLM"""
    
    def __init__(self):
        # OpenAI клиент
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if self.openai_api_key:
            self.openai_client = AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url if self.openai_base_url.strip() else None
            )
            logger.info("✅ OpenAI client initialized")
        else:
            self.openai_client = None
            logger.warning("⚠️ OpenAI API key not configured")
        
        # Google Vertex AI для Claude (будет реализовано позже)
        self.vertex_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.vertex_location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.vertex_client = None
        
        if self.vertex_project:
            try:
                from google.cloud import aiplatform
                aiplatform.init(project=self.vertex_project, location=self.vertex_location)
                logger.info(f"✅ Vertex AI initialized: {self.vertex_project}/{self.vertex_location}")
                self.vertex_client = aiplatform
            except Exception as e:
                logger.warning(f"⚠️ Vertex AI not available: {e}")
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> tuple[str, int]:
        """
        Универсальный метод для chat completion
        
        Args:
            model: ID модели (gpt-5.1, claude-sonnet-4.5)
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимум токенов в ответе
        
        Returns:
            tuple[str, int]: (response_text, tokens_used)
        
        Raises:
            ValueError: Если модель не поддерживается
            RuntimeError: Если произошла ошибка при запросе
        """
        if model.startswith("gpt"):
            return await self._openai_completion(model, messages, temperature, max_tokens)
        elif model.startswith("claude"):
            return await self._claude_completion(model, messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    async def _openai_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> tuple[str, int]:
        """OpenAI completion (GPT-5.1)"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized. Check OPENAI_API_KEY")
        
        try:
            logger.info(f"🤖 Calling OpenAI: model={model}, messages={len(messages)}")
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ OpenAI response: {len(response_text)} chars, {tokens_used} tokens")
            
            return (response_text, tokens_used)
            
        except Exception as e:
            logger.error(f"❌ OpenAI API error: {str(e)}")
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def _claude_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> tuple[str, int]:
        """Claude completion через Google Vertex AI"""
        if not self.vertex_client:
            # Fallback на OpenAI если Vertex AI недоступен
            logger.warning(f"⚠️ Vertex AI not available, falling back to GPT-5.1")
            return await self._openai_completion("gpt-5.1", messages, temperature, max_tokens)
        
        try:
            logger.info(f"🤖 Calling Claude via Vertex AI: model={model}, messages={len(messages)}")
            
            # Конвертируем формат сообщений для Claude
            system_message = None
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Используем Vertex AI Anthropic API
            from anthropic import AnthropicVertex
            
            client = AnthropicVertex(
                project_id=self.vertex_project,
                region=self.vertex_location
            )
            
            # Маппинг моделей
            vertex_model = "claude-sonnet-4-5@20250514" if model == "claude-sonnet-4.5" else model
            
            response = await client.messages.create(
                model=vertex_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message,
                messages=claude_messages
            )
            
            response_text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            logger.info(f"✅ Claude response: {len(response_text)} chars, {tokens_used} tokens")
            
            return (response_text, tokens_used)
            
        except Exception as e:
            logger.error(f"❌ Claude/Vertex AI error: {str(e)}")
            # Fallback на OpenAI
            logger.warning(f"⚠️ Falling back to GPT-5.1 due to error")
            return await self._openai_completion("gpt-5.1", messages, temperature, max_tokens)


# Singleton instance
llm_client = UniversalLLMClient()
