"""
Скрипт для проверки статуса индексации RAG.

Использование:
    python -m gpt_integration.ai_chat.RAG.check_status <cabinet_id>
"""

import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from gpt_integration.ai_chat.RAG.database import RAGSessionLocal
from gpt_integration.ai_chat.RAG.models import RAGIndexStatus, RAGMetadata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_status(cabinet_id: int):
    """Проверка статуса индексации"""
    db = RAGSessionLocal()
    try:
        index_status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()
        
        if index_status:
            print(f"📊 Статус индексации для кабинета {cabinet_id}:")
            print(f"   Статус: {index_status.indexing_status}")
            print(f"   Всего чанков: {index_status.total_chunks}")
            print(f"   Последняя индексация: {index_status.last_indexed_at}")
        else:
            print(f"ℹ️ Статус индексации для кабинета {cabinet_id} не найден")
        
        # Проверить количество реальных записей в БД
        metadata_count = db.query(RAGMetadata).filter(
            RAGMetadata.cabinet_id == cabinet_id
        ).count()
        
        print(f"   Записей в БД: {metadata_count}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке статуса: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m gpt_integration.ai_chat.RAG.check_status <cabinet_id>")
        print("Пример: python -m gpt_integration.ai_chat.RAG.check_status 2")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    check_status(cabinet_id)

