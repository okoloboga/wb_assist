"""
Card Generation service endpoints.
"""

import logging
from typing import Dict, Any

from gpt_integration.gpt_client import GPTClient
from gpt_integration.card_generation.prompt_generator import (
    create_card_prompt,
    format_card_response,
)

logger = logging.getLogger(__name__)


def generate_card(
    characteristics: Dict[str, str],
    target_audience: str,
    selling_points: str,
    semantic_core_text: str = None
) -> Dict[str, Any]:
    """
    Генерация карточки товара через GPT.
    
    Args:
        characteristics: Характеристики товара (name, brand, category)
        target_audience: Целевая аудитория
        selling_points: Уникальные преимущества
        semantic_core_text: Опциональный текст семантического ядра
        
    Returns:
        Dict с сгенерированной карточкой
    """
    try:
        logger.info(f"🎨 Starting card generation for: {characteristics.get('name', 'Unknown')}")
        
        # Формируем промпт для GPT
        prompt = create_card_prompt(
            characteristics=characteristics,
            target_audience=target_audience,
            selling_points=selling_points,
            semantic_core_text=semantic_core_text
        )
        
        # Создаем системное сообщение для GPT
        system_message = (
            "Ты — эксперт по созданию карточек товаров для Wildberries. "
            "Ты умеешь создавать привлекательные, SEO-оптимизированные описания товаров, "
            "которые помогают продавцам увеличить продажи на маркетплейсе. "
            "Твои описания точные, убедительные и ориентированы на целевую аудиторию."
        )
        
        # Подготавливаем сообщения для GPT
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Вызываем GPT
        client = GPTClient.from_env()
        logger.info(f"🤖 Calling GPT with model={client.model}, max_tokens={client.max_tokens}")
        
        response_text = client.complete_messages(messages)
        
        # Проверяем, не вернулась ли ошибка (начинается с "ERROR:")
        if response_text.startswith("ERROR:"):
            error_msg = response_text.replace("ERROR:", "").strip()
            
            # Проверяем на ошибку региона
            if "unsupported_country_region_territory" in error_msg or "not available in your region" in error_msg.lower():
                logger.error(f"❌ Regional restriction error: {error_msg}")
                return {
                    "status": "error",
                    "error_type": "regional_restriction",
                    "message": (
                        "❌ OpenAI API недоступен в вашем регионе.\n\n"
                        "🔧 Решение:\n"
                        "Обратитесь к администратору для настройки альтернативного API endpoint "
                        "(через OPENAI_BASE_URL).\n\n"
                        "Это может быть прокси-сервер или OpenAI-совместимый провайдер."
                    )
                }
            
            # Другие ошибки
            logger.error(f"❌ GPT error: {error_msg}")
            return {
                "status": "error",
                "message": f"Ошибка при обращении к GPT: {error_msg}"
            }
        
        logger.info(f"✅ GPT response received, length={len(response_text)} chars")
        
        # Форматируем ответ
        card_text = format_card_response(response_text)
        
        logger.info(f"✅ Card generated successfully")
        
        return {
            "status": "success",
            "card": card_text
        }
    
    except Exception as e:
        logger.error(f"❌ Card generation failed: {e}", exc_info=True)
        error_str = str(e)
        
        # Проверяем на ошибку региона в исключении
        if "unsupported_country_region_territory" in error_str or "not available in your region" in error_str.lower():
            return {
                "status": "error",
                "error_type": "regional_restriction",
                "message": (
                    "❌ OpenAI API недоступен в вашем регионе.\n\n"
                    "🔧 Решение:\n"
                    "Обратитесь к администратору для настройки альтернативного API endpoint "
                    "(через OPENAI_BASE_URL).\n\n"
                    "Это может быть прокси-сервер или OpenAI-совместимый провайдер."
                )
            }
        
        return {
            "status": "error",
            "message": f"Ошибка генерации карточки: {error_str}"
        }

