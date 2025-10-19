import pytest

from utils.formatters import escape_markdown_v2, split_telegram_message


def test_escape_markdown_v2_escapes_specials():
    text = "Тест _подчеркивание_ и *звезды* (скобки) [ссылки]! #хэш | труба {фигуры}"
    escaped = escape_markdown_v2(text)
    # Проверяем, что основные спецсимволы экранированы
    assert "\\_" in escaped
    assert "\\*" in escaped
    assert "\\(" in escaped and "\\)" in escaped
    assert "\\[" in escaped and "\\]" in escaped
    assert "\\!" in escaped
    assert "\\#" in escaped
    assert "\\|" in escaped
    assert "\\{" in escaped and "\\}" in escaped


def test_split_telegram_message_splits_long_text_by_lines():
    # Конструируем длинный текст с переносами строк
    part1 = "A" * 3000
    part2 = "B" * 3000
    text = part1 + "\n" + part2
    parts = split_telegram_message(text, limit=4000)
    assert len(parts) == 2
    assert parts[0] == part1 + "\n"
    assert parts[1] == part2
    assert len(parts[0]) <= 4000
    assert len(parts[1]) <= 4000