from datetime import datetime, timedelta
from typing import Dict, List
from .client import WildberriesAPI

class WBAnalytics:
    def __init__(self):
        self.api = WildberriesAPI()
    
    def get_daily_sales(self, days: int = 7) -> Dict:
        """Аналитика продаж по дням"""
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        sales = self.api.get_sales(date_from)
        
        daily_stats = {}
        for sale in sales:
            sale_date = sale['date'][:10]  # YYYY-MM-DD
            if sale_date not in daily_stats:
                daily_stats[sale_date] = {
                    'revenue': 0,
                    'orders': 0,
                    'items': 0
                }
            
            daily_stats[sale_date]['revenue'] += sale.get('totalPrice', 0)
            daily_stats[sale_date]['orders'] += 1
            daily_stats[sale_date]['items'] += sale.get('quantity', 0)
        
        return daily_stats
    
    def get_top_products(self, limit: int = 10) -> List[Dict]:
        """Топ товаров по продажам"""
        sales = self.api.get_sales()
        
        product_stats = {}
        for sale in sales:
            nm_id = sale.get('nmId')
            if nm_id not in product_stats:
                product_stats[nm_id] = {
                    'nmId': nm_id,
                    'name': sale.get('subject', 'Unknown'),
                    'revenue': 0,
                    'quantity': 0,
                    'orders': 0
                }
            
            product_stats[nm_id]['revenue'] += sale.get('totalPrice', 0)
            product_stats[nm_id]['quantity'] += sale.get('quantity', 0)
            product_stats[nm_id]['orders'] += 1
        
        return sorted(
            product_stats.values(), 
            key=lambda x: x['revenue'], 
            reverse=True
        )[:limit]
    
    def get_stock_analysis(self) -> Dict:
        """Анализ остатков"""
        stocks = self.api.get_stocks()
        
        analysis = {
            'total_sku': len(stocks),
            'total_quantity': sum(stock.get('quantity', 0) for stock in stocks),
            'zero_stock': len([s for s in stocks if s.get('quantity', 0) == 0]),
            'low_stock': len([s for s in stocks if 0 < s.get('quantity', 0) < 10]),
            'warehouses': {}
        }
        
        # Остатки по складам
        for stock in stocks:
            warehouse = stock.get('warehouseName', 'Unknown')
            if warehouse not in analysis['warehouses']:
                analysis['warehouses'][warehouse] = 0
            analysis['warehouses'][warehouse] += stock.get('quantity', 0)
        
        return analysis