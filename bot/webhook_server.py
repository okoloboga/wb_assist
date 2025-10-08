"""
Webhook сервер для получения уведомлений от сервера
"""
import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

from core.config import config
from handlers.notifications import handle_new_order_notification, handle_critical_stocks_notification

logger = logging.getLogger(__name__)

# Создаем FastAPI приложение для webhook
webhook_app = FastAPI(title="Bot Webhook Server", version="1.0.0")

@webhook_app.post("/webhook/notifications")
async def receive_notification(request: Request):
    """Получение уведомления от сервера"""
    try:
        # Получаем данные из запроса
        data = await request.json()
        
        logger.info(f"📥 RECEIVED WEBHOOK: {data.get('type', 'unknown')}")
        logger.info(f"   Telegram ID: {data.get('telegram_id', 'N/A')}")
        logger.info(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        logger.info(f"   Data keys: {list(data.get('data', {}).keys())}")
        
        # Проверяем тип уведомления
        notification_type = data.get("type")
        telegram_id = data.get("telegram_id")
        notification_data = data.get("data", {})
        
        # Логируем детали данных
        if notification_type == "new_order":
            logger.info(f"📦 ORDER DATA:")
            logger.info(f"   Order ID: {notification_data.get('order_id', 'N/A')}")
            logger.info(f"   Amount: {notification_data.get('amount', 'N/A')}₽")
            logger.info(f"   Product: {notification_data.get('product_name', 'N/A')}")
            logger.info(f"   Brand: {notification_data.get('brand', 'N/A')}")
            logger.info(f"   Route: {notification_data.get('warehouse_from', 'N/A')} → {notification_data.get('warehouse_to', 'N/A')}")
            logger.info(f"   Today stats: {notification_data.get('today_stats', {})}")
            logger.info(f"   Stocks: {notification_data.get('stocks', {})}")
        
        if not notification_type or not telegram_id:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Обрабатываем уведомление в зависимости от типа
        if notification_type == "new_order":
            logger.info(f"🔄 Processing new order notification for user {telegram_id}")
            await handle_new_order_webhook(telegram_id, notification_data)
            logger.info(f"✅ New order notification processed successfully for user {telegram_id}")
        elif notification_type == "critical_stocks":
            logger.info(f"🔄 Processing critical stocks notification for user {telegram_id}")
            await handle_critical_stocks_webhook(telegram_id, notification_data)
            logger.info(f"✅ Critical stocks notification processed successfully for user {telegram_id}")
        else:
            logger.warning(f"❓ Unknown notification type: {notification_type}")
            return JSONResponse(content={"status": "ignored", "reason": "Unknown type"})
        
        logger.info(f"🎯 WEBHOOK COMPLETED: {notification_type} for user {telegram_id}")
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        logger.error(f"Error processing webhook notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_new_order_webhook(telegram_id: int, data: Dict[str, Any]):
    """Обработка webhook уведомления о новом заказе"""
    try:
        # Создаем бота для отправки сообщений
        from aiogram import Bot
        bot = Bot(token=config.bot_token)
        
        # Получаем полный формат заказа через API
        import aiohttp
        import asyncio
        
        # Ждем немного, чтобы заказ успел обработаться
        await asyncio.sleep(3)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://server:8000/api/v1/bot/orders/{data.get('order_id')}",
                params={"telegram_id": telegram_id},
                headers={"X-API-SECRET-KEY": "CnWvwoDwwGKh"}
            ) as response:
                if response.status == 200:
                    order_data = await response.json()
                    text = order_data.get("telegram_text", "🧾 Детали заказа")
                    logger.info(f"✅ Получен полный формат заказа {data.get('order_id')}")
                else:
                    # Fallback к полному формату
                    logger.warning(f"⚠️ API недоступен для заказа {data.get('order_id')}, используем полный формат")
                    order_id = data.get('order_id', 'N/A')
                    order_date = data.get('date', 'N/A')
                    brand = data.get('brand', 'N/A')
                    product_name = data.get('product_name', 'N/A')
                    nm_id = data.get('nm_id', 'N/A')
                    supplier_article = data.get('supplier_article', '')
                    size = data.get('size', '')
                    barcode = data.get('barcode', '')
                    warehouse_from = data.get('warehouse_from', 'N/A')
                    warehouse_to = data.get('warehouse_to', 'N/A')
                    order_amount = data.get('amount', 0)
                    commission_percent = data.get('commission_percent', 0)
                    commission_amount = data.get('commission_amount', 0)
                    spp_percent = data.get('spp_percent', 0)
                    customer_price = data.get('customer_price', 0)
                    logistics_amount = data.get('logistics_amount', 0)
                    dimensions = data.get('dimensions', '')
                    volume_liters = data.get('volume_liters', 0)
                    warehouse_rate_per_liter = data.get('warehouse_rate_per_liter', 0)
                    warehouse_rate_extra = data.get('warehouse_rate_extra', 0)
                    rating = data.get('rating', 0)
                    reviews_count = data.get('reviews_count', 0)
                    buyout_rates = data.get('buyout_rates', {})
                    order_speed = data.get('order_speed', {})
                    sales_periods = data.get('sales_periods', {})
                    category_availability = data.get('category_availability', '')
                    stocks = data.get('stocks', {})
                    stock_days = data.get('stock_days', {})
                    
                    text = f"🧾 Заказ [#{order_id}] {order_date}\n\n"
                    text += f"👑 {brand} ({brand})\n"
                    text += f"✏ Название: {product_name}\n"
                    text += f"🆔 {nm_id} / {supplier_article} / ({size})\n"
                    text += f"🎹 {barcode}\n"
                    text += f"🚛 {warehouse_from} ⟶ {warehouse_to}\n"
                    text += f"💰 Цена заказа: {order_amount:,.0f}₽\n"
                    text += f"💶 Комиссия WB: {commission_percent}% ({commission_amount:,.0f}₽)\n"
                    text += f"🛍 СПП: {spp_percent}% (Цена для покупателя: {customer_price:,.0f}₽)\n"
                    text += f"💶 Логистика WB: {logistics_amount:,.1f}₽\n"
                    text += f"        Габариты: {dimensions}. ({volume_liters}л.)\n"
                    text += f"        Тариф склада: {warehouse_rate_per_liter:,.1f}₽ за 1л. | {warehouse_rate_extra:,.1f}₽ за л. свыше)\n"
                    text += f"🌟 Оценка: {rating}\n"
                    text += f"💬 Отзывы: {reviews_count}\n"
                    text += f"⚖️ Выкуп/с учетом возврата (7/14/30):\n"
                    text += f"        {buyout_rates.get('7_days', 0):.1f}% / {buyout_rates.get('14_days', 0):.1f}% / {buyout_rates.get('30_days', 0):.1f}%\n"
                    text += f"💠 Скорость заказов за 7/14/30 дней:\n"
                    text += f"        {order_speed.get('7_days', 0):.2f} | {order_speed.get('14_days', 0):.1f} | {order_speed.get('30_days', 0):.1f} шт. в день\n"
                    text += f"📖 Продаж за 7 / 14 / 30 дней:\n"
                    text += f"        {sales_periods.get('7_days', 0)} | {sales_periods.get('14_days', 0)} | {sales_periods.get('30_days', 0)} шт.\n"
                    text += f"💈 Оборачиваемость категории 90:\n"
                    text += f"        {category_availability}\n"
                    text += f"📦 Остаток:\n"
                    for size in ["L", "M", "S", "XL"]:
                        stock_count = stocks.get(size, 0)
                        stock_days_count = stock_days.get(size, 0)
                        text += f"        {size} ({stock_count} шт.) ≈ на {stock_days_count} дн.\n"
        
        # Логируем текст сообщения
        logger.info(f"📤 SENDING MESSAGE to user {telegram_id}:")
        logger.info(f"   Text length: {len(text)} characters")
        logger.info(f"   Message preview: {text[:100]}...")
        
        # Отправляем сообщение пользователю
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"✅ New order notification sent to user {telegram_id}")
        
        # Закрываем сессию бота
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Error sending new order notification to user {telegram_id}: {e}")
        # Закрываем сессию бота в случае ошибки
        try:
            await bot.session.close()
        except:
            pass

async def handle_critical_stocks_webhook(telegram_id: int, data: Dict[str, Any]):
    """Обработка webhook уведомления о критичных остатках"""
    try:
        # Создаем бота для отправки сообщений
        from aiogram import Bot
        bot = Bot(token=config.bot_token)
        
        # Формируем текст уведомления
        text = f"⚠️ КРИТИЧНЫЕ ОСТАТКИ!\n\n"
        
        products = data.get("products", [])
        for product in products:
            text += f"📦 {product.get('name', 'N/A')}\n"
            text += f"   Остаток: {product.get('total_stock', 0)} шт\n"
            text += f"   Размеры: {product.get('stocks_summary', 'N/A')}\n\n"
        
        text += "💡 Проверьте остатки и пополните склад!"
        
        # Отправляем сообщение пользователю
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Critical stocks notification sent to user {telegram_id}")
        
        # Закрываем сессию бота
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Error sending critical stocks notification to user {telegram_id}: {e}")
        # Закрываем сессию бота в случае ошибки
        try:
            await bot.session.close()
        except:
            pass

@webhook_app.get("/health")
async def health_check():
    """Проверка здоровья webhook сервера"""
    return {"status": "healthy", "service": "bot-webhook"}

def start_webhook_server():
    """Запуск webhook сервера"""
    logger.info("Starting webhook server on port 8001")
    uvicorn.run(
        webhook_app,
        host="0.0.0.0",
        port=8001,
        log_level=config.log_level.lower()
    )

if __name__ == "__main__":
    start_webhook_server()
