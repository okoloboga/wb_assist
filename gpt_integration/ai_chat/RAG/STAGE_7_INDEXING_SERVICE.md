# Этап 7: Сервис индексации (Celery Task)

## 📋 Обзор этапа

**Цель:** Создать автоматическую индексацию данных по расписанию.

**Длительность:** 1-2 дня

**Зависимости:** Этап 2 (модуль индексации)

**Результат:** Автоматическая индексация данных каждые N часов.

---

## 🎯 Задачи этапа

### Задача 7.1: Создание Celery Task

**Файл:** `server/app/tasks/rag_indexing.py` (или в основном сервисе)

**Task:**
```python
from celery import shared_task
from gpt_integration.ai_chat.rag.indexer import RAGIndexer

@shared_task(bind=True, max_retries=3)
def index_rag_for_cabinet(self, cabinet_id: int):
    """Celery task для индексации кабинета."""
    try:
        indexer = RAGIndexer()
        result = await indexer.index_cabinet(cabinet_id)
        
        if not result['success']:
            raise Exception(f"Индексация не удалась: {result.get('errors')}")
        
        return result
        
    except Exception as e:
        # Retry при ошибке
        raise self.retry(exc=e, countdown=60)
```

---

### Задача 7.2: Периодическая индексация

**Настройка Celery Beat:**

**Файл:** `server/app/celery_app.py` (или аналогичный)

```python
from celery.schedules import crontab

beat_schedule = {
    'rag-indexing-every-6-hours': {
        'task': 'server.app.tasks.rag_indexing.index_all_cabinets',
        'schedule': crontab(hour='*/6'),  # Каждые 6 часов
    },
}
```

**Task для всех кабинетов:**
```python
@shared_task
def index_all_cabinets():
    """Индексация всех кабинетов."""
    # Получить список всех кабинетов
    cabinets = get_all_cabinets()  # Функция для получения кабинетов
    
    for cabinet_id in cabinets:
        index_rag_for_cabinet.delay(cabinet_id)
```

---

### Задача 7.3: API endpoint для ручного запуска

**Файл:** `server/app/api/v1/rag.py`

**Endpoint:**
```python
@router.post("/rag/index/{cabinet_id}")
async def trigger_indexing(
    cabinet_id: int,
    _: None = Depends(_verify_api_key)
):
    """Запуск индексации для кабинета вручную."""
    index_rag_for_cabinet.delay(cabinet_id)
    return {"message": f"Индексация кабинета {cabinet_id} запущена"}
```

---

## ✅ Критерии готовности

- ✅ Celery task создан
- ✅ Периодическая индексация настроена
- ✅ API endpoint работает (если реализован)

---

**Версия:** 1.0.0  
**Дата:** 2025-01-XX  
**Статус:** Детальный план Этапа 7

