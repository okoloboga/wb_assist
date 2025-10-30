import sys
from pathlib import Path
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

# Добавляем путь к модулям бота
sys.path.insert(0, str(Path(__file__).parent.parent))

from keyboards.keyboards import wb_menu_keyboard
from api.client import register_user_on_server, bot_api_client
from core.states import WBCabinetStates
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command(commands=["start"]))
async def register_user(message: Message, state: FSMContext):
    """
    Обрабатывает команду /start, собирает данные пользователя,
    регистрирует на сервере и проверяет наличие WB API ключа.
    """
    first_name = message.from_user.first_name or ""
    user_id = message.from_user.id
    
    # Регистрируем пользователя на сервере
    payload = {
        "telegram_id": user_id,
        "username": message.from_user.username or None,
        "first_name": first_name,
        "last_name": message.from_user.last_name or None
    }

    status, _ = await register_user_on_server(payload)

    if status not in [200, 201]:
        if status == 503:
            await message.answer("Не удалось связаться с сервером. Пожалуйста, попробуйте позже.")
        else:
            await message.answer("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        return

    # Проверяем наличие WB API ключа
    has_api_key = await _check_user_api_key(user_id)
    
    if has_api_key:
        # Пользователь уже подключен - показываем дашборд
        dashboard_response = await bot_api_client.get_dashboard(
            user_id=user_id
        )
        
        if dashboard_response.success:
            await message.answer(
                dashboard_response.telegram_text or "📊 Дашборд загружен",
                reply_markup=wb_menu_keyboard()
            )
        else:
            # Если дашборд не загрузился, показываем обычное меню
            await message.answer(
                "✅ Кабинет подключен\n\nВыберите действие:",
                reply_markup=wb_menu_keyboard()
            )
    else:
        # Требуем подключение API ключа
        await _require_api_key(message, first_name, state)


async def _check_user_api_key(user_id: int) -> bool:
    """Проверяет наличие API ключа у пользователя"""
    try:
        response = await bot_api_client.get_cabinet_status(user_id)
        
        if not response.success:
            return False
        
        # Проверяем, есть ли подключенные кабинеты
        cabinets = response.data.get('cabinets', []) if response.data else []
        return len(cabinets) > 0
        
    except Exception as e:
        return False


async def _require_api_key(message: Message, first_name: str, state: FSMContext):
    """Требует ввод API ключа от пользователя"""
    await state.set_state(WBCabinetStates.waiting_for_api_key)
    
    welcome_text = (
        f"Здравствуйте, {first_name}! 👋\n\n"
        "🔑 **ТРЕБУЕТСЯ ПОДКЛЮЧЕНИЕ WB КАБИНЕТА**\n\n"
        "Для использования бота необходимо подключить ваш WB кабинет.\n"
        "Пожалуйста, введите ваш API ключ от Wildberries:\n\n"
        "💡 **Как получить API ключ:**\n"
        "1. Зайдите в личный кабинет WB\n"
        "2. Перейдите в раздел 'Настройки' → 'Доступ к API'\n"
        "3. Создайте новый токен доступа\n"
        "4. Скопируйте и отправьте его боту\n\n"
        "⚠️ **Важно:** API ключ должен быть действительным и иметь права на чтение данных."
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown"
    )

