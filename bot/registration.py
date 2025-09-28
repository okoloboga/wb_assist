import aiohttp
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from keyboards import main_keyboard, wb_menu_keyboard

router = Router()

SERVER_URL = "http://127.0.0.1:8000/user/register"  # сюда сервер принимает регистрацию


@router.message(Command(commands=["start"]))
async def register_user(message: Message):
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    last_name = message.from_user.last_name or ""

    payload = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(SERVER_URL, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Сервер возвращает, зарегистрирован ли пользователь
                    if result.get("registered", False):
                        await message.answer(
                            f"Здравствуйте, {first_name}! 👋\nДобро пожаловать обратно!",
                            reply_markup=wb_menu_keyboard()
                        )
                    else:
                        await message.answer(
                            f"Здравствуйте, {first_name}! 👋\nРегистрация завершена!",
                            reply_markup=main_keyboard()
                        )
                else:
                    await message.answer("Ошибка сервера при регистрации.")
        except Exception as e:
            await message.answer(f"Ошибка соединения с сервером: {e}")
