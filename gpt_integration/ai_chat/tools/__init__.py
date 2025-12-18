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
            "description": "Получить отчет о топ-товарах по выручке за выбранный период. ВАЖНО: params ОБЯЗАТЕЛЬНО должен содержать telegram_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_name": {
                        "type": "string",
                        "enum": ["top_products"],
                        "description": "Тип отчета. Сейчас доступен только 'top_products' (топ товаров по выручке)"
                    },
                    "params": {
                        "type": "object",
                        "properties": {
                            "telegram_id": {
                                "type": "integer",
                                "description": "ID пользователя в Telegram (ОБЯЗАТЕЛЬНО)"
                            },
                            "period": {
                                "type": "string",
                                "description": "Период для отчета (опционально)",
                                "enum": ["7d", "14d", "30d", "90d"]
                            }
                        },
                        "required": ["telegram_id"],
                        "additionalProperties": True
                    },
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        args = json.loads(args_json or "{}")
        logger.info(f"🔧 Executing tool: {name} with args: {args}")
        
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
            # AI может передавать параметры в двух форматах:
            # 1. {"report_name": "...", "params": {...}}
            # 2. {"report_name": "...", "telegram_id": ..., "period": ..., ...}
            # Обрабатываем оба случая
            if "params" in args and isinstance(args["params"], dict):
                # Формат 1: параметры в отдельном объекте params
                report_name = args.get("report_name")
                params = args["params"]
            else:
                # Формат 2: все параметры на верхнем уровне
                report_name = args.pop("report_name", None)
                if report_name is None:
                    raise ValueError("Missing required parameter 'report_name' for run_report")
                params = args  # Остальные параметры становятся params
            
            data = await run_report(report_name=report_name, params=params)
            return json.dumps(data, ensure_ascii=False)
        if name == "run_sql_template":
            # AI передает все аргументы напрямую, а не в params
            # Извлекаем 'name' и остальные передаем как params
            template_name = args.pop("name")
            data = await run_sql_template(name=template_name, params=args)
            return json.dumps(data, ensure_ascii=False)
        
        logger.error(f"❌ Unknown tool: {name}")
        raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"❌ Error executing tool {name} with args {args_json}: {e}", exc_info=True)
        # Возвращаем JSON с ошибкой, чтобы AI мог обработать её
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "tool": name
        }
        return json.dumps(error_response, ensure_ascii=False)
