"""
Шаблон анализа конкурентов для мониторинга цен.

Содержит классы и методы для создания детального анализа конкурентов,
включая расчет метрик, KPI, визуализацию данных и сравнительный анализ.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
import json
import statistics
from abc import ABC, abstractmethod

# Импорты моделей
from ..models.product import Product
from ..models.price_history import PriceHistory, PriceHistoryEntry
from ..models.competitor import Competitor


class CompetitorMetric(Enum):
    """Метрики для анализа конкурентов."""
    PRICE_ADVANTAGE = "price_advantage"
    MARKET_SHARE = "market_share"
    PRICE_VOLATILITY = "price_volatility"
    COMPETITIVE_INDEX = "competitive_index"
    POSITIONING_SCORE = "positioning_score"


class AnalysisTimeframe(Enum):
    """Временные рамки для анализа."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class CompetitorKPI:
    """KPI для анализа конкурента."""
    competitor_id: str
    competitor_name: str
    average_price: float
    price_volatility: float
    market_position: int
    price_trend: str  # "increasing", "decreasing", "stable"
    competitive_advantage: float
    last_price_change: datetime
    price_change_frequency: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует KPI в словарь."""
        return {
            "competitor_id": self.competitor_id,
            "competitor_name": self.competitor_name,
            "average_price": self.average_price,
            "price_volatility": self.price_volatility,
            "market_position": self.market_position,
            "price_trend": self.price_trend,
            "competitive_advantage": self.competitive_advantage,
            "last_price_change": self.last_price_change.isoformat(),
            "price_change_frequency": self.price_change_frequency
        }


@dataclass
class MarketAnalysis:
    """Анализ рынка для товара."""
    product_id: str
    product_name: str
    our_price: float
    market_average: float
    market_median: float
    price_percentile: float
    competitors_count: int
    price_range: Tuple[float, float]
    market_leader: str
    price_leader: str
    our_market_position: int
    competitive_gap: float
    recommended_price: float
    potential_savings: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует анализ в словарь."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "our_price": self.our_price,
            "market_average": self.market_average,
            "market_median": self.market_median,
            "price_percentile": self.price_percentile,
            "competitors_count": self.competitors_count,
            "price_range": {"min": self.price_range[0], "max": self.price_range[1]},
            "market_leader": self.market_leader,
            "price_leader": self.price_leader,
            "our_market_position": self.our_market_position,
            "competitive_gap": self.competitive_gap,
            "recommended_price": self.recommended_price,
            "potential_savings": self.potential_savings
        }


@dataclass
class VisualizationData:
    """Данные для визуализации."""
    chart_type: str
    title: str
    data: Dict[str, Any]
    labels: List[str]
    colors: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CompetitorAnalysisTemplate:
    """
    Шаблон для анализа конкурентов.
    
    Предоставляет методы для расчета метрик, KPI и создания
    сравнительного анализа конкурентов.
    """
    
    def __init__(self, timeframe: AnalysisTimeframe = AnalysisTimeframe.WEEKLY):
        """
        Инициализация шаблона анализа конкурентов.
        
        Args:
            timeframe: Временные рамки для анализа
        """
        self.timeframe = timeframe
        self.competitor_kpis: List[CompetitorKPI] = []
        self.market_analyses: List[MarketAnalysis] = []
        self.visualizations: List[VisualizationData] = []
        self.created_at = datetime.now()
    
    def analyze_product_competitors(self, product: Product, 
                                  competitors: List[Competitor],
                                  price_history: Optional[PriceHistory] = None) -> MarketAnalysis:
        """
        Анализирует конкурентов для конкретного товара.
        
        Args:
            product: Товар для анализа
            competitors: Список конкурентов
            price_history: История цен (опционально)
            
        Returns:
            Анализ рынка для товара
        """
        if not competitors:
            raise ValueError("Список конкурентов не может быть пустым")
        
        # Извлекаем цены конкурентов
        competitor_prices = [comp.current_price for comp in competitors if comp.current_price > 0]
        
        if not competitor_prices:
            raise ValueError("Нет действительных цен конкурентов")
        
        # Расчет базовых метрик
        market_average = statistics.mean(competitor_prices)
        market_median = statistics.median(competitor_prices)
        min_price, max_price = min(competitor_prices), max(competitor_prices)
        
        # Определяем позицию нашего товара
        all_prices = competitor_prices + [product.current_price]
        sorted_prices = sorted(all_prices)
        our_position = sorted_prices.index(product.current_price) + 1
        
        # Расчет перцентиля
        price_percentile = (len([p for p in competitor_prices if p <= product.current_price]) / len(competitor_prices)) * 100
        
        # Поиск лидеров рынка
        market_leader = self._find_market_leader(competitors)
        price_leader = self._find_price_leader(competitors)
        
        # Расчет конкурентного разрыва
        competitive_gap = product.current_price - market_average
        
        # Рекомендуемая цена (стратегия: чуть ниже медианы)
        recommended_price = market_median * 0.95
        potential_savings = product.current_price - recommended_price
        
        analysis = MarketAnalysis(
            product_id=product.id,
            product_name=product.name,
            our_price=product.current_price,
            market_average=market_average,
            market_median=market_median,
            price_percentile=price_percentile,
            competitors_count=len(competitors),
            price_range=(min_price, max_price),
            market_leader=market_leader,
            price_leader=price_leader,
            our_market_position=our_position,
            competitive_gap=competitive_gap,
            recommended_price=recommended_price,
            potential_savings=potential_savings
        )
        
        self.market_analyses.append(analysis)
        return analysis
    
    def calculate_competitor_kpis(self, competitors: List[Competitor],
                                price_history: Optional[PriceHistory] = None) -> List[CompetitorKPI]:
        """
        Рассчитывает KPI для каждого конкурента.
        
        Args:
            competitors: Список конкурентов
            price_history: История цен
            
        Returns:
            Список KPI конкурентов
        """
        kpis = []
        
        for competitor in competitors:
            # Базовые метрики
            avg_price = competitor.current_price
            volatility = 0.0
            trend = "stable"
            last_change = competitor.last_updated
            change_frequency = 0
            
            # Если есть история цен, рассчитываем дополнительные метрики
            if price_history:
                competitor_history = price_history.get_competitor_history(competitor.id)
                if competitor_history:
                    prices = [entry.price for entry in competitor_history]
                    avg_price = statistics.mean(prices)
                    
                    if len(prices) > 1:
                        volatility = statistics.stdev(prices)
                        trend = self._calculate_price_trend(prices)
                        change_frequency = len([i for i in range(1, len(prices)) 
                                              if prices[i] != prices[i-1]])
            
            # Позиция на рынке (упрощенная)
            all_competitors = sorted(competitors, key=lambda x: x.current_price)
            market_position = all_competitors.index(competitor) + 1
            
            # Конкурентное преимущество (относительно средней цены)
            market_avg = statistics.mean([c.current_price for c in competitors])
            competitive_advantage = (market_avg - competitor.current_price) / market_avg * 100
            
            kpi = CompetitorKPI(
                competitor_id=competitor.id,
                competitor_name=competitor.name,
                average_price=avg_price,
                price_volatility=volatility,
                market_position=market_position,
                price_trend=trend,
                competitive_advantage=competitive_advantage,
                last_price_change=last_change,
                price_change_frequency=change_frequency
            )
            
            kpis.append(kpi)
        
        self.competitor_kpis = kpis
        return kpis
    
    def generate_price_comparison_chart(self, product: Product, 
                                      competitors: List[Competitor]) -> VisualizationData:
        """
        Генерирует данные для графика сравнения цен.
        
        Args:
            product: Наш товар
            competitors: Конкуренты
            
        Returns:
            Данные для визуализации
        """
        labels = [product.name] + [comp.name for comp in competitors]
        prices = [product.current_price] + [comp.current_price for comp in competitors]
        
        # Цвета: наш товар - синий, конкуренты - различные оттенки
        colors = ["#2E86AB"] + [f"#A23B72", "#F18F01", "#C73E1D", "#592E83", "#1B998B"][:len(competitors)]
        
        visualization = VisualizationData(
            chart_type="bar",
            title=f"Сравнение цен: {product.name}",
            data={"labels": labels, "values": prices},
            labels=labels,
            colors=colors,
            metadata={
                "product_id": product.id,
                "chart_description": "Сравнение цен нашего товара с конкурентами"
            }
        )
        
        self.visualizations.append(visualization)
        return visualization
    
    def generate_market_position_chart(self, analysis: MarketAnalysis) -> VisualizationData:
        """
        Генерирует данные для графика позиции на рынке.
        
        Args:
            analysis: Анализ рынка
            
        Returns:
            Данные для визуализации
        """
        # Создаем данные для scatter plot
        data = {
            "our_position": {
                "x": analysis.our_price,
                "y": analysis.our_market_position,
                "label": "Наша позиция"
            },
            "market_average": {
                "x": analysis.market_average,
                "y": analysis.competitors_count // 2,
                "label": "Средняя цена рынка"
            },
            "recommended": {
                "x": analysis.recommended_price,
                "y": analysis.our_market_position - 1,
                "label": "Рекомендуемая цена"
            }
        }
        
        visualization = VisualizationData(
            chart_type="scatter",
            title=f"Позиция на рынке: {analysis.product_name}",
            data=data,
            labels=["Наша позиция", "Средняя цена", "Рекомендуемая"],
            colors=["#2E86AB", "#F18F01", "#1B998B"],
            metadata={
                "product_id": analysis.product_id,
                "chart_description": "Позиционирование товара относительно конкурентов"
            }
        )
        
        self.visualizations.append(visualization)
        return visualization
    
    def generate_competitive_matrix(self, products: List[Product],
                                  competitors_map: Dict[str, List[Competitor]]) -> Dict[str, Any]:
        """
        Генерирует матрицу конкурентного анализа.
        
        Args:
            products: Список наших товаров
            competitors_map: Карта конкурентов для каждого товара
            
        Returns:
            Матрица конкурентного анализа
        """
        matrix = {
            "products": [],
            "summary": {
                "total_products": len(products),
                "average_competitive_gap": 0,
                "products_with_advantage": 0,
                "products_need_adjustment": 0
            }
        }
        
        total_gap = 0
        
        for product in products:
            if product.id not in competitors_map:
                continue
                
            competitors = competitors_map[product.id]
            analysis = self.analyze_product_competitors(product, competitors)
            
            product_data = {
                "product_id": product.id,
                "product_name": product.name,
                "current_price": product.current_price,
                "market_position": analysis.our_market_position,
                "competitive_status": self._determine_competitive_status(analysis),
                "price_adjustment_needed": abs(analysis.potential_savings) > product.current_price * 0.05,
                "recommended_action": self._recommend_action(analysis)
            }
            
            matrix["products"].append(product_data)
            total_gap += analysis.competitive_gap
            
            if analysis.competitive_gap < 0:
                matrix["summary"]["products_with_advantage"] += 1
            elif abs(analysis.potential_savings) > product.current_price * 0.05:
                matrix["summary"]["products_need_adjustment"] += 1
        
        matrix["summary"]["average_competitive_gap"] = total_gap / len(products) if products else 0
        
        return matrix
    
    def export_analysis_report(self, format_type: str = "json") -> Union[str, Dict[str, Any]]:
        """
        Экспортирует отчет анализа в указанном формате.
        
        Args:
            format_type: Формат экспорта ("json", "dict")
            
        Returns:
            Отчет в указанном формате
        """
        report = {
            "analysis_metadata": {
                "created_at": self.created_at.isoformat(),
                "timeframe": self.timeframe.value,
                "total_analyses": len(self.market_analyses),
                "total_competitors": len(self.competitor_kpis)
            },
            "market_analyses": [analysis.to_dict() for analysis in self.market_analyses],
            "competitor_kpis": [kpi.to_dict() for kpi in self.competitor_kpis],
            "visualizations": [
                {
                    "chart_type": viz.chart_type,
                    "title": viz.title,
                    "data": viz.data,
                    "metadata": viz.metadata
                }
                for viz in self.visualizations
            ]
        }
        
        if format_type == "json":
            return json.dumps(report, indent=2, ensure_ascii=False)
        else:
            return report
    
    def _find_market_leader(self, competitors: List[Competitor]) -> str:
        """Находит лидера рынка (упрощенная логика)."""
        if not competitors:
            return "Не определен"
        
        # Простая логика: конкурент с наибольшим количеством товаров или самой стабильной ценой
        return max(competitors, key=lambda x: x.name).name
    
    def _find_price_leader(self, competitors: List[Competitor]) -> str:
        """Находит ценового лидера."""
        if not competitors:
            return "Не определен"
        
        return min(competitors, key=lambda x: x.current_price).name
    
    def _calculate_price_trend(self, prices: List[float]) -> str:
        """Рассчитывает тренд цен."""
        if len(prices) < 2:
            return "stable"
        
        recent_prices = prices[-5:]  # Последние 5 цен
        if len(recent_prices) < 2:
            return "stable"
        
        trend_sum = sum(recent_prices[i] - recent_prices[i-1] for i in range(1, len(recent_prices)))
        
        if trend_sum > 0:
            return "increasing"
        elif trend_sum < 0:
            return "decreasing"
        else:
            return "stable"
    
    def _determine_competitive_status(self, analysis: MarketAnalysis) -> str:
        """Определяет конкурентный статус."""
        if analysis.price_percentile <= 25:
            return "Ценовое преимущество"
        elif analysis.price_percentile <= 50:
            return "Конкурентная позиция"
        elif analysis.price_percentile <= 75:
            return "Выше среднего"
        else:
            return "Высокая цена"
    
    def _recommend_action(self, analysis: MarketAnalysis) -> str:
        """Рекомендует действие на основе анализа."""
        if analysis.potential_savings > analysis.our_price * 0.1:
            return "Снизить цену"
        elif analysis.potential_savings < -analysis.our_price * 0.05:
            return "Можно повысить цену"
        else:
            return "Цена оптимальна"


class CompetitorAnalysisFactory:
    """Фабрика для создания анализов конкурентов."""
    
    @staticmethod
    def create_daily_analysis() -> CompetitorAnalysisTemplate:
        """Создает ежедневный анализ конкурентов."""
        return CompetitorAnalysisTemplate(AnalysisTimeframe.DAILY)
    
    @staticmethod
    def create_weekly_analysis() -> CompetitorAnalysisTemplate:
        """Создает еженедельный анализ конкурентов."""
        return CompetitorAnalysisTemplate(AnalysisTimeframe.WEEKLY)
    
    @staticmethod
    def create_monthly_analysis() -> CompetitorAnalysisTemplate:
        """Создает месячный анализ конкурентов."""
        return CompetitorAnalysisTemplate(AnalysisTimeframe.MONTHLY)
    
    @staticmethod
    def create_custom_analysis(timeframe: AnalysisTimeframe) -> CompetitorAnalysisTemplate:
        """Создает анализ с пользовательскими временными рамками."""
        return CompetitorAnalysisTemplate(timeframe)