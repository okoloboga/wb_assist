import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

class WildberriesAPI:
    def __init__(self):
        self.api_key = os.getenv('WB_API_KEY')
        self.base_url = "https://statistics-api.wildberries.ru/api/v1/supplier"
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[List[Dict]]:
        """Базовый метод для выполнения запросов"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка запроса к {endpoint}: {e}")
            return None
    
    def get_orders(self, date_from: str = None) -> List[Dict]:
        """Получить заказы"""
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {'dateFrom': date_from, 'flag': 1}
        return self._make_request('orders', params) or []
    
    def get_sales(self, date_from: str = None) -> List[Dict]:
        """Получить продажи"""
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        params = {'dateFrom': date_from}
        return self._make_request('sales', params) or []
    
    def get_stocks(self) -> List[Dict]:
        """Получить остатки на складах"""
        return self._make_request('stocks') or []
    
    def get_prices(self) -> List[Dict]:
        """Получить цены товаров"""
        url = "https://discounts-prices-api.wildberries.ru/api/v1/list/goods/filter"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json() or []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка получения цен: {e}")
            return []