"""
Скрипт для тестирования индексации RAG и проверки работы векторной БД.

Использование:
    python -m gpt_integration.ai_chat.RAG.test_indexing <cabinet_id>

Пример:
    python -m gpt_integration.ai_chat.RAG.test_indexing 2
"""

import asyncio
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from gpt_integration.ai_chat.RAG.indexer import RAGIndexer
from gpt_integration.ai_chat.RAG.vector_search import VectorSearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_indexing(cabinet_id: int):
    """Тестирование индексации кабинета"""
    logger.info(f"🚀 Начинаю индексацию кабинета {cabinet_id}...")
    
    indexer = RAGIndexer()
    result = await indexer.index_cabinet(cabinet_id)
    
    if result['success']:
        logger.info(f"✅ Индексация завершена успешно!")
        logger.info(f"   Всего чанков: {result['total_chunks']}")
        if result.get('chunks_by_type'):
            for chunk_type, count in result['chunks_by_type'].items():
                logger.info(f"   - {chunk_type}: {count}")
    else:
        logger.error(f"❌ Ошибка индексации: {result.get('errors', [])}")
    
    return result


async def test_search(cabinet_id: int, query: str):
    """Тестирование поиска в векторной БД"""
    logger.info(f"🔍 Тестирую поиск для кабинета {cabinet_id}...")
    logger.info(f"   Запрос: '{query}'")
    
    searcher = VectorSearch()
    results = await searcher.search_relevant_chunks(
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


async def main():
    if len(sys.argv) < 2:
        print("Использование: python -m gpt_integration.ai_chat.RAG.test_indexing <cabinet_id>")
        print("Пример: python -m gpt_integration.ai_chat.RAG.test_indexing 2")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    
    # 1. Запустить индексацию
    logger.info("=" * 60)
    logger.info("ШАГ 1: Индексация данных")
    logger.info("=" * 60)
    index_result = await test_indexing(cabinet_id)
    
    if not index_result['success']:
        logger.error("Индексация не удалась. Проверьте логи выше.")
        return
    
    # 2. Тестировать поиск с разными запросами
    logger.info("\n" + "=" * 60)
    logger.info("ШАГ 2: Тестирование поиска")
    logger.info("=" * 60)
    
    test_queries = [
        "какие товары продались лучше всего",
        "сколько заказов было вчера",
        "какие товары на складе",
        "какие отзывы получили товары",
        "какая выручка за последний месяц"
    ]
    
    for query in test_queries:
        logger.info(f"\n📝 Тестовый запрос: '{query}'")
        await test_search(cabinet_id, query)
        logger.info("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())

