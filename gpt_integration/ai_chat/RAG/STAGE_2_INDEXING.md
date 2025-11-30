# Этап 2: Модуль индексации данных

## 📋 Обзор этапа

**Цель:** Реализовать сервис для индексации данных из основной БД (wb_orders, wb_products, wb_stocks, wb_reviews, wb_sales) в векторную БД.

**Длительность:** 3-4 дня

**Зависимости:** Этап 1 (инфраструктура должна быть готова)

**Результат:** Модуль, который может извлекать данные из основной БД, создавать текстовые чанки, генерировать эмбеддинги и сохранять их в векторную БД.

---

## 🎯 Задачи этапа

### Задача 2.1: Создание структуры модуля индексации

#### Описание
Создание основного класса `RAGIndexer` с методами для полного цикла индексации данных.

#### Файл: `gpt_integration/ai_chat/rag/indexer.py`

**Структура класса:**

```python
"""
RAG Indexer - сервис для индексации данных в векторную БД.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from openai import OpenAI

from .database import get_rag_db, RAGSessionLocal
from .models import RAGMetadata, RAGEmbedding, RAGIndexStatus
from ..tools.db_pool import get_asyncpg_pool  # Для подключения к основной БД

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
        embeddings_model: str = "text-embedding-3-small",
        batch_size: int = 100
    ):
        """
        Инициализация индексера.
        
        Args:
            openai_client: Клиент OpenAI (если None, создается новый)
            embeddings_model: Модель для генерации эмбеддингов
            batch_size: Размер батча для генерации эмбеддингов
        """
        self.openai_client = openai_client or OpenAI()
        self.embeddings_model = embeddings_model
        self.batch_size = batch_size
        
    def extract_data_from_main_db(self, cabinet_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Извлечение данных из основной БД для кабинета.
        
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
        # Реализация в следующей задаче
        pass
    
    def create_chunks(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        """
        Создание текстовых чанков из структурированных данных.
        
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
        # Реализация в задаче 2.3
        pass
    
    def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Генерация эмбеддингов для списка текстовых чанков.
        
        Args:
            chunks: Список текстовых чанков
            
        Returns:
            Список векторов (список списков float)
        """
        # Реализация в задаче 2.4
        pass
    
    def save_to_vector_db(
        self,
        embeddings: List[List[float]],
        chunks_metadata: List[Dict[str, Any]],
        cabinet_id: int,
        db: Session
    ) -> int:
        """
        Сохранение эмбеддингов и метаданных в векторную БД.
        
        Args:
            embeddings: Список векторов
            chunks_metadata: Список метаданных для каждого чанка
            cabinet_id: ID кабинета
            db: Сессия БД
            
        Returns:
            Количество сохраненных записей
        """
        # Реализация в задаче 2.5
        pass
    
    def index_cabinet(self, cabinet_id: int) -> Dict[str, Any]:
        """
        Главный метод индексации кабинета.
        
        Выполняет полный цикл индексации:
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
                'total_chunks': 100,
                'errors': [...]
            }
        """
        # Реализация в задаче 2.6
        pass
```

#### Действия

1. **Создать файл `gpt_integration/ai_chat/rag/indexer.py`**
   - Создать класс `RAGIndexer`
   - Определить все методы (пока с `pass`)
   - Добавить docstrings и type hints

2. **Добавить импорты**
   - SQLAlchemy для работы с БД
   - OpenAI для генерации эмбеддингов
   - Логирование

3. **Настроить логирование**
   - Использовать модуль `logging`
   - Логировать все этапы индексации

#### Критерии готовности
- ✅ Файл `indexer.py` создан
- ✅ Класс `RAGIndexer` определен
- ✅ Все методы определены (пока без реализации)
- ✅ Импорты добавлены

---

### Задача 2.2: Извлечение данных из основной БД

#### Описание
Реализация метода `extract_data_from_main_db()`, который извлекает данные из всех таблиц Wildberries для конкретного кабинета.

#### Реализация метода

**Подключение к основной БД:**
- Использовать существующий пул соединений из `tools.db_pool`
- Или создать новое подключение через SQLAlchemy

**SQL запросы для каждой таблицы:**

**1. wb_orders:**
```sql
SELECT 
    id,
    order_id,
    nm_id,
    name,
    size,
    price,
    total_price,
    order_date,
    status
FROM wb_orders
WHERE cabinet_id = :cabinet_id
  AND order_date >= NOW() - INTERVAL '90 days'
ORDER BY order_date DESC;
```

**2. wb_products:**
```sql
SELECT 
    nm_id,
    name,
    brand,
    category,
    price,
    rating,
    reviews_count
FROM wb_products
WHERE cabinet_id = :cabinet_id
  AND is_active = true;
```

**3. wb_stocks:**
```sql
SELECT 
    nm_id,
    size,
    warehouse_name,
    quantity
FROM wb_stocks
WHERE cabinet_id = :cabinet_id
  AND quantity > 0;
```

**4. wb_reviews:**
```sql
SELECT 
    id,
    nm_id,
    rating,
    text,
    created_at
FROM wb_reviews
WHERE cabinet_id = :cabinet_id
  AND created_at >= NOW() - INTERVAL '90 days'
ORDER BY created_at DESC;
```

**5. wb_sales:**
```sql
SELECT 
    id,
    nm_id,
    type,
    sale_date,
    price
FROM wb_sales
WHERE cabinet_id = :cabinet_id
  AND sale_date >= NOW() - INTERVAL '90 days'
ORDER BY sale_date DESC;
```

#### Реализация

```python
async def extract_data_from_main_db(self, cabinet_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Извлечение данных из основной БД для кабинета.
    
    Использует asyncpg для асинхронных запросов к основной БД.
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
                SELECT nm_id, size, warehouse_name, quantity
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
                SELECT id, nm_id, type, sale_date, price
                FROM wb_sales
                WHERE cabinet_id = $1
                  AND sale_date >= NOW() - INTERVAL '90 days'
                ORDER BY sale_date DESC
            """, cabinet_id)
            data['sales'] = [dict(row) for row in sales]
            
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных для кабинета {cabinet_id}: {e}")
        raise
    
    logger.info(
        f"Извлечено данных для кабинета {cabinet_id}: "
        f"orders={len(data['orders'])}, products={len(data['products'])}, "
        f"stocks={len(data['stocks'])}, reviews={len(data['reviews'])}, "
        f"sales={len(data['sales'])}"
    )
    
    return data
```

**Важно:** Метод должен быть асинхронным, так как использует asyncpg.

#### Действия

1. **Реализовать метод `extract_data_from_main_db()`**
   - Использовать asyncpg для запросов
   - Выполнить все 5 SQL запросов
   - Обработать ошибки

2. **Добавить логирование**
   - Логировать количество извлеченных записей
   - Логировать ошибки

3. **Протестировать**
   - Вызвать метод для тестового кабинета
   - Проверить, что данные извлекаются корректно

#### Критерии готовности
- ✅ Метод реализован
- ✅ Все 5 таблиц обрабатываются
- ✅ Данные извлекаются корректно
- ✅ Ошибки обрабатываются
- ✅ Логирование работает

---

### Задача 2.3: Создание текстовых чанков

#### Описание
Реализация функций для преобразования структурированных данных в текстовые чанки. Каждый тип данных имеет свой формат.

#### Форматы чанков

**1. Заказ (order):**
```
Заказ #{order_id} от {order_date}: товар '{name}' (nm_id: {nm_id}), размер {size}, цена {price}₽, статус: {status}
```

**2. Товар (product):**
```
Товар '{name}' (nm_id: {nm_id}), бренд: {brand}, категория: {category}, рейтинг: {rating}, отзывов: {reviews_count}, цена: {price}₽
```

**3. Остаток (stock):**
```
Остаток товара '{name}' (nm_id: {nm_id}), размер {size}, склад: {warehouse_name}, количество: {quantity} шт
```

**4. Отзыв (review):**
```
Отзыв на товар '{name}' (nm_id: {nm_id}): рейтинг {rating}⭐, дата: {created_at}, текст: '{text}'
```

**5. Продажа (sale):**
```
Продажа товара '{name}' (nm_id: {nm_id}) от {sale_date}: тип - {type}, сумма: {price}₽
```

#### Реализация

```python
def _create_order_chunk(self, order: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, str]:
    """Создание чанка для заказа."""
    name = product_name or order.get('name', 'Неизвестный товар')
    order_id = order.get('order_id', order.get('id', 'N/A'))
    order_date = order.get('order_date')
    if isinstance(order_date, datetime):
        order_date = order_date.strftime('%Y-%m-%d')
    
    chunk_text = (
        f"Заказ #{order_id} от {order_date}: "
        f"товар '{name}' (nm_id: {order.get('nm_id', 'N/A')}), "
        f"размер {order.get('size', 'N/A')}, "
        f"цена {order.get('price', 0):.2f}₽, "
        f"статус: {order.get('status', 'N/A')}"
    )
    
    return {
        'chunk_type': 'order',
        'source_table': 'wb_orders',
        'source_id': order.get('id'),
        'chunk_text': chunk_text
    }


def _create_product_chunk(self, product: Dict[str, Any]) -> Dict[str, str]:
    """Создание чанка для товара."""
    name = product.get('name', 'Неизвестный товар')
    brand = product.get('brand', 'Неизвестный бренд')
    category = product.get('category', 'Без категории')
    rating = product.get('rating', 0)
    reviews_count = product.get('reviews_count', 0)
    price = product.get('price', 0)
    
    chunk_text = (
        f"Товар '{name}' (nm_id: {product.get('nm_id', 'N/A')}), "
        f"бренд: {brand}, категория: {category}, "
        f"рейтинг: {rating:.1f}, отзывов: {reviews_count}, "
        f"цена: {price:.2f}₽"
    )
    
    return {
        'chunk_type': 'product',
        'source_table': 'wb_products',
        'source_id': product.get('nm_id'),
        'chunk_text': chunk_text
    }


def _create_stock_chunk(self, stock: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, str]:
    """Создание чанка для остатка."""
    name = product_name or 'Неизвестный товар'
    warehouse = stock.get('warehouse_name', 'Неизвестный склад')
    quantity = stock.get('quantity', 0)
    size = stock.get('size', 'N/A')
    
    chunk_text = (
        f"Остаток товара '{name}' (nm_id: {stock.get('nm_id', 'N/A')}), "
        f"размер {size}, склад: {warehouse}, количество: {quantity} шт"
    )
    
    return {
        'chunk_type': 'stock',
        'source_table': 'wb_stocks',
        'source_id': stock.get('nm_id'),  # Используем nm_id как идентификатор
        'chunk_text': chunk_text
    }


def _create_review_chunk(self, review: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, str]:
    """Создание чанка для отзыва."""
    name = product_name or 'Неизвестный товар'
    rating = review.get('rating', 0)
    text = review.get('text', 'Без текста')
    created_at = review.get('created_at')
    if isinstance(created_at, datetime):
        created_at = created_at.strftime('%Y-%m-%d')
    
    # Ограничение длины текста отзыва (чтобы чанк не был слишком длинным)
    if len(text) > 200:
        text = text[:200] + '...'
    
    chunk_text = (
        f"Отзыв на товар '{name}' (nm_id: {review.get('nm_id', 'N/A')}): "
        f"рейтинг {rating}⭐, дата: {created_at}, текст: '{text}'"
    )
    
    return {
        'chunk_type': 'review',
        'source_table': 'wb_reviews',
        'source_id': review.get('id'),
        'chunk_text': chunk_text
    }


def _create_sale_chunk(self, sale: Dict[str, Any], product_name: Optional[str] = None) -> Dict[str, str]:
    """Создание чанка для продажи."""
    name = product_name or 'Неизвестный товар'
    sale_type = sale.get('type', 'N/A')
    sale_date = sale.get('sale_date')
    if isinstance(sale_date, datetime):
        sale_date = sale_date.strftime('%Y-%m-%d')
    price = sale.get('price', 0)
    
    chunk_text = (
        f"Продажа товара '{name}' (nm_id: {sale.get('nm_id', 'N/A')}) от {sale_date}: "
        f"тип - {sale_type}, сумма: {price:.2f}₽"
    )
    
    return {
        'chunk_type': 'sale',
        'source_table': 'wb_sales',
        'source_id': sale.get('id'),
        'chunk_text': chunk_text
    }


def create_chunks(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """
    Создание текстовых чанков из структурированных данных.
    
    Создает словарь названий товаров для использования в других чанках.
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
    
    logger.info(f"Создано {len(chunks)} чанков из данных")
    
    return chunks
```

#### Обработка NULL значений

Важно обрабатывать случаи, когда поля могут быть NULL:
- Использовать `.get()` с значениями по умолчанию
- Проверять типы данных перед форматированием
- Ограничивать длину текстовых полей (например, текст отзыва)

#### Действия

1. **Реализовать все функции создания чанков**
   - `_create_order_chunk()`
   - `_create_product_chunk()`
   - `_create_stock_chunk()`
   - `_create_review_chunk()`
   - `_create_sale_chunk()`

2. **Реализовать метод `create_chunks()`**
   - Создать словарь названий товаров
   - Вызвать функции для каждого типа данных
   - Вернуть список чанков

3. **Протестировать**
   - Создать тестовые данные
   - Проверить форматирование чанков
   - Проверить обработку NULL значений

#### Критерии готовности
- ✅ Все функции создания чанков реализованы
- ✅ Метод `create_chunks()` работает
- ✅ Чанки читаемые и информативные
- ✅ NULL значения обрабатываются корректно

---

### Задача 2.4: Генерация эмбеддингов

#### Описание
Реализация метода для генерации векторных представлений текстовых чанков через OpenAI Embeddings API.

#### Особенности

1. **Batch processing:** Группировка чанков для экономии запросов к API
2. **Rate limiting:** Обработка ограничений API
3. **Retry logic:** Повторные попытки при ошибках
4. **Логирование:** Отслеживание прогресса

#### Реализация

```python
def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
    """
    Генерация эмбеддингов для списка текстовых чанков.
    
    Использует batch processing для экономии запросов к API.
    
    Args:
        chunks: Список текстовых чанков
        
    Returns:
        Список векторов (каждый вектор - список из 1536 float)
    """
    if not chunks:
        return []
    
    all_embeddings = []
    total_chunks = len(chunks)
    
    # Разбить на батчи
    for i in range(0, total_chunks, self.batch_size):
        batch = chunks[i:i + self.batch_size]
        batch_num = (i // self.batch_size) + 1
        total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
        
        logger.info(
            f"Генерация эмбеддингов: батч {batch_num}/{total_batches} "
            f"({len(batch)} чанков)"
        )
        
        try:
            # Вызов OpenAI Embeddings API
            response = self.openai_client.embeddings.create(
                model=self.embeddings_model,
                input=batch
            )
            
            # Извлечь векторы из ответа
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            logger.info(
                f"✅ Батч {batch_num} обработан: {len(batch_embeddings)} эмбеддингов"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации эмбеддингов для батча {batch_num}: {e}")
            # При ошибке можно:
            # 1. Пропустить батч (не рекомендуется)
            # 2. Повторить попытку (рекомендуется)
            # 3. Выбросить исключение (если критично)
            raise
    
    logger.info(f"✅ Всего сгенерировано {len(all_embeddings)} эмбеддингов")
    
    return all_embeddings
```

#### Retry логика (опционально)

Можно добавить retry с экспоненциальной задержкой:

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def _generate_batch_embeddings(self, batch: List[str]) -> List[List[float]]:
    """Генерация эмбеддингов для одного батча с retry логикой."""
    response = self.openai_client.embeddings.create(
        model=self.embeddings_model,
        input=batch
    )
    return [item.embedding for item in response.data]
```

#### Действия

1. **Реализовать метод `generate_embeddings()`**
   - Разбить чанки на батчи
   - Вызвать OpenAI API для каждого батча
   - Обработать ошибки

2. **Добавить retry логику** (опционально)
   - Использовать библиотеку `tenacity`
   - Настроить параметры retry

3. **Протестировать**
   - Создать тестовые чанки
   - Вызвать метод
   - Проверить размерность векторов (1536)

#### Критерии готовности
- ✅ Метод реализован
- ✅ Batch processing работает
- ✅ Эмбеддинги генерируются корректно
- ✅ Размерность векторов = 1536
- ✅ Ошибки обрабатываются

---

### Задача 2.5: Сохранение в векторную БД

#### Описание
Реализация метода для сохранения эмбеддингов и метаданных в векторную БД с обработкой дубликатов.

#### Логика сохранения

1. **Проверка дубликатов:** Использовать UNIQUE constraint `(cabinet_id, source_table, source_id)`
2. **Обновление существующих:** Если запись существует, обновить чанк и embedding
3. **Транзакции:** Использовать транзакции для атомарности

#### Реализация

```python
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
    
    Args:
        embeddings: Список векторов
        chunks_metadata: Список метаданных для каждого чанка
        cabinet_id: ID кабинета
        db: Сессия БД
        
    Returns:
        Количество сохраненных записей
    """
    if len(embeddings) != len(chunks_metadata):
        raise ValueError(
            f"Количество эмбеддингов ({len(embeddings)}) "
            f"не совпадает с количеством метаданных ({len(chunks_metadata)})"
        )
    
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
                    chunk_text=chunk_meta['chunk_text']
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
        logger.info(f"✅ Сохранено {saved_count} записей в векторную БД")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка при сохранении в векторную БД: {e}")
        raise
    
    return saved_count
```

#### Оптимизация: Batch insert

Для больших объемов данных можно использовать batch insert:

```python
# Использовать bulk operations для оптимизации
from sqlalchemy.dialects.postgresql import insert

# Batch insert для метаданных
metadata_values = [
    {
        'cabinet_id': cabinet_id,
        'source_table': chunk['source_table'],
        'source_id': chunk['source_id'],
        'chunk_type': chunk['chunk_type'],
        'chunk_text': chunk['chunk_text']
    }
    for chunk in chunks_metadata
]

stmt = insert(RAGMetadata).values(metadata_values)
stmt = stmt.on_conflict_do_update(
    index_elements=['cabinet_id', 'source_table', 'source_id'],
    set_=dict(
        chunk_text=stmt.excluded.chunk_text,
        chunk_type=stmt.excluded.chunk_type,
        updated_at=datetime.now()
    )
)
db.execute(stmt)
```

#### Действия

1. **Реализовать метод `save_to_vector_db()`**
   - Обработать дубликаты
   - Сохранить метаданные и эмбеддинги
   - Использовать транзакции

2. **Протестировать**
   - Сохранить тестовые данные
   - Проверить обработку дубликатов
   - Проверить связи между таблицами

#### Критерии готовности
- ✅ Метод реализован
- ✅ Данные сохраняются корректно
- ✅ Дубликаты обрабатываются
- ✅ Транзакции работают
- ✅ Ошибки обрабатываются

---

### Задача 2.6: Главный метод индексации

#### Описание
Реализация метода `index_cabinet()`, который объединяет все этапы индексации и управляет статусом.

#### Логика

1. Проверить статус индексации
2. Установить статус 'in_progress'
3. Выполнить все этапы индексации
4. Обновить статус 'completed'
5. Обработать ошибки

#### Реализация

```python
async def index_cabinet(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Главный метод индексации кабинета.
    
    Выполняет полный цикл индексации с управлением статусом.
    """
    result = {
        'success': False,
        'cabinet_id': cabinet_id,
        'total_chunks': 0,
        'errors': []
    }
    
    # Получить сессию БД
    db = RAGSessionLocal()
    
    try:
        # 1. Проверить статус индексации
        index_status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()
        
        if index_status and index_status.indexing_status == 'in_progress':
            logger.warning(
                f"Индексация кабинета {cabinet_id} уже выполняется. Пропуск."
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
        
        logger.info(f"🚀 Начало индексации кабинета {cabinet_id}")
        
        # 3. Извлечение данных
        try:
            data = await self.extract_data_from_main_db(cabinet_id)
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных: {e}")
            result['errors'].append(f"Извлечение данных: {str(e)}")
            raise
        
        # 4. Создание чанков
        try:
            chunks_metadata = self.create_chunks(data)
        except Exception as e:
            logger.error(f"Ошибка при создании чанков: {e}")
            result['errors'].append(f"Создание чанков: {str(e)}")
            raise
        
        if not chunks_metadata:
            logger.warning(f"Нет данных для индексации кабинета {cabinet_id}")
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
            logger.error(f"Ошибка при генерации эмбеддингов: {e}")
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
            logger.error(f"Ошибка при сохранении в БД: {e}")
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
        
        logger.error(f"❌ Ошибка при индексации кабинета {cabinet_id}: {e}")
        result['errors'].append(str(e))
        
    finally:
        db.close()
    
    return result
```

#### Действия

1. **Реализовать метод `index_cabinet()`**
   - Объединить все этапы
   - Управлять статусом
   - Обработать ошибки

2. **Протестировать end-to-end**
   - Вызвать метод для тестового кабинета
   - Проверить все этапы
   - Проверить статус в БД

#### Критерии готовности
- ✅ Метод реализован
- ✅ Все этапы выполняются последовательно
- ✅ Статус обновляется корректно
- ✅ Ошибки обрабатываются
- ✅ End-to-end тест проходит

---

### Задача 2.7: Инкрементальная индексация

#### Описание
Реализация метода для обновления только новых/измененных записей.

#### Логика

1. Получить `last_incremental_at` из статуса
2. Извлечь только записи с `updated_at > last_incremental_at`
3. Обновить существующие чанки
4. Обновить `last_incremental_at`

#### Реализация

```python
async def incremental_index_cabinet(self, cabinet_id: int) -> Dict[str, Any]:
    """
    Инкрементальная индексация кабинета.
    
    Обновляет только новые/измененные записи с момента последней индексации.
    """
    db = RAGSessionLocal()
    
    try:
        # Получить дату последней инкрементальной индексации
        index_status = db.query(RAGIndexStatus).filter(
            RAGIndexStatus.cabinet_id == cabinet_id
        ).first()
        
        if not index_status:
            # Если статуса нет, выполнить полную индексацию
            return await self.index_cabinet(cabinet_id)
        
        last_incremental = index_status.last_incremental_at
        if not last_incremental:
            # Если даты нет, выполнить полную индексацию
            return await self.index_cabinet(cabinet_id)
        
        # Извлечь только новые/измененные данные
        # (добавить условие WHERE updated_at > last_incremental в SQL запросы)
        # ... реализация аналогична index_cabinet, но с фильтром по дате
        
        # Обновить last_incremental_at
        index_status.last_incremental_at = datetime.now()
        db.commit()
        
    finally:
        db.close()
```

#### Действия

1. **Реализовать метод `incremental_index_cabinet()`**
   - Добавить фильтр по дате в SQL запросы
   - Обновить только измененные записи

2. **Протестировать**
   - Выполнить полную индексацию
   - Внести изменения в данные
   - Выполнить инкрементальную индексацию
   - Проверить, что обновились только измененные записи

#### Критерии готовности
- ✅ Метод реализован
- ✅ Инкрементальная индексация работает
- ✅ Обновляются только измененные данные

---

## ✅ Критерии готовности Этапа 2

### Общие критерии

- ✅ Модуль индексации создан и структурирован
- ✅ Извлечение данных из всех таблиц работает
- ✅ Создание текстовых чанков работает для всех типов данных
- ✅ Генерация эмбеддингов через OpenAI API работает
- ✅ Сохранение в векторную БД работает
- ✅ Полная индексация кабинета работает end-to-end
- ✅ Инкрементальная индексация работает (опционально)

### Тестирование

**1. Тест извлечения данных:**
```python
indexer = RAGIndexer()
data = await indexer.extract_data_from_main_db(cabinet_id=1)
assert 'orders' in data
assert 'products' in data
# и т.д.
```

**2. Тест создания чанков:**
```python
chunks = indexer.create_chunks(data)
assert len(chunks) > 0
assert all('chunk_text' in chunk for chunk in chunks)
```

**3. Тест генерации эмбеддингов:**
```python
chunk_texts = [chunk['chunk_text'] for chunk in chunks[:5]]  # Тест на 5 чанках
embeddings = indexer.generate_embeddings(chunk_texts)
assert len(embeddings) == 5
assert len(embeddings[0]) == 1536  # Размерность OpenAI embedding
```

**4. Тест полной индексации:**
```python
result = await indexer.index_cabinet(cabinet_id=1)
assert result['success'] == True
assert result['total_chunks'] > 0
```

---

## 🐛 Возможные проблемы и решения

### Проблема 1: Ошибка подключения к основной БД

**Симптомы:** Ошибка при извлечении данных

**Решения:**
- Проверить настройки подключения
- Проверить права доступа к таблицам
- Проверить наличие данных в таблицах

### Проблема 2: Превышение лимитов OpenAI API

**Симптомы:** Rate limit errors при генерации эмбеддингов

**Решения:**
- Уменьшить размер батча
- Добавить задержки между запросами
- Использовать retry логику

### Проблема 3: Ошибка при сохранении в векторную БД

**Симптомы:** Ошибки UNIQUE constraint или других ограничений

**Решения:**
- Проверить обработку дубликатов
- Проверить типы данных (особенно vector)
- Проверить связи между таблицами

---

**Версия:** 1.0.0  
**Дата:** 2025-01-XX  
**Статус:** Детальный план Этапа 2

