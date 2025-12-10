"""
Vector Search - модуль для векторного поиска в pgvector.

Предоставляет функциональность для поиска релевантных чанков данных
на основе запроса пользователя с использованием векторного поиска.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI

from .database import RAGSessionLocal
from .models import RAGEmbedding, RAGMetadata

logger = logging.getLogger(__name__)


class VectorSearch:
    """
    Класс для векторного поиска релевантных чанков.
    
    Процесс поиска:
    1. Генерация эмбеддинга для запроса пользователя
    2. Векторный поиск в pgvector
    3. Получение метаданных для найденных векторов
    """
    
    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
        embeddings_model: Optional[str] = None,
        similarity_threshold: Optional[float] = None
    ):
        """
        Инициализация поиска.
        
        Args:
            openai_client: Клиент OpenAI (если None, создается новый)
            embeddings_model: Модель для генерации эмбеддингов (из env или default)
            similarity_threshold: Минимальный порог релевантности (0-1, из env или default)
        """
        if openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            base_url_raw = os.getenv("OPENAI_BASE_URL")
            base_url = None
            if base_url_raw and base_url_raw.strip():
                base_url_clean = base_url_raw.strip()
                # Проверяем, что URL валидный (начинается с http:// или https://)
                if base_url_clean.startswith(("http://", "https://")):
                    base_url = base_url_clean
            client_kwargs = {}
            if api_key:
                client_kwargs["api_key"] = api_key
            if base_url:
                client_kwargs["base_url"] = base_url
            self.openai_client = OpenAI(**client_kwargs) if client_kwargs else OpenAI()
        else:
            self.openai_client = openai_client
        self.embeddings_model = embeddings_model or os.getenv(
            "OPENAI_EMBEDDINGS_MODEL",
            "text-embedding-3-small"
        )
        self.similarity_threshold = similarity_threshold or float(
            os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5")
        )
    
    def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        Генерация эмбеддинга для запроса пользователя.
        
        Использует ту же модель, что и при индексации, для обеспечения
        совместимости векторов.
        
        Args:
            query_text: Текст запроса пользователя
            
        Returns:
            Вектор размерности 1536
            
        Raises:
            ValueError: Если запрос пустой
            Exception: При ошибке API OpenAI
        """
        if not query_text or not query_text.strip():
            raise ValueError("Запрос не может быть пустым")
        
        try:
            logger.info(f"🔄 Generating embedding for query: '{query_text[:50]}...'")
            
            # Вызов OpenAI Embeddings API
            response = self.openai_client.embeddings.create(
                model=self.embeddings_model,
                input=[query_text]  # Один запрос
            )
            
            # Извлечь вектор из ответа
            embedding = response.data[0].embedding
            
            logger.info(f"✅ Embedding generated: dimension {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        cabinet_id: int,
        chunk_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск в pgvector.
        
        Использует cosine distance для поиска наиболее похожих векторов.
        
        Args:
            query_embedding: Эмбеддинг запроса (список float)
            cabinet_id: ID кабинета (обязательная фильтрация)
            chunk_types: Список типов чанков для фильтрации (опционально)
            limit: Максимальное количество результатов
            
        Returns:
            Список словарей с результатами:
            [
                {
                    'embedding_id': 1,
                    'metadata_id': 1,
                    'similarity': 0.85,
                    'distance': 0.15
                },
                ...
            ]
        """
        db = RAGSessionLocal()
        
        try:
            # Преобразовать список в строку для PostgreSQL vector
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Построить SQL запрос
            # Используем cosine distance (<#>) и вычисляем similarity как 1 - distance
            # Важно: используем f-string для embedding_str, так как SQLAlchemy не может правильно
            # обработать placeholder с ::vector из-за двойного двоеточия
            if chunk_types and len(chunk_types) > 0:
                # Фильтрация по типам чанков
                # Используем правильный формат массива PostgreSQL
                chunk_types_array = '{' + ','.join(f'"{ct}"' for ct in chunk_types) + '}'
                query = text(f"""
                    SELECT 
                        e.id AS embedding_id,
                        e.metadata_id,
                        1 - (e.embedding <#> '{embedding_str}'::vector) AS similarity,
                        e.embedding <#> '{embedding_str}'::vector AS distance
                    FROM rag_embeddings e
                    JOIN rag_metadata m ON e.metadata_id = m.id
                    WHERE m.cabinet_id = :cabinet_id
                      AND m.chunk_type = ANY(:chunk_types::text[])
                    ORDER BY e.embedding <#> '{embedding_str}'::vector
                    LIMIT :limit
                """)
                params = {
                    'cabinet_id': cabinet_id,
                    'chunk_types': chunk_types_array,
                    'limit': limit
                }
            else:
                # Без фильтрации по типам
                query = text(f"""
                    SELECT 
                        e.id AS embedding_id,
                        e.metadata_id,
                        1 - (e.embedding <#> '{embedding_str}'::vector) AS similarity,
                        e.embedding <#> '{embedding_str}'::vector AS distance
                    FROM rag_embeddings e
                    JOIN rag_metadata m ON e.metadata_id = m.id
                    WHERE m.cabinet_id = :cabinet_id
                    ORDER BY e.embedding <#> '{embedding_str}'::vector
                    LIMIT :limit
                """)
                params = {
                    'cabinet_id': cabinet_id,
                    'limit': limit
                }
            
            # Выполнить запрос
            logger.info(
                f"📊 Executing vector search: "
                f"cabinet_id={cabinet_id}, "
                f"limit={limit}, "
                f"chunk_types={chunk_types if chunk_types else 'all'}, "
                f"similarity_threshold={self.similarity_threshold}"
            )
            
            result = db.execute(query, params)
            rows = result.fetchall()
            
            logger.info(f"📈 Retrieved {len(rows)} results from DB (before threshold filtering)")
            
            # Преобразовать результаты
            results = []
            filtered_out = []
            for idx, row in enumerate(rows):
                similarity = float(row.similarity)
                distance = float(row.distance)
                
                logger.debug(
                    f"  [{idx+1}/{len(rows)}] embedding_id={row.embedding_id}, "
                    f"metadata_id={row.metadata_id}, "
                    f"similarity={similarity:.4f}, "
                    f"distance={distance:.4f}"
                )
                
                # Применить порог релевантности
                if similarity >= self.similarity_threshold:
                    results.append({
                        'embedding_id': row.embedding_id,
                        'metadata_id': row.metadata_id,
                        'similarity': similarity,
                        'distance': distance
                    })
                else:
                    filtered_out.append({
                        'embedding_id': row.embedding_id,
                        'similarity': similarity,
                        'distance': distance
                    })
            
            logger.info(
                f"✅ Filtering results: "
                f"passed={len(results)}, "
                f"filtered_out={len(filtered_out)}, "
                f"threshold={self.similarity_threshold}"
            )
            
            if results:
                logger.info(
                    f"📊 Similarity range for passed results: "
                    f"min={min(r['similarity'] for r in results):.4f}, "
                    f"max={max(r['similarity'] for r in results):.4f}, "
                    f"avg={sum(r['similarity'] for r in results) / len(results):.4f}"
                )
            
            if filtered_out:
                logger.info(
                    f"⚠️ Filtered out results (below threshold {self.similarity_threshold}): "
                    f"min={min(f['similarity'] for f in filtered_out):.4f}, "
                    f"max={max(f['similarity'] for f in filtered_out):.4f}"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in vector search: {e}")
            raise
            
        finally:
            db.close()
    
    def get_metadata_for_embeddings(
        self,
        embedding_ids: List[int],
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Получение метаданных для найденных embedding IDs.
        
        Args:
            embedding_ids: Список ID эмбеддингов
            db: Сессия БД
            
        Returns:
            Список словарей с метаданными:
            [
                {
                    'id': 1,
                    'embedding_id': 1,
                    'chunk_text': '...',
                    'chunk_type': 'order',
                    'source_table': 'wb_orders',
                    'source_id': 123
                },
                ...
            ]
        """
        if not embedding_ids:
            return []
        
        try:
            # Запрос метаданных через JOIN
            results = db.query(
                RAGMetadata.id,
                RAGMetadata.chunk_text,
                RAGMetadata.chunk_type,
                RAGMetadata.source_table,
                RAGMetadata.source_id,
                RAGEmbedding.id.label('embedding_id')
            ).join(
                RAGEmbedding,
                RAGMetadata.id == RAGEmbedding.metadata_id
            ).filter(
                RAGEmbedding.id.in_(embedding_ids)
            ).all()
            
            # Преобразовать в список словарей
            metadata_list = []
            for row in results:
                metadata_list.append({
                    'id': row.id,
                    'embedding_id': row.embedding_id,
                    'chunk_text': row.chunk_text,
                    'chunk_type': row.chunk_type,
                    'source_table': row.source_table,
                    'source_id': row.source_id
                })
            
            logger.info(f"📋 Retrieved {len(metadata_list)} metadata records")
            
            return metadata_list
            
        except Exception as e:
            logger.error(f"❌ Error retrieving metadata: {e}")
            raise
    
    def search_relevant_chunks(
        self,
        query_text: str,
        cabinet_id: int,
        chunk_types: Optional[List[str]] = None,
        max_chunks: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Главный метод поиска релевантных чанков.
        
        Объединяет все этапы:
        1. Генерация эмбеддинга запроса
        2. Векторный поиск
        3. Получение метаданных
        
        Args:
            query_text: Текст запроса пользователя
            cabinet_id: ID кабинета
            chunk_types: Типы чанков для фильтрации (опционально)
            max_chunks: Максимальное количество результатов
            
        Returns:
            Список релевантных чанков с метаданными и similarity:
            [
                {
                    'id': 1,
                    'embedding_id': 1,
                    'chunk_text': '...',
                    'chunk_type': 'order',
                    'source_table': 'wb_orders',
                    'source_id': 123,
                    'similarity': 0.85
                },
                ...
            ]
        """
        try:
            logger.info(
                f"🔍 Starting search for relevant chunks:\n"
                f"  📝 Query: '{query_text}'\n"
                f"  🏢 Cabinet ID: {cabinet_id}\n"
                f"  📦 Chunk types: {chunk_types if chunk_types else 'all'}\n"
                f"  🔢 Max results: {max_chunks}\n"
                f"  📊 Similarity threshold: {self.similarity_threshold}"
            )
            
            # 1. Генерация эмбеддинга запроса
            query_embedding = self.generate_query_embedding(query_text)
            
            # 2. Векторный поиск
            search_results = self.search(
                query_embedding=query_embedding,
                cabinet_id=cabinet_id,
                chunk_types=chunk_types,
                limit=max_chunks
            )
            
            if not search_results:
                logger.warning(
                    f"⚠️ No relevant chunks found for query '{query_text[:100]}...' "
                    f"(cabinet_id={cabinet_id}, threshold={self.similarity_threshold})"
                )
                return []
            
            logger.info(
                f"📋 Found {len(search_results)} results after filtering, "
                f"fetching metadata..."
            )
            
            # 3. Получение метаданных
            db = RAGSessionLocal()
            try:
                embedding_ids = [r['embedding_id'] for r in search_results]
                logger.debug(f"🔍 Запрашиваю метаданные для {len(embedding_ids)} embedding IDs: {embedding_ids}")
                
                metadata_list = self.get_metadata_for_embeddings(embedding_ids, db)
                
                # Объединить с similarity
                similarity_map = {r['embedding_id']: r['similarity'] for r in search_results}
                for metadata in metadata_list:
                    embedding_id = metadata['embedding_id']
                    metadata['similarity'] = similarity_map.get(embedding_id, 0.0)
                
                # Сортировать по similarity (от большего к меньшему)
                metadata_list.sort(key=lambda x: x['similarity'], reverse=True)
                
                logger.info(
                    f"✅ Final search results:\n"
                    f"  📊 Total found: {len(metadata_list)} chunks\n"
                    f"  📈 Similarity range: {metadata_list[0]['similarity']:.4f} - "
                    f"{metadata_list[-1]['similarity']:.4f}\n"
                    f"  📝 Chunk types: {', '.join(set(m['chunk_type'] for m in metadata_list))}"
                )
                
                # Детальный лог по каждому результату
                for idx, metadata in enumerate(metadata_list, 1):
                    logger.debug(
                        f"  [{idx}] similarity={metadata['similarity']:.4f}, "
                        f"type={metadata['chunk_type']}, "
                        f"source={metadata['source_table']}:{metadata['source_id']}, "
                        f"text_preview='{metadata['chunk_text'][:50]}...'"
                    )
                
                return metadata_list
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error searching relevant chunks: {e}")
            # Вернуть пустой список при ошибке (fallback)
            return []

