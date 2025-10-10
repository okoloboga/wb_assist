import pytest
from wb_api.models import WBOrder, WBSale, WBStock

class TestWBModels:
    """Тесты моделей данных Wildberries"""
    
    def test_order_model_creation(self):
        """Тест создания модели заказа"""
        # ✅ Полные данные для модели заказа
        order_data = {
            "date": "2023-10-01T12:00:00Z",
            "lastChangeDate": "2023-10-01T12:30:00Z",
            "warehouseName": "Москва",
            "countryName": "Россия",
            "oblastOkrugName": "Центральный ФО",
            "regionName": "Московская область",
            "supplierArticle": "ART001",
            "nmId": 123456789,
            "barcode": "4651234567890",
            "category": "Одежда",
            "subject": "Футболка",
            "brand": "Nike",
            "techSize": "M",
            "incomeID": 12345,
            "isSupply": True,
            "isRealization": False,
            "totalPrice": 1500.0,
            "discountPercent": 10,
            "spp": 0.0,
            "finishedPrice": 1350.0,
            "priceWithDisc": 1350.0,
            "isCancel": False,
            "orderType": "Клиентский",
            "gNumber": "G123456789"
        }
        
        order = WBOrder(**order_data)
        
        assert order.nmId == 123456789
        assert order.totalPrice == 1500.0
        assert order.finishedPrice == 1350.0
        assert order.warehouseName == "Москва"
    
    def test_order_model_validation(self):
        """Тест валидации данных заказа"""
        # 🔴 Тест на обязательные поля
        invalid_data = {
            "date": "2023-10-01",
            # Отсутствуют обязательные поля
        }
        
        with pytest.raises(ValueError):
            WBOrder(**invalid_data)
    
    def test_sale_model_creation(self):
        """Тест создания модели продажи"""
        # ✅ Полные данные для модели продажи
        sale_data = {
            "date": "2023-10-01T14:00:00Z",
            "lastChangeDate": "2023-10-01T14:30:00Z",
            "supplierArticle": "ART001",
            "techSize": "M",
            "barcode": "4651234567890",
            "totalPrice": 1350.0,
            "discountPercent": 10,
            "warehouseName": "Москва",
            "countryName": "Россия",
            "oblastOkrugName": "Центральный ФО",
            "regionName": "Московская область",
            "incomeID": 12345,
            "odid": 67890,
            "spp": 0.0,
            "forPay": 1215.0,
            "finishedPrice": 1350.0,
            "priceWithDisc": 1350.0,
            "nmId": 123456789,
            "subject": "Футболка",
            "category": "Одежда",
            "brand": "Nike",
            "gNumber": "G123456789"
        }
        
        sale = WBSale(**sale_data)
        
        assert sale.nmId == 123456789
        assert sale.totalPrice == 1350.0
        assert sale.subject == "Футболка"
    
    def test_stock_model_creation(self):
        """Тест создания модели остатка"""
        # ✅ Полные данные для модели остатка
        stock_data = {
            "lastChangeDate": "2023-10-01T10:00:00Z",
            "supplierArticle": "ART001",
            "techSize": "M",
            "barcode": "4651234567890",
            "quantity": 50,
            "isSupply": True,
            "isRealization": False,
            "quantityFull": 50,
            "warehouseName": "Москва",
            "nmId": 123456789,
            "subject": "Футболка",
            "category": "Одежда",
            "daysOnSite": 30,
            "brand": "Nike",
            "SCCode": "SC123",
            "Price": 1500.0,
            "Discount": 10.0
        }
        
        stock = WBStock(**stock_data)
        
        assert stock.nmId == 123456789
        assert stock.quantity == 50
        assert stock.warehouseName == "Москва"