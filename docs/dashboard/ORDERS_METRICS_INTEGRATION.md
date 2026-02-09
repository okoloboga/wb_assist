# Добавление метрик заказов в Dashboard бота

## 📋 ОБЗОР

Данное руководство описывает процесс добавления метрик заказов в dashboard Telegram бота:
- **Новых заказов** за период (7 и 30 дней)
- **Сумма заказов** за период (7 и 30 дней)

---

## 🎯 ЦЕЛЬ

Добавить в текстовое сообщение dashboard бота информацию о заказах:

```
📊 Ваша статистика

📦 Заказы:
• Новых заказов (7 дней): 15
• На сумму (7 дней): 45 750 ₽
• Новых заказов (30 дней): 67
• На сумму (30 дней): 198 340 ₽

⭐ Отзывы:
• Новых отзывов: 8
• Средний рейтинг: 4.7
...
```

---

## 📁 СТРУКТУРА ИЗМЕНЕНИЙ

### Файлы для изменения:

```
server/
├── app/
│   └── features/
│       └── bot_api/
│           ├── service.py          # Добавить логику подсчета заказов
│           └── routes.py           # Обновить endpoint dashboard
│
bot/
└── handlers/
    └── commands.py                 # Обновить форматирование dashboard
```

---

## 🔧 ЭТАП 1: Backend - Добавление логики подсчета заказов

### 1.1 Обновить `server/app/features/bot_api/service.py`

Добавить функцию для подсчета заказов за период:

```python
async def get_orders_stats(
    db: AsyncSession,
    telegram_id: int,
    days: int = 7
) -> Dict[str, Any]:
    """
    Получить статистику заказов за указанный период
    
    Args:
        db: Сессия базы данных
        telegram_id: Telegram ID пользователя
        days: Количество дней для анализа (7 или 30)
    
    Returns:
        Dict с количеством заказов и суммой
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select, func
    from app.models import Order, User
    
    # Получаем пользователя
    user_result = await db.execute(
        select(User).where(User.tg_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return {
            "count": 0,
            "total_amount": 0
        }
    
    # Вычисляем дату начала периода
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Подсчитываем количество заказов и сумму
    result = await db.execute(
        select(
            func.count(Order.id).label('count'),
            func.coalesce(func.sum(Order.total_price), 0).label('total_amount')
        )
        .where(
            Order.user_id == user.id,
            Order.created_at >= start_date
        )
    )
    
    stats = result.one()
    
    return {
        "count": stats.count,
        "total_amount": float(stats.total_amount)
    }
```

### 1.2 Обновить функцию `get_dashboard_data` в `service.py`

Добавить вызов новой функции:

```python
async def get_dashboard_data(
    db: AsyncSession,
    telegram_id: int
) -> Dict[str, Any]:
    """Получить данные для dashboard"""
    
    # Существующий код...
    
    # Добавить статистику заказов
    orders_7d = await get_orders_stats(db, telegram_id, days=7)
    orders_30d = await get_orders_stats(db, telegram_id, days=30)
    
    return {
        # Существующие поля...
        "orders_7d_count": orders_7d["count"],
        "orders_7d_amount": orders_7d["total_amount"],
        "orders_30d_count": orders_30d["count"],
        "orders_30d_amount": orders_30d["total_amount"],
    }
```

---

## 🔧 ЭТАП 2: Backend - Обновление API endpoint

### 2.1 Обновить схему ответа в `routes.py`

Добавить новые поля в схему `DashboardResponse`:

```python
class DashboardResponse(BaseModel):
    """Схема ответа dashboard"""
    
    # Существующие поля...
    
    # Новые поля для заказов
    orders_7d_count: int = Field(0, description="Количество заказов за 7 дней")
    orders_7d_amount: float = Field(0.0, description="Сумма заказов за 7 дней")
    orders_30d_count: int = Field(0, description="Количество заказов за 30 дней")
    orders_30d_amount: float = Field(0.0, description="Сумма заказов за 30 дней")
```

### 2.2 Обновить endpoint `/api/v1/bot/dashboard`

Убедиться, что endpoint возвращает новые поля:

```python
@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить данные для dashboard бота"""
    
    data = await get_dashboard_data(db, telegram_id)
    
    return DashboardResponse(
        # Существующие поля...
        orders_7d_count=data.get("orders_7d_count", 0),
        orders_7d_amount=data.get("orders_7d_amount", 0.0),
        orders_30d_count=data.get("orders_30d_count", 0),
        orders_30d_amount=data.get("orders_30d_amount", 0.0),
    )
```

---

## 🔧 ЭТАП 3: Bot - Обновление форматирования dashboard

### 3.1 Обновить `bot/handlers/commands.py`

Найти функцию форматирования dashboard и добавить секцию заказов:

```python
async def format_dashboard_message(dashboard_data: dict) -> str:
    """Форматировать сообщение dashboard"""
    
    # Форматирование сумм
    def format_amount(amount: float) -> str:
        """Форматировать сумму с разделителями"""
        return f"{amount:,.0f}".replace(",", " ") + " ₽"
    
    # Извлекаем данные заказов
    orders_7d_count = dashboard_data.get("orders_7d_count", 0)
    orders_7d_amount = dashboard_data.get("orders_7d_amount", 0.0)
    orders_30d_count = dashboard_data.get("orders_30d_count", 0)
    orders_30d_amount = dashboard_data.get("orders_30d_amount", 0.0)
    
    message = "📊 Ваша статистика\n\n"
    
    # Секция заказов
    message += "📦 Заказы:\n"
    message += f"• Новых заказов (7 дней): {orders_7d_count}\n"
    message += f"• На сумму (7 дней): {format_amount(orders_7d_amount)}\n"
    message += f"• Новых заказов (30 дней): {orders_30d_count}\n"
    message += f"• На сумму (30 дней): {format_amount(orders_30d_amount)}\n\n"
    
    # Существующие секции (отзывы, склад и т.д.)
    # ...
    
    return message
```

### 3.2 Пример полного форматирования

```python
async def format_dashboard_message(dashboard_data: dict) -> str:
    """Форматировать сообщение dashboard с метриками заказов"""
    
    def format_amount(amount: float) -> str:
        """Форматировать сумму"""
        return f"{amount:,.0f}".replace(",", " ") + " ₽"
    
    # Заказы
    orders_7d_count = dashboard_data.get("orders_7d_count", 0)
    orders_7d_amount = dashboard_data.get("orders_7d_amount", 0.0)
    orders_30d_count = dashboard_data.get("orders_30d_count", 0)
    orders_30d_amount = dashboard_data.get("orders_30d_amount", 0.0)
    
    # Отзывы
    new_reviews = dashboard_data.get("new_reviews_count", 0)
    avg_rating = dashboard_data.get("average_rating", 0.0)
    
    # Склад
    low_stock_count = dashboard_data.get("low_stock_count", 0)
    out_of_stock_count = dashboard_data.get("out_of_stock_count", 0)
    
    message = "📊 Ваша статистика\n\n"
    
    # Заказы
    message += "📦 Заказы:\n"
    message += f"• Новых заказов (7 дней): {orders_7d_count}\n"
    message += f"• На сумму (7 дней): {format_amount(orders_7d_amount)}\n"
    message += f"• Новых заказов (30 дней): {orders_30d_count}\n"
    message += f"• На сумму (30 дней): {format_amount(orders_30d_amount)}\n\n"
    
    # Отзывы
    message += "⭐ Отзывы:\n"
    message += f"• Новых отзывов: {new_reviews}\n"
    message += f"• Средний рейтинг: {avg_rating:.1f}\n\n"
    
    # Склад
    message += "📦 Склад:\n"
    message += f"• Товаров с низким остатком: {low_stock_count}\n"
    message += f"• Товаров нет в наличии: {out_of_stock_count}\n\n"
    
    message += "Используйте меню ниже для подробной информации"
    
    return message
```

---

## 🗄️ ЭТАП 4: База данных - Проверка структуры

### 4.1 Убедиться, что таблица `orders` существует

Проверить наличие таблицы и необходимых полей:

```sql
-- Структура таблицы orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    total_price DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50),
    -- другие поля...
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at);
```
 

*Документация создана: 7 февраля 2026*  
*Версия: 1.0*