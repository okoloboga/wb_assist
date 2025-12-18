"""
Vector Search - модуль для векторного поиска в pgvector.

Предоставляет функциональность для поиска релевантных чанков данных
на основе запроса пользователя с использованием векторного поиска.
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from gpt_integration.comet_client import comet_client

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
        similarity_threshold: Optional[float] = None
    ):
        """
        Initializes the searcher.
        The client for creating embeddings is now the centralized CometClient.
        """
        # Similarity threshold для cosine similarity (1 - cosine distance), диапазон [0, 1]
        self.similarity_threshold = similarity_threshold or float(
            os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3")
        )
    
    async def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        Generate an embedding for a user query using CometAPI.
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text cannot be empty")
        
        try:
            logger.info(f"🔄 Generating embedding via CometAPI for query: '{query_text[:50]}...'")
            
            response = await comet_client.create_embeddings(
                texts=[query_text]
            )
            
            embedding = response['data'][0]['embedding']
            
            usage = response.get("usage")
            if usage:
                prompt_tokens = usage.get("prompt_tokens")
                total_tokens = usage.get("total_tokens")
                logger.info(
                    f"🧮 Embedding tokens: prompt={prompt_tokens}, total={total_tokens}"
                )
            
            logger.info(f"✅ Embedding generated: dimension {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}", exc_info=True)
            raise
    
    def search(
        self,
        query_embedding: List[float],
        cabinet_id: int,
        chunk_types: Optional[List[str]] = None,
        limit: int = 5,
        source_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск в pgvector.
        
        Использует cosine distance для поиска наиболее похожих векторов.
        
        Args:
            query_embedding: Эмбеддинг запроса (список float)
            cabinet_id: ID кабинета (обязательная фильтрация)
            chunk_types: Список типов чанков для фильтрации (опционально)
            limit: Максимальное количество результатов
            source_id: Фильтр по source_id (например, nm_id из запроса)
            
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
            # Используем inner product (<=>) для нормализованных векторов (OpenAI embeddings)
            # Для нормализованных векторов: cosine similarity ≈ inner product
            # pgvector возвращает NEGATIVE inner product с оператором <=>
            # Значения в диапазоне [-1, 1], где -1 = наиболее похожие, 1 = наименее похожие
            # Поэтому умножаем на -1 для получения similarity в диапазоне [0, 1]
            # Сортируем по ASC (от меньшего к большему = от самого отрицательного к положительному)
            # Важно: используем f-string для embedding_str, так как SQLAlchemy не может правильно
            # обработать placeholder с ::vector из-за двойного двоеточия
            filter_by_chunk_types = bool(chunk_types and len(chunk_types) > 0)
            if filter_by_chunk_types:
                query = text(f"""
                    SELECT
                        e.id AS embedding_id,
                        e.metadata_id,
                        (1 - (e.embedding <=> '{embedding_str}'::vector)) AS similarity,
                        e.embedding <=> '{embedding_str}'::vector AS distance,
                        m.source_id
                    FROM rag_embeddings e
                    JOIN rag_metadata m ON e.metadata_id = m.id
                    WHERE m.cabinet_id = :cabinet_id
                      AND m.chunk_type = ANY(:chunk_types)
                      {"AND m.source_id = :source_id" if source_id is not None else ""}
                    ORDER BY e.embedding <=> '{embedding_str}'::vector ASC, m.source_id DESC
                    LIMIT :limit
                """)
            else:
                query = text(f"""
                    SELECT
                        e.id AS embedding_id,
                        e.metadata_id,
                        (1 - (e.embedding <=> '{embedding_str}'::vector)) AS similarity,
                        e.embedding <=> '{embedding_str}'::vector AS distance,
                        m.source_id
                    FROM rag_embeddings e
                    JOIN rag_metadata m ON e.metadata_id = m.id
                    WHERE m.cabinet_id = :cabinet_id
                      {"AND m.source_id = :source_id" if source_id is not None else ""}
                    ORDER BY e.embedding <=> '{embedding_str}'::vector ASC, m.source_id DESC
                    LIMIT :limit
                """)

            params = {
                'cabinet_id': cabinet_id,
                'limit': limit
            }
            if filter_by_chunk_types:
                params['chunk_types'] = chunk_types
            if source_id is not None:
                params['source_id'] = source_id
            
            # Выполнить запрос
            logger.info(
                f"📊 Executing vector search: "
                f"cabinet_id={cabinet_id}, "
                f"limit={limit}, "
                f"chunk_types={chunk_types if chunk_types else 'all'}, "
                f"similarity_threshold={self.similarity_threshold}, "
                f"source_id_filter={source_id if source_id is not None else 'none'}"
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

                # Детальное логирование каждого результата
                logger.info(
                    f"  [{idx+1}/{len(rows)}] embedding_id={row.embedding_id}, "
                    f"metadata_id={row.metadata_id}, "
                    f"similarity={similarity:.4f} (1 - distance), "
                    f"distance={distance:.4f}"
                )

                # Применить порог релевантности
                if similarity >= self.similarity_threshold:
                    results.append({
                        'embedding_id': row.embedding_id,
                        'metadata_id': row.metadata_id,
                        'similarity': similarity,
                        'distance': distance,
                        'source_id': row.source_id  # Добавлено для debug и future use
                    })
                    logger.info(f"    ✅ PASSED threshold ({similarity:.4f} >= {self.similarity_threshold})")
                else:
                    filtered_out.append({
                        'embedding_id': row.embedding_id,
                        'similarity': similarity,
                        'distance': distance
                    })
                    logger.info(f"    ❌ FILTERED ({similarity:.4f} < {self.similarity_threshold})")
            
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
    
    def _detect_chunk_types_from_query(self, query_text: str) -> Optional[List[str]]:
        """
        Определяет типы чанков для поиска на основе ключевых слов в запросе.

        Автоматически фильтрует chunk_types если запрос явно указывает на конкретный тип данных.
        Это улучшает точность поиска и предотвращает возврат нерелевантных результатов.

        Args:
            query_text: Текст запроса пользователя

        Returns:
            Список типов чанков ['sale', 'order', 'product', 'stock', 'review'] или None (все типы)
        """
        query_lower = query_text.lower()

        # Ключевые слова для каждого типа чанков
        keywords_map = {
            'sale': [
                'выкуп', 'выкупов', 'выкупы', 'выкупа',
                'продаж', 'продажи', 'продажа', 'продаже',
                'возврат', 'возвратов', 'возвраты', 'возврата',
                'sales', 'sale', 'buyout', 'return',
                'купи', 'купили', 'купил',  # "кто купил товар"
                'проданн',  # проданный, проданных, проданные
            ],
            'order': [
                'заказ', 'заказов', 'заказы', 'заказа',
                'order', 'orders',
                'отмен',  # отменен, отмененных, отмены
                'новых заказ', 'последних заказ',
            ],
            'product': [
                'товар', 'товаров', 'товары', 'товара',
                'product', 'products',
                'артикул', 'nm_id', 'nmid',
                'цена', 'цены', 'ценой',
                'рейтинг', 'рейтинга',
                'бренд', 'бренда',
                'категори',  # категория, категории
            ],
            'stock': [
                'остат', 'остатков', 'остатки', 'остатка',
                'stock', 'stocks',
                'склад', 'складов', 'складе', 'складах',
                'warehouse',
                'количеств', 'количества',
                'сколько осталось', 'сколько на складе',
                'где хранится', 'где товар',
            ],
            'review': [
                'отзыв', 'отзывов', 'отзывы', 'отзыва',
                'review', 'reviews',
                'комментари', 'комментарий',
                'оценк', 'оценок', 'оценка',
                'негатив', 'позитив',
                'плох', 'хорош',  # плохие отзывы, хорошие отзывы
            ]
        }

        # Подсчитываем совпадения для каждого типа
        matches = {}
        for chunk_type, keywords in keywords_map.items():
            match_count = sum(1 for keyword in keywords if keyword in query_lower)
            if match_count > 0:
                matches[chunk_type] = match_count

        # Если нет совпадений - вернуть None (искать во всех типах)
        if not matches:
            return None

        # Если есть явный winner (на 2+ совпадений больше) - вернуть только его
        max_matches = max(matches.values())
        top_types = [t for t, count in matches.items() if count == max_matches]

        # Если несколько типов с одинаковым счетом - вернуть все (неоднозначность)
        # Но если один явно лидирует - вернуть только его
        if len(top_types) == 1:
            logger.info(f"🎯 Detected chunk_type from query: {top_types[0]} (matches: {max_matches})")
            return top_types
        else:
            # Несколько типов с одинаковым счетом - вернуть их все
            logger.info(f"🎯 Detected multiple chunk_types from query: {top_types} (matches: {max_matches})")
            return top_types

    def _is_temporal_query(self, query_text: str) -> bool:
        """
        Определяет, является ли запрос временным (требует сортировки по дате).

        Args:
            query_text: Текст запроса

        Returns:
            True если запрос содержит временные индикаторы
        """
        temporal_keywords = [
            # Относительное время (последние/недавние)
            'последн',  # последних, последние, последний
            'недавн',  # недавних, недавние
            'новых', 'новые', 'новый',
            'свежих', 'свежие', 'свежий',
            'recent', 'latest',

            # Абсолютное время (сегодня/вчера)
            'сегодня', 'today',
            'вчера', 'yesterday',
            'позавчера',

            # Периоды
            'за день', 'за сутки',
            'за неделю', 'на этой неделе', 'this week',
            'за месяц', 'в этом месяце', 'this month',
            'за год', 'в этом году', 'this year',

            # Текущее время
            'теперь', 'сейчас', 'now', 'currently',
        ]
        query_lower = query_text.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)

    def _extract_date_from_chunk(self, chunk_text: str) -> Optional[str]:
        """
        Извлекает дату из текста чанка.

        Ищет даты в формате YYYY-MM-DD (например, "от 2025-12-18").

        Args:
            chunk_text: Текст чанка

        Returns:
            Дата в формате YYYY-MM-DD или None
        """
        # Ищем даты в формате YYYY-MM-DD
        date_pattern = r'от (\d{4}-\d{2}-\d{2})'
        match = re.search(date_pattern, chunk_text)
        if match:
            return match.group(1)
        return None

    def _rerank_by_date(self, metadata_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Переранжирует результаты по дате (от новых к старым).

        Комбинирует semantic similarity с temporal ranking:
        - Сначала сортирует по дате (DESC)
        - Затем по similarity (DESC) для записей с одинаковой датой

        Args:
            metadata_list: Список метаданных с similarity scores

        Returns:
            Переранжированный список
        """
        # Извлекаем даты из chunk_text
        for metadata in metadata_list:
            chunk_date = self._extract_date_from_chunk(metadata['chunk_text'])
            metadata['extracted_date'] = chunk_date or '0000-00-00'  # Fallback для записей без даты

        # Сортируем: сначала по дате (DESC), затем по similarity (DESC)
        metadata_list.sort(
            key=lambda x: (x['extracted_date'], x['similarity']),
            reverse=True
        )

        logger.info(
            f"🔄 Re-ranked by date: "
            f"date_range={metadata_list[0]['extracted_date']} to {metadata_list[-1]['extracted_date']}"
        )

        return metadata_list

    async def search_relevant_chunks(
        self,
        query_text: str,
        cabinet_id: int,
        chunk_types: Optional[List[str]] = None,
        max_chunks: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Main method for finding relevant chunks.
        Combines all steps: query embedding, vector search, and metadata retrieval.
        """
        try:
            # Detect nm_id in the query text to filter more accurately
            nm_id_match = re.search(r"\b\d{6,}\b", query_text)
            nm_id_filter = int(nm_id_match.group()) if nm_id_match else None

            # Auto-detect chunk types from query keywords (if not explicitly provided)
            if chunk_types is None:
                detected_types = self._detect_chunk_types_from_query(query_text)
                effective_chunk_types = detected_types
            else:
                # Use explicitly provided chunk_types
                effective_chunk_types = chunk_types
                logger.info(f"📌 Using explicitly provided chunk_types: {chunk_types}")

            # Special case: nm_id detected but no chunk_types specified
            if nm_id_filter and effective_chunk_types is None:
                effective_chunk_types = ["stock", "product"]
                logger.info(f"🔍 nm_id detected, limiting to stock/product")

            # Detect temporal queries
            is_temporal = self._is_temporal_query(query_text)

            logger.info(
                f"🔍 Starting search for relevant chunks:\n"
                f"  📝 Query: '{query_text}'\n"
                f"  🏢 Cabinet ID: {cabinet_id}\n"
                f"  📦 Chunk types: {effective_chunk_types if effective_chunk_types else 'all'}\n"
                f"  🔢 Max results: {max_chunks}\n"
                f"  📊 Similarity threshold: {self.similarity_threshold}\n"
                f"  🔎 Source ID filter: {nm_id_filter if nm_id_filter else 'none'}\n"
                f"  ⏰ Temporal query: {is_temporal}"
            )

            # 1. Generate query embedding
            query_embedding = await self.generate_query_embedding(query_text)

            # 2. Vector Search (fetch more results for temporal queries to have better date coverage)
            search_limit = max_chunks * 3 if is_temporal else max_chunks
            search_results = self.search(
                query_embedding=query_embedding,
                cabinet_id=cabinet_id,
                chunk_types=effective_chunk_types,
                limit=search_limit,
                source_id=nm_id_filter
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

            # 3. Retrieve metadata
            db = RAGSessionLocal()
            try:
                embedding_ids = [r['embedding_id'] for r in search_results]
                logger.debug(f"🔍 Requesting metadata for {len(embedding_ids)} embedding IDs: {embedding_ids}")

                metadata_list = self.get_metadata_for_embeddings(embedding_ids, db)

                # Combine with similarity scores
                similarity_map = {r['embedding_id']: r['similarity'] for r in search_results}
                for metadata in metadata_list:
                    embedding_id = metadata['embedding_id']
                    metadata['similarity'] = similarity_map.get(embedding_id, 0.0)

                # 4. Sort: by date if temporal, otherwise by similarity
                if is_temporal:
                    logger.info("⏰ Temporal query detected - re-ranking by date")
                    metadata_list = self._rerank_by_date(metadata_list)
                    # Limit to max_chunks after re-ranking
                    metadata_list = metadata_list[:max_chunks]
                else:
                    # Sort by similarity (descending)
                    metadata_list.sort(key=lambda x: x['similarity'], reverse=True)

                logger.info(
                    f"✅ Final search results:\n"
                    f"  📊 Total found: {len(metadata_list)} chunks\n"
                    f"  📈 Similarity range: {metadata_list[0]['similarity']:.4f} - "
                    f"{metadata_list[-1]['similarity']:.4f}\n"
                    f"  📝 Chunk types: {', '.join(set(m['chunk_type'] for m in metadata_list))}"
                )

                # Detailed log for each result
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
            logger.error(f"❌ Error searching relevant chunks: {e}", exc_info=True)
            # Fallback to empty list on error
            return []
