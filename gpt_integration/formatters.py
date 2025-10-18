import re
from typing import List

TELEGRAM_MD_V2_SPECIALS = r"_[]()~`>#+-=|{}.!*"


def escape_markdown_v2(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2 Телеграма."""
    if not text:
        return ""
    return re.sub(f"([{re.escape(TELEGRAM_MD_V2_SPECIALS)}])", r"\\\\\1", text)


def split_telegram_message(text: str, limit: int = 4000) -> List[str]:
    """Разбивает длинный текст на части, не превышающие limit символов.
    Сохраняет границы по строкам, чтобы не разрывать слова.
    """
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    parts: List[str] = []
    buf: List[str] = []
    buf_len = 0

    for line in text.splitlines(keepends=True):
        if buf_len + len(line) > limit:
            parts.append("".join(buf))
            buf = [line]
            buf_len = len(line)
        else:
            buf.append(line)
            buf_len += len(line)

    if buf:
        parts.append("".join(buf))
    return parts


def truncate(text: str, max_len: int = 1000) -> str:
    """Обрезает текст до max_len с многоточием."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"