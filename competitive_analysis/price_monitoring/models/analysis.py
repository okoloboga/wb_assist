"""
Аналитическая модель CompetitorAnalysis.

Перенесена из competitor.py для снижения размеров файла и
улучшения модульности.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import statistics

if TYPE_CHECKING:
    # Только для подсказок типов, избегаем циклического импорта на рантайме
    from .competitor import Competitor


@dataclass
class CompetitorAnalysis:
    """
    Анализ конкурентов для конкретного товара.
    
    Attributes:
        product_id: ID анализируемого товара
        competitors: Список конкурентов
        analysis_date: Дата анализа
        market_position: Позиция на рынке
        price_recommendations: Рекомендации по ценообразованию
        metadata: Дополнительные метаданные анализа
    """
    
    product_id: str
    competitors: List['Competitor'] = field(default_factory=list)
    analysis_date: datetime = field(default_factory=datetime.now)
    market_position: Optional[str] = None
    price_recommendations: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_competitor(self, competitor: 'Competitor') -> None:
        """Добавление конкурента в анализ."""
        self.competitors.append(competitor)
    
    def get_all_competitor_prices(self) -> List[float]:
        """Получение всех цен конкурентов."""
        prices = []
        for competitor in self.competitors:
            for product in competitor.get_available_products():
                if product.current_price > 0:
                    prices.append(product.current_price)
        return prices
    
    def calculate_market_position(self, our_price: float) -> str:
        """
        Расчет позиции на рынке относительно конкурентов.
        
        Args:
            our_price: Наша цена
            
        Returns:
            Описание позиции на рынке
        """
        competitor_prices = self.get_all_competitor_prices()
        
        if not competitor_prices:
            return "Нет данных о конкурентах"
        
        min_price = min(competitor_prices)
        max_price = max(competitor_prices)
        avg_price = statistics.mean(competitor_prices)
        
        if our_price < min_price:
            position = "Лидер по цене (самая низкая цена)"
        elif our_price > max_price:
            position = "Премиум сегмент (самая высокая цена)"
        elif our_price <= avg_price:
            position = "Ниже среднего (конкурентная цена)"
        else:
            position = "Выше среднего"
        
        self.market_position = position
        return position
    
    def generate_price_recommendations(self, our_price: float) -> Dict[str, Any]:
        """
        Генерация рекомендаций по ценообразованию.
        
        Args:
            our_price: Наша текущая цена
            
        Returns:
            Словарь с рекомендациями
        """
        competitor_prices = self.get_all_competitor_prices()
        
        if not competitor_prices:
            return {
                'status': 'no_data',
                'message': 'Недостаточно данных о конкурентах'
            }
        
        min_price = min(competitor_prices)
        max_price = max(competitor_prices)
        avg_price = statistics.mean(competitor_prices)
        median_price = statistics.median(competitor_prices)
        
        recommendations = {
            'current_price': our_price,
            'market_stats': {
                'min_competitor_price': min_price,
                'max_competitor_price': max_price,
                'avg_competitor_price': avg_price,
                'median_competitor_price': median_price,
                'competitors_count': len(competitor_prices)
            },
            'recommendations': []
        }
        
        # Рекомендации на основе позиции
        if our_price > max_price:
            recommendations['recommendations'].append({
                'type': 'price_reduction',
                'message': 'Рассмотрите снижение цены для повышения конкурентоспособности',
                'suggested_price': max_price * 0.95,
                'potential_savings': our_price - (max_price * 0.95)
            })
        elif our_price < min_price:
            recommendations['recommendations'].append({
                'type': 'price_increase',
                'message': 'Возможность повышения цены без потери конкурентоспособности',
                'suggested_price': min_price * 1.05,
                'potential_profit': (min_price * 1.05) - our_price
            })
        else:
            recommendations['recommendations'].append({
                'type': 'maintain',
                'message': 'Цена находится в конкурентном диапазоне',
                'suggested_price': our_price
            })
        
        self.price_recommendations = recommendations
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь."""
        return {
            'product_id': self.product_id,
            'competitors': [c.to_dict() for c in self.competitors],
            'analysis_date': self.analysis_date.isoformat(),
            'market_position': self.market_position,
            'price_recommendations': self.price_recommendations,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompetitorAnalysis':
        """Создание объекта из словаря."""
        from .competitor import Competitor  # Локальный импорт для избежания циклов
        if isinstance(data.get('analysis_date'), str):
            data['analysis_date'] = datetime.fromisoformat(data['analysis_date'])
        
        competitors = [Competitor.from_dict(c_data) 
                       for c_data in data.get('competitors', [])]
        data['competitors'] = competitors
        
        return cls(**data)


__all__ = [
    "CompetitorAnalysis",
]