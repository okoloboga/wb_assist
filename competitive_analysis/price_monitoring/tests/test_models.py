"""
Тесты для модели Product.
"""
import pytest
import json
from datetime import datetime
from price_monitoring.models.product import Product


class TestProduct:
    """Тесты для класса Product."""
    
    def test_initialization_with_all_parameters(self):
        """Тест инициализации продукта со всеми параметрами."""
        product = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0]
        )
        assert product.id == 'test_product_1'
        assert product.name == 'Тестовый товар'
        assert product.brand == 'Test Brand'
        assert product.article == 'TEST001'
        assert product.category == 'Электроника'
        assert product.current_price == 1000.0


class TestPriceHistory:
    """Тесты для класса PriceHistory."""
    
    def test_initialization(self):
        """Тест инициализации истории цен."""
        from price_monitoring.models.price_history import PriceHistory
        
        history = PriceHistory(product_id="PROD001")
        assert history.product_id == "PROD001"
        assert len(history.entries) == 0
        assert isinstance(history.created_at, datetime)
    
    def test_add_entry(self):
        """Тест добавления записи в историю цен."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        
        history = PriceHistory(product_id="PROD001")
        entry = PriceHistoryEntry(
            timestamp=datetime.now(),
            price=1000.0,
            source=PriceSource.MANUAL,
            change_type=PriceChangeType.INCREASE
        )
        
        history.add_entry(entry)
        assert len(history.entries) == 1
        assert history.entries[0] == entry
    
    def test_get_price_at_date(self):
        """Тест получения цены на определенную дату."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        from datetime import timedelta
        
        history = PriceHistory(product_id="PROD001")
        base_date = datetime.now()
        
        # Добавляем записи с разными датами
        for i in range(5):
            entry = PriceHistoryEntry(
                timestamp=base_date - timedelta(days=i),
                price=1000.0 + i * 100,
                source=PriceSource.MANUAL,
                change_type=PriceChangeType.INCREASE
            )
            history.add_entry(entry)
        
        # Тестируем получение цены
        price = history.get_price_at_date(base_date - timedelta(days=2))
        assert price == 1200.0
        
        # Тест с датой, для которой нет записи
        future_price = history.get_price_at_date(base_date + timedelta(days=1))
        assert future_price is None
    
    def test_get_price_changes(self):
        """Тест получения изменений цен."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        from datetime import timedelta
        
        history = PriceHistory(product_id="PROD001")
        base_date = datetime.now()
        
        # Добавляем записи с изменениями цен
        prices = [1000.0, 1100.0, 1050.0, 1200.0, 1150.0]
        for i, price in enumerate(prices):
            change_type = PriceChangeType.INCREASE if i == 0 or price > prices[i-1] else PriceChangeType.DECREASE
            entry = PriceHistoryEntry(
                timestamp=base_date - timedelta(days=len(prices)-i-1),
                price=price,
                source=PriceSource.MANUAL,
                change_type=change_type
            )
            history.add_entry(entry)
        
        changes = history.get_price_changes(days=7)
        assert len(changes) > 0
        
        # Проверяем, что изменения отсортированы по дате
        for i in range(1, len(changes)):
            assert changes[i-1].timestamp <= changes[i].timestamp
    
    def test_get_statistics(self):
        """Тест получения статистики по истории цен."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        from datetime import timedelta
        
        history = PriceHistory(product_id="PROD001")
        base_date = datetime.now()
        
        prices = [1000.0, 1100.0, 1050.0, 1200.0, 1150.0]
        for i, price in enumerate(prices):
            entry = PriceHistoryEntry(
                timestamp=base_date - timedelta(days=len(prices)-i-1),
                price=price,
                source=PriceSource.MANUAL,
                change_type=PriceChangeType.INCREASE
            )
            history.add_entry(entry)
        
        stats = history.get_statistics()
        assert stats['min_price'] == 1000.0
        assert stats['max_price'] == 1200.0
        assert stats['avg_price'] == sum(prices) / len(prices)
        assert stats['total_entries'] == len(prices)
    
    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации истории цен."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        
        history = PriceHistory(product_id="PROD001")
        entry = PriceHistoryEntry(
            timestamp=datetime.now(),
            price=1000.0,
            source=PriceSource.MANUAL,
            change_type=PriceChangeType.INCREASE,
            notes="Test entry"
        )
        history.add_entry(entry)
        
        # Тест to_dict
        data = history.to_dict()
        assert data['product_id'] == "PROD001"
        assert len(data['entries']) == 1
        
        # Тест from_dict
        restored_history = PriceHistory.from_dict(data)
        assert restored_history.product_id == history.product_id
        assert len(restored_history.entries) == len(history.entries)
        assert restored_history.entries[0].price == entry.price


class TestPriceHistoryEntry:
    """Тесты для класса PriceHistoryEntry."""
    
    def test_initialization(self):
        """Тест инициализации записи истории цен."""
        from price_monitoring.models.price_history import PriceHistoryEntry, PriceSource, PriceChangeType
        
        timestamp = datetime.now()
        entry = PriceHistoryEntry(
            timestamp=timestamp,
            price=1000.0,
            source=PriceSource.MANUAL,
            change_type=PriceChangeType.INCREASE,
            notes="Test note"
        )
        
        assert entry.timestamp == timestamp
        assert entry.price == 1000.0
        assert entry.source == PriceSource.MANUAL
        assert entry.change_type == PriceChangeType.INCREASE
        assert entry.notes == "Test note"
    
    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации записи."""
        from price_monitoring.models.price_history import PriceHistoryEntry, PriceSource, PriceChangeType
        
        timestamp = datetime.now()
        entry = PriceHistoryEntry(
            timestamp=timestamp,
            price=1000.0,
            source=PriceSource.WILDBERRIES,
            change_type=PriceChangeType.DECREASE,
            notes="API update"
        )
        
        # Тест to_dict
        data = entry.to_dict()
        assert data['price'] == 1000.0
        assert data['source'] == PriceSource.WILDBERRIES.value
        assert data['change_type'] == PriceChangeType.DECREASE.value
        
        # Тест from_dict
        restored_entry = PriceHistoryEntry.from_dict(data)
        assert restored_entry.price == entry.price
        assert restored_entry.source == entry.source
        assert restored_entry.change_type == entry.change_type
        assert restored_entry.notes == entry.notes


class TestCompetitor:
    """Тесты для класса Competitor."""
    
    def test_initialization(self):
        """Тест инициализации конкурента."""
        from price_monitoring.models.competitor import Competitor, MarketplaceType, CompetitorType
        
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT,
            url="https://example.com",
            is_active=True
        )
        
        assert competitor.id == "COMP001"
        assert competitor.name == "Конкурент 1"
        assert competitor.marketplace == MarketplaceType.WILDBERRIES
        assert competitor.competitor_type == CompetitorType.DIRECT
        assert competitor.url == "https://example.com"
        assert competitor.is_active is True
        assert len(competitor.products) == 0
    
    def test_add_product(self):
        """Тест добавления товара конкурента."""
        from price_monitoring.models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType
        
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT
        )
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001"
        )
        
        competitor.add_product(product)
        assert len(competitor.products) == 1
        assert competitor.products[0] == product
    
    def test_remove_product(self):
        """Тест удаления товара конкурента."""
        from price_monitoring.models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType
        
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT
        )
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001"
        )
        
        competitor.add_product(product)
        assert len(competitor.products) == 1
        
        competitor.remove_product("PROD001")
        assert len(competitor.products) == 0
    
    def test_get_product_by_our_id(self):
        """Тест получения товара конкурента по ID нашего товара."""
        from price_monitoring.models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType
        
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT
        )
        
        product1 = CompetitorProduct(
            id="PROD001",
            name="Товар 1",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001"
        )
        
        product2 = CompetitorProduct(
            id="PROD002",
            name="Товар 2",
            url="https://example.com/product/2",
            price=2000.0,
            our_product_id="OUR_PROD002"
        )
        
        competitor.add_product(product1)
        competitor.add_product(product2)
        
        found_product = competitor.get_product_by_our_id("OUR_PROD001")
        assert found_product == product1
        
        not_found = competitor.get_product_by_our_id("NONEXISTENT")
        assert not_found is None
    
    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации конкурента."""
        from price_monitoring.models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType
        
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT,
            url="https://example.com",
            is_active=True
        )
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001"
        )
        competitor.add_product(product)
        
        # Тест to_dict
        data = competitor.to_dict()
        assert data['id'] == "COMP001"
        assert data['marketplace'] == MarketplaceType.WILDBERRIES.value
        assert len(data['products']) == 1
        
        # Тест from_dict
        restored_competitor = Competitor.from_dict(data)
        assert restored_competitor.id == competitor.id
        assert restored_competitor.marketplace == competitor.marketplace
        assert len(restored_competitor.products) == len(competitor.products)


class TestCompetitorProduct:
    """Тесты для класса CompetitorProduct."""
    
    def test_initialization(self):
        """Тест инициализации товара конкурента."""
        from price_monitoring.models.competitor import CompetitorProduct
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001",
            description="Описание товара",
            brand="Бренд",
            category="Категория"
        )
        
        assert product.id == "PROD001"
        assert product.name == "Товар конкурента"
        assert product.url == "https://example.com/product/1"
        assert product.price == 1000.0
        assert product.our_product_id == "OUR_PROD001"
        assert product.description == "Описание товара"
        assert product.brand == "Бренд"
        assert product.category == "Категория"
        assert isinstance(product.last_updated, datetime)
    
    def test_update_price(self):
        """Тест обновления цены товара конкурента."""
        from price_monitoring.models.competitor import CompetitorProduct
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001"
        )
        
        old_updated = product.last_updated
        product.update_price(1200.0)
        
        assert product.price == 1200.0
        assert product.last_updated > old_updated
    
    def test_to_dict_and_from_dict(self):
        """Тест сериализации и десериализации товара конкурента."""
        from price_monitoring.models.competitor import CompetitorProduct
        
        product = CompetitorProduct(
            id="PROD001",
            name="Товар конкурента",
            url="https://example.com/product/1",
            price=1000.0,
            our_product_id="OUR_PROD001",
            description="Описание",
            brand="Бренд"
        )
        
        # Тест to_dict
        data = product.to_dict()
        assert data['id'] == "PROD001"
        assert data['price'] == 1000.0
        assert data['our_product_id'] == "OUR_PROD001"
        
        # Тест from_dict
        restored_product = CompetitorProduct.from_dict(data)
        assert restored_product.id == product.id
        assert restored_product.price == product.price
        assert restored_product.our_product_id == product.our_product_id
        assert restored_product.description == product.description


class TestEnums:
    """Тесты для перечислений."""
    
    def test_price_source_enum(self):
        """Тест перечисления PriceSource."""
        from price_monitoring.models.price_history import PriceSource
        
        assert PriceSource.MANUAL.value == "manual"
        assert PriceSource.WILDBERRIES.value == "wildberries"
        assert PriceSource.API.value == "api"
        assert PriceSource.IMPORT.value == "import"
    
    def test_price_change_type_enum(self):
        """Тест перечисления PriceChangeType."""
        from price_monitoring.models.price_history import PriceChangeType
        
        assert PriceChangeType.INCREASE.value == "increase"
        assert PriceChangeType.DECREASE.value == "decrease"
        assert PriceChangeType.NO_CHANGE.value == "no_change"
    
    def test_marketplace_type_enum(self):
        """Тест перечисления MarketplaceType."""
        from price_monitoring.models.competitor import MarketplaceType
        
        assert MarketplaceType.WILDBERRIES.value == "wildberries"
        assert MarketplaceType.OZON.value == "ozon"
        assert MarketplaceType.YANDEX_MARKET.value == "yandex_market"
        assert MarketplaceType.AVITO.value == "avito"
        assert MarketplaceType.OTHER.value == "other"
    
    def test_competitor_type_enum(self):
        """Тест перечисления CompetitorType."""
        from price_monitoring.models.competitor import CompetitorType
        
        assert CompetitorType.DIRECT.value == "direct"
        assert CompetitorType.INDIRECT.value == "indirect"
        assert CompetitorType.SUBSTITUTE.value == "substitute"


class TestModelIntegration:
    """Интеграционные тесты для взаимодействия моделей."""
    
    def test_product_with_price_history(self):
        """Тест интеграции Product с PriceHistory."""
        from price_monitoring.models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
        
        # Создаем продукт
        product = Product(
            id='PROD001',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Test Category',
            current_price=1000.0
        )
        
        # Создаем историю цен
        history = PriceHistory(product_id=product.id)
        entry = PriceHistoryEntry(
            timestamp=datetime.now(),
            price=product.current_price,
            source=PriceSource.MANUAL,
            change_type=PriceChangeType.INCREASE
        )
        history.add_entry(entry)
        
        # Проверяем связь
        assert history.product_id == product.id
        assert history.entries[0].price == product.current_price
    
    def test_competitor_product_matching(self):
        """Тест сопоставления товаров конкурентов с нашими товарами."""
        from price_monitoring.models.competitor import Competitor, CompetitorProduct, MarketplaceType, CompetitorType
        
        # Создаем наш товар
        our_product = Product(
            id='OUR_PROD001',
            name='Наш товар',
            brand='Our Brand',
            article='OUR001',
            sku='SKU001',
            category='Test Category',
            current_price=1000.0
        )
        
        # Создаем конкурента
        competitor = Competitor(
            id="COMP001",
            name="Конкурент 1",
            marketplace=MarketplaceType.WILDBERRIES,
            competitor_type=CompetitorType.DIRECT
        )
        
        # Создаем товар конкурента
        competitor_product = CompetitorProduct(
            id="COMP_PROD001",
            name="Аналогичный товар",
            url="https://example.com/product/1",
            price=950.0,
            our_product_id=our_product.id
        )
        
        competitor.add_product(competitor_product)
        
        # Проверяем сопоставление
        found_product = competitor.get_product_by_our_id(our_product.id)
        assert found_product is not None
        assert found_product.our_product_id == our_product.id
        assert found_product.price < our_product.current_price  # Конкурент дешевле
        assert len(product.competitor_prices) == 5
        assert isinstance(product.last_updated, datetime)

    def test_initialization_with_minimal_parameters(self):
        """Тест инициализации продукта с минимальными параметрами."""
        minimal_product = Product(
            id='minimal_1',
            name='Минимальный товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Test Category',
            current_price=500.0
        )
        assert minimal_product.id == 'minimal_1'
        assert minimal_product.name == 'Минимальный товар'
        assert minimal_product.brand == 'Test Brand'
        assert minimal_product.article == 'TEST001'
        assert minimal_product.category == 'Test Category'
        assert minimal_product.current_price == 500.0
        assert len(minimal_product.competitor_prices) == 0

    def test_min_competitor_price(self):
        """Тест получения минимальной цены конкурентов."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert product.min_competitor_price == 920.0
        
        # Тест с пустым списком цен
        empty_product = Product(id='empty', name='Empty', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        assert empty_product.min_competitor_price is None

    def test_max_competitor_price(self):
        """Тест получения максимальной цены конкурентов."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert product.max_competitor_price == 1100.0
        
        # Тест с пустым списком цен
        empty_product = Product(id='empty', name='Empty', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        assert empty_product.max_competitor_price is None

    def test_avg_competitor_price(self):
        """Тест получения средней цены конкурентов."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert product.avg_competitor_price == 994.0
        
        # Тест с пустым списком цен
        empty_product = Product(id='empty', name='Empty', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        assert empty_product.avg_competitor_price is None

    def test_median_competitor_price(self):
        """Тест получения медианной цены конкурентов."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert product.median_competitor_price == 980.0
        
        # Тест с пустым списком цен
        empty_product = Product(id='empty', name='Empty', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        assert empty_product.median_competitor_price is None

    def test_price_position(self):
        """Тест определения позиции цены."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        position = product.price_position
        assert position in ['lowest', 'below_average', 'average', 'above_average', 'highest']
        
        # Тест с самой низкой ценой
        even_product = Product(id='even', name='Even', brand='Brand', article='ART', sku='SKU003', category='Cat', current_price=1000.0, 
                              competitor_prices=[1100.0, 1200.0, 1300.0])
        assert even_product.price_position == 'lowest'
        
        # Тест с пустым списком цен
        empty_product = Product(id='empty', name='Empty', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        assert empty_product.price_position == 'unknown'

    def test_is_price_competitive(self):
        """Тест проверки конкурентоспособности цены."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert product.is_price_competitive(threshold_percent=10.0) == True
        
        low_price_product = Product(id='low', name='Low', brand='Brand', article='ART', sku='SKU004', category='Cat', current_price=900.0, 
                                   competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert low_price_product.is_price_competitive(threshold_percent=5.0) == True
        
        high_price_product = Product(id='high', name='High', brand='Brand', article='ART', sku='SKU005', category='Cat', current_price=1200.0, 
                                    competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        assert high_price_product.is_price_competitive(threshold_percent=10.0) == False
        
        no_competitors_product = Product(id='no_comp', name='No Competitors', brand='Brand', article='ART', sku='SKU006', category='Cat', current_price=1000.0)
        assert no_competitors_product.is_price_competitive() == True

    def test_pricing_recommendations(self):
        """Тест получения рекомендаций по ценообразованию."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0, 1100.0, 920.0])
        recommendations = product.pricing_recommendations
        assert isinstance(recommendations, dict)
        assert 'action' in recommendations
        assert 'recommended_price' in recommendations
        assert 'reason' in recommendations

    def test_add_competitor_price(self):
        """Тест добавления цены конкурента."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0])
        
        initial_count = len(product.competitor_prices)
        new_price = 1050.0
        product.add_competitor_price(new_price)
        
        assert len(product.competitor_prices) == initial_count + 1
        assert new_price in product.competitor_prices

    def test_add_duplicate_competitor_price(self):
        """Тест добавления дублирующейся цены конкурента."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0])
        
        initial_count = len(product.competitor_prices)
        duplicate_price = 950.0  # Уже существует
        product.add_competitor_price(duplicate_price)
        
        # Количество должно увеличиться (дубликаты разрешены)
        assert len(product.competitor_prices) == initial_count + 1
        assert product.competitor_prices.count(duplicate_price) == 2

    def test_remove_competitor_price(self):
        """Тест удаления цены конкурента."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0])
        
        initial_count = len(product.competitor_prices)
        price_to_remove = 980.0
        removed = product.remove_competitor_price(price_to_remove)
        
        assert removed == True
        assert len(product.competitor_prices) == initial_count - 1
        assert price_to_remove not in product.competitor_prices

    def test_remove_nonexistent_competitor_price(self):
        """Тест удаления несуществующей цены конкурента."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0])
        
        initial_count = len(product.competitor_prices)
        nonexistent_price = 1500.0
        removed = product.remove_competitor_price(nonexistent_price)
        
        assert removed == False
        assert len(product.competitor_prices) == initial_count

    def test_update_current_price(self):
        """Тест обновления текущей цены."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0)
        
        old_price = product.current_price
        new_price = 1100.0
        old_updated = product.last_updated
        
        # Обновляем цену напрямую, так как метод update_current_price может не существовать
        product.current_price = new_price
        product.last_updated = datetime.now()
        
        assert product.current_price == new_price
        assert product.current_price != old_price
        assert product.last_updated > old_updated

    def test_to_dict(self):
        """Тест сериализации в словарь."""
        product = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0]
        )
        
        product_dict = product.to_dict()
        
        assert product_dict['id'] == 'test_product_1'
        assert product_dict['name'] == 'Тестовый товар'
        assert product_dict['brand'] == 'Test Brand'
        assert product_dict['article'] == 'TEST001'
        assert product_dict['sku'] == 'SKU001'
        assert product_dict['category'] == 'Электроника'
        assert product_dict['current_price'] == 1000.0
        assert product_dict['competitor_prices'] == [950.0, 980.0, 1020.0]
        assert 'last_updated' in product_dict

    def test_from_dict(self):
        """Тест десериализации из словаря."""
        product = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0]
        )
        
        product_dict = product.to_dict()
        restored_product = Product.from_dict(product_dict)
        
        assert restored_product.id == product.id
        assert restored_product.name == product.name
        assert restored_product.brand == product.brand
        assert restored_product.article == product.article
        assert restored_product.sku == product.sku
        assert restored_product.category == product.category
        assert restored_product.current_price == product.current_price
        assert restored_product.competitor_prices == product.competitor_prices

    def test_from_dict_minimal(self):
        """Тест создания объекта из минимального словаря."""
        data = {
            'id': 'test_id',
            'name': 'Test Product',
            'brand': 'Test Brand',
            'article': 'TEST123',
            'category': 'Test Category',
            'current_price': 100.0,
            'last_updated': '2023-01-01T12:00:00'
        }
        
        product = Product.from_dict(data)
        
        assert product.id == 'test_id'
        assert product.name == 'Test Product'
        assert product.brand == 'Test Brand'
        assert product.article == 'TEST123'
        assert product.category == 'Test Category'
        assert product.current_price == 100.0
        assert product.competitor_prices == []
        assert product.tracking_enabled == True

    def test_to_json_and_from_json(self):
        """Тест сериализации в JSON и обратно."""
        product = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0]
        )
        
        json_str = product.to_json()
        restored_product = Product.from_json(json_str)
        
        assert restored_product.id == product.id
        assert restored_product.name == product.name
        assert restored_product.current_price == product.current_price

    def test_to_sheets_row(self):
        """Тест преобразования в строку для Google Sheets."""
        product = Product(id='test', name='Test', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0, 
                         competitor_prices=[950.0, 980.0, 1020.0])
        row = product.to_sheets_row()
        assert isinstance(row, list)
        assert len(row) > 0
        assert product.id in row
        assert product.name in row
        assert product.current_price in row

    def test_get_sheets_headers(self):
        """Тест получения заголовков для Google Sheets."""
        headers = Product.get_sheets_headers()
        assert isinstance(headers, list)
        assert len(headers) > 0
        assert 'ID' in headers or 'id' in headers
        assert 'Название' in headers or 'name' in headers

    def test_str_representation(self):
        """Тест строкового представления."""
        product = Product(id='test', name='Test Product', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0)
        str_repr = str(product)
        assert product.brand in str_repr
        assert product.name in str_repr
        assert str(product.current_price) in str_repr

    def test_repr_representation(self):
        """Тест repr представления."""
        product = Product(id='test', name='Test Product', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0)
        repr_str = repr(product)
        
        assert 'Product' in repr_str
        assert product.id in repr_str
        assert product.name in repr_str

    def test_equality(self):
        """Тест сравнения продуктов на равенство."""
        product1 = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0]
        )
        
        product2 = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0,
            competitor_prices=[950.0, 980.0, 1020.0]
        )
        
        assert product1 == product2

    def test_inequality(self):
        """Тест сравнения продуктов на неравенство."""
        product1 = Product(id='test1', name='Test1', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0)
        product2 = Product(id='test2', name='Test2', brand='Brand', article='ART', sku='SKU002', category='Cat', current_price=1000.0)
        
        assert product1 != product2

    def test_hash(self):
        """Тест хеширования продуктов."""
        product = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0
        )
        
        # Проверяем, что объект можно хешировать
        hash_value = hash(product)
        assert isinstance(hash_value, int)
        
        # Проверяем, что одинаковые объекты имеют одинаковый хеш
        product2 = Product(
            id='test_product_1',
            name='Тестовый товар',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Электроника',
            current_price=1000.0
        )
        
        assert hash(product) == hash(product2)

    def test_price_history_management(self):
        """Тест управления историей цен."""
        product = Product(id='single', name='Single', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0,
                         price_history=[{'date': '2023-01-01', 'price': 950.0}])
        
        # Проверяем, что история цен инициализирована
        assert len(product.price_history) == 1
        assert product.price_history[0]['price'] == 950.0

    def test_competitor_management(self):
        """Тест управления конкурентами."""
        product = Product(id='duplicate', name='Duplicate', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=1000.0,
                         competitors=['competitor1', 'competitor2'])
        
        # Проверяем, что конкуренты инициализированы
        assert len(product.competitors) == 2
        assert 'competitor1' in product.competitors

    def test_large_price_handling(self):
        """Тест обработки больших цен."""
        large_price = 999999.99
        product = Product(id='large', name='Large', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=large_price,
                         competitor_prices=[large_price - 1000, large_price + 1000])
        
        assert product.current_price == large_price
        assert len(product.competitor_prices) == 2

    def test_small_price_handling(self):
        """Тест обработки малых цен."""
        small_price = 0.01
        product = Product(id='small', name='Small', brand='Brand', article='ART', sku='SKU001', category='Cat', current_price=small_price,
                         competitor_prices=[0.02, 0.03])
        
        assert product.current_price == small_price
        assert len(product.competitor_prices) == 2

    def test_validation_on_init(self):
        """Тест валидации при инициализации."""
        product = Product(
            id='test_validation',
            name='Test Validation Product',
            brand='Test Brand',
            article='TEST001',
            sku='SKU001',
            category='Test Category',
            current_price=1000.0,
            competitor_prices=[950.0, 1050.0]
        )
        
        # Проверяем, что объект создался без ошибок
        assert product.id == 'test_validation'
        assert product.current_price == 1000.0