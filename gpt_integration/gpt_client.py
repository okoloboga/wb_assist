from typing import List, Dict, Optional
import os
import time
import logging

logger = logging.getLogger(__name__)


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
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1"
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(max_tokens)))
        # Timeout is optional; library may not accept it directly
        env_timeout = os.getenv("OPENAI_TIMEOUT")
        self.timeout = int(env_timeout) if env_timeout else (timeout or None)
        self.system_prompt = system_prompt or os.getenv("OPENAI_SYSTEM_PROMPT") or "You are a helpful assistant."

        # Retry config (Stage 5)
        # Increase default retries for connection errors
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        # Connection errors may need more retries - start with higher default
        self.max_retries_connection = int(os.getenv("OPENAI_MAX_RETRIES_CONNECTION", "8"))
        self.retry_delay_ms = int(os.getenv("OPENAI_RETRY_DELAY_MS", "500"))
        self.retry_backoff = float(os.getenv("OPENAI_RETRY_BACKOFF", "2"))
        # Longer initial delay for connection errors
        self.retry_delay_connection_ms = int(os.getenv("OPENAI_RETRY_DELAY_CONNECTION_MS", "2000"))

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
            # Disable OpenAI SDK's built-in retries - we handle retries ourselves
            # This gives us better control over retry logic and error detection
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                max_retries=0,  # Disable SDK retries, we handle them ourselves
                timeout=self.timeout if self.timeout else 60.0,  # Default 60s timeout
            )
            logger.debug(f"Initialized OpenAI client: base_url={self.base_url}, timeout={self.timeout}")
        except Exception as e:
            logger.warning(f"Failed to initialize modern OpenAI client: {e}, falling back to legacy client")
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
            # Disable OpenAI SDK's built-in retries to have full control
            # We'll handle retries ourselves with better error detection
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,  # Pass timeout if available
                )
            except Exception as e:
                # Re-raise with more context for better error detection
                logger.debug(f"OpenAI API call failed: {type(e).__name__}: {str(e)}")
                raise
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

    def _is_connection_error(self, error: Exception) -> bool:
        """Check if error is a connection-related error that might be temporary."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        error_type_lower = error_type.lower()
        
        logger.debug(f"Checking if error is connection error: type={error_type}, str={error_str[:100]}")
        
        # First, check for OpenAI library specific connection errors (highest priority)
        try:
            from openai import APIConnectionError, APITimeoutError, APIError, InternalServerError
            if isinstance(error, (APIConnectionError, APITimeoutError)):
                logger.info(f"✅ Detected OpenAI connection error by type: {error_type}")
                return True
            # APIConnectionError might be wrapped in APIError
            if isinstance(error, APIError):
                # Check if it's a connection-related API error
                error_code = getattr(error, 'code', None)
                error_message = getattr(error, 'message', '')
                if error_code in ('connection_error', 'timeout', 'rate_limit_error'):
                    logger.info(f"✅ Detected OpenAI API connection error by code: {error_type}, code={error_code}")
                    return True
                # Also check error message for connection-related keywords
                if any(keyword in error_message.lower() for keyword in ['connection', 'timeout', 'network', 'dns', 'socket']):
                    logger.info(f"✅ Detected OpenAI API connection error by message: {error_type}, message={error_message[:100]}")
                    return True
        except ImportError:
            logger.debug("OpenAI library not available for error type checking")
            pass
        
        # Check for requests library connection errors
        try:
            import requests
            if isinstance(error, (requests.exceptions.ConnectionError, 
                                  requests.exceptions.Timeout,
                                  requests.exceptions.ConnectTimeout,
                                  requests.exceptions.ReadTimeout,
                                  requests.exceptions.SSLError)):
                logger.debug(f"Detected requests connection error: {error_type}")
                return True
        except ImportError:
            pass
        
        # Check error type name for connection-related keywords
        connection_error_types = [
            'connectionerror', 'connection', 'connect', 'timeouterror', 'timeout',
            'network', 'dns', 'resolverror', 'gaierror', 'socket', 'ssl', 
            'certificate', 'errno'
        ]
        
        for err_type in connection_error_types:
            if err_type in error_type_lower:
                logger.debug(f"Detected connection error by type name: {error_type}")
                return True
        
        # Check error message for connection-related keywords (most reliable method)
        connection_keywords = [
            'connection error', 'connection', 'connect', 'timeout', 'network', 'dns', 'socket',
            'refused', 'reset', 'unreachable', 'unavailable', 'failed to establish',
            'name resolution', 'ssl', 'certificate', 'handshake', 'tls',
            'connection refused', 'connection reset',
            'connection timed out', 'network is unreachable', 'no route to host',
            'cannot connect', 'unable to connect', 'connection closed', 'connection lost',
            'connection aborted', 'broken pipe', 'connection pool', 'proxy error'
        ]
        
        for keyword in connection_keywords:
            if keyword in error_str:
                logger.info(f"✅ Detected connection error by message keyword '{keyword}': {error_str[:150]}")
                return True
        
        # If error has a response with HTTP status, it's likely not a connection error
        # (connection errors typically don't get HTTP responses)
        if hasattr(error, 'response') and error.response is not None:
            try:
                # If we can access status code, it's likely an HTTP error, not connection
                if hasattr(error.response, 'status_code'):
                    logger.debug(f"Error has HTTP response with status_code, not a connection error: {error_type}")
                    return False
            except Exception:
                pass
        
        # Check for common Python connection errors
        try:
            import socket
            if isinstance(error, (socket.error, socket.gaierror, socket.timeout, OSError)):
                # OSError can be many things, check error code
                if hasattr(error, 'errno'):
                    errno = error.errno
                    # Common connection-related errnos
                    connection_errnos = [
                        111,  # Connection refused
                        110,  # Connection timed out
                        113,  # No route to host
                        101,  # Network is unreachable
                        104,  # Connection reset by peer
                    ]
                    if errno in connection_errnos:
                        logger.debug(f"Detected connection error by errno: {error_type}, errno={errno}")
                        return True
        except ImportError:
            pass
        
        return False

    def complete_messages(self, messages: List[Dict[str, str]]) -> str:
        """Execute chat completion and return plain text content.
        If messages do not include a system prompt, prepend one from config/env.
        Implements retries with exponential backoff for robustness.
        Connection errors get more retries and longer delays.
        """
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": self.system_prompt}] + messages

        client = self._get_client()
        attempt = 0
        delay_ms = self.retry_delay_ms
        last_error: Optional[Exception] = None
        is_connection_error = False
        max_attempts = self.max_retries
        connection_error_started_at = None
        
        logger.info(
            f"🚀 Starting LLM request: max_retries={self.max_retries}, "
            f"max_retries_connection={self.max_retries_connection}, "
            f"model={self.model}, base_url={self.base_url}"
        )

        # Track total attempts for logging
        total_attempts_made = 0
        
        while attempt <= max_attempts:
            total_attempts_made = attempt + 1
            try:
                content = self._do_completion(client, messages)
                # Treat empty content as a transient failure eligible for retry
                if isinstance(content, str) and content.strip():
                    logger.info(f"✅ LLM request succeeded on attempt {total_attempts_made}")
                    return content
                # If empty and retries remain, wait and retry
                if attempt < max_attempts:
                    logger.warning(f"⚠️ Empty response on attempt {total_attempts_made}, retrying...")
                    time.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_backoff)
                    attempt += 1
                    continue
                # No content and no retries left
                logger.error(f"❌ Empty response after {total_attempts_made} attempts")
                break
            except Exception as e:
                last_error = e
                error_str = str(e)
                error_type = type(e).__name__
                error_code = None
                error_message = None
                
                # Log detailed error information for debugging (use info level for visibility)
                logger.info(
                    f"⚠️ Exception caught on attempt {attempt + 1}/{max_attempts + 1}: "
                    f"type={error_type}, str={error_str[:300]}, "
                    f"has_response={hasattr(e, 'response')}, "
                    f"has_status_code={hasattr(e, 'status_code')}"
                )
                
                # Check if this is a connection error
                is_conn_err = self._is_connection_error(e)
                logger.info(
                    f"🔍 Connection error check: {is_conn_err} "
                    f"(current mode: connection_error={is_connection_error}, "
                    f"attempt={attempt}, max_attempts={max_attempts})"
                )
                
                # Also check error string directly for "connection" keyword as a fallback
                if not is_conn_err and "connection" in error_str.lower():
                    logger.warning(
                        f"⚠️ Error string contains 'connection' but _is_connection_error returned False. "
                        f"Treating as connection error anyway. Error: {error_str[:200]}"
                    )
                    is_conn_err = True
                
                if is_conn_err and not is_connection_error:
                    # First connection error - switch to connection error retry mode immediately
                    is_connection_error = True
                    connection_error_started_at = attempt
                    # Calculate how many attempts we've made so far
                    attempts_already_made = attempt + 1
                    # Add connection retries to the remaining attempts
                    # We want to continue from current attempt, so we add connection retries
                    # max_attempts is the maximum index (0-based), so if we want N more attempts:
                    # new_max = current_attempt + N
                    max_attempts = attempt + self.max_retries_connection
                    delay_ms = self.retry_delay_connection_ms
                    # Reset client to try new connection
                    self._client = None
                    client = self._get_client()
                    total_expected_attempts = attempts_already_made + self.max_retries_connection
                    logger.warning(
                        f"🔌 Connection error detected on attempt {attempts_already_made}, "
                        f"switching to connection retry mode: up to {total_expected_attempts} total attempts "
                        f"(already done: {attempts_already_made}, will try {self.max_retries_connection} more), "
                        f"{delay_ms}ms initial delay. Error type: {error_type}, Error: {error_str[:200]}"
                    )
                elif is_conn_err and is_connection_error:
                    # Subsequent connection error - reset client to try new connection
                    self._client = None
                    client = self._get_client()
                    logger.debug(f"Connection error on attempt {attempt + 1}, resetting client")
                elif not is_conn_err:
                    # Not a connection error - log for debugging
                    logger.debug(f"Non-connection error: {error_type}: {error_str[:200]}")
                
                # Try to extract error details from OpenAI exception
                if hasattr(e, 'response') and hasattr(e.response, 'json'):
                    try:
                        error_data = e.response.json()
                        if isinstance(error_data, dict) and 'error' in error_data:
                            error_info = error_data['error']
                            error_code = error_info.get('code')
                            error_message = error_info.get('message', '')
                    except Exception:
                        pass
                
                # Also check status code
                status_code = None
                if hasattr(e, 'status_code'):
                    status_code = e.status_code
                elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                
                # If it's a regional restriction, don't retry - it won't help
                is_regional_error = (
                    status_code == 403 and 
                    (error_code == 'unsupported_country_region_territory' or 
                     'unsupported_country' in error_str.lower() or
                     'region' in error_str.lower() and 'not supported' in error_str.lower())
                )
                
                if is_regional_error:
                    # Return immediately with helpful message
                    return (
                        f"ERROR: LLM request failed: OpenAI API is not available in your region.\n"
                        f"Error code: 403 - {error_code or 'unsupported_country_region_territory'}\n"
                        f"Message: {error_message or 'Country, region, or territory not supported'}\n\n"
                        f"Решение: Настройте OPENAI_BASE_URL для использования альтернативного API endpoint "
                        f"(например, прокси-сервер или OpenAI-совместимый провайдер)."
                    )
                
                # Log retry attempt
                if attempt < max_attempts:
                    total_attempt = (connection_error_started_at + 1 + attempt) if connection_error_started_at is not None else (attempt + 1)
                    logger.warning(
                        f"Attempt {total_attempt} failed ({'connection error' if is_conn_err else 'general error'}): "
                        f"{error_str[:200]}. Retrying in {delay_ms}ms... "
                        f"(retry {attempt + 1}/{max_attempts + 1})"
                    )
                    time.sleep(delay_ms / 1000.0)
                    delay_ms = int(delay_ms * self.retry_backoff)
                    attempt += 1
                    continue
                break

        if last_error is not None:
            # Format error message with more context
            error_str = str(last_error)
            error_type = type(last_error).__name__
            
            # Calculate total attempts - use the tracked total
            if connection_error_started_at is not None:
                # Connection error mode: attempts made before switch + attempts made after switch
                attempts_before_switch = connection_error_started_at + 1
                attempts_after_switch = attempt - connection_error_started_at
                total_attempts = attempts_before_switch + attempts_after_switch
                logger.info(
                    f"📊 Total attempts calculation: before_switch={attempts_before_switch}, "
                    f"after_switch={attempts_after_switch}, total={total_attempts}, "
                    f"current_attempt_index={attempt}"
                )
            else:
                # Regular mode: just current attempt + 1
                total_attempts = attempt + 1
                logger.info(f"📊 Total attempts (regular mode): {total_attempts}, current_attempt_index={attempt}")
            
            # Determine error category for better user message
            if is_connection_error:
                error_category = "Connection error"
                error_description = (
                    "Не удалось установить соединение с API. "
                    "Возможные причины: проблемы с сетью, временная недоступность сервера, "
                    "или неправильная настройка прокси/DNS."
                )
            else:
                error_category = "API error"
                error_description = "Ошибка при обращении к API."
            
            # Try to extract error details from OpenAI exception
            if hasattr(last_error, 'response') and hasattr(last_error.response, 'json'):
                try:
                    error_data = last_error.response.json()
                    if isinstance(error_data, dict) and 'error' in error_data:
                        error_info = error_data['error']
                        error_code = error_info.get('code', '')
                        error_message = error_info.get('message', '')
                        if error_code or error_message:
                            return (
                                f"ERROR: LLM request failed after {total_attempts} attempts: {error_category}\n"
                                f"Error type: {error_type}\n"
                                f"Error code: {error_code}\n"
                                f"Error message: {error_message}\n\n"
                                f"{error_description}"
                            )
                except Exception:
                    pass
            
            # Check if error message contains "connection" - if so, it's likely a connection error
            # This is a fallback for cases where error detection didn't work
            if "connection" in error_str.lower() and not is_connection_error:
                logger.warning(
                    f"⚠️ Error message contains 'connection' but wasn't detected as connection error. "
                    f"Treating as connection error for user message."
                )
                error_category = "Connection error"
                error_description = (
                    "Не удалось установить соединение с API. "
                    "Возможные причины: проблемы с сетью, временная недоступность сервера, "
                    "или неправильная настройка прокси/DNS."
                )
            
            return (
                f"ERROR: LLM request failed after {total_attempts} attempts: {error_category}\n"
                f"Error type: {error_type}\n"
                f"Error: {error_str}\n\n"
                f"{error_description}"
            )
        return "ERROR: LLM returned empty response after retries"