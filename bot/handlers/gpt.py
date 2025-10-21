import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.states import GPTStates
from utils.formatters import (
    safe_send_message,
    safe_edit_message,
    handle_telegram_errors,
    escape_markdown_v2,
    split_telegram_message,
)
from gpt_integration.gpt_client import GPTClient

logger = logging.getLogger(__name__)

router = Router()


def _format_and_split(text: str) -> list[str]:
    md = escape_markdown_v2(text)
    return split_telegram_message(md)


@router.message(Command("gpt"))
@handle_telegram_errors
async def cmd_gpt(message: Message, state: FSMContext):
    """Вход в режим GPT-чата по команде /gpt"""
    await state.set_state(GPTStates.gpt_chat)
    await safe_send_message(
        message,
        "🤖 Вы вошли в режим AI-чат.\nНапишите вопрос для GPT.\n\nЧтобы выйти, используйте команду /exit",
        user_id=message.from_user.id,
    )


@router.callback_query(F.data == "ai_chat")
@handle_telegram_errors
async def cb_ai_chat(callback: CallbackQuery, state: FSMContext):
    """Вход в режим GPT-чата по кнопке 'AI-чат'"""
    await state.set_state(GPTStates.gpt_chat)
    await safe_edit_message(
        callback,
        "🤖 Режим AI-чат активирован.\nНапишите вопрос для GPT.\n\nЧтобы выйти, используйте команду /exit",
        user_id=callback.from_user.id,
    )


@router.message(Command("exit"))
@handle_telegram_errors
async def cmd_exit(message: Message, state: FSMContext):
    """Выход из режима GPT-чата"""
    await state.clear()
    await safe_send_message(
        message,
        "✅ Вы вышли из режима AI-чат. Возвращайтесь, когда будут вопросы!",
        user_id=message.from_user.id,
    )


@router.message(GPTStates.gpt_chat)
@handle_telegram_errors
async def gpt_chat_message(message: Message, state: FSMContext):
    """Обработка сообщений пользователя в GPT-чате"""
    user_text = (message.text or "").strip()
    if not user_text:
        await safe_send_message(
            message,
            "✍️ Пожалуйста, отправьте текстовый вопрос.",
            user_id=message.from_user.id,
        )
        return

    # Вызываем LLM через клиента
    try:
        client = GPTClient.from_env()
        messages = [{"role": "user", "content": user_text}]
        llm_text = client.complete_messages(messages)
    except Exception as e:
        logger.exception("LLM вызов завершился ошибкой")
        await safe_send_message(
            message,
            f"❌ Ошибка запроса к LLM: {e}",
            user_id=message.from_user.id,
        )
        return

    # Подготовка MarkdownV2 и отправка по частям
    chunks = _format_and_split(llm_text)
    if not chunks:
        chunks = ["(пустой ответ)"]

    for chunk in chunks:
        await safe_send_message(
            message,
            chunk,
            user_id=message.from_user.id,
            parse_mode="MarkdownV2",
        )