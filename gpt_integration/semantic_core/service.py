import os
import logging
from typing import Dict, Any

from gpt_integration.gpt_client import GPTClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SEMANTIC_CORE_PROMPT_TEMPLATE = """
Ты — опытный маркетолог, который анализирует товарные ниши. Проанализируй предоставленный список описаний товаров и составь подробное семантическое ядро.

ИНСТРУКЦИЯ:
1. Разбей все найденные фразы и слова на следующие группы (кластеры):
   - **Характеристики товара:** (материалы, размеры, цвет, технические параметры)
   - **Преимущества и выгоды:** (что получает покупатель: удобство, комфорт, экономия)
   - **Проблемы и решения:** (какую проблему решает товар: "не мнется" -> решает проблему глажки)
   - **Сценарии использования:** (для кого и для чего: "для офиса", "на природу", "для подарка")
   - **Эмоции и триггеры:** ("стильный", "эксклюзивный", "модный", "популярный")

2. Внутри каждой группы выдели самые частотные и важные фразы.

3. Представь результат в виде четкой таблицы со столбцами: [Группа | Ключевая фраза | Пример из текста | Частота (высокая/средняя/низкая)].

Список описаний для анализа:
{descriptions_text}
"""

def generate_semantic_core(descriptions_text: str) -> Dict[str, Any]:
    """
    Генерирует семантическое ядро на основе предоставленного текста описаний товаров.
    """
    client = GPTClient.from_env()
    
    prompt = SEMANTIC_CORE_PROMPT_TEMPLATE.format(descriptions_text=descriptions_text)
    
    logger.info("Generating semantic core with GPT...")
    try:
        response_text = client.send_request(prompt)
        logger.info("Semantic core generated successfully.")
        return {"status": "success", "core": response_text}
    except Exception as e:
        logger.error(f"Error generating semantic core: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
