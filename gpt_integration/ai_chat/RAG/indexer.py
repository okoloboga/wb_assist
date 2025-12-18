"""
RAG Indexer - сервис для индексации данных в векторную БД.

Модуль для извлечения данных из основной БД, создания текстовых чанков,
генерации эмбеддингов и сохранения их в векторную БД.
"""

import os
import asyncio
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from gpt_integration.comet_client import comet_client

from .database import RAGSessionLocal
from .models import RAGMetadata, RAGEmbedding, RAGIndexStatus
from ..tools.db_pool import get_asyncpg_pool

logger = logging.getLogger(__name__)


class RAGIndexer:
    """
    Класс для индексации данных из основной БД в векторную БД.
    
    Процесс индексации:
    1. Извлечение данных из основной БД
    2. Создание текстовых чанков
    3. Генерация эмбеддингов через OpenAI API
    4. Сохранение в векторную БД
    """
    
    def __init__(
        self,
        batch_size: Optional[int] = None
    ):
        """
        Initializes the indexer.
        The client for creating embeddings is now the centralized CometClient.
        """
        self.batch_size = batch_size or int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "100"))

    @staticmethod
    def calculate_chunk_hash(chunk_text: str) -> str:
        """
        Вычислить SHA256 hash от chunk_text.

        Используется для hash-based change detection:
        - Если hash не изменился, то chunk_text не изменился
        - Можно пропустить генерацию эмбеддинга (экономия API)

        Args:
            chunk_text: Текст чанка

        Returns:
            SHA256 hash в hex формате (64 символа)
        """
        return hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
        
    async def extract_data_from_main_db(self, cabinet_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Извлечение данных из основной БД для кабинета.
        
        Использует asyncpg для асинхронных запросов к основной БД.
        Подключается к основной БД через DATABASE_URL (не векторной).
        
        Args:
            cabinet_id: ID кабинета Wildberries
            
        Returns:
            Словарь с данными по типам:
            {
                'orders': [...],
                'products': [...],
                'stocks': [...],
                'reviews': [...],
                'sales': [...]
            }
        """
        # Получить пул подключений к основной БД
        pool = await get_asyncpg_pool()
        
        data = {
            'orders': [],
            'products': [],
            'stocks': [],
            'reviews': [],
            'sales': []
        }
        
        try:
            async with pool.acquire() as conn:
                # 1. Заказы
                orders = await conn.fetch("""
                    SELECT id, order_id, nm_id, name, size, price, total_price, 
                           order_date, status
                    FROM wb_orders
                    WHERE cabinet_id = $1
                      AND order_date >= NOW() - INTERVAL '90 days'
                    ORDER BY order_date DESC
                """, cabinet_id)
                data['orders'] = [dict(row) for row in orders]
                
                # 2. Товары
                products = await conn.fetch("""
                    SELECT nm_id, name, brand, category, price, rating, reviews_count
                    FROM wb_products
                    WHERE cabinet_id = $1
                      AND is_active = true
                """, cabinet_id)
                data['products'] = [dict(row) for row in products]
                
                # 3. Остатки
                stocks = await conn.fetch("""
                    SELECT nm_id, size, warehouse_name, quantity, name
                    FROM wb_stocks
                    WHERE cabinet_id = $1
                      AND quantity > 0
                """, cabinet_id)
                data['stocks'] = [dict(row) for row in stocks]
                
                # 4. Отзывы
                reviews = await conn.fetch("""
                    SELECT id, nm_id, rating, text, created_at
                    FROM wb_reviews
                    WHERE cabinet_id = $1
                      AND created_at >= NOW() - INTERVAL '90 days'
                    ORDER BY created_at DESC
                """, cabinet_id)
                data['reviews'] = [dict(row) for row in reviews]
                
                # 5. Продажи (JOIN с wb_products для получения полного названия товара)
                sales = await conn.fetch("""
                    SELECT s.id, s.nm_id, s.type, s.sale_date, s.amount,
                           COALESCE(p.name, s.product_name) as product_name
                    FROM wb_sales s
                    LEFT JOIN wb_products p ON s.nm_id = p.nm_id AND s.cabinet_id = p.cabinet_id
                    WHERE s.cabinet_id = $1
                      AND s.sale_date >= NOW() - INTERVAL '90 days'
                    ORDER BY s.sale_date DESC
                """, cabinet_id)
                data['sales'] = [dict(row) for row in sales]
                
        except Exception as e:
            logger.error(f"❌ Error extracting data for cabinet {cabinet_id}: {e}")
            raise
        
        logger.info(
            f"📊 Extracted data for cabinet {cabinet_id}: "
            f"orders={len(data['orders'])}, products={len(data['products'])}, "
            f"stocks={len(data['stocks'])}, reviews={len(data['reviews'])}, "
            f"sales={len(data['sales'])}"
        )
        
        return data

    async def extract_data_by_ids(
        self,
        cabinet_id: int,
        changed_ids: Dict[str, List[int]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Извлечение данных по списку ID (Event-driven indexing).

        Вместо запросов по timestamp, извлекаем только данные по переданным ID.
        Гораздо быстрее т.к. использует indexed lookup.

        Args:
            cabinet_id: ID кабинета
            changed_ids: Дельта изменений от WB sync
                {
                    "orders": [12345, 12346],
                    "products": [98765],
                    "stocks": [11111, 11112],
                    "reviews": [55555],
                    "sales": [77777]
                }

        Returns:
            Словарь с данными по типам (только для измененных записей)
        """
        pool = await get_asyncpg_pool()

        data = {
            'orders': [],
            'products': [],
            'stocks': [],
            'reviews': [],
            'sales': []
        }

        try:
            async with pool.acquire() as conn:
                # 1. Заказы
                if changed_ids.get('orders'):
                    orders = await conn.fetch("""
                        SELECT id, order_id, nm_id, name, size, price, total_price,
                               order_date, status
                        FROM wb_orders
                        WHERE cabinet_id = $1
                          AND id = ANY($2::bigint[])
                          AND order_date >= NOW() - INTERVAL '90 days'
                        ORDER BY order_date DESC
                    """, cabinet_id, changed_ids['orders'])
                    data['orders'] = [dict(row) for row in orders]

                # 2. Товары
                if changed_ids.get('products'):
                    products = await conn.fetch("""
                        SELECT nm_id, name, brand, category, price, rating, reviews_count
                        FROM wb_products
                        WHERE cabinet_id = $1
                          AND id = ANY($2::bigint[])
                          AND is_active = true
                    """, cabinet_id, changed_ids['products'])
                    data['products'] = [dict(row) for row in products]

                # 3. Остатки
                if changed_ids.get('stocks'):
                    stocks = await conn.fetch("""
                        SELECT nm_id, size, warehouse_name, quantity, name
                        FROM wb_stocks
                        WHERE cabinet_id = $1
                          AND id = ANY($2::bigint[])
                          AND quantity > 0
                    """, cabinet_id, changed_ids['stocks'])
                    data['stocks'] = [dict(row) for row in stocks]

                # 4. Отзывы
                if changed_ids.get('reviews'):
                    reviews = await conn.fetch("""
                        SELECT id, nm_id, rating, text, created_at
                        FROM wb_reviews
                        WHERE cabinet_id = $1
                          AND id = ANY($2::bigint[])
                          AND created_at >= NOW() - INTERVAL '90 days'
                        ORDER BY created_at DESC
                    """, cabinet_id, changed_ids['reviews'])
                    data['reviews'] = [dict(row) for row in reviews]

                # 5. Продажи (JOIN с wb_products для получения полного названия товара)
                if changed_ids.get('sales'):
                    sales = await conn.fetch("""
                        SELECT s.id, s.nm_id, s.type, s.sale_date, s.amount,
                               COALESCE(p.name, s.product_name) as product_name
                        FROM wb_sales s
                        LEFT JOIN wb_products p ON s.nm_id = p.nm_id AND s.cabinet_id = p.cabinet_id
                        WHERE s.cabinet_id = $1
                          AND s.id = ANY($2::bigint[])
                          AND s.sale_date >= NOW() - INTERVAL '90 days'
                        ORDER BY s.sale_date DESC
                    """, cabinet_id, changed_ids['sales'])
                    data['sales'] = [dict(row) for row in sales]

        except Exception as e:
            logger.error(f"Error extracting data by IDs for cabinet {cabinet_id}: {e}")
            raise

        logger.info(
            f"Extracted data by IDs for cabinet {cabinet_id}: "
            f"orders={len(data['orders'])}, products={len(data['products'])}, "
            f"stocks={len(data['stocks'])}, reviews={len(data['reviews'])}, "
            f"sales={len(data['sales'])}"
        )

        return data

    def _create_order_chunk(self, order: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, Any]:
        """Создание чанка для заказа."""
        name = product_name or order.get('name', 'Неизвестный товар')
        order_id = order.get('order_id', order.get('id', 'N/A'))
        order_date = order.get('order_date')
        if isinstance(order_date, datetime):
            order_date = order_date.strftime('%Y-%m-%d')
        elif order_date:
            order_date = str(order_date)
        else:
            order_date = 'N/A'
        
        price = order.get('price', 0) or 0
        if not isinstance(price, (int, float)):
            price = 0
        
        chunk_text = (
            f"Заказ #{order_id} от {order_date}: "
            f"товар '{name}' (nm_id: {order.get('nm_id', 'N/A')}), "
            f"размер {order.get('size', 'N/A')}, "
            f"цена {price:.2f}₽, "
            f"статус: {order.get('status', 'N/A')}"
        )
        
        return {
            'chunk_type': 'order',
            'source_table': 'wb_orders',
            'source_id': order.get('id'),
            'chunk_text': chunk_text
        }
    
    def _create_product_chunk(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Создание чанка для товара."""
        name = product.get('name', 'Неизвестный товар')
        brand = product.get('brand', 'Неизвестный бренд')
        category = product.get('category', 'Без категории')
        rating = product.get('rating', 0) or 0
        reviews_count = product.get('reviews_count', 0) or 0
        price = product.get('price', 0) or 0
        nm_id = product.get('nm_id', 'N/A')
        
        if not isinstance(rating, (int, float)):
            rating = 0
        if not isinstance(reviews_count, (int, float)):
            reviews_count = 0
        if not isinstance(price, (int, float)):
            price = 0
        
        # Улучшенное описание с большим количеством ключевых слов и синонимов
        # для лучшего поиска по различным формулировкам запросов
        chunk_text = (
            f"Товар продукт '{name}' артикул nm_id {nm_id}. "
            f"Бренд производитель: {brand}. "
            f"Категория тип товара: {category}. "
            f"Рейтинг оценка: {rating:.1f} из 5. "
            f"Количество отзывов: {reviews_count}. "
            f"Цена стоимость: {price:.2f} рублей. "
            f"Артикул nm_id: {nm_id}"
        )
        
        return {
            'chunk_type': 'product',
            'source_table': 'wb_products',
            'source_id': nm_id,
            'chunk_text': chunk_text
        }
    
    def _create_stock_chunk(self, stock: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, Any]:
        """Создание чанка для остатка с ключевыми словами для поиска."""
        # Приоритет: product_name из словаря -> name из БД -> fallback
        name = product_name or stock.get('name') or 'Неизвестный товар'
        warehouse = stock.get('warehouse_name', 'Неизвестный склад')
        quantity = stock.get('quantity', 0) or 0
        size = stock.get('size', 'N/A')
        nm_id = stock.get('nm_id', 'N/A')

        if not isinstance(quantity, (int, float)):
            quantity = 0

        # Определяем статус остатка и добавляем соответствующие ключевые слова
        status_keywords = []
        if quantity == 0:
            status_keywords = ["нулевой остаток", "товар закончился", "СРОЧНО пополнить", "критический остаток"]
        elif quantity <= 5:
            status_keywords = ["критический остаток", "очень мало", "срочно пополнить", "требует пополнения"]
        elif quantity <= 10:
            status_keywords = ["низкий остаток", "мало товара", "нужно пополнить", "скоро закончится"]
        elif quantity <= 20:
            status_keywords = ["невысокий остаток", "стоит пополнить", "запас на исходе"]
        else:
            status_keywords = ["достаточный остаток", "запас в норме"]

        # Формируем расширенный текст чанка с ключевыми словами
        chunk_text = (
            f"Остаток запас товара '{name}' артикул nm_id {nm_id}: "
            f"размер {size}, склад {warehouse}, количество {int(quantity)} штук. "
            f"Статус: {', '.join(status_keywords)}."
        )

        return {
            'chunk_type': 'stock',
            'source_table': 'wb_stocks',
            'source_id': nm_id,
            'chunk_text': chunk_text
        }
    
    def _create_review_chunk(self, review: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, Any]:
        """Создание чанка для отзыва."""
        name = product_name or 'Неизвестный товар'
        rating = review.get('rating', 0) or 0
        text = review.get('text', 'Без текста') or 'Без текста'
        created_at = review.get('created_at')
        
        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d')
        elif created_at:
            created_at = str(created_at)
        else:
            created_at = 'N/A'
        
        # Ограничение длины текста отзыва (чтобы чанк не был слишком длинным)
        if len(text) > 200:
            text = text[:200] + '...'
        
        if not isinstance(rating, (int, float)):
            rating = 0
        
        chunk_text = (
            f"Отзыв на товар '{name}' (nm_id: {review.get('nm_id', 'N/A')}): "
            f"рейтинг {int(rating)}⭐, дата: {created_at}, текст: '{text}'"
        )
        
        return {
            'chunk_type': 'review',
            'source_table': 'wb_reviews',
            'source_id': review.get('id'),
            'chunk_text': chunk_text
        }
    
    def _create_sale_chunk(self, sale: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, Any]:
        """Создание чанка для продажи."""
        # Приоритет: product_name из словаря -> product_name из БД -> fallback
        name = product_name or sale.get('product_name') or 'Неизвестный товар'
        sale_type = sale.get('type', 'N/A')
        sale_date = sale.get('sale_date')

        if isinstance(sale_date, datetime):
            sale_date = sale_date.strftime('%Y-%m-%d')
        elif sale_date:
            sale_date = str(sale_date)
        else:
            sale_date = 'N/A'

        amount = sale.get('amount', 0) or 0
        if not isinstance(amount, (int, float)):
            amount = 0

        # Определяем метку типа продажи (выделяем ВЫКУП vs ВОЗВРАТ)
        if sale_type == "buyout":
            type_label = "ВЫКУП"
        elif sale_type == "return":
            type_label = "ВОЗВРАТ"
        else:
            type_label = sale_type.upper()

        # Новый формат: тип и дата вначале для лучшей семантической дифференциации
        chunk_text = (
            f"{type_label} от {sale_date}: товар '{name}' (nm_id: {sale.get('nm_id', 'N/A')}), "
            f"сумма: {amount:.2f}₽"
        )

        return {
            'chunk_type': 'sale',
            'source_table': 'wb_sales',
            'source_id': sale.get('id'),
            'chunk_text': chunk_text
        }
    
    def create_chunks(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Создание текстовых чанков из структурированных данных.
        
        Создает словарь названий товаров для использования в других чанках.
        
        Args:
            data: Словарь с данными по типам
            
        Returns:
            Список словарей с чанками:
            [
                {
                    'chunk_type': 'order',
                    'source_table': 'wb_orders',
                    'source_id': 123,
                    'chunk_text': 'Заказ #12345...'
                },
                ...
            ]
        """
        chunks = []
        
        # Создать словарь названий товаров (nm_id -> name)
        product_names = {}
        for product in data.get('products', []):
            nm_id = product.get('nm_id')
            if nm_id:
                product_names[nm_id] = product.get('name', 'Неизвестный товар')
        
        # Создать чанки для каждого типа данных
        for order in data.get('orders', []):
            nm_id = order.get('nm_id')
            product_name = product_names.get(nm_id) if nm_id else None
            chunks.append(self._create_order_chunk(order, product_name))
        
        for product in data.get('products', []):
            chunks.append(self._create_product_chunk(product))
        
        for stock in data.get('stocks', []):
            nm_id = stock.get('nm_id')
            product_name = product_names.get(nm_id) if nm_id else None
            chunks.append(self._create_stock_chunk(stock, product_name))
        
        for review in data.get('reviews', []):
            nm_id = review.get('nm_id')
            product_name = product_names.get(nm_id) if nm_id else None
            chunks.append(self._create_review_chunk(review, product_name))
        
        for sale in data.get('sales', []):
            nm_id = sale.get('nm_id')
            product_name = product_names.get(nm_id) if nm_id else None
            chunks.append(self._create_sale_chunk(sale, product_name))
        
        logger.info(f"📝 Created {len(chunks)} chunks from data")
        
        return chunks
    
    async def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text chunks using CometAPI.
        Uses batch processing and includes retry logic for each batch.
        """
        import time

        if not chunks:
            return []

        all_embeddings = []
        total_chunks = len(chunks)
        failed_batches = []

        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            logger.info(
                f"🔄 Generating embeddings via CometAPI: batch {batch_num}/{total_batches} "
                f"({len(batch)} chunks)"
            )

            max_retries = 5
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    response = await comet_client.create_embeddings(
                        texts=batch
                    )
                    
                    batch_embeddings = [item['embedding'] for item in response['data']]
                    all_embeddings.extend(batch_embeddings)

                    usage = response.get("usage")
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens")
                        total_tokens = usage.get("total_tokens")
                        logger.info(
                            f"🧮 Embedding tokens (batch {batch_num}): "
                            f"prompt={prompt_tokens}, total={total_tokens}"
                        )

                    logger.info(
                        f"✅ Batch {batch_num} processed: {len(batch_embeddings)} embeddings"
                    )
                    break

                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"⚠️ Batch {batch_num} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"❌ Batch {batch_num} failed after {max_retries} attempts: {e}. "
                            f"Skipping batch and continuing..."
                        )
                        failed_batches.append({
                            'batch_num': batch_num,
                            'start_idx': i,
                            'end_idx': i + len(batch),
                            'error': str(e)
                        })
                        break

        if failed_batches:
            logger.warning(
                f"⚠️ Indexing completed with errors: {len(failed_batches)} batches failed. "
                f"Successfully processed: {len(all_embeddings)}/{total_chunks} chunks"
            )
            logger.warning(f"Failed batches info: {failed_batches}")
        else:
            logger.info(f"✅ Generated {len(all_embeddings)} embeddings total")

        return all_embeddings
    
    def save_to_vector_db(
        self,
        embeddings: List[List[float]],
        chunks_metadata: List[Dict[str, Any]],
        cabinet_id: int,
        db: Session
    ) -> int:
        """
        Сохранение эмбеддингов и метаданных в векторную БД.

        Обрабатывает дубликаты: обновляет существующие записи.
        Обрабатывает частичную индексацию: сохраняет только успешные чанки.

        ВАЖНО: Использует batch commits (каждые 100 чанков) для предотвращения
        длинных транзакций, которые блокируют доступ к RAG search.

        Args:
            embeddings: Список векторов
            chunks_metadata: Список метаданных для каждого чанка
            cabinet_id: ID кабинета
            db: Сессия БД

        Returns:
            Количество сохраненных записей
        """
        if len(embeddings) != len(chunks_metadata):
            logger.warning(
                f"⚠️ Несовпадение длин: эмбеддингов ({len(embeddings)}) != "
                f"метаданных ({len(chunks_metadata)}). "
                f"Сохраняем только успешно проиндексированные чанки."
            )
            # Сохраняем только те чанки, для которых есть эмбеддинги
            min_length = min(len(embeddings), len(chunks_metadata))
            embeddings = embeddings[:min_length]
            chunks_metadata = chunks_metadata[:min_length]
            logger.info(f"📊 Будет сохранено {min_length} чанков")

        saved_count = 0
        batch_size = 100  # Коммитим каждые 100 чанков для предотвращения длинных транзакций

        try:
            for idx, (embedding, chunk_meta) in enumerate(zip(embeddings, chunks_metadata)):
                # Проверить, существует ли запись
                existing_metadata = db.query(RAGMetadata).filter(
                    RAGMetadata.cabinet_id == cabinet_id,
                    RAGMetadata.source_table == chunk_meta['source_table'],
                    RAGMetadata.source_id == chunk_meta['source_id']
                ).first()

                if existing_metadata:
                    # Обновить существующую запись
                    existing_metadata.chunk_text = chunk_meta['chunk_text']
                    existing_metadata.chunk_type = chunk_meta['chunk_type']
                    existing_metadata.chunk_hash = self.calculate_chunk_hash(chunk_meta['chunk_text'])
                    from datetime import timezone
                    existing_metadata.updated_at = datetime.now(timezone.utc)

                    # Обновить embedding
                    existing_embedding = db.query(RAGEmbedding).filter(
                        RAGEmbedding.metadata_id == existing_metadata.id
                    ).first()

                    if existing_embedding:
                        existing_embedding.embedding = embedding
                        from datetime import timezone
                        existing_embedding.updated_at = datetime.now(timezone.utc)
                    else:
                        # Создать новый embedding (если по какой-то причине его нет)
                        new_embedding = RAGEmbedding(
                            embedding=embedding,
                            metadata_id=existing_metadata.id
                        )
                        db.add(new_embedding)

                else:
                    # Создать новую запись
                    new_metadata = RAGMetadata(
                        cabinet_id=cabinet_id,
                        source_table=chunk_meta['source_table'],
                        source_id=chunk_meta['source_id'],
                        chunk_type=chunk_meta['chunk_type'],
                        chunk_text=chunk_meta['chunk_text'],
                        chunk_hash=self.calculate_chunk_hash(chunk_meta['chunk_text'])
                    )
                    db.add(new_metadata)
                    db.flush()  # Получить ID новой записи

                    new_embedding = RAGEmbedding(
                        embedding=embedding,
                        metadata_id=new_metadata.id
                    )
                    db.add(new_embedding)

                saved_count += 1

                # Batch commit: коммитим каждые batch_size чанков
                # Это предотвращает длинные транзакции, которые блокируют RAG search
                if (idx + 1) % batch_size == 0:
                    db.commit()
                    logger.debug(f"📦 Batch committed: {saved_count}/{len(embeddings)} chunks saved")

            # Финальный коммит для оставшихся записей
            db.commit()
            logger.info(f"✅ Saved {saved_count} records to vector DB (batch size: {batch_size})")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving to vector DB: {e}")
            raise

        return saved_count
    
    async def index_cabinet(
        self,
        cabinet_id: int,
        full_rebuild: bool = False,
        changed_ids: Optional[Dict[str, List[int]]] = None
    ) -> Dict[str, Any]:
        """
        Главный метод индексации кабинета.

        Поддерживает два режима:
        1. Event-driven (changed_ids): Индексация только измененных записей
        2. Full rebuild: Полная переиндексация с очисткой устаревших данных

        Args:
            cabinet_id: ID кабинета
            full_rebuild: Полная переиндексация (weekly cleanup)
            changed_ids: Дельта изменений от WB sync (Event-driven)
                {
                    "orders": [12345, 12346],
                    "products": [98765],
                    "stocks": [11111],
                    "reviews": [55555],
                    "sales": [77777]
                }

        Returns:
            Словарь с результатами:
            {
                'success': True/False,
                'cabinet_id': int,
                'indexing_mode': 'incremental' | 'full_rebuild',
                'total_chunks': int,
                'metrics': {...},
                'errors': List[str]
            }
        """
        # Определить режим индексации
        indexing_mode = 'full_rebuild' if full_rebuild else 'incremental'

        result = {
            'success': False,
            'cabinet_id': cabinet_id,
            'indexing_mode': indexing_mode,
            'total_chunks': 0,
            'metrics': {
                'new_chunks': 0,
                'updated_chunks': 0,
                'skipped_chunks': 0,
                'deleted_chunks': 0,
                'embeddings_generated': 0
            },
            'errors': []
        }

        # Получить сессию БД
        db = RAGSessionLocal()
        index_status = None

        try:
            # 1. Атомарная проверка и установка статуса с SELECT FOR UPDATE
            # Это предотвращает race condition между параллельными задачами
            from sqlalchemy import text
            from datetime import timedelta, timezone

            # Начинаем транзакцию с блокировкой
            index_status = db.query(RAGIndexStatus).filter(
                RAGIndexStatus.cabinet_id == cabinet_id
            ).with_for_update(nowait=False).first()

            # Проверяем статус индексации
            if index_status:
                current_status = index_status.indexing_status

                # Проверка 1: Индексация уже выполняется
                if current_status == 'in_progress':
                    # Проверяем, не зависла ли задача (timeout 30 минут)
                    if index_status.updated_at:
                        # Используем UTC aware datetime для корректного сравнения
                        now_utc = datetime.now(timezone.utc)
                        updated_at = index_status.updated_at

                        # Если updated_at naive, делаем его aware (UTC)
                        if updated_at.tzinfo is None:
                            updated_at = updated_at.replace(tzinfo=timezone.utc)

                        time_since_update = now_utc - updated_at

                        if time_since_update > timedelta(minutes=30):
                            logger.warning(
                                f"⏰ Индексация кабинета {cabinet_id} зависла "
                                f"(обновление {time_since_update.total_seconds():.0f} секунд назад). "
                                f"Сбрасываем статус и перезапускаем."
                            )
                            # Сбрасываем зависший статус
                            index_status.indexing_status = 'failed'
                            db.commit()
                        else:
                            logger.warning(
                                f"Индексация кабинета {cabinet_id} уже выполняется "
                                f"(обновление {time_since_update.total_seconds():.0f} секунд назад). Пропуск."
                            )
                            result['errors'].append("Индексация уже выполняется")
                            db.rollback()  # Отменяем блокировку
                            return result

                # Проверка 2: Предыдущая индексация провалилась - разрешаем повторный запуск
                if current_status == 'failed':
                    logger.info(
                        f"⚠️ Предыдущая индексация кабинета {cabinet_id} провалилась. "
                        f"Перезапускаем индексацию."
                    )

            # 2. Установить статус 'in_progress' (атомарно)
            if not index_status:
                index_status = RAGIndexStatus(
                    cabinet_id=cabinet_id,
                    indexing_status='in_progress'
                )
                db.add(index_status)
            else:
                index_status.indexing_status = 'in_progress'
                # Используем UTC aware datetime
                index_status.updated_at = datetime.now(timezone.utc)

            db.commit()  # Commit и освобождение блокировки

            logger.info(
                f"Starting {indexing_mode} indexing for cabinet {cabinet_id}"
                + (f" with {sum(len(ids) for ids in changed_ids.values())} changed IDs" if changed_ids else "")
            )

            # 3. Извлечение данных
            try:
                if changed_ids and not full_rebuild:
                    # Event-driven: извлечь только измененные данные
                    data = await self.extract_data_by_ids(cabinet_id, changed_ids)
                else:
                    # Full rebuild: извлечь все данные
                    data = await self.extract_data_from_main_db(cabinet_id)
            except Exception as e:
                logger.error(f"Error extracting data: {e}")
                result['errors'].append(f"Извлечение данных: {str(e)}")
                raise
            
            # 4. Создание чанков
            try:
                chunks_metadata = self.create_chunks(data)
            except Exception as e:
                logger.error(f"❌ Error creating chunks: {e}")
                result['errors'].append(f"Создание чанков: {str(e)}")
                raise
            
            if not chunks_metadata:
                logger.warning(f"⚠️ No data to index for cabinet {cabinet_id}")
                index_status.indexing_status = 'completed'
                index_status.total_chunks = 0
                from datetime import timezone
                index_status.last_indexed_at = datetime.now(timezone.utc)
                db.commit()
                result['success'] = True
                return result
            
            # 5. Генерация эмбеддингов
            try:
                chunk_texts = [chunk['chunk_text'] for chunk in chunks_metadata]
                embeddings = await self.generate_embeddings(chunk_texts)
            except Exception as e:
                logger.error(f"❌ Error generating embeddings: {e}")
                result['errors'].append(f"Генерация эмбеддингов: {str(e)}")
                raise
            
            # 6. Сохранение в БД
            try:
                saved_count = self.save_to_vector_db(
                    embeddings=embeddings,
                    chunks_metadata=chunks_metadata,
                    cabinet_id=cabinet_id,
                    db=db
                )
            except Exception as e:
                logger.error(f"❌ Error saving to DB: {e}")
                result['errors'].append(f"Сохранение в БД: {str(e)}")
                raise
            
            # 7. Обновить статус 'completed'
            from datetime import timezone
            index_status.indexing_status = 'completed'
            index_status.total_chunks = saved_count
            index_status.updated_at = datetime.now(timezone.utc)

            # Обновить timestamps в зависимости от режима
            if full_rebuild:
                index_status.last_indexed_at = datetime.now(timezone.utc)
                index_status.last_incremental_at = datetime.now(timezone.utc)  # Full rebuild обновляет оба
            else:
                index_status.last_incremental_at = datetime.now(timezone.utc)

            db.commit()

            result['success'] = True
            result['total_chunks'] = saved_count
            result['metrics']['embeddings_generated'] = len(embeddings)

            logger.info(
                f"{indexing_mode.capitalize()} indexing completed for cabinet {cabinet_id}: "
                f"{saved_count} chunks indexed"
            )
            
        except Exception as e:
            # Установить статус 'failed'
            if index_status:
                from datetime import timezone
                index_status.indexing_status = 'failed'
                index_status.updated_at = datetime.now(timezone.utc)
                db.commit()

            logger.error(f"❌ Error indexing cabinet {cabinet_id}: {e}")
            result['errors'].append(str(e))
            
        finally:
            db.close()
        
        return result
