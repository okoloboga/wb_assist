"""
Скрипт для заполнения chunk_hash существующих записей.

Выполняется один раз после миграции для обратной совместимости.

Usage:
    python -m gpt_integration.ai_chat.RAG.migrations.001_populate_chunk_hash
"""

import hashlib
import logging
from sqlalchemy.orm import Session
from gpt_integration.ai_chat.RAG.database import RAGSessionLocal
from gpt_integration.ai_chat.RAG.models import RAGMetadata

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_chunk_hash(chunk_text: str) -> str:
    """
    Вычислить SHA256 hash от chunk_text.

    Args:
        chunk_text: Текст чанка

    Returns:
        SHA256 hash в hex формате (64 символа)
    """
    return hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()


def populate_chunk_hash():
    """Заполнить chunk_hash для существующих записей."""
    db: Session = RAGSessionLocal()

    try:
        logger.info("🚀 Starting chunk_hash population...")

        # Получить все записи без chunk_hash
        records = db.query(RAGMetadata).filter(
            RAGMetadata.chunk_hash.is_(None)
        ).all()

        total = len(records)
        logger.info(f"📊 Found {total} records without chunk_hash")

        if total == 0:
            logger.info("✅ All records already have chunk_hash. Nothing to do.")
            return

        # Обработать батчами
        batch_size = 1000
        updated = 0

        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"🔄 Processing batch {batch_num}/{total_batches}...")

            for record in batch:
                record.chunk_hash = calculate_chunk_hash(record.chunk_text)
                updated += 1

            db.commit()
            logger.info(f"✅ Updated {updated}/{total} records")

        logger.info(f"✅ Successfully populated chunk_hash for {updated} records")

        # Проверка результата
        remaining = db.query(RAGMetadata).filter(
            RAGMetadata.chunk_hash.is_(None)
        ).count()

        if remaining > 0:
            logger.warning(f"⚠️ Warning: {remaining} records still without chunk_hash")
        else:
            logger.info("✅ Verification passed: All records have chunk_hash")

    except Exception as e:
        logger.error(f"❌ Error populating chunk_hash: {e}", exc_info=True)
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    populate_chunk_hash()
