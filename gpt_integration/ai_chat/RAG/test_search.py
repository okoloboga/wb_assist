"""
Скрипт для тестирования RAG поиска.

Использование:
    python -m gpt_integration.ai_chat.RAG.test_search <cabinet_id> "<query>"
"""

import asyncio
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from gpt_integration.ai_chat.RAG.vector_search import VectorSearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_search(cabinet_id: int, query: str):
    """Тестирование поиска"""
    logger.info(f"🔍 Тестирую поиск для кабинета {cabinet_id}...")
    logger.info(f"   Запрос: '{query}'")
    
    searcher = VectorSearch()
    results = searcher.search_relevant_chunks(
        query_text=query,
        cabinet_id=cabinet_id,
        max_chunks=5
    )
    
    if results:
        logger.info(f"✅ Найдено {len(results)} релевантных чанков:")
        for idx, chunk in enumerate(results, 1):
            logger.info(
                f"   [{idx}] similarity={chunk['similarity']:.4f}, "
                f"type={chunk['chunk_type']}, "
                f"text_preview='{chunk['chunk_text'][:80]}...'"
            )
    else:
        logger.warning("⚠️ Релевантные чанки не найдены")
    
    return results


def main():
    if len(sys.argv) < 3:
        print("Использование: python -m gpt_integration.ai_chat.RAG.test_search <cabinet_id> \"<query>\"")
        print("Пример: python -m gpt_integration.ai_chat.RAG.test_search 2 \"сколько заказов было вчера\"")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    query = sys.argv[2]
    
    test_search(cabinet_id, query)


if __name__ == "__main__":
    main()

