"""
Скрипт для тестирования генерации карточек товаров.
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gpt_integration.card_generation.service import generate_card


def test_card_generation():
    """Тест генерации карточки товара."""
    print("🧪 Тестирование генерации карточки товара...\n")
    
    # Тестовые данные
    characteristics = {
        "name": "Платье летнее с цветочным принтом",
        "brand": "Fashion Style",
        "category": "Одежда > Платья"
    }
    target_audience = "Женщины 25-40 лет, активные, следящие за модой, ценящие качество и комфорт"
    selling_points = (
        "Премиальное качество ткани (100% хлопок), "
        "уникальный дизайн с цветочным принтом, "
        "удобная посадка по фигуре, "
        "экологичное производство"
    )
    
    print("📝 Входные данные:")
    print(f"  Название: {characteristics['name']}")
    print(f"  Бренд: {characteristics['brand']}")
    print(f"  Категория: {characteristics['category']}")
    print(f"  Целевая аудитория: {target_audience}")
    print(f"  Преимущества: {selling_points}\n")
    
    print("⏳ Генерация карточки...\n")
    
    try:
        result = generate_card(
            characteristics=characteristics,
            target_audience=target_audience,
            selling_points=selling_points
        )
        
        if result.get("status") == "success":
            print("✅ Карточка успешно сгенерирована!\n")
            print("=" * 80)
            print("РЕЗУЛЬТАТ:")
            print("=" * 80)
            print(result.get("card", ""))
            print("=" * 80)
        else:
            print(f"❌ Ошибка генерации: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при генерации: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    # Проверяем наличие API ключа
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  ВНИМАНИЕ: OPENAI_API_KEY не установлен!")
        print("   Установите переменную окружения перед запуском теста.\n")
    
    success = test_card_generation()
    sys.exit(0 if success else 1)

