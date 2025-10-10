"""
Тесты для шаблона анализа конкурентов.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from ..templates.competitor_analysis_template import (
    CompetitorMetric,
    AnalysisTimeframe,
    CompetitorKPI,
    MarketAnalysis,
    VisualizationData,
    CompetitorAnalysisTemplate,
    CompetitorAnalysisFactory
)
from ..models.product import Product
from ..models.competitor import Competitor


class TestCompetitorMetric:
    """Тесты для enum CompetitorMetric."""
    
    def test_competitor_metric_values(self):
        """Тест значений метрик конкурентов."""
        assert CompetitorMetric.PRICE_ADVANTAGE.value == "price_advantage"
        assert CompetitorMetric.MARKET_SHARE.value == "market_share"
        assert CompetitorMetric.PRICE_VOLATILITY.value == "price_volatility"
        assert CompetitorMetric.COMPETITIVE_INDEX.value == "competitive_index"
        assert CompetitorMetric.POSITIONING_SCORE.value == "positioning_score"


class TestAnalysisTimeframe:
    """Тесты для enum AnalysisTimeframe."""
    
    def test_analysis_timeframe_values(self):
        """Тест значений временных рамок анализа."""
        assert AnalysisTimeframe.DAILY.value == "daily"
        assert AnalysisTimeframe.WEEKLY.value == "weekly"
        assert AnalysisTimeframe.MONTHLY.value == "monthly"
        assert AnalysisTimeframe.QUARTERLY.value == "quarterly"
        assert AnalysisTimeframe.YEARLY.value == "yearly"


class TestCompetitorKPI:
    """Тесты для класса CompetitorKPI."""
    
    def test_competitor_kpi_creation(self):
        """Тест создания KPI конкурента."""
        kpi = CompetitorKPI(
            competitor_id="comp_1",
            competitor_name="Конкурент А",
            average_price=950.0,
            price_volatility=5.2,
            market_position=2,
            price_trend="increasing",
            competitive_advantage=8.5,
            last_price_change=datetime.now(),
            price_change_frequency=3
        )
        
        assert kpi.competitor_id == "comp_1"
        assert kpi.competitor_name == "Конкурент А"
        assert kpi.average_price == 950.0
        assert kpi.price_volatility == 5.2
        assert kpi.market_position == 2
        assert kpi.price_trend == "increasing"
        assert kpi.competitive_advantage == 8.5
        assert kpi.price_change_frequency == 3
    
    def test_competitor_kpi_to_dict(self):
        """Тест преобразования KPI в словарь."""
        now = datetime.now()
        kpi = CompetitorKPI(
            competitor_id="comp_1",
            competitor_name="Конкурент А",
            average_price=950.0,
            price_volatility=5.2,
            market_position=2,
            price_trend="increasing",
            competitive_advantage=8.5,
            last_price_change=now,
            price_change_frequency=3
        )
        
        result = kpi.to_dict()
        
        assert isinstance(result, dict)
        assert result["competitor_id"] == "comp_1"
        assert result["competitor_name"] == "Конкурент А"
        assert result["average_price"] == 950.0
        assert result["last_price_change"] == now.isoformat()


class TestMarketAnalysis:
    """Тесты для класса MarketAnalysis."""
    
    def test_market_analysis_creation(self):
        """Тест создания рыночного анализа."""
        analysis = MarketAnalysis(
            product_id="prod_1",
            product_name="Продукт А",
            our_price=1000.0,
            market_average=1200.0,
            market_median=1150.0,
            price_percentile=25.0,
            competitors_count=5,
            price_range=(800.0, 1500.0),
            market_leader="Лидер рынка",
            price_leader="Ценовой лидер",
            our_market_position=2,
            competitive_gap=200.0,
            recommended_price=1100.0,
            potential_savings=100.0
        )
        
        assert analysis.product_id == "prod_1"
        assert analysis.product_name == "Продукт А"
        assert analysis.our_price == 1000.0
        assert analysis.market_average == 1200.0
        assert analysis.competitors_count == 5
        assert analysis.price_range == (800.0, 1500.0)
    
    def test_market_analysis_to_dict(self):
        """Тест преобразования анализа в словарь."""
        analysis = MarketAnalysis(
            product_id="prod_1",
            product_name="Продукт А",
            our_price=1000.0,
            market_average=1200.0,
            market_median=1150.0,
            price_percentile=25.0,
            competitors_count=5,
            price_range=(800.0, 1500.0),
            market_leader="Лидер рынка",
            price_leader="Ценовой лидер",
            our_market_position=2,
            competitive_gap=200.0,
            recommended_price=1100.0,
            potential_savings=100.0
        )
        
        result = analysis.to_dict()
        
        assert isinstance(result, dict)
        assert result["product_id"] == "prod_1"
        assert result["our_price"] == 1000.0
        assert result["price_range"]["min"] == 800.0
        assert result["price_range"]["max"] == 1500.0


class TestVisualizationData:
    """Тесты для класса VisualizationData."""
    
    def test_visualization_data_creation(self):
        """Тест создания данных для визуализации."""
        viz_data = VisualizationData(
            chart_type="bar",
            title="Квартальные продажи",
            data={"values": [100, 200, 150, 300]},
            labels=["Q1", "Q2", "Q3", "Q4"],
            colors=["#FF0000", "#00FF00", "#0000FF", "#FFFF00"]
        )
        
        assert viz_data.chart_type == "bar"
        assert viz_data.title == "Квартальные продажи"
        assert viz_data.data == {"values": [100, 200, 150, 300]}
        assert viz_data.labels == ["Q1", "Q2", "Q3", "Q4"]
        assert len(viz_data.colors) == 4


class TestCompetitorAnalysisTemplate:
    """Тесты для основного класса шаблона анализа конкурентов."""
    
    @pytest.fixture
    def template(self):
        """Фикстура для создания экземпляра шаблона."""
        return CompetitorAnalysisTemplate()
    
    @pytest.fixture
    def sample_product(self):
        """Фикстура с примером продукта."""
        product = Mock(spec=Product)
        product.id = "prod_1"
        product.name = "Тестовый продукт"
        product.current_price = 1000.0  # Используем float вместо Decimal
        product.last_updated = datetime.now()
        return product
    
    @pytest.fixture
    def sample_competitors(self):
        """Фикстура с примерами конкурентов."""
        competitors = []
        for i in range(3):
            competitor = Mock(spec=Competitor)
            competitor.id = f"comp_{i+1}"
            competitor.name = f"Конкурент {i+1}"
            competitor.current_price = float(1000 + i*100)
            competitor.last_updated = datetime.now() - timedelta(days=i)
            competitors.append(competitor)
        return competitors
    
    def test_template_initialization(self, template):
        """Тест инициализации шаблона."""
        assert template.timeframe == AnalysisTimeframe.WEEKLY
        assert template.competitor_kpis == []
        assert template.market_analyses == []
        assert template.visualizations == []
    
    def test_analyze_product_competitors(self, template, sample_product, sample_competitors):
        """Тест анализа конкурентов продукта."""
        result = template.analyze_product_competitors(sample_product, sample_competitors)
        
        assert isinstance(result, MarketAnalysis)
        assert result.product_id == "prod_1"
        assert result.product_name == "Тестовый продукт"
        assert result.our_price == 1000.0
        assert result.competitors_count == 3
    
    def test_calculate_competitor_kpis(self, template, sample_competitors):
        """Тест расчета KPI конкурентов."""
        kpis = template.calculate_competitor_kpis(sample_competitors)
        
        assert len(kpis) == 3
        assert all(isinstance(kpi, CompetitorKPI) for kpi in kpis)
        
        # Проверяем, что KPI созданы для всех конкурентов
        competitor_ids = [kpi.competitor_id for kpi in kpis]
        assert "comp_1" in competitor_ids
        assert "comp_2" in competitor_ids
        assert "comp_3" in competitor_ids
    
    def test_generate_price_comparison_chart(self, template, sample_product, sample_competitors):
        """Тест генерации графика сравнения цен."""
        chart_data = template.generate_price_comparison_chart(sample_product, sample_competitors)
        
        assert isinstance(chart_data, VisualizationData)
        assert chart_data.chart_type == "bar"
        assert chart_data.title == f"Сравнение цен: {sample_product.name}"
        assert len(chart_data.labels) == 4  # Наш продукт + 3 конкурента
    
    def test_generate_market_position_chart(self, template, sample_product, sample_competitors):
        """Тест генерации графика позиции на рынке."""
        # Сначала создаем анализ рынка
        analysis = template.analyze_product_competitors(sample_product, sample_competitors)
        
        chart_data = template.generate_market_position_chart(analysis)
        
        assert isinstance(chart_data, VisualizationData)
        assert chart_data.chart_type == "scatter"
        assert chart_data.title == f"Позиция на рынке: {analysis.product_name}"
        assert len(chart_data.labels) == 3
    
    def test_generate_competitive_matrix(self, template):
        """Тест создания конкурентной матрицы."""
        # Создаем тестовые продукты с правильными атрибутами
        products = []
        for i in range(2):
            product = Mock(spec=Product)
            product.id = f"prod_{i}"
            product.name = f"Продукт {i}"
            product.current_price = 1000.0 + i * 100
            products.append(product)
        
        # Создаем карту конкурентов
        competitors_map = {}
        for product in products:
            competitors = []
            for j in range(2):
                competitor = Mock(spec=Competitor)
                competitor.id = f"comp_{product.id}_{j}"
                competitor.name = f"Конкурент {j}"
                competitor.current_price = product.current_price + j * 50
                competitors.append(competitor)
            competitors_map[product.id] = competitors
        
        matrix = template.generate_competitive_matrix(products, competitors_map)
        
        assert isinstance(matrix, dict)
        assert "products" in matrix
        assert "summary" in matrix
        assert len(matrix["products"]) == 2
        assert matrix["summary"]["total_products"] == 2
    
    def test_export_analysis_report_json(self, template):
        """Тест экспорта отчета в JSON."""
        report = template.export_analysis_report("json")
        
        assert isinstance(report, str)
        # Проверяем, что это валидный JSON
        import json
        parsed = json.loads(report)
        assert "analysis_metadata" in parsed
        assert "market_analyses" in parsed
        assert "competitor_kpis" in parsed
        assert "visualizations" in parsed
    
    def test_export_analysis_report_html(self, template):
        """Тест экспорта отчета в dict формате."""
        report = template.export_analysis_report("dict")
        
        assert isinstance(report, dict)
        assert "analysis_metadata" in report
        assert "market_analyses" in report
        assert "competitor_kpis" in report
        assert "visualizations" in report


class TestCompetitorAnalysisFactory:
    """Тесты для фабрики шаблонов анализа конкурентов."""
    
    def test_create_daily_analysis(self):
        """Тест создания ежедневного анализа."""
        template = CompetitorAnalysisFactory.create_daily_analysis()
        
        assert isinstance(template, CompetitorAnalysisTemplate)
        assert template.timeframe == AnalysisTimeframe.DAILY
    
    def test_create_weekly_analysis(self):
        """Тест создания еженедельного анализа."""
        template = CompetitorAnalysisFactory.create_weekly_analysis()
        
        assert isinstance(template, CompetitorAnalysisTemplate)
        assert template.timeframe == AnalysisTimeframe.WEEKLY
    
    def test_create_monthly_analysis(self):
        """Тест создания ежемесячного анализа."""
        template = CompetitorAnalysisFactory.create_monthly_analysis()
        
        assert isinstance(template, CompetitorAnalysisTemplate)
        assert template.timeframe == AnalysisTimeframe.MONTHLY
    
    def test_create_custom_analysis(self):
        """Тест создания пользовательского анализа."""
        template = CompetitorAnalysisFactory.create_custom_analysis(AnalysisTimeframe.QUARTERLY)
        
        assert isinstance(template, CompetitorAnalysisTemplate)
        assert template.timeframe == AnalysisTimeframe.QUARTERLY


if __name__ == "__main__":
    pytest.main([__file__])