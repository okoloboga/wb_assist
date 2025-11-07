"""
FSM States для bot_young
"""
from aiogram.fsm.state import State, StatesGroup


class AddChannelStates(StatesGroup):
    """Состояния для добавления канала"""
    waiting_for_channel = State()  # Ожидание ссылки/username канала
    entering_hours = State()  # Ввод часов (0-23)
    entering_minutes = State()  # Ввод минут (0-59)

