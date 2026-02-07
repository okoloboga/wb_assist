"""
Обработчики раздела параметров пользователя
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.measurements import MeasurementStates
from keyboards.measurements import (
    get_cancel_keyboard,
    get_measurements_menu_keyboard,
    get_edit_measurements_keyboard
)
from keyboards.fitter_keyboards import get_fitter_main_menu
from api.client import bot_api_client as api_client

router = Router()


# Конфигурация параметров: название, диапазон валидации, сообщения
PARAM_CONFIG = {
    'russian_size': {
        'name': 'российский размер',
        'prompt': 'Укажи свой российский размер (например: 42-44)',
        'type': 'string',
        'example': '42-44',
        'validation': None,
        'state': MeasurementStates.editing_russian_size
    },
    'shoulder_length': {
        'name': 'длину плеч',
        'prompt': 'Укажи длину плеч в сантиметрах (например: 40)',
        'type': 'int',
        'example': '40',
        'validation': None,
        'state': MeasurementStates.editing_shoulder_length
    },
    'back_width': {
        'name': 'ширину спины',
        'prompt': 'Укажи ширину спины в сантиметрах (например: 38)',
        'type': 'int',
        'example': '38',
        'validation': None,
        'state': MeasurementStates.editing_back_width
    },
    'sleeve_length': {
        'name': 'длину рукава',
        'prompt': 'Укажи длину рукава в сантиметрах (например: 60)',
        'type': 'int',
        'example': '60',
        'validation': None,
        'state': MeasurementStates.editing_sleeve_length
    },
    'back_length': {
        'name': 'длину изделия по спинке',
        'prompt': 'Укажи длину изделия по спинке в сантиметрах (например: 70)',
        'type': 'int',
        'example': '70',
        'validation': None,
        'state': MeasurementStates.editing_back_length
    },
    'chest': {
        'name': 'обхват груди',
        'prompt': 'Укажи обхват груди в сантиметрах (например: 90)',
        'type': 'int',
        'example': '90',
        'validation': None,
        'state': MeasurementStates.editing_chest
    },
    'waist': {
        'name': 'обхват талии',
        'prompt': 'Укажи обхват талии в сантиметрах (например: 70)',
        'type': 'int',
        'example': '70',
        'validation': None,
        'state': MeasurementStates.editing_waist
    },
    'hips': {
        'name': 'обхват бедер',
        'prompt': 'Укажи обхват бедер в сантиметрах (например: 95)',
        'type': 'int',
        'example': '95',
        'validation': None,
        'state': MeasurementStates.editing_hips
    },
    'pants_length': {
        'name': 'длину брюк',
        'prompt': 'Укажи длину брюк в сантиметрах (например: 100)',
        'type': 'int',
        'example': '100',
        'validation': None,
        'state': MeasurementStates.editing_pants_length
    },
    'waist_girth': {
        'name': 'обхват в поясе',
        'prompt': 'Укажи обхват в поясе в сантиметрах (например: 75)',
        'type': 'int',
        'example': '75',
        'validation': None,
        'state': MeasurementStates.editing_waist_girth
    },
    'rise_height': {
        'name': 'высоту посадки',
        'prompt': 'Укажи высоту посадки в сантиметрах (например: 25)',
        'type': 'int',
        'example': '25',
        'validation': None,
        'state': MeasurementStates.editing_rise_height
    },
    'back_rise_height': {
        'name': 'высоту посадки сзади',
        'prompt': 'Укажи высоту посадки сзади в сантиметрах (например: 35)',
        'type': 'int',
        'example': '35',
        'validation': None,
        'state': MeasurementStates.editing_back_rise_height
    }
}


def format_measurements_text(measurements: dict) -> str:
    """Форматировать текст с параметрами (только заполненные)"""
    lines = ["✨ Твои параметры:\n"]

    param_labels = {
        'russian_size': '📏 Российский размер',
        'shoulder_length': '👔 Длина плеч',
        'back_width': '👔 Ширина спины',
        'sleeve_length': '👕 Длина рукава',
        'back_length': '👕 Длина по спинке',
        'chest': '👚 Обхват груди',
        'waist': '👖 Обхват талии',
        'hips': '🍑 Обхват бедер',
        'pants_length': '👖 Длина брюк',
        'waist_girth': '⚡ Обхват в поясе',
        'rise_height': '📐 Высота посадки',
        'back_rise_height': '📐 Высота посадки сзади'
    }

    filled_count = 0
    for key, label in param_labels.items():
        value = measurements.get(key)
        if value is not None and value != '':
            filled_count += 1
            if isinstance(value, int):
                lines.append(f"• {label}: {value} см")
            else:
                lines.append(f"• {label}: {value}")

    if filled_count == 0:
        return "📐 Параметры не заполнены\n\nНажми кнопку ниже, чтобы добавить свои параметры. Можешь заполнить только те, которые знаешь!"

    lines.append("\nТеперь мы будем показывать рекомендуемый размер для каждого товара!")
    return "\n".join(lines)


@router.callback_query(F.data.in_(["measurements", "measurements_menu"]))
async def show_measurements(callback: CallbackQuery):
    """Показать раздел параметров"""
    user_id = callback.from_user.id
    # measurements = await api_client.get_measurements(user_id)
    measurements = {}  # Заглушка

    if not measurements:
        measurements = {}

    await callback.message.edit_text(
        format_measurements_text(measurements),
        reply_markup=get_measurements_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "measurements:edit_menu")
async def show_edit_menu(callback: CallbackQuery):
    """Показать меню редактирования параметров"""
    user_id = callback.from_user.id
    # measurements = await api_client.get_measurements(user_id)
    measurements = {}  # Заглушка

    await callback.message.edit_text(
        "Выбери параметр для изменения:\n\n💡 Можешь заполнить только те параметры, которые знаешь!",
        reply_markup=get_edit_measurements_keyboard(measurements)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("measurements:edit:"))
async def start_edit_parameter(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование конкретного параметра"""
    param = callback.data.split(":")[2]

    if param in PARAM_CONFIG:
        config = PARAM_CONFIG[param]
        await state.set_state(config['state'])
        await callback.message.edit_text(
            config['prompt'],
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "measurements:cancel")
async def cancel_measurements_input(callback: CallbackQuery, state: FSMContext):
    """Отменить ввод параметров"""
    await state.clear()
    user_id = callback.from_user.id
    # measurements = await api_client.get_measurements(user_id)
    measurements = {}  # Заглушка

    if not measurements:
        measurements = {}

    await callback.message.edit_text(
        format_measurements_text(measurements),
        reply_markup=get_measurements_menu_keyboard()
    )
    await callback.answer()


async def _update_single_measurement(message: Message, state: FSMContext, param_name: str, value):
    """Вспомогательная функция для обновления одного параметра через API"""
    user_id = message.from_user.id

    # Сохраняем только этот параметр через API
    # await api_client.save_measurements(user_id, **{param_name: value})

    await state.clear()
    # measurements = await api_client.get_measurements(user_id)
    measurements = {}  # Заглушка
    if not measurements:
        measurements = {}

    await message.answer(
        f"✅ Параметр обновлен!\n\n{format_measurements_text(measurements)}",
        reply_markup=get_measurements_menu_keyboard()
    )


# Генерируем хендлеры для всех параметров
@router.message(MeasurementStates.editing_russian_size)
async def edit_russian_size(message: Message, state: FSMContext):
    """Редактирование российского размера"""
    value = message.text.strip()
    if not value or len(value) > 20:
        await message.answer(
            "Пожалуйста, введи корректный размер (например: 42-44)",
            reply_markup=get_cancel_keyboard()
        )
        return
    await _update_single_measurement(message, state, "russian_size", value)


@router.message(MeasurementStates.editing_shoulder_length)
async def edit_shoulder_length(message: Message, state: FSMContext):
    """Редактирование длины плеч"""
    config = PARAM_CONFIG['shoulder_length']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "shoulder_length", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_back_width)
async def edit_back_width(message: Message, state: FSMContext):
    """Редактирование ширины спины"""
    config = PARAM_CONFIG['back_width']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "back_width", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_sleeve_length)
async def edit_sleeve_length(message: Message, state: FSMContext):
    """Редактирование длины рукава"""
    config = PARAM_CONFIG['sleeve_length']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "sleeve_length", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_back_length)
async def edit_back_length(message: Message, state: FSMContext):
    """Редактирование длины изделия по спинке"""
    config = PARAM_CONFIG['back_length']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "back_length", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_chest)
async def edit_chest(message: Message, state: FSMContext):
    """Редактирование обхвата груди"""
    config = PARAM_CONFIG['chest']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "chest", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_waist)
async def edit_waist(message: Message, state: FSMContext):
    """Редактирование обхвата талии"""
    config = PARAM_CONFIG['waist']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "waist", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_hips)
async def edit_hips(message: Message, state: FSMContext):
    """Редактирование обхвата бедер"""
    config = PARAM_CONFIG['hips']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "hips", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_pants_length)
async def edit_pants_length(message: Message, state: FSMContext):
    """Редактирование длины брюк"""
    config = PARAM_CONFIG['pants_length']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "pants_length", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_waist_girth)
async def edit_waist_girth(message: Message, state: FSMContext):
    """Редактирование обхвата в поясе"""
    config = PARAM_CONFIG['waist_girth']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "waist_girth", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_rise_height)
async def edit_rise_height(message: Message, state: FSMContext):
    """Редактирование высоты посадки"""
    config = PARAM_CONFIG['rise_height']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "rise_height", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )


@router.message(MeasurementStates.editing_back_rise_height)
async def edit_back_rise_height(message: Message, state: FSMContext):
    """Редактирование высоты посадки сзади"""
    config = PARAM_CONFIG['back_rise_height']
    try:
        value = int(message.text)
        if value <= 0:
            await message.answer(
                "Пожалуйста, введи корректное положительное число.",
                reply_markup=get_cancel_keyboard()
            )
            return
        await _update_single_measurement(message, state, "back_rise_height", value)
    except ValueError:
        await message.answer(
            f"Пожалуйста, введи число (например: {config['example']})",
            reply_markup=get_cancel_keyboard()
        )