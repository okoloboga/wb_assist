"""
Prompt Enricher - модуль для обогащения промптов контекстом из RAG.
"""

import os
import logging
from typing import Optional, List

from .vector_search import VectorSearch
from .context_builder import ContextBuilder

logger = logging.getLogger(__name__)


# Флаг включения/выключения RAG
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"


def enrich_prompt_with_rag(
    user_message: str,
    cabinet_id: int,
    original_prompt: str,
    chunk_types: Optional[List[str]] = None,
    max_chunks: Optional[int] = None
) -> str:
    """
    Обогащение промпта контекстом из RAG.
    
    Процесс:
    1. Поиск релевантных чанков через VectorSearch
    2. Формирование контекста через ContextBuilder
    3. Объединение исходного промпта с контекстом
    
    Args:
        user_message: Сообщение пользователя (используется как запрос для поиска)
        cabinet_id: ID кабинета пользователя
        original_prompt: Исходный системный промпт
        chunk_types: Типы чанков для фильтрации (опционально)
        max_chunks: Максимальное количество чанков (из env или default)
        
    Returns:
        Обогащенный промпт или исходный промпт (при ошибке или отсутствии данных)
    """
    if not RAG_ENABLED:
        logger.debug("⚠️ RAG отключен, возвращаем исходный промпт")
        return original_prompt
    
    if not cabinet_id:
        logger.debug("⚠️ cabinet_id не указан, возвращаем исходный промпт")
        return original_prompt
    
    try:
        logger.info(
            f"🔍 Обогащение промпта RAG: cabinet_id={cabinet_id}, "
            f"query='{user_message[:50]}...'"
        )
        
        # 1. Поиск релевантных чанков
        vector_search = VectorSearch()
        chunks = vector_search.search_relevant_chunks(
            query_text=user_message,
            cabinet_id=cabinet_id,
            chunk_types=chunk_types,
            max_chunks=max_chunks or int(os.getenv("RAG_MAX_CHUNKS", "5"))
        )
        
        if not chunks:
            logger.info(
                f"⚠️ Релевантные чанки не найдены для cabinet_id={cabinet_id}, "
                f"возвращаем исходный промпт"
            )
            return original_prompt
        
        # 2. Формирование контекста
        context_builder = ContextBuilder()
        context = context_builder.build_context(chunks)
        
        if not context or not context.strip():
            logger.warning(
                f"⚠️ Контекст пуст после формирования для cabinet_id={cabinet_id}, "
                f"возвращаем исходный промпт"
            )
            return original_prompt
        
        # 3. Объединение промпта с контекстом
        enriched_prompt = f"""{original_prompt}

=== КОНТЕКСТ ИЗ БАЗЫ ДАННЫХ ===
{context}

=== ИНСТРУКЦИИ ===
Используй данные из контекста выше для ответа на вопрос пользователя.
Если в контексте нет нужной информации, отвечай на основе общих знаний, но укажи это.
Отвечай на русском языке, используя данные из контекста для персонализированных ответов.
"""
        
        logger.info(
            f"✅ Промпт обогащен контекстом: "
            f"длина контекста={len(context)}, "
            f"чанков={len(chunks)}, "
            f"cabinet_id={cabinet_id}"
        )
        
        return enriched_prompt
        
    except Exception as e:
        logger.error(
            f"❌ Ошибка при обогащении промпта RAG для cabinet_id={cabinet_id}: {e}",
            exc_info=True
        )
        # Fallback на исходный промпт
        return original_prompt

