from typing import Any, Dict
import json

from .analytics import (
    get_dashboard,
    get_sales_timeseries,
    compute_kpis,
    forecast_sales,
)
from .reports import run_report
from .db import run_sql_template

# Stage 2: registry filled with JSON Schemas
registry = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard",
            "description": "Сводка: выручка, заказы, AOV, рейтинг, негатив, остатки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "integer", "minimum": 1},
                    "period": {"type": "string", "default": "7d", "enum": ["7d", "14d", "30d", "90d"]},
                },
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_report",
            "description": "Предопределенные отчеты (топы, просадки, маржинальность, отзывы, реклама).",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_name": {"type": "string", "enum": [
                        "top_products",
                        "decliners",
                        "margins",
                        "reviews",
                        "ad_performance",
                    ]},
                    "params": {"type": "object", "additionalProperties": True},
                },
                "required": ["report_name", "params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql_template",
            "description": "Выполнить SQL-шаблон из allowlist с параметрами.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": [
                        "timeseries_sales",
                        "top_products_by_revenue",
                        "orders_summary",
                        "stock_levels",
                        "neg_reviews_agg",
                    ]},
                    "params": {"type": "object", "additionalProperties": True},
                },
                "required": ["name", "params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_timeseries",
            "description": "Таймсерия продаж (qty, revenue).",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "integer", "minimum": 1},
                    "period": {"type": "string", "default": "30d", "enum": ["7d", "14d", "30d", "90d", "180d"]},
                    "granularity": {"type": "string", "default": "day", "enum": ["day", "week"]},
                },
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_kpis",
            "description": "KPI по области (all/sku/category) и периоду.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kpi_list": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["revenue", "orders", "aov", "conversion", "roas", "margin"]},
                        "minItems": 1,
                    },
                    "scope": {
                        "type": "object",
                        "properties": {
                            "level": {"type": "string", "enum": ["all", "sku", "category"], "default": "all"},
                            "sku_id": {"type": "integer"},
                            "category_id": {"type": "integer"},
                            "telegram_id": {"type": "integer", "minimum": 1},
                        },
                        "required": ["level", "telegram_id"],
                    },
                    "period": {"type": "string", "default": "7d", "enum": ["7d", "14d", "30d", "90d"]},
                },
                "required": ["kpi_list", "scope", "period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_sales",
            "description": "Прогноз продаж/спроса.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "integer", "minimum": 1},
                    "sku_id": {"type": "integer"},
                    "horizon": {"type": "integer", "default": 14, "minimum": 7, "maximum": 60},
                    "method": {"type": "string", "default": "auto", "enum": ["auto", "sma", "prophet", "arima"]},
                    "include_ci": {"type": "boolean", "default": True},
                },
                "required": ["telegram_id"],
            },
        },
    },
]


async def execute_tool(name: str, args_json: str) -> str:
    """Execute a tool by name and return JSON string result."""
    args = json.loads(args_json or "{}")
    if name == "get_dashboard":
        data = await get_dashboard(**args)
        return json.dumps(data, ensure_ascii=False)
    if name == "get_sales_timeseries":
        data = await get_sales_timeseries(**args)
        return json.dumps(data, ensure_ascii=False)
    if name == "compute_kpis":
        data = await compute_kpis(**args)
        return json.dumps(data, ensure_ascii=False)
    if name == "forecast_sales":
        data = await forecast_sales(**args)
        return json.dumps(data, ensure_ascii=False)
    if name == "run_report":
        data = await run_report(**args)
        return json.dumps(data, ensure_ascii=False)
    if name == "run_sql_template":
        # AI передает все аргументы напрямую, а не в params
        # Извлекаем 'name' и остальные передаем как params
        template_name = args.pop("name")
        data = await run_sql_template(name=template_name, params=args)
        return json.dumps(data, ensure_ascii=False)
    raise ValueError(f"Unknown tool: {name}")
