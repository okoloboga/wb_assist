"""
Centralized client for interacting with the CometAPI for various AI tasks.
"""
import os
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CometClient:
    """
    An asynchronous client for interacting with CometAPI for text generation and embeddings.
    """

    def __init__(self):
        self.api_key = os.getenv("COMET_API_KEY")
        self.text_base_url = os.getenv("COMET_TEXT_BASE_URL")
        self.embeddings_base_url = os.getenv("COMET_EMBEDDINGS_BASE_URL")
        self.text_model = os.getenv("COMET_TEXT_MODEL")
        self.embeddings_model = os.getenv("COMET_EMBEDDINGS_MODEL")
        
        timeout = int(os.getenv("COMET_API_TIMEOUT", "60"))
        
        if not self.api_key:
            raise ValueError("COMET_API_KEY environment variable is not set.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        self._client = httpx.AsyncClient(headers=self.headers, timeout=timeout, follow_redirects=True)

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the CometAPI text generation endpoint.
        Assumes an OpenAI-compatible API structure.
        """
        if not self.text_base_url:
            raise ValueError("COMET_TEXT_BASE_URL environment variable is not set.")
            
        request_payload = {
            "model": model or self.text_model,
            "messages": messages,
            **kwargs,
        }
        
        try:
            response = await self._client.post(
                url=self.text_base_url, 
                json=request_payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # Re-raise with more context if needed, or handle specific errors
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during completion: {e}")
            raise

    async def create_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create embeddings for a list of texts using the CometAPI embeddings endpoint.
        Assumes an OpenAI-compatible API structure.
        """
        if not self.embeddings_base_url:
            raise ValueError("COMET_EMBEDDINGS_BASE_URL environment variable is not set.")

        request_payload = {
            "model": model or self.embeddings_model,
            "input": texts,
        }

        try:
            response = await self._client.post(
                url=self.embeddings_base_url, 
                json=request_payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while creating embeddings: {e.response.status_code} - {e.response.text}")
            # Re-raise with more context
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during embedding creation: {e}")
            raise

    async def close(self):
        """
        Close the underlying HTTP client.
        """
        await self._client.aclose()

# Singleton instance of the client
comet_client = CometClient()
