"""
Общие утилиты для сериализации моделей (to_dict/from_dict, to_json/from_json).

Цель: централизовать преобразования, чтобы избежать дублирования логики
в моделях и упростить поддержку форматов.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import json

# Импорты, безопасные с точки зрения циклов (эти модули не импортируют utils)
from ..models.enums import MarketplaceType, CompetitorType


# -------- Product --------

def product_to_dict(product: Any) -> Dict[str, Any]:
    """Сериализация Product в словарь (значения и форматы как раньше)."""
    return {
        'id': product.id,
        'name': product.name,
        'brand': product.brand,
        'article': product.article,
        'sku': product.sku,
        'category': product.category,
        'current_price': product.current_price,
        'target_price': getattr(product, 'target_price', None),
        'min_price': getattr(product, 'min_price', None),
        'max_price': getattr(product, 'max_price', None),
        'competitor_prices': product.competitor_prices,
        'last_updated': product.last_updated.isoformat() if hasattr(product, 'last_updated') else None,
        'tracking_enabled': getattr(product, 'tracking_enabled', True),
        'price_threshold': getattr(product, 'price_threshold', 5.0),
        'marketplace_url': getattr(product, 'marketplace_url', None),
        'competitor_urls': getattr(product, 'competitor_urls', []),
        'tags': getattr(product, 'tags', []),
    }


def product_from_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготовка словаря для конструктора Product (преобразование типов)."""
    out = dict(data)
    # Обработка даты
    if 'last_updated' in out and isinstance(out['last_updated'], str):
        out['last_updated'] = datetime.fromisoformat(out['last_updated'])
    # Добавляем sku если его нет
    if 'sku' not in out:
        out['sku'] = out.get('article', '')
    return out


def product_to_json(product: Any) -> str:
    return json.dumps(product_to_dict(product), ensure_ascii=False, indent=2)


def product_from_json_data(json_str: str) -> Dict[str, Any]:
    data = json.loads(json_str)
    return product_from_dict_data(data)


# -------- CompetitorProduct --------

def competitor_product_to_dict(product: Any) -> Dict[str, Any]:
    """Сериализация CompetitorProduct в словарь."""
    return {
        'id': product.id,
        'name': product.name,
        'brand': getattr(product, 'brand', None),
        'article': getattr(product, 'article', None),
        'sku': getattr(product, 'sku', None),
        'url': getattr(product, 'url', ''),
        'marketplace': getattr(product, 'marketplace', MarketplaceType.OTHER).value,
        'current_price': getattr(product, 'current_price', 0.0),
        'original_price': getattr(product, 'original_price', None),
        'discount_percent': getattr(product, 'discount_percent', None),
        'rating': getattr(product, 'rating', None),
        'reviews_count': getattr(product, 'reviews_count', 0),
        'availability': getattr(product, 'availability', True),
        'last_updated': getattr(product, 'last_updated', None).isoformat() if getattr(product, 'last_updated', None) else None,
        'metadata': getattr(product, 'metadata', {}),
    }


def competitor_product_from_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготовка словаря для конструктора CompetitorProduct."""
    out = dict(data)
    if isinstance(out.get('last_updated'), str):
        out['last_updated'] = datetime.fromisoformat(out['last_updated'])
    if out.get('marketplace') is not None and not isinstance(out['marketplace'], MarketplaceType):
        out['marketplace'] = MarketplaceType(out['marketplace'])
    return out


# -------- Competitor --------

def competitor_to_dict(competitor: Any) -> Dict[str, Any]:
    """Сериализация Competitor в словарь."""
    products = getattr(competitor, 'products', [])
    return {
        'id': competitor.id,
        'name': competitor.name,
        'type': getattr(competitor, 'type', CompetitorType.DIRECT).value,
        'marketplace': getattr(competitor, 'marketplace', MarketplaceType.OTHER).value,
        'website_url': getattr(competitor, 'website_url', None),
        'products': [competitor_product_to_dict(p) for p in products],
        'is_active': getattr(competitor, 'is_active', True),
        'priority': getattr(competitor, 'priority', 5),
        'created_at': getattr(competitor, 'created_at', None).isoformat() if getattr(competitor, 'created_at', None) else None,
        'updated_at': getattr(competitor, 'updated_at', None).isoformat() if getattr(competitor, 'updated_at', None) else None,
        'metadata': getattr(competitor, 'metadata', {}),
    }


def competitor_from_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготовка словаря для конструктора Competitor."""
    out = dict(data)
    if isinstance(out.get('created_at'), str):
        out['created_at'] = datetime.fromisoformat(out['created_at'])
    if isinstance(out.get('updated_at'), str):
        out['updated_at'] = datetime.fromisoformat(out['updated_at'])
    if out.get('type') is not None and not isinstance(out['type'], CompetitorType):
        out['type'] = CompetitorType(out['type'])
    if out.get('marketplace') is not None and not isinstance(out['marketplace'], MarketplaceType):
        out['marketplace'] = MarketplaceType(out['marketplace'])
    # Продукты пока оставляем словарями; инстанцирование делается в модели
    return out


def competitor_to_json(competitor: Any) -> str:
    return json.dumps(competitor_to_dict(competitor), ensure_ascii=False, indent=2)


def competitor_from_json_data(json_str: str) -> Dict[str, Any]:
    return competitor_from_dict_data(json.loads(json_str))


# -------- PriceHistory --------

def price_history_to_dict(history: Any) -> Dict[str, Any]:
    """Сериализация PriceHistory в словарь."""
    entries = getattr(history, 'entries', [])
    return {
        'product_id': history.product_id,
        'entries': [entry.to_dict() for entry in entries],
        'created_at': getattr(history, 'created_at', None).isoformat() if getattr(history, 'created_at', None) else None,
        'updated_at': getattr(history, 'updated_at', None).isoformat() if getattr(history, 'updated_at', None) else None,
    }


def price_history_from_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготовка словаря для конструктора PriceHistory."""
    out = dict(data)
    if isinstance(out.get('created_at'), str):
        out['created_at'] = datetime.fromisoformat(out['created_at'])
    if isinstance(out.get('updated_at'), str):
        out['updated_at'] = datetime.fromisoformat(out['updated_at'])
    # entries оставляем как есть (список словарей); инстанцирование делается в модели
    return out


def price_history_to_json(history: Any) -> str:
    return json.dumps(price_history_to_dict(history), ensure_ascii=False, indent=2)


def price_history_from_json_data(json_str: str) -> Dict[str, Any]:
    return price_history_from_dict_data(json.loads(json_str))


__all__ = [
    # Product
    'product_to_dict', 'product_from_dict_data', 'product_to_json', 'product_from_json_data',
    # CompetitorProduct
    'competitor_product_to_dict', 'competitor_product_from_dict_data',
    # Competitor
    'competitor_to_dict', 'competitor_from_dict_data', 'competitor_to_json', 'competitor_from_json_data',
    # PriceHistory
    'price_history_to_dict', 'price_history_from_dict_data', 'price_history_to_json', 'price_history_from_json_data',
]