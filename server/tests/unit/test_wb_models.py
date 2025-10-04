import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.features.wb_api.models import (
    WBCabinet, WBOrder, WBProduct, WBStock, WBReview, 
    WBAnalyticsCache, WBWarehouse, WBSyncLog
)


class TestWBCabinetModel:
    """Тесты модели WBCabinet"""

    def test_wb_cabinet_creation(self, db_session):
        """Тест создания кабинета WB"""
        cabinet = WBCabinet(
            user_id=1,
            api_key="test-api-key",
            cabinet_name="Test Cabinet",
            region="Москва",
            is_active=True
        )
        
        db_session.add(cabinet)
        db_session.commit()
        db_session.refresh(cabinet)
        
        assert cabinet.id is not None
        assert cabinet.user_id == 1
        assert cabinet.api_key == "test-api-key"
        assert cabinet.cabinet_name == "Test Cabinet"
        assert cabinet.region == "Москва"
        assert cabinet.is_active is True
        assert cabinet.created_at is not None

    def test_wb_cabinet_unique_api_key(self, db_session):
        """Тест уникальности API ключа"""
        cabinet1 = WBCabinet(
            user_id=1,
            api_key="unique-key",
            cabinet_name="Cabinet 1"
        )
        db_session.add(cabinet1)
        db_session.commit()
        
        cabinet2 = WBCabinet(
            user_id=2,
            api_key="unique-key",  # Дублирующий ключ
            cabinet_name="Cabinet 2"
        )
        db_session.add(cabinet2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBOrderModel:
    """Тесты модели WBOrder"""

    def test_wb_order_creation(self, db_session):
        """Тест создания заказа WB"""
        order = WBOrder(
            cabinet_id=1,
            order_id="12345",
            nm_id=525760326,
            article="ART001",
            brand="Test Brand",
            name="Test Product",
            size="M",
            barcode="1234567890123",
            total_price=1500.0,
            finished_price=1350.0,
            discount_percent=10.0,
            spp=0.0,
            is_cancel=False,
            is_realization=True,
            order_date=datetime.now(timezone.utc),
            last_change_date=datetime.now(timezone.utc)
        )
        
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        assert order.id is not None
        assert order.cabinet_id == 1
        assert order.order_id == "12345"
        assert order.nm_id == 525760326
        assert order.total_price == 1500.0
        assert order.finished_price == 1350.0

    def test_wb_order_unique_constraint(self, db_session):
        """Тест уникальности заказа по cabinet_id + order_id"""
        order1 = WBOrder(
            cabinet_id=1,
            order_id="12345",
            nm_id=525760326
        )
        db_session.add(order1)
        db_session.commit()
        
        order2 = WBOrder(
            cabinet_id=1,
            order_id="12345",  # Дублирующий order_id для того же кабинета
            nm_id=525760327
        )
        db_session.add(order2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBProductModel:
    """Тесты модели WBProduct"""

    def test_wb_product_creation(self, db_session):
        """Тест создания товара WB"""
        product = WBProduct(
            cabinet_id=1,
            nm_id=525760326,
            article="ART001",
            brand="Test Brand",
            name="Test Product",
            subject="Одежда",
            category="Пиджаки",
            characteristics={"color": "зеленый", "size": "M"},
            sizes=["M", "L", "XL"],
            photos=["photo1.jpg", "photo2.jpg"],
            is_active=True
        )
        
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        
        assert product.id is not None
        assert product.cabinet_id == 1
        assert product.nm_id == 525760326
        assert product.article == "ART001"
        assert product.brand == "Test Brand"
        assert product.characteristics == {"color": "зеленый", "size": "M"}
        assert product.sizes == ["M", "L", "XL"]

    def test_wb_product_unique_nm_id_per_cabinet(self, db_session):
        """Тест уникальности nm_id в рамках кабинета"""
        product1 = WBProduct(
            cabinet_id=1,
            nm_id=525760326,
            article="ART001"
        )
        db_session.add(product1)
        db_session.commit()
        
        product2 = WBProduct(
            cabinet_id=1,
            nm_id=525760326,  # Дублирующий nm_id для того же кабинета
            article="ART002"
        )
        db_session.add(product2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBStockModel:
    """Тесты модели WBStock"""

    def test_wb_stock_creation(self, db_session):
        """Тест создания остатка WB"""
        stock = WBStock(
            cabinet_id=1,
            nm_id=525760326,
            warehouse_id=658434,
            warehouse_name="Коледино",
            article="ART001",
            size="M",
            quantity=50,
            price=1500.0,
            discount=10.0,
            last_change_date=datetime.now(timezone.utc)
        )
        
        db_session.add(stock)
        db_session.commit()
        db_session.refresh(stock)
        
        assert stock.id is not None
        assert stock.cabinet_id == 1
        assert stock.nm_id == 525760326
        assert stock.warehouse_id == 658434
        assert stock.quantity == 50
        assert stock.price == 1500.0

    def test_wb_stock_unique_constraint(self, db_session):
        """Тест уникальности остатка по cabinet_id + nm_id + warehouse_id + size"""
        stock1 = WBStock(
            cabinet_id=1,
            nm_id=525760326,
            warehouse_id=658434,
            size="M",
            quantity=50
        )
        db_session.add(stock1)
        db_session.commit()
        
        stock2 = WBStock(
            cabinet_id=1,
            nm_id=525760326,
            warehouse_id=658434,
            size="M",  # Дублирующая комбинация
            quantity=30
        )
        db_session.add(stock2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBReviewModel:
    """Тесты модели WBReview"""

    def test_wb_review_creation(self, db_session):
        """Тест создания отзыва WB"""
        review = WBReview(
            cabinet_id=1,
            nm_id=525760326,
            review_id="rev123",
            text="Отличный товар!",
            rating=5,
            is_answered=False,
            created_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc)
        )
        
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)
        
        assert review.id is not None
        assert review.cabinet_id == 1
        assert review.nm_id == 525760326
        assert review.review_id == "rev123"
        assert review.text == "Отличный товар!"
        assert review.rating == 5
        assert review.is_answered is False

    def test_wb_review_unique_constraint(self, db_session):
        """Тест уникальности отзыва по cabinet_id + review_id"""
        review1 = WBReview(
            cabinet_id=1,
            review_id="rev123",
            nm_id=525760326
        )
        db_session.add(review1)
        db_session.commit()
        
        review2 = WBReview(
            cabinet_id=1,
            review_id="rev123",  # Дублирующий review_id для того же кабинета
            nm_id=525760327
        )
        db_session.add(review2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBAnalyticsCacheModel:
    """Тесты модели WBAnalyticsCache"""

    def test_wb_analytics_cache_creation(self, db_session):
        """Тест создания кэша аналитики WB"""
        analytics = WBAnalyticsCache(
            cabinet_id=1,
            nm_id=525760326,
            period="7d",
            sales_count=10,
            sales_amount=15000.0,
            buyouts_count=8,
            buyouts_amount=12000.0,
            buyout_rate=0.8,
            avg_order_speed=2.5,
            reviews_count=5,
            avg_rating=4.2,
            last_calculated=datetime.now(timezone.utc)
        )
        
        db_session.add(analytics)
        db_session.commit()
        db_session.refresh(analytics)
        
        assert analytics.id is not None
        assert analytics.cabinet_id == 1
        assert analytics.nm_id == 525760326
        assert analytics.period == "7d"
        assert analytics.sales_count == 10
        assert analytics.buyout_rate == 0.8

    def test_wb_analytics_cache_unique_constraint(self, db_session):
        """Тест уникальности кэша по cabinet_id + nm_id + period"""
        analytics1 = WBAnalyticsCache(
            cabinet_id=1,
            nm_id=525760326,
            period="7d",
            sales_count=10
        )
        db_session.add(analytics1)
        db_session.commit()
        
        analytics2 = WBAnalyticsCache(
            cabinet_id=1,
            nm_id=525760326,
            period="7d",  # Дублирующая комбинация
            sales_count=15
        )
        db_session.add(analytics2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBWarehouseModel:
    """Тесты модели WBWarehouse"""

    def test_wb_warehouse_creation(self, db_session):
        """Тест создания склада WB"""
        warehouse = WBWarehouse(
            cabinet_id=1,
            warehouse_id=658434,
            name="Коледино",
            address="Московская область, г. Коледино",
            region="Москва"
        )
        
        db_session.add(warehouse)
        db_session.commit()
        db_session.refresh(warehouse)
        
        assert warehouse.id is not None
        assert warehouse.cabinet_id == 1
        assert warehouse.warehouse_id == 658434
        assert warehouse.name == "Коледино"
        assert warehouse.region == "Москва"

    def test_wb_warehouse_unique_constraint(self, db_session):
        """Тест уникальности склада по cabinet_id + warehouse_id"""
        warehouse1 = WBWarehouse(
            cabinet_id=1,
            warehouse_id=658434,
            name="Коледино"
        )
        db_session.add(warehouse1)
        db_session.commit()
        
        warehouse2 = WBWarehouse(
            cabinet_id=1,
            warehouse_id=658434,  # Дублирующий warehouse_id для того же кабинета
            name="Коледино 2"
        )
        db_session.add(warehouse2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestWBSyncLogModel:
    """Тесты модели WBSyncLog"""

    def test_wb_sync_log_creation(self, db_session):
        """Тест создания лога синхронизации WB"""
        sync_log = WBSyncLog(
            cabinet_id=1,
            sync_type="full",
            status="success",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            records_processed=100,
            records_created=50,
            records_updated=30,
            records_skipped=20,
            error_message=None
        )
        
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)
        
        assert sync_log.id is not None
        assert sync_log.cabinet_id == 1
        assert sync_log.sync_type == "full"
        assert sync_log.status == "success"
        assert sync_log.records_processed == 100
        assert sync_log.error_message is None

    def test_wb_sync_log_with_error(self, db_session):
        """Тест создания лога синхронизации с ошибкой"""
        sync_log = WBSyncLog(
            cabinet_id=1,
            sync_type="orders",
            status="error",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            error_message="API rate limit exceeded"
        )
        
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)
        
        assert sync_log.status == "error"
        assert sync_log.error_message == "API rate limit exceeded"