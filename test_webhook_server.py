#!/usr/bin/env python3
"""
Простой webhook сервер для тестирования получения уведомлений
"""
import asyncio
import json
from aiohttp import web, web_request
from datetime import datetime

class TestWebhookServer:
    """Простой webhook сервер для тестирования"""
    
    def __init__(self, port=9000):
        self.port = port
        self.app = web.Application()
        self.app.router.add_post('/webhook/notifications', self.handle_webhook)
        self.app.router.add_get('/health', self.health_check)
        self.received_notifications = []
    
    async def handle_webhook(self, request: web_request.Request):
        """Обработка webhook уведомлений"""
        try:
            # Получаем данные
            data = await request.json()
            
            # Логируем полученное уведомление
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🔔 [{timestamp}] Получено webhook уведомление:")
            print(f"📋 Тип: {data.get('type', 'unknown')}")
            print(f"👤 Пользователь: {data.get('user_id', 'unknown')}")
            print(f"📝 Данные: {json.dumps(data.get('data', {}), indent=2, ensure_ascii=False)}")
            print(f"💬 Telegram текст: {data.get('telegram_text', 'N/A')}")
            print("-" * 50)
            
            # Сохраняем для истории
            self.received_notifications.append({
                "timestamp": timestamp,
                "data": data
            })
            
            # Возвращаем успешный ответ
            return web.json_response({
                "success": True,
                "message": "Webhook received successfully",
                "timestamp": timestamp
            })
            
        except Exception as e:
            print(f"❌ Ошибка обработки webhook: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def health_check(self, request: web_request.Request):
        """Проверка здоровья сервера"""
        return web.json_response({
            "status": "healthy",
            "notifications_received": len(self.received_notifications),
            "timestamp": datetime.now().isoformat()
        })
    
    async def start(self):
        """Запуск сервера"""
        print(f"🚀 Запуск тестового webhook сервера на порту {self.port}")
        print(f"📡 Webhook URL: http://localhost:{self.port}/webhook/notifications")
        print(f"🏥 Health check: http://localhost:{self.port}/health")
        print("=" * 60)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print("✅ Webhook сервер запущен и готов к получению уведомлений")
        print("💡 Для остановки нажмите Ctrl+C")
        
        try:
            # Ждем бесконечно
            await asyncio.Future()
        except KeyboardInterrupt:
            print("\n🛑 Остановка webhook сервера...")
            await runner.cleanup()
            print("✅ Сервер остановлен")

async def main():
    """Главная функция"""
    server = TestWebhookServer(port=9000)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
