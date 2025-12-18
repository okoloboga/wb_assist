# Этап 1.3: API Спецификация для инкрементальной индексации

**Дата:** 2025-12-16
**Статус:** ✅ Завершен

---

## 📋 Обзор изменений API

### Изменения в AI-сервисе (gpt_integration):

1. **Новый параметр `full_rebuild` в POST `/v1/rag/index/{cabinet_id}`**
   - Тип: Query parameter (boolean)
   - По умолчанию: `false` (инкрементальная индексация)
   - Назначение: Выбор типа индексации

2. **Новый endpoint GET `/v1/rag/metrics/{cabinet_id}`**
   - Назначение: Получение метрик последней индексации
   - Формат: JSON с детальной статистикой

3. **Расширенный ответ `/v1/rag/status/{cabinet_id}`**
   - Добавлены поля: indexing_mode, metrics, performance

---

## 📡 API Endpoints

### 1. POST `/v1/rag/index/{cabinet_id}`

**Описание:** Запуск индексации для кабинета (инкрементальная или полная)

**URL:** `POST /v1/rag/index/{cabinet_id}?full_rebuild=false`

**Headers:**
```
X-API-KEY: {API_SECRET_KEY}
Content-Type: application/json
```

**Path Parameters:**
- `cabinet_id` (integer, required) - ID кабинета Wildberries

**Query Parameters:**
- `full_rebuild` (boolean, optional, default=false) - Тип индексации:
  - `false` → Инкрементальная индексация (по умолчанию)
  - `true` → Полная переиндексация с очисткой устаревших данных

**Request Body:** Нет

**Response 200 (Success):**
```json
{
  "status": "success",
  "message": "Индексация кабинета 1 завершена успешно",
  "cabinet_id": 1,
  "indexing_mode": "incremental",  // "incremental" | "full_rebuild"
  "total_chunks": 2350,
  "metrics": {
    "new_chunks": 45,
    "updated_chunks": 23,
    "skipped_chunks": 1920,  // Не изменились (hash-based detection)
    "deleted_chunks": 0,  // Только для full_rebuild
    "embeddings_generated": 68,  // new + updated
    "execution_time_seconds": 8.5,
    "api_cost_estimate": 0.00068  // В долларах
  },
  "timestamp": "2025-12-16T15:30:00Z"
}
```

**Response 500 (Error):**
```json
{
  "status": "error",
  "message": "Ошибка индексации кабинета 1",
  "cabinet_id": 1,
  "errors": [
    "OpenAI API timeout after 5 retries"
  ],
  "timestamp": "2025-12-16T15:30:00Z"
}
```

**Response 403 (Forbidden):**
```json
{
  "detail": "Invalid or missing API key"
}
```

---

### 2. GET `/v1/rag/status/{cabinet_id}`

**Описание:** Получить статус индексации для кабинета

**URL:** `GET /v1/rag/status/{cabinet_id}`

**Headers:**
```
X-API-KEY: {API_SECRET_KEY}
```

**Path Parameters:**
- `cabinet_id` (integer, required) - ID кабинета Wildberries

**Response 200 (Success):**
```json
{
  "status": "success",
  "cabinet_id": 1,
  "indexing_status": "completed",  // "pending" | "in_progress" | "completed" | "failed"
  "indexing_mode": "incremental",  // "incremental" | "full_rebuild"
  "last_indexed_at": "2025-12-16T15:30:00Z",  // Последняя полная индексация
  "last_incremental_at": "2025-12-16T15:30:00Z",  // Последняя инкрементальная индексация
  "total_chunks": 2350,
  "updated_at": "2025-12-16T15:35:00Z"
}
```

**Response 200 (Not Found):**
```json
{
  "status": "not_found",
  "message": "Индексация для кабинета 1 еще не запускалась",
  "cabinet_id": 1,
  "indexing_status": null,
  "last_indexed_at": null,
  "total_chunks": 0
}
```

---

### 3. GET `/v1/rag/metrics/{cabinet_id}` (NEW)

**Описание:** Получить детальные метрики последней индексации

**URL:** `GET /v1/rag/metrics/{cabinet_id}`

**Headers:**
```
X-API-KEY: {API_SECRET_KEY}
```

**Path Parameters:**
- `cabinet_id` (integer, required) - ID кабинета Wildberries

**Response 200 (Success):**
```json
{
  "status": "success",
  "cabinet_id": 1,
  "latest_indexing": {
    "mode": "incremental",
    "started_at": "2025-12-16T15:30:00Z",
    "completed_at": "2025-12-16T15:30:08Z",
    "execution_time_seconds": 8.5,
    "status": "completed"
  },
  "chunks": {
    "total": 2350,
    "new": 45,
    "updated": 23,
    "skipped": 1920,
    "deleted": 0
  },
  "embeddings": {
    "generated": 68,
    "batch_size": 100,
    "batches_processed": 1,
    "failed_batches": 0
  },
  "api_usage": {
    "openai_requests": 1,
    "tokens_used": 6800,
    "cost_estimate_usd": 0.00068
  },
  "performance": {
    "extraction_time_seconds": 1.2,
    "chunking_time_seconds": 0.8,
    "embedding_time_seconds": 5.5,
    "saving_time_seconds": 1.0
  },
  "comparison_with_full": {
    "time_saved_percent": 91,  // (90s - 8.5s) / 90s * 100
    "api_saved_percent": 95,   // (1500 - 68) / 1500 * 100
    "chunks_processed_percent": 5  // 68 / 1500 * 100
  }
}
```

**Response 200 (Not Found):**
```json
{
  "status": "not_found",
  "message": "Метрики для кабинета 1 недоступны (индексация не запускалась)",
  "cabinet_id": 1
}
```

---

## 🔧 Изменения в Celery Tasks (server)

### 1. `index_rag_for_cabinet(cabinet_id, full_rebuild=False, changed_ids=None)`

**Описание:** Индексация RAG для конкретного кабинета (Event-driven или Full)

**Параметры:**
- `cabinet_id` (int, required) - ID кабинета
- `full_rebuild` (bool, optional, default=False) - Тип индексации
- `changed_ids` (dict, optional, default=None) - Дельта изменений от WB sync
  ```python
  {
      "orders": [12345, 12346],
      "products": [98765],
      "stocks": [11111, 11112],
      "reviews": [55555],
      "sales": [77777]
  }
  ```

**Использование:**
```python
# Event-driven индексация (вызывается из WB sync task)
changed_ids = {
    "orders": [12345, 12346],
    "products": [98765]
}
index_rag_for_cabinet.delay(1, changed_ids=changed_ids)

# Полная переиндексация
index_rag_for_cabinet.delay(1, full_rebuild=True)
```

**Возвращаемое значение:**
```python
{
    "status": "success",
    "cabinet_id": 1,
    "message": "Индексация завершена",
    "total_chunks": 2350,
    "metrics": {...}  # Детальные метрики
}
```

---

### 2. `index_all_cabinets_rag(full_rebuild=False)` (UPDATED)

**Описание:** Индексация RAG для всех активных кабинетов

**Параметры:**
- `full_rebuild` (bool, optional, default=False) - Тип индексации

**Изменения:**
- Теперь принимает параметр `full_rebuild`
- Передает его в `index_rag_for_cabinet` для каждого кабинета

**Использование:**
```python
# Инкрементальная индексация всех кабинетов
index_all_cabinets_rag.delay()

# Полная переиндексация всех кабинетов
index_all_cabinets_rag.delay(full_rebuild=True)
```

---

### 3. `full_rebuild_all_cabinets_rag()` (NEW)

**Описание:** Полная переиндексация всех активных кабинетов (wrapper для удобства)

**Параметры:** Нет

**Использование:**
```python
# Полная переиндексация всех кабинетов
full_rebuild_all_cabinets_rag.delay()
```

**Реализация:**
```python
@celery_app.task
def full_rebuild_all_cabinets_rag():
    """Wrapper для полной переиндексации всех кабинетов."""
    return index_all_cabinets_rag(full_rebuild=True)
```

---

## 📅 Celery Beat Schedule (UPDATED)

### Текущий schedule:
```python
"index-all-cabinets-rag": {
    "task": "app.features.rag.tasks.index_all_cabinets_rag",
    "schedule": crontab(hour=f'*/{rag_indexing_interval_hours}', minute=0),
}
```

### Новый schedule (Event-driven):
```python
# УДАЛЕНО: Инкрементальная индексация по расписанию
# Теперь индексация триггерится из WB sync task (Event-driven)

# Полная переиндексация (воскресенье, 03:00 UTC)
"index-full-rebuild-rag": {
    "task": "app.features.rag.tasks.index_all_cabinets_rag",
    "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Воскресенье
    "kwargs": {"full_rebuild": True}
},
```

**Альтернативный вариант (с wrapper):**
```python
# Полная переиндексация
"index-full-rebuild-rag": {
    "task": "app.features.rag.tasks.full_rebuild_all_cabinets_rag",
    "schedule": crontab(hour=3, minute=0, day_of_week=0),
},
```

### Триггер инкрементальной индексации:
Инкрементальная индексация НЕ запускается по расписанию. Она триггерится из WB sync task:

```python
# В sync_cabinet_data task (server/app/features/sync/tasks.py)
@celery_app.task
def sync_cabinet_data(cabinet_id: int):
    """Синхронизация данных WB API для кабинета."""

    # ... синхронизация WB API ...

    # Собрать дельту изменений
    changed_ids = {
        "orders": [id for id in new_or_updated_orders],
        "products": [id for id in new_or_updated_products],
        "stocks": [id for id in new_or_updated_stocks],
        "reviews": [id for id in new_or_updated_reviews],
        "sales": [id for id in new_or_updated_sales]
    }

    # Триггер RAG индексации (Event-driven)
    if changed_ids:
        index_rag_for_cabinet.delay(cabinet_id, changed_ids=changed_ids)

    return result
```

---

## 🔐 Аутентификация

**Метод:** API Key в заголовке

**Header:**
```
X-API-KEY: {API_SECRET_KEY}
```

**Источник ключа:**
- Environment variable: `API_SECRET_KEY`
- Один и тот же ключ для server и gpt сервисов

**Проверка:**
```python
def _verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-KEY")) -> None:
    expected_key = os.getenv("API_SECRET_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API authentication not configured")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
```

---

## 📊 Структура метрик

### Основные метрики индексации:

```python
@dataclass
class IndexingMetrics:
    """Метрики индексации."""

    # Режим индексации
    mode: str  # "incremental" | "full_rebuild"

    # Время выполнения
    started_at: datetime
    completed_at: datetime
    execution_time_seconds: float

    # Статистика чанков
    total_chunks: int
    new_chunks: int
    updated_chunks: int
    skipped_chunks: int  # Не изменились (hash-based)
    deleted_chunks: int  # Только для full_rebuild

    # Эмбеддинги
    embeddings_generated: int  # new + updated
    batch_size: int
    batches_processed: int
    failed_batches: int

    # API usage
    openai_requests: int
    tokens_used: int
    cost_estimate_usd: float

    # Детальная производительность
    extraction_time_seconds: float
    chunking_time_seconds: float
    embedding_time_seconds: float
    saving_time_seconds: float

    # Сравнение с полной индексацией (для инкремента)
    time_saved_percent: Optional[float] = None
    api_saved_percent: Optional[float] = None
```

---

## 🔄 Примеры использования API

### Пример 1: Инкрементальная индексация

**Request:**
```bash
curl -X POST \
  http://localhost:9000/v1/rag/index/1 \
  -H "X-API-KEY: ${API_SECRET_KEY}"
```

**Response:**
```json
{
  "status": "success",
  "message": "Индексация кабинета 1 завершена успешно",
  "cabinet_id": 1,
  "indexing_mode": "incremental",
  "total_chunks": 2350,
  "metrics": {
    "new_chunks": 45,
    "updated_chunks": 23,
    "skipped_chunks": 1920,
    "embeddings_generated": 68,
    "execution_time_seconds": 8.5
  }
}
```

---

### Пример 2: Полная переиндексация

**Request:**
```bash
curl -X POST \
  "http://localhost:9000/v1/rag/index/1?full_rebuild=true" \
  -H "X-API-KEY: ${API_SECRET_KEY}"
```

**Response:**
```json
{
  "status": "success",
  "message": "Полная переиндексация кабинета 1 завершена успешно",
  "cabinet_id": 1,
  "indexing_mode": "full_rebuild",
  "total_chunks": 2305,
  "metrics": {
    "new_chunks": 12,
    "updated_chunks": 38,
    "skipped_chunks": 1900,
    "deleted_chunks": 45,  // Устаревшие чанки удалены
    "embeddings_generated": 50,
    "execution_time_seconds": 92.3
  }
}
```

---

### Пример 3: Получение метрик

**Request:**
```bash
curl -X GET \
  http://localhost:9000/v1/rag/metrics/1 \
  -H "X-API-KEY: ${API_SECRET_KEY}"
```

**Response:**
```json
{
  "status": "success",
  "cabinet_id": 1,
  "latest_indexing": {
    "mode": "incremental",
    "started_at": "2025-12-16T15:30:00Z",
    "completed_at": "2025-12-16T15:30:08Z",
    "execution_time_seconds": 8.5,
    "status": "completed"
  },
  "chunks": {
    "total": 2350,
    "new": 45,
    "updated": 23,
    "skipped": 1920,
    "deleted": 0
  },
  "comparison_with_full": {
    "time_saved_percent": 91,
    "api_saved_percent": 95
  }
}
```

---

### Пример 4: Запуск через Celery (из кода)

```python
from app.features.rag.tasks import index_rag_for_cabinet

# Инкрементальная индексация
result = index_rag_for_cabinet.delay(cabinet_id=1)
print(f"Task ID: {result.id}")

# Полная переиндексация
result = index_rag_for_cabinet.delay(cabinet_id=1, full_rebuild=True)
print(f"Task ID: {result.id}")

# Ожидание результата
result_data = result.get(timeout=600)  # Макс 10 минут
print(f"Result: {result_data}")
```

---

## ⚠️ Обработка ошибок

### Типы ошибок:

1. **Кабинет не найден:**
```json
{
  "status": "error",
  "cabinet_id": 999,
  "message": "Кабинет не найден или неактивен"
}
```

2. **Индексация уже выполняется:**
```json
{
  "status": "error",
  "cabinet_id": 1,
  "message": "Индексация уже выполняется",
  "errors": ["Индексация уже выполняется"]
}
```

3. **Ошибка OpenAI API:**
```json
{
  "status": "error",
  "cabinet_id": 1,
  "message": "Ошибка генерации эмбеддингов",
  "errors": [
    "OpenAI API timeout after 5 retries",
    "Batch 59 failed after 5 attempts"
  ]
}
```

4. **Ошибка БД:**
```json
{
  "status": "error",
  "cabinet_id": 1,
  "message": "Ошибка сохранения в БД",
  "errors": ["Database connection timeout"]
}
```

---

## 🎯 Совместимость с текущим API

### Обратная совместимость:

**ДО (текущий API):**
```bash
POST /v1/rag/index/1
```

**ПОСЛЕ (новый API):**
```bash
# Эквивалентно старому поведению (полная переиндексация)
POST /v1/rag/index/1?full_rebuild=true

# Новое поведение по умолчанию (инкрементальная)
POST /v1/rag/index/1
```

**Важно:** Текущие пользователи API будут автоматически использовать инкрементальную индексацию (более эффективную) после обновления.

---

## ✅ Чеклист готовности API

### Перед реализацией:

- [ ] Согласована спецификация API с командой
- [ ] Определены метрики для логирования
- [ ] Подготовлены примеры использования

### После реализации:

- [ ] Реализованы все endpoints
- [ ] Добавлена обработка ошибок
- [ ] Написаны тесты для API
- [ ] Обновлена документация
- [ ] Протестирована обратная совместимость

---

**Дата завершения:** 2025-12-16
**Статус:** ✅ Этап 1.3 завершен успешно
**Следующий этап:** 2 - Реализация инкрементальной индексации
