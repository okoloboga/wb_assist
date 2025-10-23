#!/usr/bin/env python3
"""
Скрипт для создания тестовых данных для проверки уведомлений
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.app.core.database import get_db
from server.app.features.user.crud import get_user_by_telegram_id
from server.app.features.wb_api.crud import get_cabinet_by_user_id
from server.app.features.wb_api.models import WBOrder, WBReview, WBStock, WBProduct
from server.app.features.notifications.models import NotificationSettings

async def create_test_data():
    """Создание тестовых данных"""
    print("📊 Создание тестовых данных...")
    
    db = next(get_db())
    
    try:
        # Находим пользователя
        user = get_user_by_telegram_id(db, 123456789)  # Замените на ваш telegram_id
        if not user:
            print("❌ Пользователь не найден. Создайте пользователя с telegram_id=123456789")
            return
        
        print(f"✅ Найден пользователь: {user.id}")
        
        # Находим кабинет
        cabinet = get_cabinet_by_user_id(db, user.id)
        if not cabinet:
            print("❌ Кабинет не найден")
            return
        
        print(f"✅ Найден кабинет: {cabinet.id}")
        
        # Создаем тестовый продукт
        test_product = WBProduct(
            cabinet_id=cabinet.id,
            nm_id=123456789,
            name="Тестовый товар",
            sku="TEST_SKU_001",
            price=1000.0,
            discount_price=800.0,
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        # Проверяем, существует ли уже такой продукт
        existing_product = db.query(WBProduct).filter(
            WBProduct.cabinet_id == cabinet.id,
            WBProduct.nm_id == test_product.nm_id
        ).first()
        
        if not existing_product:
            db.add(test_product)
            db.commit()
            print("✅ Создан тестовый продукт")
        else:
            test_product = existing_product
            print("✅ Используем существующий продукт")
        
        # Создаем тестовые заказы
        test_orders = [
            {
                "order_id": 9999999999999999999,
                "status": "active",
                "created_at": datetime.utcnow() - timedelta(minutes=15),
                "updated_at": datetime.utcnow() - timedelta(minutes=10)
            },
            {
                "order_id": 9999999999999999998,
                "status": "canceled",
                "created_at": datetime.utcnow() - timedelta(minutes=20),
                "updated_at": datetime.utcnow() - timedelta(minutes=5)
            }
        ]
        
        for order_data in test_orders:
            existing_order = db.query(WBOrder).filter(
                WBOrder.cabinet_id == cabinet.id,
                WBOrder.order_id == order_data["order_id"]
            ).first()
            
            if not existing_order:
                test_order = WBOrder(
                    cabinet_id=cabinet.id,
                    order_id=order_data["order_id"],
                    nm_id=test_product.nm_id,
                    status=order_data["status"],
                    order_date=datetime.utcnow() - timedelta(days=1),
                    created_at=order_data["created_at"],
                    updated_at=order_data["updated_at"]
                )
                db.add(test_order)
                print(f"✅ Создан тестовый заказ: {order_data['order_id']}")
            else:
                # Обновляем статус для тестирования
                existing_order.status = order_data["status"]
                existing_order.updated_at = order_data["updated_at"]
                print(f"✅ Обновлен тестовый заказ: {order_data['order_id']}")
        
        # Создаем тестовые отзывы
        test_reviews = [
            {
                "review_id": 8888888888888888888,
                "rating": 1,
                "created_date": datetime.utcnow() - timedelta(minutes=12)
            },
            {
                "review_id": 8888888888888888887,
                "rating": 2,
                "created_date": datetime.utcnow() - timedelta(minutes=8)
            }
        ]
        
        for review_data in test_reviews:
            existing_review = db.query(WBReview).filter(
                WBReview.cabinet_id == cabinet.id,
                WBReview.review_id == review_data["review_id"]
            ).first()
            
            if not existing_review:
                test_review = WBReview(
                    cabinet_id=cabinet.id,
                    review_id=review_data["review_id"],
                    nm_id=test_product.nm_id,
                    rating=review_data["rating"],
                    text="Тестовый негативный отзыв",
                    created_date=review_data["created_date"]
                )
                db.add(test_review)
                print(f"✅ Создан тестовый отзыв: {review_data['review_id']}")
            else:
                print(f"✅ Используем существующий отзыв: {review_data['review_id']}")
        
        # Создаем тестовые остатки
        test_stocks = [
            {
                "nm_id": test_product.nm_id,
                "quantity": 5,
                "updated_at": datetime.utcnow() - timedelta(minutes=18)
            },
            {
                "nm_id": test_product.nm_id,
                "quantity": 1,
                "updated_at": datetime.utcnow() - timedelta(minutes=3)
            }
        ]
        
        for stock_data in test_stocks:
            existing_stock = db.query(WBStock).filter(
                WBStock.cabinet_id == cabinet.id,
                WBStock.nm_id == stock_data["nm_id"]
            ).first()
            
            if not existing_stock:
                test_stock = WBStock(
                    cabinet_id=cabinet.id,
                    nm_id=stock_data["nm_id"],
                    quantity=stock_data["quantity"],
                    updated_at=stock_data["updated_at"]
                )
                db.add(test_stock)
                print(f"✅ Создан тестовый остаток: {stock_data['nm_id']}")
            else:
                # Обновляем количество для тестирования
                existing_stock.quantity = stock_data["quantity"]
                existing_stock.updated_at = stock_data["updated_at"]
                print(f"✅ Обновлен тестовый остаток: {stock_data['nm_id']}")
        
        db.commit()
        
        # Проверяем настройки уведомлений
        settings = db.query(NotificationSettings).filter(
            NotificationSettings.user_id == user.id
        ).first()
        
        if not settings:
            settings = NotificationSettings(
                user_id=user.id,
                notify_orders=True,
                notify_reviews=True,
                notify_stocks=True,
                notify_claims=True,
                notify_sales=True
            )
            db.add(settings)
            db.commit()
            print("✅ Созданы настройки уведомлений")
        else:
            print("✅ Настройки уведомлений уже существуют")
        
        print("\n✅ Тестовые данные созданы успешно!")
        print(f"   - Продукт: {test_product.nm_id}")
        print(f"   - Заказы: {len(test_orders)}")
        print(f"   - Отзывы: {len(test_reviews)}")
        print(f"   - Остатки: {len(test_stocks)}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании тестовых данных: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_test_data())
