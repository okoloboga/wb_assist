"""
Нагрузочное тестирование для Dashboard API с использованием Locust

Запуск:
    locust -f locustfile.py --host=http://localhost:8000

Веб-интерфейс:
    http://localhost:8089
"""

from locust import HttpUser, task, between
import random
import os


class DashboardUser(HttpUser):
    """Симуляция пользователя дашборда"""
    
    # Время ожидания между запросами (1-3 секунды)
    wait_time = between(1, 3)
    
    # API ключ из переменной окружения
    api_key = os.getenv("API_SECRET_KEY", "CnWvwoDwwGKh")
    
    # Тестовые telegram_id
    telegram_ids = [123, 456, 789, 1011, 1213]
    
    def on_start(self):
        """Выполняется при старте каждого пользователя"""
        self.telegram_id = random.choice(self.telegram_ids)
        self.headers = {"X-API-SECRET-KEY": self.api_key}
    
    @task(5)
    def get_warehouses(self):
        """Получение списка складов (высокий приоритет)"""
        self.client.get(
            f"/api/v1/bot/warehouses?telegram_id={self.telegram_id}",
            headers=self.headers,
            name="/warehouses"
        )
    
    @task(5)
    def get_sizes(self):
        """Получение списка размеров (высокий приоритет)"""
        self.client.get(
            f"/api/v1/bot/sizes?telegram_id={self.telegram_id}",
            headers=self.headers,
            name="/sizes"
        )
    
    @task(10)
    def get_analytics_summary(self):
        """Получение сводной статистики (очень высокий приоритет)"""
        period = random.choice(["7d", "30d", "60d", "90d", "180d"])
        self.client.get(
            f"/api/v1/bot/analytics/summary?telegram_id={self.telegram_id}&period={period}",
            headers=self.headers,
            name="/analytics/summary"
        )
    
    @task(8)
    def get_stocks_all(self):
        """Получение остатков (высокий приоритет)"""
        # Случайные параметры
        limit = random.choice([10, 15, 20, 50])
        offset = random.choice([0, 10, 20, 50])
        
        params = f"telegram_id={self.telegram_id}&limit={limit}&offset={offset}"
        
        # Иногда добавляем фильтры
        if random.random() > 0.5:
            warehouse = random.choice(["Коледино", "Казань", "Подольск"])
            params += f"&warehouse={warehouse}"
        
        if random.random() > 0.7:
            size = random.choice(["S", "M", "L", "XL"])
            params += f"&size={size}"
        
        if random.random() > 0.8:
            search = random.choice(["футболка", "джинсы", "куртка"])
            params += f"&search={search}"
        
        self.client.get(
            f"/api/v1/bot/stocks/all?{params}",
            headers=self.headers,
            name="/stocks/all"
        )
    
    @task(6)
    def get_analytics_sales(self):
        """Получение аналитики продаж (средний приоритет)"""
        period = random.choice(["7d", "30d", "60d", "90d", "180d"])
        self.client.get(
            f"/api/v1/bot/analytics/sales?telegram_id={self.telegram_id}&period={period}",
            headers=self.headers,
            name="/analytics/sales"
        )
    
    @task(3)
    def get_orders_recent(self):
        """Получение последних заказов (низкий приоритет)"""
        limit = random.choice([10, 20, 50])
        offset = random.choice([0, 10, 20])
        
        params = f"telegram_id={self.telegram_id}&limit={limit}&offset={offset}"
        
        # Иногда добавляем фильтр по статусу
        if random.random() > 0.5:
            status = random.choice(["active", "canceled"])
            params += f"&status={status}"
        
        self.client.get(
            f"/api/v1/bot/orders/recent?{params}",
            headers=self.headers,
            name="/orders/recent"
        )
    
    @task(2)
    def get_reviews_summary(self):
        """Получение отзывов (низкий приоритет)"""
        limit = random.choice([10, 20])
        offset = random.choice([0, 10])
        
        params = f"telegram_id={self.telegram_id}&limit={limit}&offset={offset}"
        
        # Иногда добавляем фильтр по рейтингу
        if random.random() > 0.6:
            rating = random.choice([1, 2, 3])
            params += f"&rating_threshold={rating}"
        
        self.client.get(
            f"/api/v1/bot/reviews/summary?{params}",
            headers=self.headers,
            name="/reviews/summary"
        )


class HeavyDashboardUser(HttpUser):
    """Симуляция пользователя с тяжелыми запросами"""
    
    wait_time = between(2, 5)
    api_key = os.getenv("API_SECRET_KEY", "CnWvwoDwwGKh")
    telegram_ids = [123, 456, 789]
    
    def on_start(self):
        self.telegram_id = random.choice(self.telegram_ids)
        self.headers = {"X-API-SECRET-KEY": self.api_key}
    
    @task(3)
    def get_stocks_with_search(self):
        """Остатки с поиском (тяжелый запрос)"""
        search_terms = ["футболка", "джинсы", "куртка", "платье", "обувь"]
        search = random.choice(search_terms)
        
        self.client.get(
            f"/api/v1/bot/stocks/all?telegram_id={self.telegram_id}&search={search}&limit=50",
            headers=self.headers,
            name="/stocks/all [search]"
        )
    
    @task(2)
    def get_stocks_with_multiple_filters(self):
        """Остатки с множественными фильтрами (тяжелый запрос)"""
        warehouses = "Коледино,Казань,Подольск"
        sizes = "S,M,L,XL"
        
        self.client.get(
            f"/api/v1/bot/stocks/all?telegram_id={self.telegram_id}&warehouse={warehouses}&size={sizes}&limit=100",
            headers=self.headers,
            name="/stocks/all [multiple filters]"
        )
    
    @task(1)
    def get_analytics_long_period(self):
        """Аналитика за длинный период (тяжелый запрос)"""
        self.client.get(
            f"/api/v1/bot/analytics/sales?telegram_id={self.telegram_id}&period=180d",
            headers=self.headers,
            name="/analytics/sales [180d]"
        )


class CacheTestUser(HttpUser):
    """Тестирование эффективности кэширования"""
    
    wait_time = between(0.5, 1)
    api_key = os.getenv("API_SECRET_KEY", "CnWvwoDwwGKh")
    telegram_id = 123
    
    def on_start(self):
        self.headers = {"X-API-SECRET-KEY": self.api_key}
    
    @task(10)
    def repeated_warehouses_request(self):
        """Повторные запросы складов (должны кэшироваться)"""
        self.client.get(
            f"/api/v1/bot/warehouses?telegram_id={self.telegram_id}",
            headers=self.headers,
            name="/warehouses [cache test]"
        )
    
    @task(10)
    def repeated_summary_request(self):
        """Повторные запросы статистики (должны кэшироваться)"""
        self.client.get(
            f"/api/v1/bot/analytics/summary?telegram_id={self.telegram_id}&period=30d",
            headers=self.headers,
            name="/analytics/summary [cache test]"
        )
    
    @task(5)
    def repeated_stocks_request(self):
        """Повторные запросы остатков (должны кэшироваться)"""
        self.client.get(
            f"/api/v1/bot/stocks/all?telegram_id={self.telegram_id}&limit=15&offset=0",
            headers=self.headers,
            name="/stocks/all [cache test]"
        )


# Сценарии нагрузочного тестирования

class LightLoad(HttpUser):
    """Легкая нагрузка: 10-20 пользователей"""
    tasks = [DashboardUser]
    wait_time = between(2, 5)


class MediumLoad(HttpUser):
    """Средняя нагрузка: 50-100 пользователей"""
    tasks = [DashboardUser, HeavyDashboardUser]
    wait_time = between(1, 3)


class HeavyLoad(HttpUser):
    """Тяжелая нагрузка: 100-200 пользователей"""
    tasks = [DashboardUser, HeavyDashboardUser, CacheTestUser]
    wait_time = between(0.5, 2)
