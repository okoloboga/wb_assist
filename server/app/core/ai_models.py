"""
AI Models Configuration
Доступные AI модели для пользователей
"""
from enum import Enum
from typing import Dict


class AIModel(str, Enum):
    """Доступные AI модели для пользователей"""
    GPT_4O_MINI = "gpt-4o-mini"
    CLAUDE_SONNET_35 = "claude-sonnet-3.5"
    
    @classmethod
    def get_display_name(cls, model: str) -> str:
        """
        Получить читаемое название модели
        
        Args:
            model: ID модели
            
        Returns:
            Читаемое название
        """
        names = {
            cls.GPT_4O_MINI: "GPT-4o Mini (OpenAI)",
            cls.CLAUDE_SONNET_35: "Claude Sonnet 3.5 (Anthropic)"
        }
        return names.get(model, model)
    
    @classmethod
    def get_description(cls, model: str) -> str:
        """
        Получить описание модели
        
        Args:
            model: ID модели
            
        Returns:
            Описание модели
        """
        descriptions = {
            cls.GPT_4O_MINI: "Быстрая и экономичная модель от OpenAI с отличным качеством",
            cls.CLAUDE_SONNET_35: "Продвинутая модель с глубоким пониманием контекста от Anthropic"
        }
        return descriptions.get(model, "")
    
    @classmethod
    def get_provider(cls, model: str) -> str:
        """
        Получить провайдера модели
        
        Args:
            model: ID модели
            
        Returns:
            Название провайдера
        """
        providers = {
            cls.GPT_4O_MINI: "OpenAI",
            cls.CLAUDE_SONNET_35: "Anthropic"
        }
        return providers.get(model, "Unknown")
    
    @classmethod
    def get_default(cls) -> str:
        """
        Модель по умолчанию
        
        Returns:
            ID модели по умолчанию
        """
        return cls.GPT_4O_MINI
    
    @classmethod
    def get_all_models(cls) -> list[Dict[str, str]]:
        """
        Получить список всех доступных моделей
        
        Returns:
            Список моделей с метаданными
        """
        return [
            {
                "id": cls.GPT_4O_MINI,
                "name": cls.get_display_name(cls.GPT_4O_MINI),
                "provider": cls.get_provider(cls.GPT_4O_MINI),
                "description": cls.get_description(cls.GPT_4O_MINI)
            },
            {
                "id": cls.CLAUDE_SONNET_35,
                "name": cls.get_display_name(cls.CLAUDE_SONNET_35),
                "provider": cls.get_provider(cls.CLAUDE_SONNET_35),
                "description": cls.get_description(cls.CLAUDE_SONNET_35)
            }
        ]
    
    @classmethod
    def is_valid(cls, model: str) -> bool:
        """
        Проверить, является ли модель валидной
        
        Args:
            model: ID модели
            
        Returns:
            True если модель валидна
        """
        return model in [cls.GPT_4O_MINI, cls.CLAUDE_SONNET_35]
