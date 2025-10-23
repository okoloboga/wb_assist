import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.states import GPTStates
from core.config import config
from keyboards.keyboards import ai_assistant_keyboard
from utils.formatters import (
    safe_send_message,
    safe_edit_message,
    handle_telegram_errors,
    escape_markdown_v2,
    split_telegram_message,
)
from gpt_integration.gpt_client import GPTClient

import aiohttp

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


@router.callback_query(F.data == "ai_analysis")
@handle_telegram_errors
async def cb_ai_analysis(callback: CallbackQuery):
    """Запустить асинхронный AI-анализ через GPT сервис"""
    # Мгновенный фидбек пользователю
    await safe_edit_message(
        callback,
        "⏳ Запускаю AI‑анализ…",
        reply_markup=ai_assistant_keyboard(),
        user_id=callback.from_user.id,
    )

    # Формируем запрос к GPT сервису
    base_url = getattr(config, "gpt_service_url", None) or os.getenv("GPT_SERVICE_URL", "http://127.0.0.1:9000")
    endpoint = f"{base_url.rstrip('/')}/v1/analysis/start"
    payload = {"telegram_id": callback.from_user.id}
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": config.api_secret_key,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=config.request_timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    # Ответ может содержать job_id или статус — пока не используем
                    _ = await resp.text()
                    await safe_edit_message(
                        callback,
                        "✅ Анализ запущен. Я пришлю результаты сообщениями, как только будут готовы.",
                        reply_markup=ai_assistant_keyboard(),
                        user_id=callback.from_user.id,
                    )
                else:
                    body = await resp.text()
                    await safe_edit_message(
                        callback,
                        f"❌ Не удалось запустить анализ.\nHTTP {resp.status}\n{body}",
                        reply_markup=ai_assistant_keyboard(),
                        user_id=callback.from_user.id,
                    )
    except Exception as e:
        await safe_edit_message(
            callback,
            f"❌ Ошибка запроса к GPT‑сервису: {e}",
            reply_markup=ai_assistant_keyboard(),
            user_id=callback.from_user.id,
        )

    await callback.answer()