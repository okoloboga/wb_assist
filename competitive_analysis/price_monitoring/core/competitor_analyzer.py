"""
Анализатор конкурентов для мониторинга цен.

Содержит основную логику для анализа конкурентов, сравнения цен,
поиска аналогичных товаров и создания рекомендаций по ценообразованию.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
import logging
import statistics
from abc import ABC, abstractmethod

# Импорты моделей
from ..models.product import Product
from ..models.price_history import PriceHistory, PriceHistoryEntry, PriceSource
from ..models.competitor import Competitor, CompetitorProduct, CompetitorAnalysis, MarketplaceType
from .exceptions import PriceMonitorError, ProductNotFoundError


class AnalysisStrategy(Enum):
    """Стратегии анализа конкурентов."""
    AGGRESSIVE = "aggressive"  # Агрессивная стратегия - низкие цены
    CONSERVATIVE = "conservative"  # Консервативная - средние цены
    PREMIUM = "premium"  # Премиум - высокие цены
    ADAPTIVE = "adaptive"  # Адаптивная - динамическое изменение


class PriceRecommendationType(Enum):
    """Типы рекомендаций по ценообразованию."""
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN = "maintain"
    MONITOR = "monitor"


@dataclass
class PriceRecommendation:
    """Рекомендация по ценообразованию."""
    product_id: str
    current_price: float
    recommended_price: float
    recommendation_type: PriceRecommendationType
    confidence: float  # Уверенность в рекомендации (0-1)
    reasoning: str
    market_position: str
    expected_impact: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CompetitorInsight:
    """Инсайт о конкуренте."""
    competitor_id: str
    competitor_name: str
    market_share: float
    price_strategy: str
    strengths: List[str]
    weaknesses: List[str]
    threat_level: str  # "low", "medium", "high"
    opportunities: List[str]


@dataclass
class MarketAnalysisResult:
    """Результат анализа рынка."""
    product_id: str
    analysis_date: datetime
    market_size: int  # Количество конкурентов
    our_position: int  # Позиция нашего товара (1 = лучшая цена)
    price_percentile: float  # Процентиль нашей цены
    market_average: float
    market_median: float
    price_range: Tuple[float, float]
    competitive_advantage: float
    recommendations: List[PriceRecommendation]
    insights: List[CompetitorInsight]


class CompetitorAnalyzer:
    """
    Основной класс для анализа конкурентов.
    
    Предоставляет функциональность для:
    - Сравнения цен с конкурентами
    - Поиска аналогичных товаров
    - Создания рекомендаций по ценообразованию
    - Анализа рыночной позиции
    """
    
    def __init__(self, strategy: AnalysisStrategy = AnalysisStrategy.ADAPTIVE):
        """
        Инициализация анализатора конкурентов.
        
        Args:
            strategy: Стратегия анализа
        """
        self.strategy = strategy
        self.logger = logging.getLogger(__name__)
        
        # Кэш для результатов анализа
        self._analysis_cache: Dict[str, MarketAnalysisResult] = {}
        self._cache_ttl = timedelta(hours=1)  # Время жизни кэша
        
        # Настройки анализа
        self.config = {
            "min_competitors": 3,  # Минимальное количество конкурентов для анализа
            "price_similarity_threshold": 0.15,  # Порог схожести цен (15%)
            "confidence_threshold": 0.7,  # Минимальная уверенность для рекомендаций
            "market_share_weight": 0.3,  # Вес доли рынка в анализе
            "price_weight": 0.4,  # Вес цены в анализе
            "trend_weight": 0.3,  # Вес тренда в анализе
        }
    
    def analyze_competitors(self, product: Product, competitors: List[Competitor], 
                          price_history: Optional[PriceHistory] = None) -> MarketAnalysisResult:
        """
        Анализирует конкурентов для товара.
        
        Args:
            product: Анализируемый товар
            competitors: Список конкурентов
            price_history: История цен (опционально)
            
        Returns:
            Результат анализа рынка
            
        Raises:
            ValueError: При недостаточном количестве конкурентов
        """
        if len(competitors) < self.config["min_competitors"]:
            raise ValueError(f"Недостаточно конкурентов для анализа. "
                           f"Минимум: {self.config['min_competitors']}, получено: {len(competitors)}")
        
        # Проверяем кэш
        cache_key = f"{product.id}_{hash(tuple(c.id for c in competitors))}"
        if cache_key in self._analysis_cache:
            cached_result = self._analysis_cache[cache_key]
            if datetime.now() - cached_result.analysis_date < self._cache_ttl:
                return cached_result
        
        # Извлекаем цены конкурентов
        competitor_prices = self._extract_competitor_prices(competitors)
        
        if not competitor_prices:
            raise ValueError("Нет действительных цен конкурентов")
        
        # Базовый анализ рынка
        market_stats = self._calculate_market_statistics(competitor_prices, product.current_price)
        
        # Определяем позицию товара
        position_data = self._calculate_market_position(product.current_price, competitor_prices)
        
        # Создаем рекомендации
        recommendations = self._generate_price_recommendations(
            product, competitors, market_stats, position_data, price_history
        )
        
        # Создаем инсайты о конкурентах
        insights = self._generate_competitor_insights(competitors, market_stats)
        
        # Формируем результат
        result = MarketAnalysisResult(
            product_id=product.id,
            analysis_date=datetime.now(),
            market_size=len(competitors),
            our_position=position_data["position"],
            price_percentile=position_data["percentile"],
            market_average=market_stats["average"],
            market_median=market_stats["median"],
            price_range=(market_stats["min_price"], market_stats["max_price"]),
            competitive_advantage=self._calculate_competitive_advantage(
                product.current_price, market_stats
            ),
            recommendations=recommendations,
            insights=insights
        )
        
        # Сохраняем в кэш
        self._analysis_cache[cache_key] = result
        
        self.logger.info(f"Анализ конкурентов для товара {product.id} завершен. "
                        f"Позиция: {position_data['position']}/{len(competitors) + 1}")
        
        return result
    
    def find_similar_products(self, target_product: Product, 
                            candidate_products: List[Product],
                            similarity_threshold: float = 0.8) -> List[Tuple[Product, float]]:
        """
        Находит аналогичные товары на основе различных критериев.
        
        Args:
            target_product: Целевой товар
            candidate_products: Список кандидатов
            similarity_threshold: Порог схожести (0-1)
            
        Returns:
            Список кортежей (товар, коэффициент схожести)
        """
        similar_products = []
        
        for candidate in candidate_products:
            if candidate.id == target_product.id:
                continue
            
            similarity_score = self._calculate_product_similarity(target_product, candidate)
            
            if similarity_score >= similarity_threshold:
                similar_products.append((candidate, similarity_score))
        
        # Сортируем по убыванию схожести
        similar_products.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Найдено {len(similar_products)} аналогичных товаров "
                        f"для {target_product.name}")
        
        return similar_products
    
    def generate_pricing_strategy(self, product: Product, 
                                competitors: List[Competitor],
                                target_margin: float = 0.2) -> Dict[str, Any]:
        """
        Генерирует стратегию ценообразования.
        
        Args:
            product: Товар
            competitors: Конкуренты
            target_margin: Целевая маржа
            
        Returns:
            Стратегия ценообразования
        """
        analysis = self.analyze_competitors(product, competitors)
        
        strategy = {
            "current_price": product.current_price,
            "strategy_type": self.strategy.value,
            "target_margin": target_margin,
            "market_position": analysis.our_position,
            "recommendations": [],
            "risk_assessment": {},
            "expected_outcomes": {}
        }
        
        # Генерируем рекомендации на основе стратегии
        if self.strategy == AnalysisStrategy.AGGRESSIVE:
            strategy.update(self._generate_aggressive_strategy(analysis, target_margin))
        elif self.strategy == AnalysisStrategy.CONSERVATIVE:
            strategy.update(self._generate_conservative_strategy(analysis, target_margin))
        elif self.strategy == AnalysisStrategy.PREMIUM:
            strategy.update(self._generate_premium_strategy(analysis, target_margin))
        else:  # ADAPTIVE
            strategy.update(self._generate_adaptive_strategy(analysis, target_margin))
        
        return strategy
    
    def _extract_competitor_prices(self, competitors: List[Competitor]) -> List[float]:
        """Извлекает действительные цены конкурентов."""
        prices = []
        for competitor in competitors:
            for product in competitor.products:
                if product.current_price > 0:
                    prices.append(product.current_price)
        return prices
    
    def _calculate_market_statistics(self, competitor_prices: List[float], 
                                   our_price: float) -> Dict[str, float]:
        """Рассчитывает статистики рынка."""
        all_prices = competitor_prices + [our_price]
        
        return {
            "average": statistics.mean(competitor_prices),
            "median": statistics.median(competitor_prices),
            "min_price": min(competitor_prices),
            "max_price": max(competitor_prices),
            "std_dev": statistics.stdev(competitor_prices) if len(competitor_prices) > 1 else 0,
            "market_average_with_us": statistics.mean(all_prices),
            "price_spread": max(competitor_prices) - min(competitor_prices)
        }
    
    def _calculate_market_position(self, our_price: float, 
                                 competitor_prices: List[float]) -> Dict[str, Any]:
        """Рассчитывает позицию товара на рынке."""
        all_prices = sorted(competitor_prices + [our_price])
        position = all_prices.index(our_price) + 1
        percentile = (len([p for p in competitor_prices if p > our_price]) / 
                     len(competitor_prices)) * 100
        
        return {
            "position": position,
            "total_positions": len(all_prices),
            "percentile": percentile,
            "is_cheapest": our_price == min(all_prices),
            "is_most_expensive": our_price == max(all_prices)
        }
    
    def _calculate_competitive_advantage(self, our_price: float, 
                                       market_stats: Dict[str, float]) -> float:
        """Рассчитывает конкурентное преимущество."""
        if market_stats["average"] == 0:
            return 0.0
        
        # Преимущество = (средняя цена рынка - наша цена) / средняя цена рынка
        advantage = (market_stats["average"] - our_price) / market_stats["average"]
        return round(advantage * 100, 2)  # В процентах
    
    def _calculate_product_similarity(self, product1: Product, product2: Product) -> float:
        """Рассчитывает коэффициент схожести товаров."""
        similarity_factors = []
        
        # Схожесть по категории
        if product1.category.lower() == product2.category.lower():
            similarity_factors.append(0.3)
        
        # Схожесть по бренду
        if product1.brand.lower() == product2.brand.lower():
            similarity_factors.append(0.2)
        
        # Схожесть по цене (в пределах 20%)
        price_diff = abs(product1.current_price - product2.current_price)
        max_price = max(product1.current_price, product2.current_price)
        if max_price > 0 and (price_diff / max_price) <= 0.2:
            similarity_factors.append(0.3)
        
        # Схожесть по названию (простая проверка общих слов)
        words1 = set(product1.name.lower().split())
        words2 = set(product2.name.lower().split())
        common_words = words1.intersection(words2)
        if len(common_words) > 0:
            word_similarity = len(common_words) / max(len(words1), len(words2))
            similarity_factors.append(word_similarity * 0.2)
        
        return sum(similarity_factors)
    
    def _generate_price_recommendations(self, product: Product, 
                                      competitors: List[Competitor],
                                      market_stats: Dict[str, float],
                                      position_data: Dict[str, Any],
                                      price_history: Optional[PriceHistory]) -> List[PriceRecommendation]:
        """Генерирует рекомендации по ценообразованию."""
        recommendations = []
        
        # Рекомендация на основе позиции на рынке
        if position_data["percentile"] > 80:  # Мы дороже 80% конкурентов
            rec = PriceRecommendation(
                product_id=product.id,
                current_price=product.current_price,
                recommended_price=market_stats["median"],
                recommendation_type=PriceRecommendationType.DECREASE,
                confidence=0.8,
                reasoning="Цена значительно выше рыночной медианы",
                market_position="expensive",
                expected_impact={"sales_increase": "15-25%", "margin_decrease": "moderate"}
            )
            recommendations.append(rec)
        
        elif position_data["percentile"] < 20:  # Мы дешевле 80% конкурентов
            rec = PriceRecommendation(
                product_id=product.id,
                current_price=product.current_price,
                recommended_price=market_stats["average"] * 0.95,
                recommendation_type=PriceRecommendationType.INCREASE,
                confidence=0.7,
                reasoning="Возможность увеличить маржу при сохранении конкурентоспособности",
                market_position="cheap",
                expected_impact={"margin_increase": "10-20%", "sales_impact": "minimal"}
            )
            recommendations.append(rec)
        
        else:  # Средняя позиция
            rec = PriceRecommendation(
                product_id=product.id,
                current_price=product.current_price,
                recommended_price=product.current_price,
                recommendation_type=PriceRecommendationType.MAINTAIN,
                confidence=0.9,
                reasoning="Цена находится в оптимальном диапазоне",
                market_position="optimal",
                expected_impact={"status": "maintain current performance"}
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _generate_competitor_insights(self, competitors: List[Competitor],
                                    market_stats: Dict[str, float]) -> List[CompetitorInsight]:
        """Генерирует инсайты о конкурентах."""
        insights = []
        
        for competitor in competitors[:5]:  # Топ-5 конкурентов
            avg_price = statistics.mean([p.current_price for p in competitor.products 
                                       if p.current_price > 0])
            
            # Определяем стратегию ценообразования
            if avg_price < market_stats["average"] * 0.9:
                price_strategy = "Низкие цены"
                threat_level = "high"
            elif avg_price > market_stats["average"] * 1.1:
                price_strategy = "Премиум"
                threat_level = "low"
            else:
                price_strategy = "Средние цены"
                threat_level = "medium"
            
            insight = CompetitorInsight(
                competitor_id=competitor.id,
                competitor_name=competitor.name,
                market_share=len(competitor.products) / sum(len(c.products) for c in competitors),
                price_strategy=price_strategy,
                strengths=self._identify_competitor_strengths(competitor, market_stats),
                weaknesses=self._identify_competitor_weaknesses(competitor, market_stats),
                threat_level=threat_level,
                opportunities=self._identify_opportunities(competitor, market_stats)
            )
            insights.append(insight)
        
        return insights
    
    def _identify_competitor_strengths(self, competitor: Competitor, 
                                     market_stats: Dict[str, float]) -> List[str]:
        """Определяет сильные стороны конкурента."""
        strengths = []
        
        avg_price = statistics.mean([p.current_price for p in competitor.products 
                                   if p.current_price > 0])
        
        if avg_price < market_stats["average"]:
            strengths.append("Конкурентные цены")
        
        if len(competitor.products) > 10:
            strengths.append("Широкий ассортимент")
        
        if competitor.marketplace == MarketplaceType.WILDBERRIES:
            strengths.append("Присутствие на Wildberries")
        
        return strengths
    
    def _identify_competitor_weaknesses(self, competitor: Competitor,
                                      market_stats: Dict[str, float]) -> List[str]:
        """Определяет слабые стороны конкурента."""
        weaknesses = []
        
        avg_price = statistics.mean([p.current_price for p in competitor.products 
                                   if p.current_price > 0])
        
        if avg_price > market_stats["average"] * 1.2:
            weaknesses.append("Высокие цены")
        
        if len(competitor.products) < 5:
            weaknesses.append("Ограниченный ассортимент")
        
        return weaknesses
    
    def _identify_opportunities(self, competitor: Competitor,
                              market_stats: Dict[str, float]) -> List[str]:
        """Определяет возможности в отношении конкурента."""
        opportunities = []
        
        avg_price = statistics.mean([p.current_price for p in competitor.products 
                                   if p.current_price > 0])
        
        if avg_price > market_stats["average"] * 1.1:
            opportunities.append("Возможность предложить более низкую цену")
        
        if len(competitor.products) < 10:
            opportunities.append("Возможность расширить ассортимент в этой нише")
        
        return opportunities
    
    def _generate_aggressive_strategy(self, analysis: MarketAnalysisResult,
                                    target_margin: float) -> Dict[str, Any]:
        """Генерирует агрессивную стратегию ценообразования."""
        return {
            "target_price": analysis.market_average * 0.9,  # На 10% ниже среднего
            "risk_level": "high",
            "expected_market_share_increase": "20-30%",
            "margin_impact": "negative"
        }
    
    def _generate_conservative_strategy(self, analysis: MarketAnalysisResult,
                                      target_margin: float) -> Dict[str, Any]:
        """Генерирует консервативную стратегию ценообразования."""
        return {
            "target_price": analysis.market_median,
            "risk_level": "low",
            "expected_market_share_increase": "5-10%",
            "margin_impact": "stable"
        }
    
    def _generate_premium_strategy(self, analysis: MarketAnalysisResult,
                                 target_margin: float) -> Dict[str, Any]:
        """Генерирует премиум стратегию ценообразования."""
        return {
            "target_price": analysis.market_average * 1.15,  # На 15% выше среднего
            "risk_level": "medium",
            "expected_market_share_increase": "0-5%",
            "margin_impact": "positive"
        }
    
    def _generate_adaptive_strategy(self, analysis: MarketAnalysisResult,
                                  target_margin: float) -> Dict[str, Any]:
        """Генерирует адаптивную стратегию ценообразования."""
        if analysis.our_position <= 3:  # Топ-3 позиции
            return self._generate_conservative_strategy(analysis, target_margin)
        elif analysis.price_percentile > 70:  # Дорогие
            return self._generate_aggressive_strategy(analysis, target_margin)
        else:  # Средние позиции
            return self._generate_premium_strategy(analysis, target_margin)