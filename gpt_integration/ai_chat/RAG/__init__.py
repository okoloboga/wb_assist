"""
RAG (Retrieval-Augmented Generation) module for AI Chat Service.

This module provides functionality for:
- Indexing data from main database into vector database
- Vector search for relevant data chunks
- Context building for prompt enrichment
"""

from .indexer import RAGIndexer
from .vector_search import VectorSearch
from .context_builder import ContextBuilder
from .prompt_enricher import enrich_prompt_with_rag, RAG_ENABLED
from .utils import get_cabinet_id_for_user
from .database import get_rag_db, init_rag_db, RAGSessionLocal
from .models import RAGMetadata, RAGEmbedding, RAGIndexStatus

__all__ = [
    'RAGIndexer',
    'VectorSearch',
    'ContextBuilder',
    'enrich_prompt_with_rag',
    'RAG_ENABLED',
    'get_cabinet_id_for_user',
    'get_rag_db',
    'init_rag_db',
    'RAGSessionLocal',
    'RAGMetadata',
    'RAGEmbedding',
    'RAGIndexStatus',
]

