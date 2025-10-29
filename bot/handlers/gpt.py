import logging
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.config import config
from keyboards.keyboards import ai_assistant_keyboard
from utils.formatters import (
    safe_edit_message,
    handle_telegram_errors,
)

import aiohttp

logger = logging.getLogger(__name__)

router = Router()


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