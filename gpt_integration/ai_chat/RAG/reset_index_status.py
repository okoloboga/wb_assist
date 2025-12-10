"""
Скрипт для сброса статуса индексации RAG.

Использование:
    python -m gpt_integration.ai_chat.RAG.reset_index_status <cabinet_id>

Пример:
    python -m gpt_integration.ai_chat.RAG.reset_index_status 2
"""

import sys
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from gpt_integration.ai_chat.RAG.database import RAGSessionLocal
from gpt_integration.ai_chat.RAG.models import RAGIndexStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reset_index_status(cabinet_id: int):
    """Сброс статуса индексации для кабинета"""
    db = RAGSessionLocal()
    try:
        index_status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()
        
        if index_status:
            old_status = index_status.indexing_status
            index_status.indexing_status = 'pending'
            db.commit()
            logger.info(f"✅ Статус индексации для кабинета {cabinet_id} сброшен: {old_status} -> pending")
        else:
            logger.info(f"ℹ️ Статус индексации для кабинета {cabinet_id} не найден (это нормально для первого запуска)")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка при сбросе статуса: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m gpt_integration.ai_chat.RAG.reset_index_status <cabinet_id>")
        print("Пример: python -m gpt_integration.ai_chat.RAG.reset_index_status 2")
        sys.exit(1)
    
    cabinet_id = int(sys.argv[1])
    reset_index_status(cabinet_id)

