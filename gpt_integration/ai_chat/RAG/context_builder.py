"""
Context Builder - модуль для формирования контекста из найденных чанков.

Преобразует найденные релевантные чанки в структурированный текст
для добавления в промпт LLM.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Класс для формирования контекста из найденных чанков.
    
    Процесс формирования:
    1. Дедупликация чанков
    2. Группировка по типам
    3. Форматирование в читаемый текст
    4. Обрезка до максимальной длины
    """
    
    def __init__(self, max_length: Optional[int] = None):
        """
        Инициализация билдера контекста.
        
        Args:
            max_length: Максимальная длина контекста в символах (из env или default)
        """
        self.max_length = max_length or int(
            os.getenv("RAG_CONTEXT_MAX_LENGTH", "3000")
        )
        
        # Названия типов на русском
        self.type_names = {
            'order': 'ЗАКАЗЫ',
            'product': 'ТОВАРЫ',
            'stock': 'ОСТАТКИ',
            'review': 'ОТЗЫВЫ',
            'sale': 'ПРОДАЖИ'
        }
        
        # Порядок вывода типов (от более важных к менее важным)
        self.type_order = ['product', 'order', 'sale', 'stock', 'review']
    
    def group_by_type(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Группировка чанков по типу данных.
        
        Также сортирует чанки внутри каждой группы по similarity (от большего к меньшему).
        
        Args:
            chunks: Список чанков с метаданными
            
        Returns:
            Словарь, где ключ - тип чанка, значение - список чанков этого типа
        """
        grouped = {}
        
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'unknown')
            if chunk_type not in grouped:
                grouped[chunk_type] = []
            grouped[chunk_type].append(chunk)
        
        # Сортировать внутри каждой группы по similarity (от большего к меньшему)
        for chunk_type in grouped:
            grouped[chunk_type].sort(
                key=lambda x: x.get('similarity', 0),
                reverse=True
            )
        
        logger.debug(f"📊 Grouping: {len(grouped)} types, total chunks: {len(chunks)}")
        
        return grouped
    
    def deduplicate(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов по source_table и source_id.
        
        Если найден дубликат, оставляется более релевантный (с большим similarity).
        
        Args:
            chunks: Список чанков с метаданными
            
        Returns:
            Список уникальных чанков (без дубликатов)
        """
        seen = {}
        unique_chunks = []
        
        for chunk in chunks:
            source_table = chunk.get('source_table')
            source_id = chunk.get('source_id')
            
            # Пропустить, если нет ключа для дедупликации
            if source_table is None or source_id is None:
                unique_chunks.append(chunk)
                continue
            
            key = (source_table, source_id)
            chunk_similarity = chunk.get('similarity', 0)
            
            if key not in seen:
                # Первое вхождение
                seen[key] = len(unique_chunks)
                unique_chunks.append(chunk)
            else:
                # Дубликат найден - сравнить similarity
                existing_index = seen[key]
                existing_chunk = unique_chunks[existing_index]
                existing_similarity = existing_chunk.get('similarity', 0)
                
                if chunk_similarity > existing_similarity:
                    # Заменить на более релевантный
                    unique_chunks[existing_index] = chunk
                    logger.debug(
                        f"🔄 Заменен дубликат: {key}, "
                        f"similarity {existing_similarity:.2f} -> {chunk_similarity:.2f}"
                    )
        
        removed_count = len(chunks) - len(unique_chunks)
        if removed_count > 0:
            logger.info(f"🗑️ Removed {removed_count} duplicates from {len(chunks)} chunks")
        
        return unique_chunks
    
    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Форматирование чанков в структурированный текст.
        
        Группирует чанки по типам и форматирует их в читаемый текст
        с заголовками и структурированным списком.
        
        Args:
            chunks: Список чанков с метаданными
            
        Returns:
            Отформатированный текст контекста
        """
        if not chunks:
            return ""
        
        # Группировать по типам
        grouped = self.group_by_type(chunks)
        
        # Начало контекста
        context_parts = ["=== РЕЛЕВАНТНЫЕ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ ===\n"]
        
        # Вывести чанки в порядке type_order
        for chunk_type in self.type_order:
            if chunk_type in grouped:
                type_name = self.type_names.get(chunk_type, chunk_type.upper())
                context_parts.append(f"## {type_name}\n")
                
                for chunk in grouped[chunk_type]:
                    chunk_text = chunk.get('chunk_text', '').strip()
                    if chunk_text:
                        # Добавить similarity для отладки (опционально)
                        similarity = chunk.get('similarity', 0)
                        context_parts.append(f"- {chunk_text}")
                        # Можно добавить similarity в комментарии для отладки:
                        # context_parts.append(f"- {chunk_text} [similarity: {similarity:.2f}]")
                
                context_parts.append("")  # Пустая строка между группами
        
        # Вывести остальные типы (если есть), которых нет в type_order
        for chunk_type, chunk_list in grouped.items():
            if chunk_type not in self.type_order:
                type_name = self.type_names.get(chunk_type, chunk_type.upper())
                context_parts.append(f"## {type_name}\n")
                
                for chunk in chunk_list:
                    chunk_text = chunk.get('chunk_text', '').strip()
                    if chunk_text:
                        context_parts.append(f"- {chunk_text}")
                
                context_parts.append("")
        
        context_text = "\n".join(context_parts)
        
        logger.debug(f"📝 Formatted context: {len(context_text)} characters")
        
        return context_text
    
    def truncate_context(self, context: str, max_length: int) -> str:
        """
        Обрезка контекста до максимальной длины.
        
        Сохраняет структуру контекста, удаляя менее релевантные чанки (в конце).
        
        Args:
            context: Текст контекста
            max_length: Максимальная длина в символах
            
        Returns:
            Обрезанный контекст (если был обрезан, добавляется индикатор)
        """
        if len(context) <= max_length:
            return context
        
        logger.info(
            f"✂️ Обрезка контекста: {len(context)} -> {max_length} символов"
        )
        
        # Разбить на строки
        lines = context.split('\n')
        truncated_lines = []
        current_length = 0
        
        # Подсчитать длину заголовка
        header_length = len("=== РЕЛЕВАНТНЫЕ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ ===\n")
        current_length = header_length
        truncated_lines.append("=== РЕЛЕВАНТНЫЕ ДАННЫЕ ИЗ БАЗЫ ДАННЫХ ===\n")
        
        # Добавлять строки до достижения лимита
        for line in lines[1:]:  # Пропустить заголовок (уже добавлен)
            line_length = len(line) + 1  # +1 для символа новой строки
            
            if current_length + line_length <= max_length:
                truncated_lines.append(line)
                current_length += line_length
            else:
                # Не помещается - остановиться
                break
        
        # Добавить индикатор обрезки, если контекст был обрезан
        if len(truncated_lines) < len(lines):
            # Убедиться, что индикатор помещается
            indicator = "\n... (контекст обрезан из-за ограничения длины)"
            if current_length + len(indicator) <= max_length:
                truncated_lines.append(indicator)
            else:
                # Если индикатор не помещается, удалить последнюю строку и добавить индикатор
                if truncated_lines:
                    truncated_lines.pop()
                truncated_lines.append("... (контекст обрезан)")
        
        truncated_text = "\n".join(truncated_lines)
        
        logger.info(
            f"✅ Контекст обрезан: {len(truncated_text)} символов "
            f"(было {len(context)})"
        )
        
        return truncated_text
    
    def build_context(
        self,
        chunks: List[Dict[str, Any]],
        max_length: Optional[int] = None
    ) -> str:
        """
        Главный метод формирования контекста.
        
        Объединяет все этапы:
        1. Дедупликация
        2. Форматирование
        3. Обрезка
        
        Args:
            chunks: Список чанков с метаданными (результат VectorSearch)
            max_length: Максимальная длина контекста (опционально, переопределяет default)
            
        Returns:
            Отформатированный текст контекста для добавления в промпт
        """
        if not chunks:
            logger.info("⚠️ No chunks to build context from")
            return ""
        
        max_length = max_length or self.max_length
        
        logger.info(
            f"🔨 Формирование контекста из {len(chunks)} чанков "
            f"(max_length={max_length})"
        )
        
        # 1. Дедупликация
        unique_chunks = self.deduplicate(chunks)
        
        # 2. Форматирование
        context = self.format_context(unique_chunks)
        
        # 3. Обрезка
        context = self.truncate_context(context, max_length)
        
        logger.info(
            f"✅ Контекст сформирован: {len(context)} символов, "
            f"{len(unique_chunks)} уникальных чанков"
        )
        
        return context
















