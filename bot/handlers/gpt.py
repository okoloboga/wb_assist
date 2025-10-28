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
# from gpt_integration.gpt_client import GPTClient  # Закомментировано - архитектурная проблема

import aiohttp

logger = logging.getLogger(__name__)

router = Router()

# Инъецируемый клиент для тестов Stage 2
_gpt_client = None


def _format_and_split(text: str) -> list[str]:
    md = escape_markdown_v2(text)
    return split_telegram_message(md)


@router.message(Command("gpt"))
@handle_telegram_errors
async def cmd_gpt(message: Message, state: FSMContext):
    """Вход в режим GPT-чата по команде /gpt"""
    await state.set_state(GPTStates.gpt_chat)
    # Инициализируем клиент для сессии чата
    global _gpt_client
    try:
        # _gpt_client = GPTClient.from_env()  # Закомментировано - архитектурная проблема
        _gpt_client = None  # Временная заглушка
    except Exception as e:
        logger.error(f"Не удалось инициализировать GPT клиент: {e}")
        _gpt_client = None
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
    # Инициализируем клиент для сессии чата
    global _gpt_client
    try:
        # _gpt_client = GPTClient.from_env()  # Закомментировано - архитектурная проблема
        _gpt_client = None  # Временная заглушка
    except Exception as e:
        logger.error(f"Не удалось инициализировать GPT клиент: {e}")
        _gpt_client = None
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


async def handle_user_prompt(message: Message, state: FSMContext):
    """Обработка сообщений пользователя в GPT-чате (использует инъецируемый _gpt_client)."""
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer(text="✍️ Пожалуйста, отправьте текстовый вопрос.")
        return

    # Используем инъецируемый клиент для тестов Stage 2
    global _gpt_client
    if _gpt_client is None:
        await message.answer(text="❌ GPT функционал временно отключен (архитектурная проблема).")
        return

    # Закомментировано - архитектурная проблема
    # try:
    #     messages = [{"role": "user", "content": user_text}]
    #     llm_text = _gpt_client.complete_messages(messages)
    # except Exception as e:
    #     logger.exception("LLM вызов завершился ошибкой")
    #     await message.answer(text=f"❌ Ошибка запроса к LLM: {e}")
    #     return

    # chunks = _format_and_split(llm_text) or ["(пустой ответ)"]
    # for chunk in chunks:
    #     await message.answer(text=chunk, parse_mode="MarkdownV2")
    
    # Временная заглушка
    await message.answer(text="🤖 GPT функционал временно недоступен. Обратитесь к старжеру для исправления архитектуры.")


@router.message(GPTStates.gpt_chat)
@handle_telegram_errors
async def gpt_chat_message(message: Message, state: FSMContext):
    """Проксирует обработку пользовательских сообщений в handle_user_prompt."""
    await handle_user_prompt(message, state)


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