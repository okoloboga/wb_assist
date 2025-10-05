#!/usr/bin/env python3
"""
Скрипт для запуска тестов бота
Запускать из директории bot/
"""
import sys
import os
import subprocess

# Добавляем текущую директорию в путь (bot/)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def run_tests():
    """Запустить все тесты"""
    print("🧪 Запуск тестов бота...")
    
    # Команда для запуска pytest из директории bot/
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",  # подробный вывод
        "--tb=short",  # короткий traceback
        "--cov=.",  # покрытие кода (текущая директория)
        "--cov-report=term-missing",  # отчет о покрытии
        "--asyncio-mode=auto"  # автоматический режим asyncio
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Все тесты прошли успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Тесты завершились с ошибкой: {e}")
        return False
    except FileNotFoundError:
        print("❌ pytest не найден. Установите его: pip install pytest pytest-asyncio pytest-cov")
        return False

def run_unit_tests():
    """Запустить только unit тесты"""
    print("🧪 Запуск unit тестов...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Unit тесты прошли успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Unit тесты завершились с ошибкой: {e}")
        return False

def run_api_key_tests():
    """Запустить тесты для проверки API ключа"""
    print("🔑 Запуск тестов проверки API ключа...")
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/test_api_key_simple.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Тесты проверки API ключа прошли успешно!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Тесты проверки API ключа завершились с ошибкой: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            success = run_unit_tests()
        elif sys.argv[1] == "api-key":
            success = run_api_key_tests()
        else:
            print("❌ Неизвестный аргумент. Используйте: unit, api-key или без аргументов")
            success = False
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)