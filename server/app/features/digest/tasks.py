"""
Celery задачи для отправки сводок в каналы
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List

import aiohttp
import asyncio
import pytz

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from .crud import ChannelReportCRUD, DigestHistoryCRUD
from .service import DigestService
from .formatter import DigestFormatter

logger = logging.getLogger(__name__)


def get_bot_token() -> str:
    """Получить токен бота из переменных окружения"""
    token = os.getenv("BOT_YOUNG_TOKEN")
    if not token:
        raise ValueError("BOT_YOUNG_TOKEN not found in environment variables")
    return token


async def send_telegram_message(bot_token: str, chat_id: int, text: str) -> dict:
    """
    Отправить сообщение через Telegram Bot API
    
    Returns:
        dict с результатом отправки
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                result = await resp.json()
                return result
    except Exception as e:
        logger.error(f"Error sending telegram message: {e}")
        return {"ok": False, "description": str(e)}


@celery_app.task(bind=True)
def check_digest_schedule(self):
    """
    Задача выполняется каждую минуту.
    Проверяет, есть ли каналы для отправки сводки в текущую минуту.
    Учитывает timezone каждого канала.
    """
    try:
        db = SessionLocal()
        
        try:
            # Получаем текущее UTC время (timezone-aware)
            utc_tz = pytz.UTC
            current_utc = datetime.now(utc_tz)
            
            # Получаем все активные каналы
            all_channels = ChannelReportCRUD.get_all_active(db)
            
            # Фильтруем каналы по времени с учетом их timezone
            channels_to_process = []
            for channel in all_channels:
                try:
                    # Конвертируем текущее UTC время в timezone канала
                    channel_tz = pytz.timezone(channel.timezone)
                    current_local = current_utc.astimezone(channel_tz)
                    current_local_time = current_local.time().replace(second=0, microsecond=0)
                    
                    # Сравниваем с report_time канала
                    if current_local_time == channel.report_time:
                        channels_to_process.append(channel)
                        logger.info(
                            f"Channel {channel.id} matched: local time {current_local_time} "
                            f"({channel.timezone}) == scheduled {channel.report_time}"
                        )
                except Exception as e:
                    logger.error(f"Error checking channel {channel.id} timezone: {e}")
                    continue
            
            channels = channels_to_process
            
            logger.info(
                f"Found {len(channels)} channels to process. "
                f"Current UTC: {current_utc.strftime('%H:%M')}, checked {len(all_channels)} active channels"
            )
            
            # Отправляем задачи на отправку сводок
            for channel in channels:
                try:
                    send_digest_to_channel.delay(channel.id)
                    logger.info(f"Scheduled digest for channel {channel.id} ({channel.chat_title})")
                except Exception as e:
                    logger.error(f"Error scheduling digest for channel {channel.id}: {e}")
            
        finally:
            db.close()
        
        return {"status": "success", "channels_scheduled": len(channels)}
        
    except Exception as e:
        logger.error(f"Error in check_digest_schedule: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_digest_to_channel(self, channel_report_id: int):
    """
    Отправка ежедневной сводки в конкретный канал.
    
    Args:
        channel_report_id: ID записи из channel_reports
    """
    db = SessionLocal()
    
    try:
        # Получаем настройки канала
        channel = ChannelReportCRUD.get_by_id(db, channel_report_id)
        if not channel:
            logger.error(f"Channel {channel_report_id} not found")
            return {"status": "error", "error": "Channel not found"}
        
        logger.info(f"Processing digest for channel {channel.id} ({channel.chat_title})")
        
        # Получаем данные сводки
        service = DigestService(db)
        # Используем сегодняшнюю дату в timezone канала (дата отправки уведомления)
        channel_tz = pytz.timezone(channel.timezone)
        current_utc = datetime.now(pytz.UTC)
        current_local = current_utc.astimezone(channel_tz)
        # Сегодняшняя дата в timezone канала
        target_date = current_local.date()
        
        # Определяем временной диапазон последних 24 часов
        end_datetime = current_local
        start_datetime = end_datetime - timedelta(hours=24)
        
        logger.info(f"Using target_date: {target_date} for channel {channel.id} (current local time: {current_local.strftime('%Y-%m-%d %H:%M')})")
        data = service.get_daily_digest(channel.cabinet_id, target_date, start_datetime, end_datetime)
        
        # Форматируем текст с учетом timezone канала
        telegram_text = DigestFormatter.format_daily_digest(data, channel.timezone)
        
        # Отправляем через Telegram Bot API
        bot_token = get_bot_token()
        
        # Используем asyncio для отправки
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            send_telegram_message(bot_token, channel.chat_id, telegram_text)
        )
        loop.close()
        
        if result.get("ok"):
            # Успешная отправка
            message_id = result.get("result", {}).get("message_id")
            
            # Сохраняем в историю
            DigestHistoryCRUD.create(
                db=db,
                channel_report_id=channel.id,
                cabinet_id=channel.cabinet_id,
                chat_id=channel.chat_id,
                digest_date=target_date,
                status="sent",
                message_id=message_id
            )
            
            # Обновляем время последней отправки
            ChannelReportCRUD.update_last_sent(db, channel.id, datetime.utcnow())
            
            logger.info(f"Successfully sent digest to channel {channel.id}")
            return {"status": "success", "channel_id": channel.id, "message_id": message_id}
        else:
            # Ошибка отправки
            error_msg = result.get("description", "Unknown error")
            logger.error(f"Failed to send digest to channel {channel.id}: {error_msg}")
            
            # Сохраняем в историю с ошибкой
            DigestHistoryCRUD.create(
                db=db,
                channel_report_id=channel.id,
                cabinet_id=channel.cabinet_id,
                chat_id=channel.chat_id,
                digest_date=target_date,
                status="failed",
                error_message=error_msg
            )
            
            # Retry если это временная ошибка
            if "bot was blocked by the user" not in error_msg.lower():
                raise self.retry(exc=Exception(error_msg))
            
            return {"status": "failed", "error": error_msg}
    
    except Exception as e:
        logger.error(f"Error in send_digest_to_channel for channel {channel_report_id}: {e}")
        
        # Пробуем сохранить ошибку в историю
        try:
            channel = ChannelReportCRUD.get_by_id(db, channel_report_id)
            if channel:
                DigestHistoryCRUD.create(
                    db=db,
                    channel_report_id=channel.id,
                    cabinet_id=channel.cabinet_id,
                    chat_id=channel.chat_id,
                    digest_date=target_date,
                    status="failed",
                    error_message=str(e)
                )
        except:
            pass
        
        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {"status": "error", "error": str(e)}
    
    finally:
        db.close()

