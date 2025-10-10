from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WBOrder(BaseModel):
    """Модель заказа Wildberries"""
    date: str
    lastChangeDate: str
    warehouseName: str
    countryName: str
    oblastOkrugName: str
    regionName: str
    supplierArticle: str
    nmId: int
    barcode: str
    category: str
    subject: str
    brand: str
    techSize: str
    incomeID: int
    isSupply: bool
    isRealization: bool
    totalPrice: float
    discountPercent: int
    spp: float
    finishedPrice: float
    priceWithDisc: float
    isCancel: bool
    cancelDate: Optional[str] = None
    orderType: str
    sticker: Optional[str] = None
    gNumber: str

class WBSale(BaseModel):
    """Модель продажи Wildberries"""
    date: str
    lastChangeDate: str
    supplierArticle: str
    techSize: str
    barcode: str
    totalPrice: float
    discountPercent: int
    warehouseName: str
    countryName: str
    oblastOkrugName: str
    regionName: str
    incomeID: int
    odid: int
    spp: float
    forPay: float
    finishedPrice: float
    priceWithDisc: float
    nmId: int
    subject: str
    category: str
    brand: str
    isStorno: Optional[int] = None
    gNumber: str

class WBStock(BaseModel):
    """Модель остатка Wildberries"""
    lastChangeDate: str
    supplierArticle: str
    techSize: str
    barcode: str
    quantity: int
    isSupply: bool
    isRealization: bool
    quantityFull: int
    warehouseName: str
    nmId: int
    subject: str
    category: str
    daysOnSite: int
    brand: str
    SCCode: str
    Price: float
    Discount: float