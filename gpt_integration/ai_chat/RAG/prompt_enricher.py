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


async def enrich_prompt_with_rag(
    user_message: str,
    cabinet_id: int,
    original_prompt: str,
    chunk_types: Optional[List[str]] = None,
    max_chunks: Optional[int] = None
) -> str:
    """
    Asynchronously enriches a prompt with context from RAG.
    
    Process:
    1. Search for relevant chunks via VectorSearch.
    2. Build context via ContextBuilder.
    3. Combine the original prompt with the context.
    """
    if not RAG_ENABLED:
        logger.debug("⚠️ RAG disabled, returning original prompt")
        return original_prompt
    
    if not cabinet_id:
        logger.debug("⚠️ cabinet_id not specified, returning original prompt")
        return original_prompt
    
    try:
        logger.info(
            f"🔍 Enriching prompt with RAG: cabinet_id={cabinet_id}, "
            f"query='{user_message[:50]}...'"
        )
        
        # 1. Search for relevant chunks
        vector_search = VectorSearch()
        chunks = await vector_search.search_relevant_chunks(
            query_text=user_message,
            cabinet_id=cabinet_id,
            chunk_types=chunk_types,
            max_chunks=max_chunks or int(os.getenv("RAG_MAX_CHUNKS", "5"))
        )
        
        if not chunks:
            logger.info(
                f"⚠️ No relevant chunks found for cabinet_id={cabinet_id}, "
                f"returning original prompt"
            )
            return original_prompt
        
        # 2. Build context
        context_builder = ContextBuilder()
        context = context_builder.build_context(chunks)
        
        if not context or not context.strip():
            logger.warning(
                f"⚠️ Context is empty after building for cabinet_id={cabinet_id}, "
                f"returning original prompt"
            )
            return original_prompt
        
        # 3. Combine prompt with context
        enriched_prompt = f"""{original_prompt}

=== КОНТЕКСТ ИЗ БАЗЫ ДАННЫХ ===
{context}

=== ИНСТРУКЦИИ ===
Используй данные из контекста выше для ответа на вопрос пользователя.
Если в контексте нет нужной информации, отвечай на основе общих знаний, но укажи это.
Отвечай на русском языке, используя данные из контекста для персонализированных ответов.
"""
        
        logger.info(
            f"✅ Prompt enriched with context: "
            f"context_length={len(context)}, "
            f"chunks={len(chunks)}, "
            f"cabinet_id={cabinet_id}"
        )
        
        return enriched_prompt
        
    except Exception as e:
        logger.error(
            f"❌ Error enriching prompt with RAG for cabinet_id={cabinet_id}: {e}",
            exc_info=True
        )
        # Fallback to the original prompt
        return original_prompt

