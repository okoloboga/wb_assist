# Этап 4: Формирование контекста

## 📋 Обзор этапа

**Цель:** Объединить найденные чанки в структурированный контекст для LLM.

**Длительность:** 1-2 дня

**Зависимости:** Этап 3 (векторный поиск должен работать)

**Результат:** Модуль, который преобразует найденные чанки в читаемый контекст для добавления в промпт.

---

## 🎯 Задачи этапа

### Задача 4.1: Создание структуры модуля

**Файл:** `gpt_integration/ai_chat/rag/context_builder.py`

**Класс:** `ContextBuilder`

**Методы:**
- `group_by_type(chunks)` — группировка по типу
- `deduplicate(chunks)` — удаление дубликатов
- `format_context(chunks)` — форматирование контекста
- `truncate_context(context, max_length)` — обрезка контекста
- `build_context(chunks)` — главный метод

---

### Задача 4.2: Группировка чанков по типу

**Реализация:**
```python
def group_by_type(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Группировка чанков по типу данных."""
    grouped = {}
    for chunk in chunks:
        chunk_type = chunk.get('chunk_type', 'unknown')
        if chunk_type not in grouped:
            grouped[chunk_type] = []
        grouped[chunk_type].append(chunk)
    
    # Сортировать внутри каждой группы по similarity
    for chunk_type in grouped:
        grouped[chunk_type].sort(key=lambda x: x.get('similarity', 0), reverse=True)
    
    return grouped
```

**Проверка:** Группировка работает, сортировка по similarity работает.

---

### Задача 4.3: Дедупликация

**Реализация:**
```python
def deduplicate(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Удаление дубликатов по source_table и source_id."""
    seen = set()
    unique_chunks = []
    
    for chunk in chunks:
        key = (chunk.get('source_table'), chunk.get('source_id'))
        if key not in seen:
            seen.add(key)
            unique_chunks.append(chunk)
        else:
            # Если дубликат найден, оставить более релевантный
            for i, existing in enumerate(unique_chunks):
                if (existing.get('source_table'), existing.get('source_id')) == key:
                    if chunk.get('similarity', 0) > existing.get('similarity', 0):
                        unique_chunks[i] = chunk
                    break
    
    return unique_chunks
```

**Проверка:** Дубликаты удаляются, остается наиболее релевантный.

---

### Задача 4.4: Форматирование контекста

**Реализация:**
```python
def format_context(self, chunks: List[Dict[str, Any]]) -> str:
    """Форматирование чанков в структурированный текст."""
    # Группировать по типам
    grouped = self.group_by_type(chunks)
    
    # Названия типов на русском
    type_names = {
        'order': 'ЗАКАЗЫ',
        'product': 'ТОВАРЫ',
        'stock': 'ОСТАТКИ',
        'review': 'ОТЗЫВЫ',
        'sale': 'ПРОДАЖИ'
    }
    
    context_parts = ["=== РЕЛЕВАНТНЫЕ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ ===\n"]
    
    # Порядок вывода типов
    type_order = ['orders', 'products', 'stocks', 'reviews', 'sales']
    
    for type_key in type_order:
        chunk_type = type_key.rstrip('s')  # orders -> order
        if chunk_type in grouped:
            type_name = type_names.get(chunk_type, chunk_type.upper())
            context_parts.append(f"{type_name}:")
            
            for chunk in grouped[chunk_type]:
                context_parts.append(f"- {chunk.get('chunk_text', '')}")
            
            context_parts.append("")  # Пустая строка между группами
    
    return "\n".join(context_parts)
```

**Проверка:** Контекст читаемый, структурированный, заголовки добавлены.

---

### Задача 4.5: Обрезка контекста

**Реализация:**
```python
def truncate_context(self, context: str, max_length: int) -> str:
    """Обрезка контекста до максимальной длины."""
    if len(context) <= max_length:
        return context
    
    # Обрезать, сохраняя структуру
    # Удалить менее релевантные чанки (в конце)
    lines = context.split('\n')
    truncated_lines = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 <= max_length:
            truncated_lines.append(line)
            current_length += len(line) + 1
        else:
            break
    
    # Добавить индикатор обрезки
    if len(truncated_lines) < len(lines):
        truncated_lines.append("... (контекст обрезан)")
    
    return "\n".join(truncated_lines)
```

**Проверка:** Обрезка работает, структура сохраняется.

---

### Задача 4.6: Главный метод

**Реализация:**
```python
def build_context(
    self,
    chunks: List[Dict[str, Any]],
    max_length: Optional[int] = None
) -> str:
    """Главный метод формирования контекста."""
    if not chunks:
        return ""
    
    max_length = max_length or self.max_length
    
    # 1. Дедупликация
    unique_chunks = self.deduplicate(chunks)
    
    # 2. Форматирование
    context = self.format_context(unique_chunks)
    
    # 3. Обрезка
    context = self.truncate_context(context, max_length)
    
    return context
```

**Проверка:** End-to-end формирование контекста работает.

---

## ✅ Критерии готовности

- ✅ Модуль создан
- ✅ Группировка работает
- ✅ Дедупликация работает
- ✅ Форматирование работает
- ✅ Обрезка работает
- ✅ End-to-end работает

---

**Версия:** 1.0.0  
**Дата:** 2025-01-XX  
**Статус:** Детальный план Этапа 4

