"""
RAG Indexer - сервис для индексации данных в векторную БД.

Модуль для извлечения данных из основной БД, создания текстовых чанков,
генерации эмбеддингов и сохранения их в векторную БД.
"""

import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI

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
        openai_client: Optional[OpenAI] = None,
        embeddings_model: Optional[str] = None,
        batch_size: Optional[int] = None
    ):
        """
        Инициализация индексера.
        
        Args:
            openai_client: Клиент OpenAI (если None, создается новый)
            embeddings_model: Модель для генерации эмбеддингов (из env или default)
            batch_size: Размер батча для генерации эмбеддингов (из env или default)
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
                
                # 5. Продажи
                sales = await conn.fetch("""
                    SELECT id, nm_id, type, sale_date, amount, product_name
                    FROM wb_sales
                    WHERE cabinet_id = $1
                      AND sale_date >= NOW() - INTERVAL '90 days'
                    ORDER BY sale_date DESC
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
        name = product_name or 'Неизвестный товар'
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
        name = product_name or 'Неизвестный товар'
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
        
        chunk_text = (
            f"Продажа товара '{name}' (nm_id: {sale.get('nm_id', 'N/A')}) от {sale_date}: "
            f"тип - {sale_type}, сумма: {amount:.2f}₽"
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
    
    def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов для списка текстовых чанков.

        Использует batch processing для экономии запросов к API.
        С retry логикой для каждого батча отдельно.

        Args:
            chunks: Список текстовых чанков

        Returns:
            Список векторов (каждый вектор - список из 1536 float)
        """
        import time

        if not chunks:
            return []

        all_embeddings = []
        total_chunks = len(chunks)
        failed_batches = []

        # Разбить на батчи
        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            logger.info(
                f"🔄 Генерация эмбеддингов: батч {batch_num}/{total_batches} "
                f"({len(batch)} чанков)"
            )

            # Retry логика для текущего батча
            max_retries = 5
            retry_delay = 2  # Начальная задержка в секундах

            for attempt in range(max_retries):
                try:
                    # Вызов OpenAI Embeddings API
                    response = self.openai_client.embeddings.create(
                        model=self.embeddings_model,
                        input=batch
                    )

                    # Извлечь векторы из ответа
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)

                    usage = getattr(response, "usage", None)
                    if usage:
                        prompt_tokens = getattr(usage, "prompt_tokens", None)
                        total_tokens = getattr(usage, "total_tokens", None)
                        logger.info(
                            f"🧮 Embedding tokens (batch {batch_num}): "
                            f"prompt={prompt_tokens}, total={total_tokens}"
                        )

                    logger.info(
                        f"✅ Батч {batch_num} обработан: {len(batch_embeddings)} эмбеддингов"
                    )
                    break  # Успешно - выходим из retry loop

                except Exception as e:
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"⚠️ Батч {batch_num} failed (попытка {attempt + 1}/{max_retries}): {e}. "
                            f"Повтор через {wait_time}с..."
                        )
                        time.sleep(wait_time)
                    else:
                        # Все попытки исчерпаны - пропускаем батч
                        logger.error(
                            f"❌ Батч {batch_num} failed после {max_retries} попыток: {e}. "
                            f"Пропускаем батч и продолжаем..."
                        )
                        failed_batches.append({
                            'batch_num': batch_num,
                            'start_idx': i,
                            'end_idx': i + len(batch),
                            'error': str(e)
                        })
                        # Добавляем пустые эмбеддинги для сохранения индексов
                        # (или можно пропустить - зависит от стратегии)
                        break

        if failed_batches:
            logger.warning(
                f"⚠️ Индексация завершена с ошибками: {len(failed_batches)} батчей пропущено. "
                f"Успешно: {len(all_embeddings)}/{total_chunks} чанков"
            )
            logger.warning(f"Пропущенные батчи: {failed_batches}")
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
        
        try:
            for embedding, chunk_meta in zip(embeddings, chunks_metadata):
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
                    existing_metadata.updated_at = datetime.now()

                    # Обновить embedding
                    existing_embedding = db.query(RAGEmbedding).filter(
                        RAGEmbedding.metadata_id == existing_metadata.id
                    ).first()

                    if existing_embedding:
                        existing_embedding.embedding = embedding
                        existing_embedding.updated_at = datetime.now()
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
            
            # Коммит всех изменений
            db.commit()
            logger.info(f"✅ Saved {saved_count} records to vector DB")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving to vector DB: {e}")
            raise
        
        return saved_count
    
    async def index_cabinet(self, cabinet_id: int) -> Dict[str, Any]:
        """
        Главный метод индексации кабинета.
        
        Выполняет полный цикл индексации с управлением статусом:
        1. Проверка статуса
        2. Извлечение данных
        3. Создание чанков
        4. Генерация эмбеддингов
        5. Сохранение в БД
        
        Args:
            cabinet_id: ID кабинета
            
        Returns:
            Словарь с результатами:
            {
                'success': True/False,
                'cabinet_id': int,
                'total_chunks': int,
                'errors': List[str]
            }
        """
        result = {
            'success': False,
            'cabinet_id': cabinet_id,
            'total_chunks': 0,
            'errors': []
        }
        
        # Получить сессию БД
        db = RAGSessionLocal()
        index_status = None
        
        try:
            # 1. Проверить статус индексации
            index_status = db.query(RAGIndexStatus).filter(
                RAGIndexStatus.cabinet_id == cabinet_id
            ).first()
            
            if index_status and index_status.indexing_status == 'in_progress':
                logger.warning(
                    f"⚠️ Индексация кабинета {cabinet_id} уже выполняется. Пропуск."
                )
                result['errors'].append("Индексация уже выполняется")
                return result
            
            # 2. Установить статус 'in_progress'
            if not index_status:
                index_status = RAGIndexStatus(
                    cabinet_id=cabinet_id,
                    indexing_status='in_progress'
                )
                db.add(index_status)
            else:
                index_status.indexing_status = 'in_progress'
                index_status.updated_at = datetime.now()
            
            db.commit()
            
            logger.info(f"🚀 Starting indexing for cabinet {cabinet_id}")
            
            # 3. Извлечение данных
            try:
                data = await self.extract_data_from_main_db(cabinet_id)
            except Exception as e:
                logger.error(f"❌ Error extracting data: {e}")
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
                index_status.last_indexed_at = datetime.now()
                db.commit()
                result['success'] = True
                return result
            
            # 5. Генерация эмбеддингов
            try:
                chunk_texts = [chunk['chunk_text'] for chunk in chunks_metadata]
                embeddings = self.generate_embeddings(chunk_texts)
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
            index_status.indexing_status = 'completed'
            index_status.last_indexed_at = datetime.now()
            index_status.total_chunks = saved_count
            index_status.updated_at = datetime.now()
            db.commit()
            
            result['success'] = True
            result['total_chunks'] = saved_count
            
            logger.info(
                f"✅ Индексация кабинета {cabinet_id} завершена: "
                f"{saved_count} чанков проиндексировано"
            )
            
        except Exception as e:
            # Установить статус 'failed'
            if index_status:
                index_status.indexing_status = 'failed'
                index_status.updated_at = datetime.now()
                db.commit()
            
            logger.error(f"❌ Error indexing cabinet {cabinet_id}: {e}")
            result['errors'].append(str(e))
            
        finally:
            db.close()
        
        return result
