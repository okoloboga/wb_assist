from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from keyboards.keyboards import main_keyboard, wb_menu_keyboard
from api.client import register_user_on_server

router = Router()


@router.message(Command(commands=["start"]))
async def register_user(message: Message):
    """
    Обрабатывает команду /start, собирает данные пользователя и
    вызывает API-клиент для регистрации на сервере.
    """
    first_name = message.from_user.first_name or ""
    payload = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username or "",
        "first_name": first_name,
        "last_name": message.from_user.last_name or ""
    }

    status, _ = await register_user_on_server(payload)

    # 201 - создан новый, 200 - пользователь уже был
    if status == 201:
        await message.answer(
            f"Здравствуйте, {first_name}! 👋\nРегистрация завершена!",
            reply_markup=main_keyboard()
        )
    elif status == 200:
        await message.answer(
            f"Здравствуйте, {first_name}! 👋\nДобро пожаловать обратно!",
            reply_markup=wb_menu_keyboard()
        )
    elif status == 503:
        await message.answer("Не удалось связаться с сервером. Пожалуйста, попробуйте позже.")
    else:
        await message.answer("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

