import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from api.client import bot_api_client
from keyboards.keyboards import wb_menu_keyboard, main_keyboard, create_analytics_keyboard
from utils.formatters import format_error_message, format_currency, format_percentage
from utils.formatters import safe_send_message, safe_edit_message
import os
import aiohttp
from core.config import config
# from gpt_integration.aggregator import aggregate
# from gpt_integration.pipeline import run_analysis

router = Router()



@router.callback_query(F.data == "analytics")
async def show_analytics_menu(callback: CallbackQuery):
    """Запуск AI-анализа (только из главного меню 'Аналитика')"""
    # Мгновенный фидбек пользователю
    await safe_edit_message(
        callback=callback,
        text="⏳ Запускаю AI‑анализ…",
        reply_markup=wb_menu_keyboard(),
        user_id=callback.from_user.id
    )

    # Вызов GPT-сервиса для запуска анализа
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
                        callback=callback,
                        text="✅ Анализ запущен. Я пришлю результаты сообщениями, как только будут готовы.",
                        reply_markup=wb_menu_keyboard(),
                        user_id=callback.from_user.id
                    )
                else:
                    body = await resp.text()
                    await safe_edit_message(
                        callback=callback,
                        text=f"❌ Не удалось запустить анализ.\nHTTP {resp.status}\n{body}",
                        reply_markup=wb_menu_keyboard(),
                        user_id=callback.from_user.id
                    )
    except Exception as e:
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка запроса к GPT‑сервису: {e}",
            reply_markup=wb_menu_keyboard(),
            user_id=callback.from_user.id
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("analytics_period_"))
async def show_analytics_period(callback: CallbackQuery):
    """Показать аналитику за выбранный период"""
    period = callback.data.split("_")[-1]
    
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period=period
    )
    
    if response.success and response.data:
        keyboard = create_analytics_keyboard(period=period)
        
        await callback.message.edit_text(
            response.telegram_text or "📈 Аналитика продаж",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки аналитики:\n\n{error_message}",
            reply_markup=create_analytics_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "refresh_analytics")
async def refresh_analytics(callback: CallbackQuery):
    """Обновить данные аналитики"""
    await callback.message.edit_text("⏳ Обновляю данные аналитики...")
    
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period="7d"
    )
    
    if response.success and response.data:
        keyboard = create_analytics_keyboard(period="7d")
        
        await callback.message.edit_text(
            response.telegram_text or "📈 Аналитика обновлена",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка обновления аналитики:\n\n{error_message}",
            reply_markup=create_analytics_keyboard()
        )
    
    await callback.answer("✅ Данные обновлены")


@router.callback_query(F.data == "dynamics")
async def show_dynamics(callback: CallbackQuery):
    """Показать динамику продаж"""
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period="7d"
    )
    
    if response.success and response.data:
        sales_periods = response.data.get("sales_periods", {})
        dynamics = response.data.get("dynamics", {})
        
        # Формируем текст для динамики
        text = "📈 ДИНАМИКА ПРОДАЖ\n\n"
        
        # Продажи по периодам
        text += "📊 ПРОДАЖИ ПО ПЕРИОДАМ:\n"
        for period, data in sales_periods.items():
            count = data.get("count", 0)
            amount = data.get("amount", 0)
            text += f"• {period.replace('_', ' ').title()}: {count} заказов на {format_currency(amount)}\n"
        
        text += "\n📈 ДИНАМИКА:\n"
        yesterday_growth = dynamics.get("yesterday_growth_percent", 0)
        week_growth = dynamics.get("week_growth_percent", 0)
        avg_check = dynamics.get("average_check", 0)
        conversion = dynamics.get("conversion_percent", 0)
        
        text += f"• Рост к вчера: {format_percentage(yesterday_growth)}\n"
        text += f"• Рост к прошлой неделе: {format_percentage(week_growth)}\n"
        text += f"• Средний чек: {format_currency(avg_check)}\n"
        text += f"• Конверсия: {conversion:.1f}%\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 К аналитике",
                callback_data="analytics"
            )]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки динамики:\n\n{error_message}",
            reply_markup=create_analytics_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "avg_check")
async def show_avg_check(callback: CallbackQuery):
    """Показать средний чек и конверсию"""
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period="7d"
    )
    
    if response.success and response.data:
        dynamics = response.data.get("dynamics", {})
        top_products = response.data.get("top_products", [])
        
        # Формируем текст для среднего чека
        text = "💰 СРЕДНИЙ ЧЕК И КОНВЕРСИЯ\n\n"
        
        avg_check = dynamics.get("average_check", 0)
        conversion = dynamics.get("conversion_percent", 0)
        
        text += f"💳 Средний чек: {format_currency(avg_check)}\n"
        text += f"📊 Конверсия: {conversion:.1f}%\n\n"
        
        if top_products:
            text += "🏆 ТОП ТОВАРЫ:\n"
            for i, product in enumerate(top_products[:3], 1):
                name = product.get("name", "Неизвестный товар")
                sales_count = product.get("sales_count", 0)
                sales_amount = product.get("sales_amount", 0)
                rating = product.get("rating", 0)
                
                text += f"{i}. {name}\n"
                text += f"   Продаж: {sales_count} шт. на {format_currency(sales_amount)}\n"
                text += f"   Рейтинг: {rating:.1f}⭐\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 К аналитике",
                callback_data="analytics"
            )]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки данных:\n\n{error_message}",
            reply_markup=create_analytics_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "sales_period")
async def show_sales_period(callback: CallbackQuery):
    """Показать аналитику продаж за период"""
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period="7d"
    )
    
    if response.success and response.data:
        keyboard = create_analytics_keyboard(period="7d")
        
        await callback.message.edit_text(
            response.telegram_text or "📈 Аналитика продаж",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await callback.message.edit_text(
            f"❌ Ошибка загрузки аналитики:\n\n{error_message}",
            reply_markup=create_analytics_keyboard()
        )
    
    await callback.answer()


@router.callback_query(F.data == "export_sales")
async def export_sales_to_google(callback: CallbackQuery):
    """Экспорт аналитики продаж в Google Sheets"""
    # TODO: Реализовать экспорт в Google Sheets
    await callback.message.edit_text(
        "📤 ЭКСПОРТ В GOOGLE SHEETS\n\n"
        "⚠️ Функция экспорта в Google Sheets будет доступна в следующей версии.\n\n"
        "Сейчас доступен просмотр аналитики продаж.",
        reply_markup=create_analytics_keyboard()
    )
    await callback.answer()


@router.message(Command("analytics"))
async def cmd_analytics(message: Message):
    """Команда /analytics"""
    response = await bot_api_client.get_analytics_sales(
        user_id=message.from_user.id,
        period="7d"
    )
    
    if response.success and response.data:
        keyboard = create_analytics_keyboard(period="7d")
        
        await message.answer(
            response.telegram_text or "📈 Аналитика продаж",
            reply_markup=keyboard
        )
    else:
        error_message = format_error_message(response.error, response.status_code)
        await message.answer(
            f"❌ Ошибка загрузки аналитики:\n\n{error_message}",
            reply_markup=main_keyboard()
        )


@router.callback_query(F.data == "llm_analysis")
async def llm_analysis(callback: CallbackQuery):
    """Запустить LLM‑анализ и отправить результаты чанками в Telegram"""
    period = "7d"
    # Обновляем сообщение, чтобы показать прогресс
    await safe_edit_message(
        callback=callback,
        text="⏳ Запускаю LLM‑анализ…",
        reply_markup=create_analytics_keyboard(period=period),
        user_id=callback.from_user.id
    )

    # Загружаем данные аналитики из Bot API
    response = await bot_api_client.get_analytics_sales(
        user_id=callback.from_user.id,
        period=period
    )

    if not (response.success and response.data):
        error_message = format_error_message(response.error, response.status_code)
        await safe_edit_message(
            callback=callback,
            text=f"❌ Ошибка загрузки аналитики для LLM:\n\n{error_message}",
            reply_markup=create_analytics_keyboard(period=period),
            user_id=callback.from_user.id
        )
        await callback.answer()
        return

    # Собираем DATA для LLM из доступных полей ответа
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
        # Поддержка неизвестных ключей через extra
        "extra": {
            "dynamics": response.data.get("dynamics") or {}
        }
    }

    # Временно отключен AI-анализ
    # try:
    #     assembled_data = aggregate(data_sources)
    # except Exception as e:
    #     await safe_edit_message(
    #         callback=callback,
    #         text=f"❌ Ошибка агрегации данных:\n\n{e}",
    #         reply_markup=create_analytics_keyboard(period=period),
    #         user_id=callback.from_user.id
    #     )
    #     await callback.answer()
    #     return

    # # Запускаем LLM анализ
    # try:
    #     result = run_analysis(
    #         data=assembled_data,
    #         validate=True
    #     )
    # except Exception as e:
    #     await safe_edit_message(
    #         callback=callback,
    #         text=f"❌ Ошибка выполнения LLM‑анализа:\n\n{e}",
    #         reply_markup=create_analytics_keyboard(period=period),
    #         user_id=callback.from_user.id
    #     )
    #     await callback.answer()
    #     return

    # Временно отключен AI-анализ - показываем базовую аналитику
    await safe_edit_message(
        callback=callback,
        text="📊 **Аналитика продаж**\n\n"
             "🤖 AI-анализ временно отключен.\n"
             "Используйте базовые отчеты для анализа данных.",
        reply_markup=create_analytics_keyboard(period=period),
        user_id=callback.from_user.id
    )

    # Финальное сообщение с клавиатурой
    # await safe_send_message(
    #     message=callback.message,
    #     text="✅ LLM‑анализ завершён",
    #     reply_markup=create_analytics_keyboard(period=period),
    #     user_id=callback.from_user.id
    # )

    await callback.answer("Готово")