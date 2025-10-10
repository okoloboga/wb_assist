"""
Тесты для класса PriceMonitor.

Содержит unit-тесты для проверки функциональности мониторинга цен,
включая добавление товаров, обновление цен, проверку пороговых значений
и управление процессом мониторинга.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Импорты тестируемых классов
from ..core.price_monitor import (
    PriceMonitor, MonitoringConfig, PriceAlert, PriceChangeEvent, MonitoringStatus
)
from ..models.product import Product
from ..models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
from ..models.competitor import Competitor, MarketplaceType, CompetitorType
from ..core.exceptions import PriceMonitorError, ProductNotFoundError, InvalidPriceError


class TestPriceMonitor:
    """Тесты для класса PriceMonitor."""
    
    @pytest.fixture
    def monitor_config(self):
        """Конфигурация для тестов."""
        return MonitoringConfig(
            update_interval=60,
            max_concurrent_updates=5,
            retry_attempts=2,
            enable_notifications=True
        )
    
    @pytest.fixture
    def price_monitor(self, monitor_config):
        """Экземпляр PriceMonitor для тестов."""
        return PriceMonitor(config=monitor_config)
    
    @pytest.fixture
    def sample_product(self):
        """Фикстура с примером товара."""
        return Product(
            id="test_product_1",
            name="Тестовый товар",
            brand="Тестовый бренд",
            article="TEST001",
            sku="SKU001",
            category="Электроника",
            current_price=1000.0,
            target_price=950.0,
            min_price=800.0,
            max_price=1200.0,
            price_threshold=5.0
        )
    
    @pytest.fixture
    def sample_competitor(self):
        """Фикстура с примером конкурента."""
        return Competitor(
            id="comp_1",
            name="Конкурент 1",
            type=CompetitorType.DIRECT,
            marketplace=MarketplaceType.WILDBERRIES
        )

    @pytest.fixture
    def sample_competitors(self):
        """Тестовые конкуренты."""
        return [
            Competitor(
                id="comp_1",
                name="Конкурент 1",
                type=CompetitorType.DIRECT,
                marketplace=MarketplaceType.WILDBERRIES
            ),
            Competitor(
                id="comp_2",
                name="Конкурент 2",
                type=CompetitorType.INDIRECT,
                marketplace=MarketplaceType.OZON
            )
        ]
    
    def test_price_monitor_initialization(self, monitor_config):
        """Тест инициализации PriceMonitor."""
        monitor = PriceMonitor(config=monitor_config)
        
        assert monitor.config == monitor_config
        assert monitor.status == MonitoringStatus.STOPPED
        assert len(monitor._monitored_products) == 0
        assert len(monitor._price_histories) == 0
        assert len(monitor._competitors) == 0
        
        # Проверяем статистику
        stats = monitor.get_statistics()
        assert stats["total_products"] == 0
        assert stats["active_products"] == 0
        assert stats["total_updates"] == 0
    
    def test_price_monitor_default_config(self):
        """Тест инициализации с конфигурацией по умолчанию."""
        monitor = PriceMonitor()
        
        assert monitor.config.update_interval == 3600
        assert monitor.config.max_concurrent_updates == 10
        assert monitor.config.enable_notifications is True
    
    def test_add_product_success(self, price_monitor, sample_product):
        """Тест успешного добавления товара."""
        price_monitor.add_product(sample_product)
        
        # Проверяем, что товар добавлен
        assert sample_product.id in price_monitor._monitored_products
        assert price_monitor._monitored_products[sample_product.id] == sample_product
        
        # Проверяем создание истории цен
        assert sample_product.id in price_monitor._price_histories
        history = price_monitor._price_histories[sample_product.id]
        assert len(history.entries) == 1
        assert history.entries[0].price == sample_product.current_price
        
        # Проверяем статистику
        stats = price_monitor.get_statistics()
        assert stats["total_products"] == 1
        assert stats["active_products"] == 1
    
    def test_add_product_with_competitors(self, price_monitor, sample_product, sample_competitors):
        """Тест добавления товара с конкурентами."""
        price_monitor.add_product(sample_product, sample_competitors)
        
        assert sample_product.id in price_monitor._competitors
        assert price_monitor._competitors[sample_product.id] == sample_competitors
    
    def test_add_product_invalid_id(self, price_monitor):
        """Тест добавления товара с пустым ID."""
        # Создаем товар с валидными данными, но затем меняем ID
        invalid_product = Product(
            id="valid_id",
            name="Товар без ID",
            brand="Test",
            article="TEST",
            sku="SKU",
            category="Test",
            current_price=100.0
        )
        # Меняем ID после создания, чтобы обойти валидацию __post_init__
        invalid_product.id = ""
        
        with pytest.raises(PriceMonitorError):
            price_monitor.add_product(invalid_product)
    
    def test_add_product_invalid_price(self, price_monitor):
        """Тест добавления товара с некорректной ценой."""
        # Создаем товар с валидными данными, но затем меняем цену
        invalid_product = Product(
            id="test_invalid",
            name="Товар с некорректной ценой",
            brand="Test",
            article="TEST",
            sku="SKU",
            category="Test",
            current_price=100.0
        )
        # Меняем цену после создания, чтобы обойти валидацию __post_init__
        invalid_product.current_price = -100.0
        
        with pytest.raises(PriceMonitorError):
            price_monitor.add_product(invalid_product)
    
    def test_remove_product_success(self, price_monitor, sample_product):
        """Тест успешного удаления товара."""
        # Добавляем товар
        price_monitor.add_product(sample_product)
        assert len(price_monitor._monitored_products) == 1
        
        # Удаляем товар
        price_monitor.remove_product(sample_product.id)
        assert len(price_monitor._monitored_products) == 0
        assert sample_product.id not in price_monitor._monitored_products
        
        # Проверяем статистику
        stats = price_monitor.get_statistics()
        assert stats["total_products"] == 0
        assert stats["active_products"] == 0
    
    def test_remove_product_not_found(self, price_monitor):
        """Тест удаления несуществующего товара."""
        with pytest.raises(ProductNotFoundError):
            price_monitor.remove_product("nonexistent_id")
    
    def test_update_product_price_success(self, price_monitor, sample_product):
        """Тест успешного обновления цены товара."""
        price_monitor.add_product(sample_product)
        old_price = sample_product.current_price
        new_price = 1100.0
        
        alert = price_monitor.update_product_price(sample_product.id, new_price)
        
        # Проверяем обновление цены
        updated_product = price_monitor.get_product(sample_product.id)
        assert updated_product.current_price == new_price
        
        # Проверяем историю цен
        history = price_monitor.get_price_history(sample_product.id)
        assert len(history.entries) == 2  # Начальная + обновленная
        assert history.entries[-1].price == new_price
        assert history.entries[-1].change_type == PriceChangeType.INCREASE
        
        # Проверяем уведомление (цена изменилась на 10%, что равно порогу)
        assert alert is not None
        assert alert.product_id == sample_product.id
        assert alert.old_price == old_price
        assert alert.new_price == new_price
        assert alert.change_percent == 10.0
    
    def test_update_product_price_threshold_not_exceeded(self, price_monitor, sample_product):
        """Тест обновления цены без превышения порога."""
        price_monitor.add_product(sample_product)
        new_price = 1040.0  # Изменение на 4%, порог 5%
        
        alert = price_monitor.update_product_price(sample_product.id, new_price)
        
        # Уведомление не должно быть создано
        assert alert is None
    
    def test_update_product_price_target_reached(self, price_monitor, sample_product):
        """Тест достижения целевой цены."""
        price_monitor.add_product(sample_product)
        target_price = sample_product.target_price  # 900.0
        
        alert = price_monitor.update_product_price(sample_product.id, target_price)
        
        assert alert is not None
        assert alert.event_type == PriceChangeEvent.TARGET_PRICE_REACHED
        assert alert.new_price == target_price
    
    def test_update_product_price_below_minimum(self, price_monitor, sample_product):
        """Тест цены ниже минимальной."""
        price_monitor.add_product(sample_product)
        below_min_price = 700.0  # Ниже min_price = 800.0
        
        alert = price_monitor.update_product_price(sample_product.id, below_min_price)
        
        assert alert is not None
        assert alert.event_type == PriceChangeEvent.PRICE_BELOW_MINIMUM
        assert "ниже минимальной" in alert.message
    
    def test_update_product_price_above_maximum(self, price_monitor, sample_product):
        """Тест цены выше максимальной."""
        price_monitor.add_product(sample_product)
        above_max_price = 1300.0  # Выше max_price = 1200.0
        
        alert = price_monitor.update_product_price(sample_product.id, above_max_price)
        
        assert alert is not None
        assert alert.event_type == PriceChangeEvent.PRICE_ABOVE_MAXIMUM
        assert "превысила максимальную" in alert.message
    
    def test_update_product_price_not_found(self, price_monitor):
        """Тест обновления цены несуществующего товара."""
        with pytest.raises(ProductNotFoundError):
            price_monitor.update_product_price("nonexistent_id", 100.0)
    
    def test_update_product_price_invalid_price(self, price_monitor, sample_product):
        """Тест обновления с некорректной ценой."""
        price_monitor.add_product(sample_product)
        
        with pytest.raises(InvalidPriceError):
            price_monitor.update_product_price(sample_product.id, -100.0)
    
    def test_event_handlers(self, price_monitor, sample_product):
        """Тест обработчиков событий."""
        # Создаем mock обработчик
        handler = Mock()
        price_monitor.add_event_handler(PriceChangeEvent.THRESHOLD_EXCEEDED, handler)
        
        # Добавляем товар и обновляем цену с превышением порога
        price_monitor.add_product(sample_product)
        price_monitor.update_product_price(sample_product.id, 1100.0)  # +10%
        
        # Проверяем, что обработчик был вызван
        handler.assert_called_once()
        call_args = handler.call_args[0][0]  # Первый аргумент первого вызова
        assert isinstance(call_args, PriceAlert)
        assert call_args.product_id == sample_product.id
    
    def test_get_product_success(self, price_monitor, sample_product):
        """Тест получения товара по ID."""
        price_monitor.add_product(sample_product)
        
        retrieved_product = price_monitor.get_product(sample_product.id)
        assert retrieved_product == sample_product
    
    def test_get_product_not_found(self, price_monitor):
        """Тест получения несуществующего товара."""
        with pytest.raises(ProductNotFoundError):
            price_monitor.get_product("nonexistent_id")
    
    def test_get_price_history_success(self, price_monitor, sample_product):
        """Тест получения истории цен."""
        price_monitor.add_product(sample_product)
        
        history = price_monitor.get_price_history(sample_product.id)
        assert isinstance(history, PriceHistory)
        assert history.product_id == sample_product.id
        assert len(history.entries) == 1
    
    def test_get_price_history_not_found(self, price_monitor):
        """Тест получения истории несуществующего товара."""
        with pytest.raises(ProductNotFoundError):
            price_monitor.get_price_history("nonexistent_id")
    
    def test_get_monitored_products(self, price_monitor, sample_product):
        """Тест получения списка всех товаров."""
        price_monitor.add_product(sample_product)
        
        products = price_monitor.get_monitored_products()
        assert len(products) == 1
        assert products[0] == sample_product
    
    def test_get_active_products(self, price_monitor):
        """Тест получения списка активных товаров."""
        # Создаем активный товар
        active_product = Product(
            id="active_1",
            name="Активный товар",
            brand="Test",
            article="ACT001",
            sku="SKU001",
            category="Test",
            current_price=100.0,
            tracking_enabled=True
        )
        
        # Создаем неактивный товар
        inactive_product = Product(
            id="inactive_1",
            name="Неактивный товар",
            brand="Test",
            article="INA001",
            sku="SKU002",
            category="Test",
            current_price=200.0,
            tracking_enabled=False
        )
        
        price_monitor.add_product(active_product)
        price_monitor.add_product(inactive_product)
        
        active_products = price_monitor.get_active_products()
        assert len(active_products) == 1
        assert active_products[0] == active_product
    
    def test_enable_product_tracking(self, price_monitor):
        """Тест включения мониторинга товара."""
        # Создаем товар с отключенным мониторингом
        product = Product(
            id="test_enable",
            name="Товар для включения",
            brand="Test",
            article="EN001",
            sku="SKU001",
            category="Test",
            current_price=100.0,
            tracking_enabled=False
        )
        
        price_monitor.add_product(product)
        assert price_monitor.get_statistics()["active_products"] == 0
        
        price_monitor.enable_product_tracking(product.id)
        
        assert product.tracking_enabled is True
        assert price_monitor.get_statistics()["active_products"] == 1
    
    def test_disable_product_tracking(self, price_monitor, sample_product):
        """Тест отключения мониторинга товара."""
        price_monitor.add_product(sample_product)
        assert price_monitor.get_statistics()["active_products"] == 1
        
        price_monitor.disable_product_tracking(sample_product.id)
        
        assert sample_product.tracking_enabled is False
        assert price_monitor.get_statistics()["active_products"] == 0
    
    def test_monitoring_status_control(self, price_monitor):
        """Тест управления статусом мониторинга."""
        # Изначально остановлен
        assert price_monitor.status == MonitoringStatus.STOPPED
        
        # Запускаем
        price_monitor.start_monitoring()
        assert price_monitor.status == MonitoringStatus.ACTIVE
        
        # Приостанавливаем
        price_monitor.pause_monitoring()
        assert price_monitor.status == MonitoringStatus.PAUSED
        
        # Возобновляем
        price_monitor.resume_monitoring()
        assert price_monitor.status == MonitoringStatus.ACTIVE
        
        # Останавливаем
        price_monitor.stop_monitoring()
        assert price_monitor.status == MonitoringStatus.STOPPED
    
    def test_statistics(self, price_monitor, sample_product):
        """Тест получения статистики."""
        # Начальная статистика
        stats = price_monitor.get_statistics()
        assert stats["total_products"] == 0
        assert stats["active_products"] == 0
        assert stats["total_updates"] == 0
        assert stats["alerts_generated"] == 0
        
        # Добавляем товар
        price_monitor.add_product(sample_product)
        stats = price_monitor.get_statistics()
        assert stats["total_products"] == 1
        assert stats["active_products"] == 1
        
        # Обновляем цену с уведомлением
        price_monitor.update_product_price(sample_product.id, 1100.0)
        stats = price_monitor.get_statistics()
        assert stats["total_updates"] == 1
        assert stats["alerts_generated"] == 1
        assert stats["last_update"] is not None
    
    def test_price_change_event_types(self, price_monitor, sample_product):
        """Тест различных типов событий изменения цены."""
        price_monitor.add_product(sample_product)
        
        # Тест увеличения цены
        alert = price_monitor.update_product_price(sample_product.id, 1100.0)
        assert alert.event_type == PriceChangeEvent.THRESHOLD_EXCEEDED
        
        # Тест достижения целевой цены (950.0)
        alert = price_monitor.update_product_price(sample_product.id, 950.0)
        assert alert.event_type == PriceChangeEvent.TARGET_PRICE_REACHED
    
    def test_concurrent_price_updates(self, price_monitor):
        """Тест одновременных обновлений цен."""
        # Создаем несколько товаров
        products = []
        for i in range(5):
            product = Product(
                id=f"concurrent_test_{i}",
                name=f"Товар {i}",
                brand="Test",
                article=f"CON{i:03d}",
                sku=f"SKU{i:03d}",
                category="Test",
                current_price=100.0 + i * 10,
                price_threshold=5.0
            )
            products.append(product)
            price_monitor.add_product(product)
        
        # Обновляем цены всех товаров
        alerts = []
        for i, product in enumerate(products):
            new_price = product.current_price * 1.1  # +10%
            alert = price_monitor.update_product_price(product.id, new_price)
            if alert:
                alerts.append(alert)
        
        # Проверяем, что все обновления прошли успешно
        assert len(alerts) == 5  # Все товары должны сгенерировать уведомления
        
        stats = price_monitor.get_statistics()
        assert stats["total_updates"] == 5
        assert stats["alerts_generated"] == 5


class TestMonitoringConfig:
    """Тесты для класса MonitoringConfig."""
    
    def test_default_config(self):
        """Тест конфигурации по умолчанию."""
        config = MonitoringConfig()
        
        assert config.update_interval == 3600
        assert config.max_concurrent_updates == 10
        assert config.retry_attempts == 3
        assert config.retry_delay == 60
        assert config.enable_notifications is True
        assert config.log_level == "INFO"
    
    def test_custom_config(self):
        """Тест пользовательской конфигурации."""
        config = MonitoringConfig(
            update_interval=1800,
            max_concurrent_updates=5,
            retry_attempts=2,
            enable_notifications=False,
            log_level="DEBUG"
        )
        
        assert config.update_interval == 1800
        assert config.max_concurrent_updates == 5
        assert config.retry_attempts == 2
        assert config.enable_notifications is False
        assert config.log_level == "DEBUG"


class TestPriceAlert:
    """Тесты для класса PriceAlert."""
    
    def test_price_alert_creation(self):
        """Тест создания уведомления о цене."""
        alert = PriceAlert(
            product_id="test_product",
            event_type=PriceChangeEvent.THRESHOLD_EXCEEDED,
            old_price=100.0,
            new_price=110.0,
            change_percent=10.0,
            message="Цена изменилась на 10%"
        )
        
        assert alert.product_id == "test_product"
        assert alert.event_type == PriceChangeEvent.THRESHOLD_EXCEEDED
        assert alert.old_price == 100.0
        assert alert.new_price == 110.0
        assert alert.change_percent == 10.0
        assert alert.message == "Цена изменилась на 10%"
        assert isinstance(alert.timestamp, datetime)
        assert isinstance(alert.metadata, dict)