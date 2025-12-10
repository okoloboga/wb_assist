"""
Скрипт для принудительного завершения индексации (если процесс завис).

Использование:
    python -m gpt_integration.ai_chat.RAG.complete_indexing <cabinet_id>
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

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


def complete_indexing(cabinet_id: int):
    """Принудительное завершение индексации"""
    db = RAGSessionLocal()
    try:
        index_status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()
        
        if index_status:
            # Подсчитать реальное количество записей
            metadata_count = db.query(RAGMetadata).filter(
                RAGMetadata.cabinet_id == cabinet_id
            ).count()
            
            # Обновить статус
            index_status.indexing_status = 'completed'
            index_status.total_chunks = metadata_count
            index_status.last_indexed_at = datetime.utcnow()
            db.commit()
            
            print(f"✅ Индексация для кабинета {cabinet_id} помечена как завершенная")
            print(f"   Всего записей в БД: {metadata_count}")
            print(f"   Статус: completed")
        else:
            print(f"ℹ️ Статус индексации для кабинета {cabinet_id} не найден")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка при завершении индексации: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m gpt_integration.ai_chat.RAG.complete_indexing <cabinet_id>")
        print("Пример: python -m gpt_integration.ai_chat.RAG.complete_indexing 2")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    complete_indexing(cabinet_id)

