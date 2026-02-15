"""
AI Models Configuration
Доступные AI модели для пользователей
"""
from enum import Enum
from typing import Dict


class AIModel(str, Enum):
    """Доступные AI модели для пользователей"""
    GPT_5_1 = "gpt-5.1"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4.5"
    
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
            cls.GPT_5_1: "GPT-5.1 (OpenAI)",
            cls.CLAUDE_SONNET_4_5: "Claude Sonnet 4.5 (Anthropic)"
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
            cls.GPT_5_1: "Новейшая модель GPT-5.1 от OpenAI с улучшенными возможностями рассуждения",
            cls.CLAUDE_SONNET_4_5: "Продвинутая модель Claude Sonnet 4.5 с глубоким пониманием контекста"
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
            cls.GPT_5_1: "OpenAI",
            cls.CLAUDE_SONNET_4_5: "Anthropic (via Google Vertex AI)"
        }
        return providers.get(model, "Unknown")
    
    @classmethod
    def get_default(cls) -> str:
        """
        Модель по умолчанию
        
        Returns:
            ID модели по умолчанию
        """
        return cls.GPT_5_1
    
    @classmethod
    def get_all_models(cls) -> list[Dict[str, str]]:
        """
        Получить список всех доступных моделей
        
        Returns:
            Список моделей с метаданными
        """
        return [
            {
                "id": cls.GPT_5_1,
                "name": cls.get_display_name(cls.GPT_5_1),
                "provider": cls.get_provider(cls.GPT_5_1),
                "description": cls.get_description(cls.GPT_5_1)
            },
            {
                "id": cls.CLAUDE_SONNET_4_5,
                "name": cls.get_display_name(cls.CLAUDE_SONNET_4_5),
                "provider": cls.get_provider(cls.CLAUDE_SONNET_4_5),
                "description": cls.get_description(cls.CLAUDE_SONNET_4_5)
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
        return model in [cls.GPT_5_1, cls.CLAUDE_SONNET_4_5]
