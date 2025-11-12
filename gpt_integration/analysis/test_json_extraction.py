#!/usr/bin/env python3
"""
Тестовый скрипт для проверки извлечения JSON из различных форматов ответов GPT.

Использование:
    python test_json_extraction.py
    
Или для тестирования конкретного файла:
    python test_json_extraction.py path/to/response.txt
"""

import sys
import json

import pytest

from gpt_integration.analysis.pipeline import _safe_json_extract

# Тестовые случаи
TEST_CASES = [
    # Случай 1: Чистый JSON в markdown блоке с меткой json
    {
        "name": "Clean JSON in ```json block",
        "text": """```json
{
  "key_metrics": {"test": 1},
  "anomalies": [],
  "insights": [],
  "recommendations": [],
  "telegram": {"chunks": ["Test message"]},
  "sheets": {"headers": [], "rows": []}
}
```""",
        "should_work": True
    },
    
    # Случай 2: JSON в markdown блоке без метки
    {
        "name": "JSON in ``` block without label",
        "text": """```
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}
```""",
        "should_work": True
    },
    
    # Случай 3: JSON с текстом до
    {
        "name": "JSON with preamble",
        "text": """Here is the analysis result:

```json
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}
```""",
        "should_work": True
    },
    
    # Случай 4: JSON без markdown блока
    {
        "name": "Raw JSON without markdown",
        "text": """{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}""",
        "should_work": True
    },
    
    # Случай 5: JSON с trailing comma
    {
        "name": "JSON with trailing comma",
        "text": """```json
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]},
}
```""",
        "should_work": True
    },
    
    # Случай 6: JSON в верхнем регистре метки
    {
        "name": "JSON in ```JSON block (uppercase)",
        "text": """```JSON
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}
```""",
        "should_work": True
    },
    
    # Случай 7: JSON с объяснением после
    {
        "name": "JSON with text after",
        "text": """```json
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}
```

This is the complete analysis based on the data provided.""",
        "should_work": True
    },
    
    # Случай 8: Множественные JSON объекты (берем первый)
    {
        "name": "Multiple JSON objects",
        "text": """```json
{
  "key_metrics": {"test": 1},
  "telegram": {"chunks": ["Test"]}
}
```

Some other data:
```json
{
  "other": "data"
}
```""",
        "should_work": True
    },
]


@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda case: case["name"])
def test_safe_json_extract_cases(test_case):
    """Проверяем извлечение JSON для заранее подготовленных кейсов."""
    result = _safe_json_extract(test_case["text"])
    
    if test_case["should_work"]:
        assert result is not None, f"JSON не извлечен для кейса: {test_case['name']}"
        assert isinstance(result, dict), "Извлеченный результат должен быть словарем"
    else:
        assert result is None, f"Ожидали провал извлечения, но кейс '{test_case['name']}' прошел"


def run_test_suite() -> bool:
    """Запускает тесты извлечения JSON в ручном режиме с выводом в консоль."""
    print("=" * 80)
    print("TESTING JSON EXTRACTION")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[Test {i}] {test_case['name']}")
        print("-" * 80)
        
        result = _safe_json_extract(test_case["text"])
        success = result is not None
        expected = test_case["should_work"]
        
        if success:
            print(f"✅ SUCCESS - Extracted JSON with {len(result)} keys")
            print(f"   Keys: {', '.join(result.keys())}")
        else:
            print("❌ FAILED - Could not extract JSON")
            print(f"   📝 Text preview: {test_case['text'][:200]}")
        
        if success == expected:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


def run_file(filepath: str) -> bool:
    """Тестировать извлечение JSON из файла (ручной запуск)."""
    print(f"Reading file: {filepath}")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    print(f"File size: {len(text)} chars")
    print("=" * 80)
    
    result = _safe_json_extract(text)
    
    if result is not None:
        print("✅ SUCCESS - Extracted JSON")
        print(f"Keys: {', '.join(result.keys())}")
        print("\nExtracted JSON (pretty):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    
    print("❌ FAILED - Could not extract JSON")
    print("\nText preview (first 500 chars):")
    print(text[:500])
    print("\nText preview (last 500 chars):")
    print(text[-500:])
    return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific file
        success = run_file(sys.argv[1])
        sys.exit(0 if success else 1)
    
    # Run standard tests
    success = run_test_suite()
    sys.exit(0 if success else 1)

