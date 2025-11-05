#!/usr/bin/env python3
"""Тестовый скрипт для проверки клавиатуры AI-помощника"""

import sys
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent))

from keyboards.keyboards import ai_assistant_keyboard

def test_keyboard():
    """Проверяет, что кнопка 'Генерация карточки' есть в клавиатуре"""
    kb = ai_assistant_keyboard()
    
    print("🔍 Проверка клавиатуры AI-помощника:\n")
    
    all_buttons = []
    for row in kb.inline_keyboard:
        for button in row:
            all_buttons.append(button.text)
            print(f"  ✅ {button.text} (callback: {button.callback_data})")
    
    print(f"\n📊 Всего кнопок: {len(all_buttons)}")
    
    if "🎨 Генерация карточки" in all_buttons:
        print("\n✅ КНОПКА '🎨 Генерация карточки' НАЙДЕНА!")
        return True
    else:
        print("\n❌ КНОПКА '🎨 Генерация карточки' НЕ НАЙДЕНА!")
        print(f"   Доступные кнопки: {', '.join(all_buttons)}")
        return False

if __name__ == "__main__":
    success = test_keyboard()
    sys.exit(0 if success else 1)

