"""
Тесты для анализатора конкурентов.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ..core.competitor_analyzer import (
    CompetitorAnalyzer, AnalysisStrategy, PriceRecommendationType,
    PriceRecommendation, CompetitorInsight, MarketAnalysisResult
)
from ..models.product import Product
from ..models.competitor import Competitor, CompetitorProduct, MarketplaceType
from ..models.price_history import PriceHistory, PriceHistoryEntry, PriceSource


class TestCompetitorAnalyzer:
    """Тесты для класса CompetitorAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Создает экземпляр анализатора."""
        return CompetitorAnalyzer(strategy=AnalysisStrategy.ADAPTIVE)
    
    @pytest.fixture
    def sample_product(self):
        """Создает тестовый товар."""
        return Product(
            id="test_product_1",
            name="Тестовый товар",
            current_price=1000.0,
            category="Электроника",
            brand="TestBrand",
            marketplace="wildberries"
        )
    
    @pytest.fixture
    def sample_competitors(self):
        """Создает список тестовых конкурентов."""
        competitors = []
        
        # Конкурент 1 - дешевый
        competitor1 = Competitor(
            id="comp_1",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            products=[
                CompetitorProduct(
                    id="comp1_prod1",
                    name="Товар конкурента 1",
                    current_price=800.0,
                    category="Электроника",
                    brand="CompBrand1"
                )
            ]
        )
        
        # Конкурент 2 - средний
        competitor2 = Competitor(
            id="comp_2",
            name="Конкурент 2",
            marketplace=MarketplaceType.OZON,
            products=[
                CompetitorProduct(
                    id="comp2_prod1",
                    name="Товар конкурента 2",
                    current_price=1200.0,
                    category="Электроника",
                    brand="CompBrand2"
                )
            ]
        )
        
        # Конкурент 3 - дорогой
        competitor3 = Competitor(
            id="comp_3",
            name="Конкурент 3",
            marketplace=MarketplaceType.WILDBERRIES,
            products=[
                CompetitorProduct(
                    id="comp3_prod1",
                    name="Товар конкурента 3",
                    current_price=1500.0,
                    category="Электроника",
                    brand="CompBrand3"
                )
            ]
        )
        
        # Конкурент 4 - еще один средний
        competitor4 = Competitor(
            id="comp_4",
            name="Конкурент 4",
            marketplace=MarketplaceType.OZON,
            products=[
                CompetitorProduct(
                    id="comp4_prod1",
                    name="Товар конкурента 4",
                    current_price=950.0,
                    category="Электроника",
                    brand="CompBrand4"
                )
            ]
        )
        
        return [competitor1, competitor2, competitor3, competitor4]
    
    def test_analyzer_initialization(self):
        """Тест инициализации анализатора."""
        analyzer = CompetitorAnalyzer(strategy=AnalysisStrategy.AGGRESSIVE)
        
        assert analyzer.strategy == AnalysisStrategy.AGGRESSIVE
        assert analyzer.config["min_competitors"] == 3
        assert analyzer.config["confidence_threshold"] == 0.7
        assert len(analyzer._analysis_cache) == 0
    
    def test_analyze_competitors_success(self, analyzer, sample_product, sample_competitors):
        """Тест успешного анализа конкурентов."""
        result = analyzer.analyze_competitors(sample_product, sample_competitors)
        
        assert isinstance(result, MarketAnalysisResult)
        assert result.product_id == sample_product.id
        assert result.market_size == 4
        assert result.our_position in range(1, 6)  # Позиция от 1 до 5
        assert 0 <= result.price_percentile <= 100
        assert result.market_average > 0
        assert result.market_median > 0
        assert len(result.recommendations) > 0
        assert len(result.insights) > 0
    
    def test_analyze_competitors_insufficient_competitors(self, analyzer, sample_product):
        """Тест анализа с недостаточным количеством конкурентов."""
        competitors = [
            Competitor(
                id="comp_1",
                name="Единственный конкурент",
                marketplace=MarketplaceType.WILDBERRIES,
                products=[
                    CompetitorProduct(
                        id="prod_1",
                        name="Товар",
                        current_price=1000.0,
                        category="Электроника",
                        brand="Brand"
                    )
                ]
            )
        ]
        
        with pytest.raises(ValueError, match="Недостаточно конкурентов"):
            analyzer.analyze_competitors(sample_product, competitors)
    
    def test_analyze_competitors_no_valid_prices(self, analyzer, sample_product):
        """Тест анализа без действительных цен."""
        competitors = [
            Competitor(
                id=f"comp_{i}",
                name=f"Конкурент {i}",
                marketplace=MarketplaceType.WILDBERRIES,
                products=[
                    CompetitorProduct(
                        id=f"prod_{i}",
                        name=f"Товар {i}",
                        current_price=0.0,  # Недействительная цена
                        category="Электроника",
                        brand="Brand"
                    )
                ]
            ) for i in range(1, 5)
        ]
        
        with pytest.raises(ValueError, match="Нет действительных цен"):
            analyzer.analyze_competitors(sample_product, competitors)
    
    def test_find_similar_products(self, analyzer):
        """Тест поиска аналогичных товаров."""
        target_product = Product(
            id="target",
            name="iPhone 13 Pro",
            current_price=80000.0,
            category="Смартфоны",
            brand="Apple",
            marketplace="wildberries"
        )
        
        candidates = [
            Product(
                id="candidate1",
                name="iPhone 13",
                current_price=75000.0,
                category="Смартфоны",
                brand="Apple",
                marketplace="wildberries"
            ),
            Product(
                id="candidate2",
                name="Samsung Galaxy S21",
                current_price=70000.0,
                category="Смартфоны",
                brand="Samsung",
                marketplace="wildberries"
            ),
            Product(
                id="candidate3",
                name="Холодильник LG",
                current_price=50000.0,
                category="Бытовая техника",
                brand="LG",
                marketplace="wildberries"
            )
        ]
        
        similar_products = analyzer.find_similar_products(target_product, candidates, 0.5)
        
        assert len(similar_products) >= 1
        assert all(isinstance(item, tuple) and len(item) == 2 for item in similar_products)
        assert all(0 <= similarity <= 1 for _, similarity in similar_products)
        
        # Проверяем, что результаты отсортированы по убыванию схожести
        similarities = [similarity for _, similarity in similar_products]
        assert similarities == sorted(similarities, reverse=True)
    
    def test_generate_pricing_strategy_aggressive(self, sample_product, sample_competitors):
        """Тест генерации агрессивной стратегии."""
        analyzer = CompetitorAnalyzer(strategy=AnalysisStrategy.AGGRESSIVE)
        
        strategy = analyzer.generate_pricing_strategy(
            sample_product, sample_competitors, target_margin=0.2
        )
        
        assert strategy["strategy_type"] == "aggressive"
        assert strategy["target_margin"] == 0.2
        assert "current_price" in strategy
        assert "market_position" in strategy
        assert "risk_assessment" in strategy
        assert "expected_outcomes" in strategy
    
    def test_generate_pricing_strategy_conservative(self, sample_product, sample_competitors):
        """Тест генерации консервативной стратегии."""
        analyzer = CompetitorAnalyzer(strategy=AnalysisStrategy.CONSERVATIVE)
        
        strategy = analyzer.generate_pricing_strategy(
            sample_product, sample_competitors, target_margin=0.15
        )
        
        assert strategy["strategy_type"] == "conservative"
        assert strategy["target_margin"] == 0.15
    
    def test_generate_pricing_strategy_premium(self, sample_product, sample_competitors):
        """Тест генерации премиум стратегии."""
        analyzer = CompetitorAnalyzer(strategy=AnalysisStrategy.PREMIUM)
        
        strategy = analyzer.generate_pricing_strategy(
            sample_product, sample_competitors, target_margin=0.3
        )
        
        assert strategy["strategy_type"] == "premium"
        assert strategy["target_margin"] == 0.3
    
    def test_cache_functionality(self, analyzer, sample_product, sample_competitors):
        """Тест функциональности кэширования."""
        # Первый вызов - результат должен быть закэширован
        result1 = analyzer.analyze_competitors(sample_product, sample_competitors)
        
        # Второй вызов - должен вернуть закэшированный результат
        result2 = analyzer.analyze_competitors(sample_product, sample_competitors)
        
        assert result1.analysis_date == result2.analysis_date
        assert len(analyzer._analysis_cache) == 1
    
    def test_extract_competitor_prices(self, analyzer, sample_competitors):
        """Тест извлечения цен конкурентов."""
        prices = analyzer._extract_competitor_prices(sample_competitors)
        
        expected_prices = [800.0, 1200.0, 1500.0, 950.0]
        assert sorted(prices) == sorted(expected_prices)
    
    def test_calculate_market_statistics(self, analyzer):
        """Тест расчета статистик рынка."""
        competitor_prices = [800.0, 1200.0, 1500.0, 950.0]
        our_price = 1000.0
        
        stats = analyzer._calculate_market_statistics(competitor_prices, our_price)
        
        assert stats["average"] == 1112.5  # (800 + 1200 + 1500 + 950) / 4
        assert stats["median"] == 1075.0   # (950 + 1200) / 2
        assert stats["min_price"] == 800.0
        assert stats["max_price"] == 1500.0
        assert stats["price_spread"] == 700.0  # 1500 - 800
    
    def test_calculate_market_position(self, analyzer):
        """Тест расчета позиции на рынке."""
        our_price = 1000.0
        competitor_prices = [800.0, 1200.0, 1500.0, 950.0]
        
        position = analyzer._calculate_market_position(our_price, competitor_prices)
        
        assert position["position"] == 3  # 3-я позиция из 5
        assert position["total_positions"] == 5
        assert position["percentile"] == 50.0  # 2 из 4 конкурентов дороже
        assert not position["is_cheapest"]
        assert not position["is_most_expensive"]
    
    def test_calculate_competitive_advantage(self, analyzer):
        """Тест расчета конкурентного преимущества."""
        our_price = 1000.0
        market_stats = {"average": 1200.0}
        
        advantage = analyzer._calculate_competitive_advantage(our_price, market_stats)
        
        expected_advantage = ((1200.0 - 1000.0) / 1200.0) * 100
        assert advantage == round(expected_advantage, 2)
    
    def test_calculate_product_similarity(self, analyzer):
        """Тест расчета схожести товаров."""
        product1 = Product(
            id="1",
            name="iPhone 13 Pro Max",
            current_price=100000.0,
            category="Смартфоны",
            brand="Apple",
            marketplace="wildberries"
        )
        
        product2 = Product(
            id="2",
            name="iPhone 13 Pro",
            current_price=95000.0,
            category="Смартфоны",
            brand="Apple",
            marketplace="wildberries"
        )
        
        product3 = Product(
            id="3",
            name="Samsung Galaxy Note",
            current_price=50000.0,
            category="Бытовая техника",
            brand="Samsung",
            marketplace="wildberries"
        )
        
        # Высокая схожесть (одинаковые категория и бренд, похожие цены и названия)
        similarity_high = analyzer._calculate_product_similarity(product1, product2)
        
        # Низкая схожесть (разные категории, бренды, цены)
        similarity_low = analyzer._calculate_product_similarity(product1, product3)
        
        assert similarity_high > similarity_low
        assert 0 <= similarity_high <= 1
        assert 0 <= similarity_low <= 1
    
    def test_generate_price_recommendations(self, analyzer, sample_product, sample_competitors):
        """Тест генерации рекомендаций по ценам."""
        market_stats = {
            "average": 1112.5,
            "median": 1075.0,
            "min_price": 800.0,
            "max_price": 1500.0
        }
        
        position_data = {
            "position": 3,
            "total_positions": 5,
            "percentile": 50.0,
            "is_cheapest": False,
            "is_most_expensive": False
        }
        
        recommendations = analyzer._generate_price_recommendations(
            sample_product, sample_competitors, market_stats, position_data, None
        )
        
        assert len(recommendations) > 0
        assert all(isinstance(rec, PriceRecommendation) for rec in recommendations)
        assert all(rec.product_id == sample_product.id for rec in recommendations)
        assert all(0 <= rec.confidence <= 1 for rec in recommendations)
    
    def test_generate_competitor_insights(self, analyzer, sample_competitors):
        """Тест генерации инсайтов о конкурентах."""
        market_stats = {
            "average": 1112.5,
            "median": 1075.0,
            "min_price": 800.0,
            "max_price": 1500.0
        }
        
        insights = analyzer._generate_competitor_insights(sample_competitors, market_stats)
        
        assert len(insights) <= 5  # Максимум 5 инсайтов
        assert all(isinstance(insight, CompetitorInsight) for insight in insights)
        assert all(insight.threat_level in ["low", "medium", "high"] for insight in insights)
        assert all(0 <= insight.market_share <= 1 for insight in insights)


class TestPriceRecommendation:
    """Тесты для класса PriceRecommendation."""
    
    def test_price_recommendation_creation(self):
        """Тест создания рекомендации по цене."""
        rec = PriceRecommendation(
            product_id="test_product",
            current_price=1000.0,
            recommended_price=950.0,
            recommendation_type=PriceRecommendationType.DECREASE,
            confidence=0.8,
            reasoning="Цена выше рыночной",
            market_position="expensive",
            expected_impact={"sales_increase": "10%"}
        )
        
        assert rec.product_id == "test_product"
        assert rec.current_price == 1000.0
        assert rec.recommended_price == 950.0
        assert rec.recommendation_type == PriceRecommendationType.DECREASE
        assert rec.confidence == 0.8
        assert isinstance(rec.created_at, datetime)


class TestCompetitorInsight:
    """Тесты для класса CompetitorInsight."""
    
    def test_competitor_insight_creation(self):
        """Тест создания инсайта о конкуренте."""
        insight = CompetitorInsight(
            competitor_id="comp_1",
            competitor_name="Конкурент 1",
            market_share=0.25,
            price_strategy="Низкие цены",
            strengths=["Конкурентные цены", "Широкий ассортимент"],
            weaknesses=["Низкое качество"],
            threat_level="high",
            opportunities=["Улучшить качество"]
        )
        
        assert insight.competitor_id == "comp_1"
        assert insight.competitor_name == "Конкурент 1"
        assert insight.market_share == 0.25
        assert insight.threat_level == "high"
        assert len(insight.strengths) == 2
        assert len(insight.weaknesses) == 1
        assert len(insight.opportunities) == 1


class TestMarketAnalysisResult:
    """Тесты для класса MarketAnalysisResult."""
    
    def test_market_analysis_result_creation(self):
        """Тест создания результата анализа рынка."""
        result = MarketAnalysisResult(
            product_id="test_product",
            analysis_date=datetime.now(),
            market_size=5,
            our_position=2,
            price_percentile=75.0,
            market_average=1200.0,
            market_median=1100.0,
            price_range=(800.0, 1500.0),
            competitive_advantage=15.5,
            recommendations=[],
            insights=[]
        )
        
        assert result.product_id == "test_product"
        assert result.market_size == 5
        assert result.our_position == 2
        assert result.price_percentile == 75.0
        assert result.competitive_advantage == 15.5
        assert isinstance(result.analysis_date, datetime)


if __name__ == "__main__":
    pytest.main([__file__])