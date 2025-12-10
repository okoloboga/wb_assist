"""
Скрипт для запуска индексации RAG (только индексация, без тестирования).

Использование:
    python -m gpt_integration.ai_chat.RAG.run_indexing <cabinet_id>

Пример:
    python -m gpt_integration.ai_chat.RAG.run_indexing 2
"""

import asyncio
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from gpt_integration.ai_chat.RAG.indexer import RAGIndexer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    if len(sys.argv) < 2:
        print("Использование: python -m gpt_integration.ai_chat.RAG.run_indexing <cabinet_id>")
        print("Пример: python -m gpt_integration.ai_chat.RAG.run_indexing 2")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    
    logger.info(f"🚀 Начинаю индексацию кабинета {cabinet_id}...")
    logger.info("⚠️ Это может занять несколько минут (223 батча эмбеддингов)")
    
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


if __name__ == "__main__":
    asyncio.run(main())

