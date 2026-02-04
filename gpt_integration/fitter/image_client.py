import base64
import io
import logging
import time
import asyncio
from typing import Optional, List

import httpx
from PIL import Image
from tenacity import retry, wait_random_exponential, stop_after_attempt

logger = logging.getLogger(__name__)

class ImageGenerationError(Exception):
    """Custom exception for image generation errors."""
    pass

async def download_telegram_photo(file_url: str) -> bytes:
    """
    Download file from Telegram's public file URL.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()
        return resp.content

class ImageGenerationClient:
    """
    Клиент для генерации изображений через CometAPI.
    
    Поддерживает модели:
    - Gemini 2.5 Flash Image / Gemini 3 Pro Image
    - GPT Image -1 / GPT Image 1.5 (и другие модели через CometAPI)

    Поддерживает:
    - image→image
    - prompt + одно или несколько изображений
    - возвращает Telegram-ready data:image/png;base64,...
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-pro-image",
        base_url: str = "https://api.cometapi.com",
        timeout: float = 600.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        # Для Gemini моделей используется формат без Bearer
        # Для GPT Image моделей используется Bearer (устанавливается в методе запроса)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"{self.api_key}",  # Для Gemini моделей
                "Content-Type": "application/json",
                "Accept": "*/*",
            },
            follow_redirects=True,
        )

    async def close(self):
        """Explicit client shutdown."""
        await self.client.aclose()

    @staticmethod
    def _encode_image_to_base64(image_bytes: bytes) -> str:
        """Return raw base64 string (no prefix)."""
        return base64.b64encode(image_bytes).decode("utf-8")

    @staticmethod
    def _decode_base64_image(b64: str) -> bytes:
        """Decode raw base64 → bytes."""
        return base64.b64decode(b64)

    @staticmethod
    def _to_telegram_data_uri(mime: str, b64: str) -> str:
        """Convert raw base64 to Telegram-ready URI."""
        return f"data:{mime};base64,{b64}"

    async def _load_image_bytes(self, image_source: str) -> tuple[bytes, str]:
        """Load image bytes and determine mime type from URL or local path.
        
        Args:
            image_source: URL or local path to image
            
        Returns:
            Tuple of (image_bytes, mime_type)
        """
        image_bytes = None
        mime_type = "image/png"  # Default mime type

        if image_source.startswith(("http://", "https://")):
            logger.debug("Downloading source image from URL: %s", image_source)
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(image_source)
                    response.raise_for_status()
                    image_bytes = response.content
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error downloading image {image_source}: {e}")
                raise ImageGenerationError(f"Failed to download image from URL: {image_source}") from e
            except httpx.RequestError as e:
                logger.error(f"Network error downloading image {image_source}: {e}")
                raise ImageGenerationError(f"Network error downloading image from URL: {image_source}") from e
        else:
            logger.debug("Reading source image from local path: %s", image_source)
            try:
                with open(image_source, "rb") as f:
                    image_bytes = f.read()
            except FileNotFoundError as e:
                logger.error(f"Local image file not found: {image_source}")
                raise ImageGenerationError(f"Local image file not found: {image_source}") from e
            except Exception as e:
                logger.error(f"Error reading local image file {image_source}: {e}")
                raise ImageGenerationError(f"Error reading local image file: {image_source}") from e
        
        if not image_bytes:
            raise ImageGenerationError(f"No image data obtained for source: {image_source}")

        try:
            # Try to determine mime type from image content
            img = Image.open(io.BytesIO(image_bytes))
            mime_type = Image.MIME.get(img.format, mime_type)
        except Exception as e:
            logger.warning(f"Could not determine mime type from image content, using default. Error: {e}")

        logger.debug("Input mime: %s, size: %d bytes", mime_type, len(image_bytes))
        return image_bytes, mime_type

    async def _prepare_image_part(self, image_source: str, for_openai: bool = False):
        """Prepares an image (from URL or local path) for the API.
        
        Args:
            image_source: URL or local path to image
            for_openai: If True, returns OpenAI format (image_url), else Gemini format (inline_data)
        """
        image_bytes, mime_type = await self._load_image_bytes(image_source)
        image_b64 = self._encode_image_to_base64(image_bytes)
        
        if for_openai:
            # OpenAI format: data URI with mime type
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}"
                }
            }
        else:
            # Gemini format
            return {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_b64
                }
            }

    @retry(
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(5),
    )
    async def process_images(
        self,
        image_sources: List[str],
        prompt: str,
    ) -> str:
        """
        image-to-image with multiple inputs:
        - скачивает картинки
        - отправляет запрос в CometAPI
        - Для Gemini моделей: использует формат Gemini API (generateContent)
        - Для GPT Image моделей: использует формат OpenAI API (multipart/form-data) согласно документации CometAPI
        - парсит ответ в зависимости от формата API
        - возвращает data:image/png;base64,...
        """
        start = time.monotonic()

        # Определяем, используем ли мы GPT Image модели
        # Согласно документации CometAPI (https://apidoc.cometapi.com/image-edits),
        # GPT Image модели используют endpoint /v1/images/edits с multipart/form-data
        model_lower = self.model.lower()
        is_gpt_image = (
            "gpt-image" in model_lower or 
            "gpt" in model_lower or 
            "openai" in model_lower
        ) and "gemini" not in model_lower  # Исключаем Gemini модели
        
        logger.info("Model: %s, is_gpt_image: %s (model_lower: %s)", self.model, is_gpt_image, model_lower)
        
        if is_gpt_image:
            # GPT Image модели через CometAPI:
            # - text→image: /v1/images/generations (application/json)
            # - image→image: /v1/images/edits (multipart/form-data)
            if not image_sources:
                return await self._generate_images_gpt_image(prompt, start)
            return await self._process_images_gpt_image(image_sources, prompt, start)
        else:
            # Gemini модели используют Gemini API формат
            return await self._process_images_gemini(image_sources, prompt, start)

    async def _generate_images_gpt_image(
        self,
        prompt: str,
        start_time: float,
        *,
        n: int = 1,
        size: str = "1024x1024",
    ) -> str:
        """
        Text-to-image для GPT Image моделей через CometAPI.
        Согласно документации пользователя: POST /v1/images/generations (JSON)
        """
        endpoint = f"{self.base_url}/v1/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        body = {
            "model": self.model,
            "prompt": prompt,
            "n": n,
            "size": size,
        }

        logger.info("Using /v1/images/generations for GPT Image model: %s, endpoint: %s", self.model, endpoint)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout), follow_redirects=True) as client:
                resp = await client.post(endpoint, json=body, headers=headers)
                resp.raise_for_status()
                response_data = resp.json()

            if "data" not in response_data or not response_data["data"]:
                raise ImageGenerationError(f"API returned no data for model {self.model}. Response: {response_data}")

            first_data = response_data["data"][0]
            output_b64 = None
            output_mime = "image/png"

            if "b64_json" in first_data:
                output_b64 = first_data["b64_json"]
            elif "url" in first_data:
                image_url = first_data["url"]
                logger.info("Got URL from API response, downloading image: %s", image_url)
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as download_client:
                    img_resp = await download_client.get(image_url)
                    img_resp.raise_for_status()
                    image_bytes = img_resp.content
                try:
                    img = Image.open(io.BytesIO(image_bytes))
                    output_mime = Image.MIME.get(img.format, "image/png")
                except Exception:
                    pass
                output_b64 = self._encode_image_to_base64(image_bytes)

            if not output_b64:
                raise ImageGenerationError(
                    f"No b64_json or url in API response for model {self.model}. Response: {response_data}"
                )

            elapsed = time.monotonic() - start_time
            logger.info("Image generation execution time for model %s: %.2fs", self.model, elapsed)
            return self._to_telegram_data_uri(output_mime, output_b64)

        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:1000] if e.response.text else "No error message"
            logger.error("API error %s for model %s at endpoint %s: %s", e.response.status_code, self.model, endpoint, error_text)
            raise ImageGenerationError(f"API error {e.response.status_code}: {error_text}") from e
        except Exception as e:
            logger.exception("Failed to generate image with GPT Image model")
            raise ImageGenerationError(f"Failed to generate image: {e}") from e

    async def _process_images_gpt_image(
        self,
        image_sources: List[str],
        prompt: str,
        start_time: float,
    ) -> str:
        """
        Обработка изображений для GPT Image моделей через CometAPI.
        Использует формат OpenAI API: multipart/form-data, endpoint /v1/images/edits
        """
        # GPT Image edits: отправляем все изображения как multipart parts с одинаковым ключом.
        # Это позволяет моделям (включая gpt-image-1.5) учитывать референсные изображения, а не только промпт.
        if not image_sources:
            raise ImageGenerationError("No image sources provided for GPT Image model")

        # Подготавливаем multipart/form-data
        # Поля согласно документации: image (file, required; допускается несколько), prompt (required), model (optional)
        files = []
        for idx, src in enumerate(image_sources):
            image_bytes, mime_type = await self._load_image_bytes(src)
            ext = mime_type.split("/")[-1] if "/" in mime_type else "png"
            files.append(("image", (f"image_{idx}.{ext}", image_bytes, mime_type)))

        data = {
            "prompt": prompt,
            "model": self.model,
            "quality": "high",  # Для gpt-image-1: high, medium, low, auto
            "size": "auto",  # Для gpt-image-1: 1024x1024, 1536x1024, 1024x1536, auto
        }
        
        # response_format поддерживается только для dall-e-3, не для gpt-image-1
        # Для gpt-image-1 ответ всегда в формате b64_json по умолчанию
        if "dall-e-3" in self.model.lower():
            data["response_format"] = "b64_json"
        
        # Endpoint согласно документации CometAPI
        endpoint = f"{self.base_url}/v1/images/edits"
        
        # Для GPT Image моделей нужен Bearer токен
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        logger.info("Using OpenAI API format for GPT Image model: %s, endpoint: %s", self.model, endpoint)
        
        try:
            # Отправляем multipart/form-data запрос
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout), follow_redirects=True) as client:
                resp = await client.post(endpoint, files=files, data=data, headers=headers)
                resp.raise_for_status()
                
                response_data = resp.json()
                logger.debug("Raw API response received successfully for model %s", self.model)
                
                # Парсим ответ в формате OpenAI API
                # Согласно документации: data[0].b64_json или data[0].url
                if "data" not in response_data or not response_data["data"]:
                    raise ImageGenerationError(f"API returned no data for model {self.model}. Response: {response_data}")
                
                first_data = response_data["data"][0]
                output_b64 = None
                output_mime = "image/png"
                
                # Проверяем наличие b64_json (предпочтительный формат)
                if "b64_json" in first_data:
                    output_b64 = first_data["b64_json"]
                    logger.debug("Got b64_json from API response")
                # Если нет b64_json, проверяем url (для gpt-image-1 может возвращаться url)
                elif "url" in first_data:
                    image_url = first_data["url"]
                    logger.info("Got URL from API response, downloading image: %s", image_url)
                    try:
                        # Скачиваем изображение по URL
                        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as download_client:
                            img_resp = await download_client.get(image_url)
                            img_resp.raise_for_status()
                            image_bytes = img_resp.content
                            
                            # Определяем mime type
                            try:
                                img = Image.open(io.BytesIO(image_bytes))
                                output_mime = Image.MIME.get(img.format, "image/png")
                            except Exception:
                                pass
                            
                            # Конвертируем в base64
                            output_b64 = self._encode_image_to_base64(image_bytes)
                            logger.debug("Downloaded and converted image from URL to base64")
                    except Exception as e:
                        logger.error("Failed to download image from URL %s: %s", image_url, e)
                        raise ImageGenerationError(f"Failed to download image from URL: {e}") from e
                
                if not output_b64:
                    raise ImageGenerationError(
                        f"No b64_json or url in API response for model {self.model}. Response: {response_data}"
                    )
                
                elapsed = time.monotonic() - start_time
                logger.info("Image generation execution time for model %s: %.2fs", self.model, elapsed)
                
                # Возвращаем в формате data URI
                return self._to_telegram_data_uri(output_mime, output_b64)
                
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:1000] if e.response.text else "No error message"
            logger.error("API error %s for model %s at endpoint %s: %s", e.response.status_code, self.model, endpoint, error_text)
            raise ImageGenerationError(f"API error {e.response.status_code}: {error_text}") from e
        except Exception as e:
            logger.exception("Failed to process images with GPT Image model")
            raise ImageGenerationError(f"Failed to process images: {e}") from e

    async def _process_images_gemini(
        self,
        image_sources: List[str],
        prompt: str,
        start_time: float,
    ) -> str:
        """
        Обработка изображений для Gemini моделей через CometAPI.
        Использует формат Gemini API: JSON, endpoint /v1beta/models/{model}:generateContent
        """
        # 1. Download and prepare all images concurrently
        image_parts = await asyncio.gather(
            *[self._prepare_image_part(source, for_openai=False) for source in image_sources]
        )

        # 2. Build request JSON в формате Gemini API
        parts = [{"text": prompt}]
        parts.extend(image_parts)

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        endpoint = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        logger.info("Using Gemini API format for model: %s, endpoint: %s", self.model, endpoint)

        resp = None
        last_error = None
        
        try:
            logger.info("Trying endpoint: %s, model=%s with %d images", endpoint, self.model, len(image_sources))
            resp = await self.client.post(endpoint, json=body)
            resp.raise_for_status()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Connection error with endpoint %s: %s", endpoint, type(e).__name__)
            raise ImageGenerationError(f"Connection error: {e}") from e
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:1000] if e.response.text else "No error message"
            logger.error("API error %s for model %s at endpoint %s: %s", e.response.status_code, self.model, endpoint, error_text)
            raise ImageGenerationError(f"API error {e.response.status_code}: {error_text}") from e
        except Exception as e:
            logger.exception("Unexpected error with endpoint %s", endpoint)
            raise ImageGenerationError(f"Unexpected error: {e}") from e

        data = resp.json()
        logger.debug("Raw API response received successfully for model %s", self.model)

        # 3. Parse API response в формате Gemini API
        try:
            candidates = data.get("candidates") or []
            if not candidates:
                raise ImageGenerationError(f"API returned no candidates for model {self.model}")

            candidate = candidates[0]
            content = candidate.get("content") or {}
            parts = content.get("parts") or []

            output_b64 = None
            output_mime = None

            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")

                if inline:
                    output_mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    output_b64 = inline.get("data")
                    break

            if not output_b64:
                raise ImageGenerationError(
                    f"No image returned by API for model {self.model}. Response: {data}"
                )

        except ImageGenerationError:
            raise
        except Exception as e:
            logger.exception("Failed to parse API response")
            raise ImageGenerationError(f"Failed to parse API response: {e}")

        elapsed = time.monotonic() - start_time
        logger.info("Image generation execution time for model %s: %.2fs", self.model, elapsed)

        # 4. Prepare final Telegram-ready data:image/...;base64,...
        return self._to_telegram_data_uri(output_mime, output_b64)