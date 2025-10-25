"""
Webhook handlers для получения уведомлений от сервера
"""
import logging
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fastapi import FastAPI, Request, HTTPException, Header, status, Depends
from fastapi.responses import JSONResponse
import json

from core.config import config

# Создаем роутер
router = Router()

# Создаем FastAPI приложение для webhook
webhook_app = FastAPI()
# Удалены импорты неиспользуемых функций

logger = logging.getLogger(__name__)


class WebhookStates(StatesGroup):
    """Состояния для настройки webhook"""
    waiting_for_webhook_url = State()


# @router.message(Command("webhook"))
# async def setup_webhook_command(message: Message, state: FSMContext):
#     """Команда для настройки webhook URL"""
#     await message.answer(
#         "🔗 **Настройка Webhook**\n\n"
#         "Для получения уведомлений в реальном времени нужно настроить webhook URL.\n\n"
#         "Введите URL вашего бота (например: https://your-bot-domain.com/webhook/notifications):",
#         parse_mode="Markdown"
#     )
#     await state.set_state(WebhookStates.waiting_for_webhook_url)


# @router.message(WebhookStates.waiting_for_webhook_url)
# async def process_webhook_url(message: Message, state: FSMContext):
#     """Обработка введенного webhook URL"""
#     # Закомментировано - webhook настраивается автоматически
#     pass

# @router.message(Command("cancel"))
# async def cancel_webhook_setup(message: Message, state: FSMContext):
#     """Отмена настройки webhook"""
#     # Закомментировано - webhook настраивается автоматически
#     pass


# Автоматический webhook endpoint с telegram_id в URL
@webhook_app.post("/webhook/notifications/{telegram_id}")
async def receive_auto_webhook(
    telegram_id: int,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Автоматический webhook endpoint для получения уведомлений от сервера.
    URL: /webhook/notifications/{telegram_id}
    """
    try:
        payload_body = await request.body()
        notification_data = json.loads(payload_body)

        # Получаем telegram_id из payload для проверки
        payload_telegram_id = notification_data.get("telegram_id")
        user_id = notification_data.get("user_id")
        
        # Проверяем соответствие telegram_id в URL и payload
        if payload_telegram_id and payload_telegram_id != telegram_id:
            logger.warning(f"Telegram ID mismatch: URL={telegram_id}, payload={payload_telegram_id}")
            # Используем telegram_id из URL (более надежно)
            telegram_id_to_use = telegram_id
        else:
            telegram_id_to_use = telegram_id
        
        logger.info(f"Processing webhook for telegram_id={telegram_id_to_use}, user_id={user_id}")

        telegram_text = notification_data.get("telegram_text")
        notification_type = notification_data.get("type")

        if not telegram_text:
            logger.error(f"Invalid webhook payload: missing telegram_text. Payload: {notification_data}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

        # Полностью отключаем проверку подписи для тестирования
        # TODO: Включить проверку подписи после настройки секретов
        logger.info(f"Webhook signature verification disabled for user {telegram_id}")

        logger.info(f"Received auto webhook notification for user {telegram_id} (type: {notification_type})")

        # Обрабатываем уведомление напрямую через отправку сообщения
        # Получаем экземпляр бота из глобального контекста
        from __main__ import bot
        
        # Для sync_completed уведомлений показываем dashboard с клавиатурой
        if notification_type == "sync_completed":
            # Извлекаем data из notification_data
            data = notification_data.get("data", {})
            is_first_sync = data.get("is_first_sync", False)
            
            if is_first_sync:
                # Первая синхронизация - показываем dashboard с клавиатурой
                from keyboards.keyboards import wb_menu_keyboard
                from api.client import bot_api_client
                
                try:
                    # Получаем dashboard данные (используем user_id как в старой версии)
                    dashboard_response = await bot_api_client.get_dashboard(user_id=telegram_id)
                    
                    if dashboard_response.success:
                        # Используем полный dashboard текст из API
                        dashboard_text = dashboard_response.telegram_text or "📊 Дашборд загружен"
                        
                        # Добавляем заголовок о завершении синхронизации
                        text = f"🎉 **ПЕРВАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!**\n\n"
                        text += f"✅ {telegram_text}\n\n"
                        text += "📊 Ваши данные готовы к использованию:\n\n"
                        text += dashboard_text
                        
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=text,
                            reply_markup=wb_menu_keyboard(),
                            parse_mode="Markdown"
                        )
                    else:
                        # Фолбэк если dashboard недоступен
                        text = f"🎉 **ПЕРВАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!**\n\n"
                        text += f"✅ {telegram_text}\n\n"
                        text += "📊 Ваши данные готовы к использованию."
                        
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=text,
                            reply_markup=wb_menu_keyboard(),
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    logger.error(f"Error getting dashboard for telegram_id {telegram_id}: {e}")
                    # Фолбэк при ошибке - показываем меню
                    text = f"🎉 **ПЕРВАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!**\n\n"
                    text += f"✅ {telegram_text}\n\n"
                    text += "📊 Ваши данные готовы к использованию."
                    
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=text,
                        reply_markup=wb_menu_keyboard(),
                        parse_mode="Markdown"
                    )
            else:
                # Последующие синхронизации - только уведомление
                await bot.send_message(
                    chat_id=telegram_id,
                    text=telegram_text,
                    parse_mode="Markdown"
                )
        else:
            # Для других типов уведомлений просто отправляем готовый текст
            await bot.send_message(
                chat_id=telegram_id,
                text=telegram_text,
                parse_mode="MarkdownV2" if notification_type == "analysis_completed" else "Markdown"
            )
        
        logger.info(f"✅ Webhook notification sent to telegram_id {telegram_id}")

        return {"status": "success", "message": "Auto webhook notification received and processed"}

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received for auto webhook")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing auto webhook notification: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}")


def _verify_signature(payload_body: bytes, secret: str, signature: str) -> bool:
    """
    Проверяет HMAC-SHA256 подпись webhook'а.
    """
    if not secret:
        logger.warning("Webhook secret not configured, skipping signature verification.")
        return True  # Если секрет не настроен, пропускаем проверку (для dev)

    if not signature or not signature.startswith("sha256="):
        logger.error("Invalid or missing X-Webhook-Signature header.")
        return False

    hash_algorithm, hex_digest = signature.split("=", 1)
    if hash_algorithm != "sha256":
        logger.error(f"Unsupported hash algorithm: {hash_algorithm}")
        return False

    hmac_obj = hmac.new(secret.encode('utf-8'), payload_body, hashlib.sha256)
    expected_signature = hmac_obj.hexdigest()

    return hmac.compare_digest(expected_signature, hex_digest)


# Удалена функция handle_webhook_notification - теперь используется простой подход


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Проверка подписи webhook для безопасности
    
    Args:
        payload: Тело запроса
        signature: Подпись из заголовка
        secret: Секретный ключ
    
    Returns:
        bool: True если подпись верна
    """
    try:
        if not signature.startswith("sha256="):
            return False
        
        # Убираем "sha256=" префикс
        received_signature = signature[7:]
        
        # Генерируем ожидаемую подпись
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем подписи безопасно
        return hmac.compare_digest(received_signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


async def handle_sync_completed_notification(bot: Bot, telegram_id: int, data: Dict[str, Any]):
    """Обработка уведомления о завершении синхронизации"""
    try:
        is_first_sync = data.get("is_first_sync", False)
        cabinet_id = data.get("cabinet_id")
        message = data.get("message", "Синхронизация завершена успешно")
        
        if is_first_sync:
            # Первая синхронизация - показываем главное меню
            from keyboards.keyboards import wb_menu_keyboard
            from api.client import bot_api_client
            
            # Получаем дашборд для показа главного меню
            dashboard_response = await bot_api_client.get_dashboard(telegram_id=telegram_id)
            
            if dashboard_response.success:
                text = f"🎉 **ПЕРВАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!**\n\n"
                text += f"✅ {message}\n\n"
                text += "📊 Выберите действие:"
                
                await safe_send_message(
                    bot, telegram_id, text, 
                    reply_markup=wb_menu_keyboard()
                )
            else:
                # Фолбэк если дашборд недоступен
                text = f"🎉 **ПЕРВАЯ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!**\n\n"
                text += f"✅ {message}"
                
                await safe_send_message(bot, telegram_id, text)
        else:
            # Последующие синхронизации - только уведомление без меню
            text = f"✅ **СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА**\n\n"
            text += f"{message}\n\n"
            text += "🔄 Данные обновлены в фоновом режиме."
            
            await safe_send_message(bot, telegram_id, text)
            
    except Exception as e:
        logger.error(f"Error handling sync completed notification: {e}")


async def safe_send_message(bot: Bot, telegram_id: int, text: str, reply_markup=None):
    """Безопасная отправка сообщения с обработкой ошибок"""
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        logger.info(f"Message sent successfully to telegram_id {telegram_id}")
    except Exception as e:
        logger.error(f"Error sending message to telegram_id {telegram_id}: {e}")


# Удалены проблемные функции с неправильными импортами - теперь используется простой подход


# Все проблемные функции с неправильными импортами удалены - теперь используется простой подход

@webhook_app.get("/health")
async def webhook_health():
    return {"status": "ok"}
