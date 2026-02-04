"""
Валидация фото пользователя через ChatGPT
"""
import logging
import json
from typing import Dict, Any

from gpt_integration.gpt_client import GPTClient

logger = logging.getLogger(__name__)


VALIDATION_PROMPT = """Проанализируй это изображение для виртуальной примерки одежды.

Проверь следующее:
1. Есть ли на фото человек (минимум по пояс)?
2. Достаточно ли качественное изображение (четкость, освещение)?
3. Нет ли неприемлемого контента (насилие, обнаженка, провокации)?

Верни ТОЛЬКО JSON в формате:
{
  "valid": true/false,
  "reason": "краткая причина (если не валидно)",
  "description": "подробное объяснение для пользователя на русском"
}

Если фото подходит - valid=true, reason="", description="Фото подходит для примерки".
Если не подходит - укажи конкретную причину понятным языком."""


async def validate_photo(image_url: str) -> Dict[str, Any]:
    """
    Валидация фото через ChatGPT (модель gpt-4.1)

    Args:
        image_url: URL фото для проверки

    Returns:
        Dict с ключами: valid, reason, description
    """
    try:
        client = GPTClient(model="gpt-4.1")

        # ChatGPT Vision API требует специальный формат
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VALIDATION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]

        response = client.complete_messages(messages)

        # Парсим JSON из ответа
        if response.startswith("ERROR"):
            logger.error(f"GPT validation error: {response}")
            return {
                "valid": False,
                "reason": "api_error",
                "description": "Не удалось проверить фото. Попробуй еще раз"
            }

        # Извлекаем JSON из ответа
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        result = json.loads(response)

        logger.info(f"Photo validation result: {result}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT response: {response}, error: {e}")
        return {
            "valid": False,
            "reason": "parse_error",
            "description": "Ошибка обработки. Попробуй загрузить другое фото"
        }

    except Exception as e:
        logger.error(f"Photo validation failed: {e}", exc_info=True)
        return {
            "valid": False,
            "reason": "error",
            "description": "Не удалось проверить фото. Попробуй еще раз"
        }