"""
Валидация данных
"""
import re
from typing import Optional


def parse_channel_link(text: str) -> Optional[str]:
    """
    Парсит ссылку или username канала
    
    Поддерживаемые форматы:
    - @channel
    - https://t.me/channel
    - t.me/channel
    
    Returns:
        @channel или None если формат неверный
    """
    text = text.strip()
    
    # Если уже в формате @channel
    if text.startswith("@"):
        return text
    
    # Парсим URL
    # https://t.me/channel или t.me/channel
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

