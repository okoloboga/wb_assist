# 🤖 Выбор AI модели пользователем

## 📋 Описание задачи

Реализовать возможность выбора AI модели (GPT-4o или Claude Sonnet 3.5) для каждого пользователя индивидуально. Выбранная модель будет использоваться для:
- AI-ассистента (RAG)
- Аналитики продаж
- Генерации контента

## 🎯 Цели

1. Убрать глобальную переменную `COMET_TEXT_MODEL` из `.env`
2. Добавить поле `preferred_ai_model` в таблицу `users`
3. Создать UI для выбора модели в настройках бота
4. Обновить GPT сервис для работы с пользовательскими моделями
5. Установить `gpt-4o` как модель по умолчанию

## 🏗 Архитектура решения

```
┌─────────────────┐
│  Telegram Bot   │
│   Настройки     │
└────────┬────────┘
         │ Выбор модели
         ▼
┌─────────────────┐
│   Backend API   │
│ Update user     │
│ preferred_model │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│ users.preferred │
│   _ai_model     │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  GPT Service    │
│ Использует      │
│ модель юзера    │
└─────────────────┘
```

---

## 📝 Этап 1: Миграция базы данных

### 1.1 Создание миграции

Создать новую миграцию Alembic:

```bash
cd server
alembic revision -m "add_preferred_ai_model_to_users"
```

### 1.2 Содержимое миграции

Файл: `server/alembic/versions/XXXX_add_preferred_ai_model_to_users.py`


```python
"""add preferred_ai_model to users

Revision ID: XXXX
Revises: YYYY
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'XXXX'
down_revision = 'YYYY'
branch_labels = None
depends_on = None

def upgrade():
    # Добавляем колонку preferred_ai_model
    op.add_column('users', 
        sa.Column('preferred_ai_model', 
                  sa.String(50), 
                  nullable=False, 
                  server_default='gpt-4o')
    )
    
    # Создаем индекс для быстрого поиска
    op.create_index('idx_users_preferred_ai_model', 
                    'users', 
                    ['preferred_ai_model'])

def downgrade():
    op.drop_index('idx_users_preferred_ai_model', table_name='users')
    op.drop_column('users', 'preferred_ai_model')
```

### 1.3 Применение миграции

```bash
cd server
alembic upgrade head
```

---

## 📝 Этап 2: Обновление модели User

### 2.1 Обновить модель пользователя

Файл: `server/app/features/wb_api/models.py` (или где определена модель User)

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Новое поле для выбора AI модели
    preferred_ai_model = Column(
        String(50), 
        nullable=False, 
        default='gpt-4o',
        server_default='gpt-4o'
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 2.2 Доступные модели

Создать enum для моделей:

Файл: `server/app/core/ai_models.py`

```python
from enum import Enum

class AIModel(str, Enum):
    """Доступные AI модели для пользователей"""
    GPT_4O = "gpt-4o"
    CLAUDE_SONNET_35 = "claude-sonnet-3.5"
    
    @classmethod
    def get_display_name(cls, model: str) -> str:
        """Получить читаемое название модели"""
        names = {
            cls.GPT_4O: "GPT-4o (OpenAI)",
            cls.CLAUDE_SONNET_35: "Claude Sonnet 3.5 (Anthropic)"
        }
        return names.get(model, model)
    
    @classmethod
    def get_default(cls) -> str:
        """Модель по умолчанию"""
        return cls.GPT_4O
```

---

## 📝 Этап 3: Backend API endpoints

### 3.1 Создать схемы Pydantic

Файл: `server/app/features/bot_api/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class UserSettingsUpdate(BaseModel):
    """Обновление настроек пользователя"""
    preferred_ai_model: Optional[str] = Field(
        None, 
        description="Предпочитаемая AI модель"
    )

class UserSettingsResponse(BaseModel):
    """Ответ с настройками пользователя"""
    telegram_id: int
    preferred_ai_model: str
    
    class Config:
        from_attributes = True

class AIModelsListResponse(BaseModel):
    """Список доступных AI моделей"""
    models: list[dict]
    default_model: str
```

### 3.2 Добавить endpoints

Файл: `server/app/features/bot_api/routes.py`


```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.ai_models import AIModel
from .schemas import UserSettingsUpdate, UserSettingsResponse, AIModelsListResponse

router = APIRouter(prefix="/api/v1/bot", tags=["bot"])

@router.get("/ai-models", response_model=AIModelsListResponse)
async def get_available_ai_models():
    """
    Получить список доступных AI моделей
    """
    models = [
        {
            "id": AIModel.GPT_4O,
            "name": AIModel.get_display_name(AIModel.GPT_4O),
            "provider": "OpenAI",
            "description": "Быстрая и точная модель от OpenAI"
        },
        {
            "id": AIModel.CLAUDE_SONNET_35,
            "name": AIModel.get_display_name(AIModel.CLAUDE_SONNET_35),
            "provider": "Anthropic",
            "description": "Продвинутая модель с глубоким пониманием контекста"
        }
    ]
    
    return {
        "models": models,
        "default_model": AIModel.get_default()
    }

@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """
    Получить настройки пользователя
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "telegram_id": user.telegram_id,
        "preferred_ai_model": user.preferred_ai_model
    }

@router.patch("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    telegram_id: int,
    settings: UserSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновить настройки пользователя
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Валидация модели
    if settings.preferred_ai_model:
        if settings.preferred_ai_model not in [AIModel.GPT_4O, AIModel.CLAUDE_SONNET_35]:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid AI model. Available: {[m.value for m in AIModel]}"
            )
        user.preferred_ai_model = settings.preferred_ai_model
    
    db.commit()
    db.refresh(user)
    
    return {
        "telegram_id": user.telegram_id,
        "preferred_ai_model": user.preferred_ai_model
    }
```

---

## 📝 Этап 4: Telegram Bot - UI для выбора модели

### 4.1 Обновить клавиатуры

Файл: `bot/keyboards/keyboards.py`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Выбор AI модели", callback_data="settings_ai_model")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    return keyboard

def get_ai_model_selection_keyboard(current_model: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора AI модели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ GPT-4o" if current_model == "gpt-4o" else "GPT-4o",
                callback_data="ai_model_gpt-4o"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Claude Sonnet 3.5" if current_model == "claude-sonnet-3.5" else "Claude Sonnet 3.5",
                callback_data="ai_model_claude-sonnet-3.5"
            )
        ],
        [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings")]
    ])
    return keyboard
```

### 4.2 Создать handler для настроек

Файл: `bot/handlers/settings.py`


```python
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from bot.api.client import BotAPIClient
from bot.keyboards.keyboards import get_settings_keyboard, get_ai_model_selection_keyboard

router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings - открыть настройки"""
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел настроек:",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "settings_ai_model")
async def show_ai_model_selection(callback: CallbackQuery):
    """Показать выбор AI модели"""
    client = BotAPIClient()
    
    # Получаем текущие настройки пользователя
    settings = await client.get_user_settings(callback.from_user.id)
    current_model = settings.get("preferred_ai_model", "gpt-4o")
    
    # Получаем список доступных моделей
    models_data = await client.get_available_ai_models()
    
    text = (
        "🤖 <b>Выбор AI модели</b>\n\n"
        f"Текущая модель: <b>{get_model_display_name(current_model)}</b>\n\n"
        "Доступные модели:\n\n"
    )
    
    for model in models_data["models"]:
        text += f"• <b>{model['name']}</b>\n"
        text += f"  {model['description']}\n\n"
    
    text += "Выберите модель для AI-ассистента и аналитики:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ai_model_selection_keyboard(current_model)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ai_model_"))
async def select_ai_model(callback: CallbackQuery):
    """Выбрать AI модель"""
    model_id = callback.data.replace("ai_model_", "")
    client = BotAPIClient()
    
    # Обновляем настройки пользователя
    await client.update_user_settings(
        telegram_id=callback.from_user.id,
        preferred_ai_model=model_id
    )
    
    model_name = get_model_display_name(model_id)
    
    await callback.answer(
        f"✅ Модель {model_name} выбрана!",
        show_alert=True
    )
    
    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=get_ai_model_selection_keyboard(model_id)
    )

@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    """Вернуться к настройкам"""
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел настроек:",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()

def get_model_display_name(model_id: str) -> str:
    """Получить читаемое название модели"""
    names = {
        "gpt-4o": "GPT-4o (OpenAI)",
        "claude-sonnet-3.5": "Claude Sonnet 3.5 (Anthropic)"
    }
    return names.get(model_id, model_id)
```

### 4.3 Обновить API клиент бота

Файл: `bot/api/client.py`

```python
class BotAPIClient:
    # ... существующий код ...
    
    async def get_available_ai_models(self) -> dict:
        """Получить список доступных AI моделей"""
        response = await self._make_request("GET", "/ai-models")
        return response
    
    async def get_user_settings(self, telegram_id: int) -> dict:
        """Получить настройки пользователя"""
        response = await self._make_request(
            "GET", 
            "/settings",
            params={"telegram_id": telegram_id}
        )
        return response
    
    async def update_user_settings(
        self, 
        telegram_id: int, 
        preferred_ai_model: str = None
    ) -> dict:
        """Обновить настройки пользователя"""
        data = {}
        if preferred_ai_model:
            data["preferred_ai_model"] = preferred_ai_model
        
        response = await self._make_request(
            "PATCH",
            "/settings",
            params={"telegram_id": telegram_id},
            json=data
        )
        return response
```

### 4.4 Зарегистрировать router

Файл: `bot/__main__.py`

```python
from bot.handlers import settings

# ... существующий код ...

# Регистрация handlers
dp.include_router(settings.router)
```

---

## 📝 Этап 5: Обновление GPT Service

### 5.1 Обновить конфигурацию

Файл: `gpt_integration/core/config.py`


```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Модель по умолчанию (если у пользователя не указана)
    DEFAULT_AI_MODEL: str = "gpt-4o"
    
    # Удалить COMET_TEXT_MODEL - больше не используется
    # COMET_TEXT_MODEL: str = "gpt-4.1"  # DEPRECATED
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 5.2 Создать универсальный LLM клиент

Файл: `gpt_integration/core/llm_client.py`

```python
from typing import Optional, List, Dict
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from .config import settings

class UniversalLLMClient:
    """Универсальный клиент для работы с разными LLM"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.anthropic_client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY
        ) if settings.ANTHROPIC_API_KEY else None
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Универсальный метод для chat completion
        
        Args:
            model: ID модели (gpt-4o, claude-sonnet-3.5)
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимум токенов
        
        Returns:
            Сгенерированный текст
        """
        if model.startswith("gpt"):
            return await self._openai_completion(model, messages, temperature, max_tokens)
        elif model.startswith("claude"):
            return await self._anthropic_completion(model, messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    async def _openai_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """OpenAI completion"""
        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    async def _anthropic_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Anthropic (Claude) completion"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")
        
        # Конвертируем формат сообщений для Claude
        system_message = None
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        response = await self.anthropic_client.messages.create(
            model=model,
            system=system_message,
            messages=claude_messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.content[0].text

# Singleton instance
llm_client = UniversalLLMClient()
```

### 5.3 Обновить AI Chat сервис

Файл: `gpt_integration/ai_chat/service.py`

```python
from gpt_integration.core.llm_client import llm_client
from gpt_integration.core.config import settings

class AIChatService:
    # ... существующий код ...
    
    async def get_user_model(self, telegram_id: int) -> str:
        """
        Получить предпочитаемую модель пользователя из БД
        
        Args:
            telegram_id: Telegram ID пользователя
        
        Returns:
            ID модели (gpt-4o, claude-sonnet-3.5)
        """
        user = self.db.query(User).filter(
            User.telegram_id == telegram_id
        ).first()
        
        if user and user.preferred_ai_model:
            return user.preferred_ai_model
        
        return settings.DEFAULT_AI_MODEL
    
    async def send_message(
        self,
        telegram_id: int,
        message: str,
        context: Optional[str] = None
    ) -> dict:
        """Отправить сообщение в AI чат"""
        
        # Получаем модель пользователя
        user_model = await self.get_user_model(telegram_id)
        
        # Проверяем лимиты
        if not await self.check_limits(telegram_id):
            return {
                "success": False,
                "error": "Daily limit exceeded"
            }
        
        # Получаем историю
        history = await self.get_history(telegram_id, limit=10)
        
        # Формируем messages
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Добавляем историю
        for msg in history:
            messages.append({"role": "user", "content": msg.user_message})
            messages.append({"role": "assistant", "content": msg.assistant_response})
        
        # Добавляем текущее сообщение
        if context:
            messages.append({"role": "user", "content": f"Контекст: {context}\n\nВопрос: {message}"})
        else:
            messages.append({"role": "user", "content": message})
        
        # Вызываем LLM с моделью пользователя
        response_text = await llm_client.chat_completion(
            model=user_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        # Сохраняем в историю
        await self.save_to_history(telegram_id, message, response_text)
        
        # Обновляем лимиты
        await self.increment_usage(telegram_id)
        
        return {
            "success": True,
            "response": response_text,
            "model_used": user_model,
            "remaining_requests": await self.get_remaining_requests(telegram_id)
        }
```

### 5.4 Обновить Analysis сервис

Файл: `gpt_integration/analysis/service.py`


```python
from gpt_integration.core.llm_client import llm_client
from gpt_integration.core.config import settings

class AnalysisService:
    # ... существующий код ...
    
    async def get_user_model(self, telegram_id: int) -> str:
        """Получить предпочитаемую модель пользователя"""
        user = self.db.query(User).filter(
            User.telegram_id == telegram_id
        ).first()
        
        if user and user.preferred_ai_model:
            return user.preferred_ai_model
        
        return settings.DEFAULT_AI_MODEL
    
    async def analyze_sales(
        self,
        telegram_id: int,
        period: str = "7d"
    ) -> dict:
        """Анализ продаж с использованием модели пользователя"""
        
        # Получаем модель пользователя
        user_model = await self.get_user_model(telegram_id)
        
        # Получаем данные для анализа
        sales_data = await self.fetch_sales_data(telegram_id, period)
        
        # Формируем промпт
        messages = [
            {"role": "system", "content": self.analysis_system_prompt},
            {"role": "user", "content": self.format_analysis_prompt(sales_data)}
        ]
        
        # Вызываем LLM с моделью пользователя
        analysis_text = await llm_client.chat_completion(
            model=user_model,
            messages=messages,
            temperature=0.3,  # Более детерминированный для аналитики
            max_tokens=3000
        )
        
        return {
            "success": True,
            "analysis": analysis_text,
            "model_used": user_model,
            "period": period
        }
```

---

## 📝 Этап 6: Обновление .env файлов

### 6.1 Обновить .env

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Модель по умолчанию
DEFAULT_AI_MODEL=gpt-4o

# DEPRECATED - больше не используется
# COMET_TEXT_MODEL=gpt-4.1
```

### 6.2 Обновить env_example.txt

```env
# AI Models Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEFAULT_AI_MODEL=gpt-4o
```

---

## 📝 Этап 7: Тестирование

### 7.1 Unit тесты

Файл: `server/tests/unit/test_ai_model_selection.py`

```python
import pytest
from app.core.ai_models import AIModel

def test_ai_model_enum():
    """Тест enum моделей"""
    assert AIModel.GPT_4O == "gpt-4o"
    assert AIModel.CLAUDE_SONNET_35 == "claude-sonnet-3.5"
    assert AIModel.get_default() == "gpt-4o"

def test_ai_model_display_names():
    """Тест отображаемых названий"""
    assert "GPT-4o" in AIModel.get_display_name(AIModel.GPT_4O)
    assert "Claude" in AIModel.get_display_name(AIModel.CLAUDE_SONNET_35)

@pytest.mark.asyncio
async def test_update_user_model(client, test_user):
    """Тест обновления модели пользователя"""
    response = await client.patch(
        f"/api/v1/bot/settings?telegram_id={test_user.telegram_id}",
        json={"preferred_ai_model": "claude-sonnet-3.5"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_ai_model"] == "claude-sonnet-3.5"

@pytest.mark.asyncio
async def test_invalid_model(client, test_user):
    """Тест невалидной модели"""
    response = await client.patch(
        f"/api/v1/bot/settings?telegram_id={test_user.telegram_id}",
        json={"preferred_ai_model": "invalid-model"}
    )
    
    assert response.status_code == 400
```

### 7.2 Integration тесты

Файл: `tests/integration/test_ai_chat_with_models.py`

```python
import pytest

@pytest.mark.asyncio
async def test_ai_chat_with_gpt(bot_client, test_user):
    """Тест AI чата с GPT-4o"""
    # Устанавливаем модель
    await bot_client.update_user_settings(
        test_user.telegram_id,
        preferred_ai_model="gpt-4o"
    )
    
    # Отправляем сообщение
    response = await bot_client.send_ai_message(
        test_user.telegram_id,
        "Привет!"
    )
    
    assert response["success"] is True
    assert response["model_used"] == "gpt-4o"
    assert len(response["response"]) > 0

@pytest.mark.asyncio
async def test_ai_chat_with_claude(bot_client, test_user):
    """Тест AI чата с Claude"""
    # Устанавливаем модель
    await bot_client.update_user_settings(
        test_user.telegram_id,
        preferred_ai_model="claude-sonnet-3.5"
    )
    
    # Отправляем сообщение
    response = await bot_client.send_ai_message(
        test_user.telegram_id,
        "Привет!"
    )
    
    assert response["success"] is True
    assert response["model_used"] == "claude-sonnet-3.5"
    assert len(response["response"]) > 0
```

### 7.3 Ручное тестирование

1. **Проверка миграции:**
```bash
cd server
alembic upgrade head
psql -U user -d wb_assist_db -c "SELECT telegram_id, preferred_ai_model FROM users LIMIT 5;"
```

2. **Проверка API:**
```bash
# Получить список моделей
curl http://localhost:8002/api/v1/bot/ai-models

# Получить настройки пользователя
curl "http://localhost:8002/api/v1/bot/settings?telegram_id=123456789"

# Обновить модель
curl -X PATCH "http://localhost:8002/api/v1/bot/settings?telegram_id=123456789" \
  -H "Content-Type: application/json" \
  -d '{"preferred_ai_model": "claude-sonnet-3.5"}'
```

3. **Проверка в боте:**
- Отправить `/settings`
- Выбрать "🤖 Выбор AI модели"
- Переключить модель
- Проверить работу AI-ассистента

---

## 📝 Этап 8: Документация для пользователей

### 8.1 Добавить в help бота

```python
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🤖 <b>Выбор AI модели</b>

Вы можете выбрать предпочитаемую AI модель для:
• AI-ассистента
• Аналитики продаж
• Генерации контента

Доступные модели:
• <b>GPT-4o</b> - быстрая и точная модель от OpenAI
• <b>Claude Sonnet 3.5</b> - продвинутая модель от Anthropic

Для выбора модели используйте /settings → Выбор AI модели
    """
    await message.answer(help_text)
```

---

## 📊 Мониторинг и метрики

### 9.1 Добавить логирование

```python
import logging

logger = logging.getLogger(__name__)

async def send_message(self, telegram_id: int, message: str):
    user_model = await self.get_user_model(telegram_id)
    
    logger.info(
        f"AI Chat request: user={telegram_id}, model={user_model}, "
        f"message_length={len(message)}"
    )
    
    # ... остальной код ...
```

### 9.2 Метрики использования моделей

```sql
-- Статистика использования моделей
SELECT 
    preferred_ai_model,
    COUNT(*) as users_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM users
GROUP BY preferred_ai_model
ORDER BY users_count DESC;
```

---

## ✅ Чеклист реализации

- [ ] Создать миграцию БД
- [ ] Обновить модель User
- [ ] Создать enum AIModel
- [ ] Добавить API endpoints
- [ ] Обновить клавиатуры бота
- [ ] Создать handler настроек
- [ ] Обновить API клиент бота
- [ ] Создать UniversalLLMClient
- [ ] Обновить AI Chat сервис
- [ ] Обновить Analysis сервис
- [ ] Обновить .env файлы
- [ ] Написать тесты
- [ ] Обновить документацию
- [ ] Провести ручное тестирование
- [ ] Задеплоить на production

---

## 🎯 Результат

После реализации:
1. Каждый пользователь может выбрать свою AI модель
2. Выбор сохраняется в БД
3. Модель используется для всех AI функций
4. По умолчанию используется GPT-4o
5. Легко добавить новые модели в будущем

**Статус:** 📝 Готово к реализации
