import sys
from pathlib import Path

# Добавляем пути к модулям бота и корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parents[2]))

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from core.states import GPTStates
from keyboards.keyboards import ai_assistant_keyboard
from utils.formatters import safe_edit_message, safe_send_message, split_telegram_message, escape_markdown_v2

from gpt_integration.gpt_client import GPTClient, LLMConfig
from gpt_integration.template_loader import get_system_prompt
from gpt_integration.aggregator import aggregate
from gpt_integration.pipeline import run_analysis
from api.client import bot_api_client

logger = logging.getLogger(__name__)
router = Router()

# Глобальный клиент GPT, конфиг берется из окружения
try:
    _gpt_client = GPTClient()
except Exception as e:
    logger.error("GPTClient init error: %r", e)
    _gpt_client = None


@router.callback_query(F.data == "ai_chat")
async def start_ai_chat(callback: CallbackQuery, state: FSMContext):
    """Вход в режим GPT-чата из меню AI-помощника."""
    await state.set_state(GPTStates.gpt_chat)
    await state.update_data(gpt_history=[])

    # Сообщение пользователю
    text = (
        "🧠 GPT-чат активирован.\n\n"
        "Напишите вопрос или задачу.\n"
        "Чтобы выйти — отправьте команду /exit"
    )

    await safe_send_message(callback.message, escape_markdown_v2(text), user_id=callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "ai_examples")
async def ai_examples(callback: CallbackQuery):
    """Показать примеры запросов для GPT и LLM‑анализа."""
    examples = (
        "❓ Примеры запросов:\n\n"
        "• Сформируй сводку продаж и рекламных расходов за 7 дней.\n"
        "• Найди аномалии в динамике выкупов и конверсии.\n"
        "• Дай рекомендации по ТОП‑5 товарам: цена, контент, рекламные кампании.\n"
        "• Предложи действия по медленно продающимся позициям.\n"
        "• Подготовь таблицу для Google Sheets с ключевыми метриками.\n\n"
        "Для запуска LLM‑анализа перейдите в раздел 📈 Аналитика и нажмите ‘🤖 LLM‑анализ’."
    )
    await safe_edit_message(
        callback=callback,
        text=escape_markdown_v2(examples),
        reply_markup=ai_assistant_keyboard(),
        user_id=callback.from_user.id
    )
    await callback.answer()

@router.callback_query(F.data == "ai_export_gs")
async def ai_export_gs(callback: CallbackQuery):
    """Подготовить предварительный просмотр выгрузки в Google Sheets из LLM‑анализа."""
    period = "7d"
    await safe_edit_message(
        callback=callback,
        text="⏳ Готовлю выгрузку в Google Sheets…",
        reply_markup=ai_assistant_keyboard(),
        user_id=callback.from_user.id
    )

    # Загружаем данные и запускаем анализ, чтобы получить секцию sheets
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period=period
    )

    if not (response.success and response.data):
        await safe_edit_message(
            callback=callback,
            text=escape_markdown_v2("❌ Ошибка загрузки данных аналитики для выгрузки."),
            reply_markup=ai_assistant_keyboard(),
            user_id=callback.from_user.id
        )
        await callback.answer()
        return

    data_sources = {
        "meta": {"user_id": callback.from_user.id, "period": period},
        "sales": {
            "periods": response.data.get("sales_periods") or {},
            "metrics": {
                "avg_check": (response.data.get("dynamics") or {}).get("average_check"),
                "conversion_percent": (response.data.get("dynamics") or {}).get("conversion_percent"),
            },
        },
        "top_products": response.data.get("top_products") or [],
        "extra": {"dynamics": response.data.get("dynamics") or {}},
    }

    try:
        assembled_data = aggregate(data_sources)
        result = run_analysis(assembled_data, validate=True)
    except Exception as e:
        await safe_edit_message(
            callback=callback,
            text=escape_markdown_v2(f"❌ Ошибка подготовки выгрузки: {e}"),
            reply_markup=ai_assistant_keyboard(),
            user_id=callback.from_user.id
        )
        await callback.answer()
        return

    sheets = (result or {}).get("sheets") or {"headers": [], "rows": []}
    headers = sheets.get("headers") or []
    rows = sheets.get("rows") or []

    preview_lines = []
    if headers:
        preview_lines.append(" | ".join(map(str, headers)))
    for r in rows[:10]:  # ограничим предпросмотр первыми 10 строками
        if isinstance(r, (list, tuple)):
            preview_lines.append(" | ".join(map(lambda x: str(x) if x is not None else "", r)))
        else:
            preview_lines.append(str(r))

    preview_text = (
        "📤 Предпросмотр таблицы для Google Sheets\n\n" +
        ("\n".join(preview_lines) if preview_lines else "Нет данных для выгрузки.") +
        "\n\nПримечание: это текстовый предпросмотр. Интеграция с Google API будет добавлена позже."
    )

    await safe_send_message(
        message=callback.message,
        text=escape_markdown_v2(preview_text),
        user_id=callback.from_user.id
    )
    await callback.answer()

@router.message(Command("gpt"))
async def cmd_gpt(message: Message, state: FSMContext):
    """Вход в режим GPT-чата по команде /gpt."""
    await state.set_state(GPTStates.gpt_chat)
    await state.update_data(gpt_history=[])

    text = (
        "🧠 GPT-чат активирован.\n\n"
        "Напишите вопрос или задачу.\n"
        "Чтобы выйти — отправьте команду /exit"
    )
    await safe_send_message(message, escape_markdown_v2(text), user_id=message.from_user.id)


@router.message(Command("exit"))
async def cmd_exit(message: Message, state: FSMContext):
    """Выход из режима GPT-чата."""
    await state.clear()
    await safe_send_message(
        message,
        escape_markdown_v2("🔙 Вы вышли из GPT-режима. Выберите действие в меню AI-помощника."),
        reply_markup=ai_assistant_keyboard(),
        user_id=message.from_user.id,
    )


@router.message(GPTStates.gpt_chat, F.text)
async def handle_user_prompt(message: Message, state: FSMContext):
    """Обработка пользовательского запроса в режиме GPT-чата."""
    if _gpt_client is None:
        await safe_send_message(
            message,
            "⚠️ GPT клиент не инициализирован. Проверьте переменные окружения OPENAI_*.",
            user_id=message.from_user.id,
        )
        return

    data = await state.get_data()
    history = data.get("gpt_history", [])

    # Добавляем сообщение пользователя
    history.append({"role": "user", "content": message.text})

    # Обрезаем историю до последних 10 сообщений (без system)
    if len(history) > 10:
        history = history[-10:]

    # Добавляем системный промпт из окружения или из шаблона
    system_prompt = (_gpt_client.config.system_prompt if _gpt_client else None) or get_system_prompt()
    messages = history.copy()
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        answer_text = _gpt_client.complete_messages(messages)
    except Exception as e:
        logger.error("GPT request error for user %s: %r", message.from_user.id, e)
        await safe_send_message(
            message,
            "❌ Ошибка запроса к GPT. Попробуйте еще раз позже.",
            user_id=message.from_user.id,
        )
        return

    # Добавляем ответ ассистента в историю
    history.append({"role": "assistant", "content": answer_text})
    await state.update_data(gpt_history=history)

    # Если ответ длинный — отправляем частями, предварительно экранировав MarkdownV2
    parts = split_telegram_message(escape_markdown_v2(answer_text))
    for part in parts:
        await safe_send_message(message, part, user_id=message.from_user.id)


__all__ = ["router"]