# Этап 5: Интеграция с AI Chat Service

## 📋 Обзор этапа

**Цель:** Интегрировать RAG модуль в существующий AI Chat Service.

**Длительность:** 2-3 дня

**Зависимости:** Этапы 1-4 (все компоненты RAG должны быть готовы)

**Результат:** AI Chat Service использует RAG для обогащения промптов контекстом из БД.

---

## 🎯 Задачи этапа

### Задача 5.1: Создание модуля обогащения промпта

**Файл:** `gpt_integration/ai_chat/rag/prompt_enricher.py`

**Функция:** `enrich_prompt_with_rag(user_message, telegram_id, cabinet_id, original_prompt)`

**Логика:**
1. Вызвать `VectorSearch.search_relevant_chunks()`
2. Вызвать `ContextBuilder.build_context()`
3. Объединить исходный промпт с контекстом
4. Вернуть обогащенный промпт

**Реализация:**
```python
def enrich_prompt_with_rag(
    user_message: str,
    telegram_id: int,
    cabinet_id: int,
    original_prompt: str,
    chunk_types: Optional[List[str]] = None
) -> str:
    """Обогащение промпта контекстом из RAG."""
    try:
        # 1. Поиск релевантных чанков
        vector_search = VectorSearch()
        chunks = vector_search.search_relevant_chunks(
            query_text=user_message,
            cabinet_id=cabinet_id,
            chunk_types=chunk_types,
            max_chunks=5
        )
        
        if not chunks:
            # Нет релевантных данных - вернуть исходный промпт
            return original_prompt
        
        # 2. Формирование контекста
        context_builder = ContextBuilder()
        context = context_builder.build_context(chunks)
        
        # 3. Объединение промпта с контекстом
        enriched_prompt = f"""{original_prompt}

=== КОНТЕКСТ ИЗ БАЗЫ ДАННЫХ ПОЛЬЗОВАТЕЛЯ ===
{context}

=== ИНСТРУКЦИИ ===
Используй данные из контекста выше для ответа на вопрос пользователя.
Если в контексте нет нужной информации, отвечай на основе общих знаний, но укажи это.
"""
        
        return enriched_prompt
        
    except Exception as e:
        logger.error(f"Ошибка при обогащении промпта: {e}")
        # Fallback на исходный промпт
        return original_prompt
```

---

### Задача 5.2: Получение cabinet_id пользователя

**Файл:** `gpt_integration/ai_chat/rag/utils.py`

**Функция:** `get_cabinet_id_for_user(telegram_id, db)`

**Реализация:**
```python
def get_cabinet_id_for_user(telegram_id: int, db: Session) -> Optional[int]:
    """Получение cabinet_id для пользователя."""
    # Запрос к основной БД через asyncpg или SQLAlchemy
    # users -> cabinet_users -> wb_cabinets
    # Вернуть первый cabinet_id или None
    pass
```

---

### Задача 5.3: Модификация AI Chat Service

**Файл:** `gpt_integration/ai_chat/app/service.py`

**Изменения в `send_message()`:**

1. Получить `cabinet_id` пользователя
2. Проверить `RAG_ENABLED` из env
3. Если RAG включен:
   - Вызвать `enrich_prompt_with_rag()`
   - Использовать обогащенный промпт
4. Если RAG выключен или ошибка:
   - Использовать исходный промпт (fallback)

**Код:**
```python
# В функции send_message(), перед вызовом _call_openai():

# Получить cabinet_id
cabinet_id = None
if RAG_ENABLED:
    try:
        cabinet_id = get_cabinet_id_for_user(telegram_id, db)
    except Exception as e:
        logger.warning(f"Не удалось получить cabinet_id: {e}")

# Обогатить промпт, если RAG включен и cabinet_id найден
system_prompt = SYSTEM_PROMPT
if RAG_ENABLED and cabinet_id:
    try:
        system_prompt = enrich_prompt_with_rag(
            user_message=message,
            telegram_id=telegram_id,
            cabinet_id=cabinet_id,
            original_prompt=SYSTEM_PROMPT
        )
        logger.info(f"Промпт обогащен контекстом RAG для кабинета {cabinet_id}")
    except Exception as e:
        logger.error(f"Ошибка при обогащении промпта: {e}")
        # Использовать исходный промпт (fallback)
```

---

### Задача 5.4: Обработка ошибок и fallback

**Логика:**
- Все ошибки RAG должны обрабатываться gracefully
- При любой ошибке → fallback на обычный промпт
- Пользователь не должен видеть ошибок
- Логировать все fallback случаи

---

### Задача 5.5: Обновление __init__.py

**Файл:** `gpt_integration/ai_chat/rag/__init__.py`

**Экспорты:**
```python
from .prompt_enricher import enrich_prompt_with_rag
from .vector_search import VectorSearch
from .context_builder import ContextBuilder
from .indexer import RAGIndexer

__all__ = [
    'enrich_prompt_with_rag',
    'VectorSearch',
    'ContextBuilder',
    'RAGIndexer'
]
```

---

## ✅ Критерии готовности

- ✅ Модуль обогащения промпта создан
- ✅ Получение cabinet_id работает
- ✅ Интеграция с AI Chat Service работает
- ✅ Fallback логика работает
- ✅ Обработка ошибок работает
- ✅ End-to-end поток работает

---

## 🧪 Тестирование

**Тест интеграции:**
1. Отправить запрос через Telegram бота
2. Проверить, что промпт обогащается контекстом
3. Проверить fallback при ошибках
4. Проверить логи

---

**Версия:** 1.0.0  
**Дата:** 2025-01-XX  
**Статус:** Детальный план Этапа 5

