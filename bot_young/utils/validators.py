"""
Валидация данных
"""
import re
from typing import Optional


def parse_channel_link(text: str) -> Optional[str]:
    """
    Парсит ссылку или username публичного канала/группы.
    
    Для приватных чатов используется механизм пересылки сообщений,
    а этот парсер является фолбэком для публичных.
    
    Поддерживаемые форматы:
    - @chat_username
    - https://t.me/chat_username
    - t.me/chat_username
    
    Returns:
        @chat_username или None если формат неверный
    """
    text = text.strip()
    
    # Если уже в формате @username
    if text.startswith("@"):
        return text
    
    # Парсим URL (https://t.me/username или t.me/username)
    pattern = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)'
    match = re.match(pattern, text)
    
    if match:
        username = match.group(1)
        return f"@{username}"
    
    return None


def validate_time_format(time_str: str) -> bool:
    """
    Валидация формата времени HH:MM
    
    Returns:
        True если формат правильный, иначе False
    """
    pattern = r'^([0-1][0-9]|2[0-3]):([0-5][0-9])$'
    return bool(re.match(pattern, time_str))

