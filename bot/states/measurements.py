"""
FSM состояния для ввода параметров пользователя
"""
from aiogram.fsm.state import State, StatesGroup


class MeasurementStates(StatesGroup):
    """Состояния для ввода/редактирования параметров тела (каждый отдельно)"""
    editing_russian_size = State()
    editing_shoulder_length = State()
    editing_back_width = State()
    editing_sleeve_length = State()
    editing_back_length = State()
    editing_chest = State()
    editing_waist = State()
    editing_hips = State()
    editing_pants_length = State()
    editing_waist_girth = State()
    editing_rise_height = State()
    editing_back_rise_height = State()