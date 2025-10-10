import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

@pytest.fixture
def sample_wb_order():
    return {
        "date": "2023-10-01T12:00:00Z",
        "lastChangeDate": "2023-10-01T12:30:00Z", 
        "warehouseName": "Москва",
        "supplierArticle": "ART001",
        "nmId": 123456789,
        "barcode": "4651234567890",
        "totalPrice": 1500.0,
        "discountPercent": 10,
        "finishedPrice": 1350.0
    }

@pytest.fixture
def sample_wb_sale():
    return {
        "date": "2023-10-01T14:00:00Z",
        "lastChangeDate": "2023-10-01T14:30:00Z",
        "supplierArticle": "ART001",
        "nmId": 123456789,
        "totalPrice": 1350.0,
        "quantity": 1,
        "subject": "Футболка",
        "brand": "Nike"
    }

@pytest.fixture
def sample_wb_stock():
    return {
        "lastChangeDate": "2023-10-01T10:00:00Z",
        "supplierArticle": "ART001", 
        "nmId": 123456789,
        "quantity": 50,
        "warehouseName": "Москва",
        "subject": "Футболка",
        "brand": "Nike"
    }