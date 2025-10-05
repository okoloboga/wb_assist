"""
Проверка импортов для тестов кабинетов
"""

def test_imports():
    """Тест что все импорты работают"""
    from app.features.user.models import User
    from app.features.wb_api.models import WBCabinet
    from app.features.bot_api.service import BotAPIService
    from app.features.bot_api.formatter import BotMessageFormatter
    
    # Проверяем что классы существуют
    assert User is not None
    assert WBCabinet is not None
    assert BotAPIService is not None
    assert BotMessageFormatter is not None