"""
Semantic Core Handler - просмотр и генерация семантических ядер.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.client import bot_api_client
from utils.formatters import handle_telegram_errors
from keyboards.keyboards import ai_assistant_keyboard

logger = logging.getLogger(__name__)

router = Router()

# --- Клавиатуры ---

def semantic_core_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для главного меню семантического ядра."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Посмотреть сгенерированные", callback_data="view_semantic_cores")],
        [InlineKeyboardButton(text="➕ Сгенерировать новое", callback_data="generate_semantic_core_start")],
        [InlineKeyboardButton(text="🔙 Назад в AI-помощник", callback_data="ai_assistant")]
    ])

def create_view_cores_keyboard(cores: list, page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Создает клавиатуру для списка семантических ядер с пагинацией."""
    builder = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size
    
    for core in cores[start:end]:
        builder.button(text=f"💎 {core['category_name']}", callback_data=f"view_core_detail_{core['id']}")
    
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_semantic_cores_page_{page-1}"))
    if end < len(cores):
        pagination_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"view_semantic_cores_page_{page+1}"))
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="semantic_core_menu"))
    return builder.as_markup()

def create_category_selection_keyboard(categories: list, page: int = 0, page_size: int = 10) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора категории для генерации ядра."""
    builder = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size
    
    for category in categories[start:end]:
        builder.button(text=category, callback_data=f"gen_core_category_{category}")

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"gen_core_cat_page_{page-1}"))
    if end < len(categories):
        pagination_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"gen_core_cat_page_{page+1}"))

    if pagination_buttons:
        builder.row(*pagination_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="semantic_core_menu"))
    builder.adjust(1)
    return builder.as_markup()

# --- Обработчики ---

@router.callback_query(F.data == "semantic_core_menu")
@handle_telegram_errors
async def semantic_core_menu(callback: CallbackQuery, state: FSMContext):
    """Отображает главное меню для работы с семантическими ядрами."""
    await state.clear()
    text = (
        "💎 <b>Семантическое ядро</b>\n\n"
        "Здесь вы можете посмотреть сгенерированные ядра или запустить создание нового "
        "на основе анализа всех ваших конкурентов."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=semantic_core_main_menu_keyboard()
    )
    await callback.answer()

# --- Просмотр существующих ядер ---

@router.callback_query(F.data == "view_semantic_cores")
@router.callback_query(F.data.startswith("view_semantic_cores_page_"))
@handle_telegram_errors
async def view_semantic_cores(callback: CallbackQuery, state: FSMContext):
    """Отображает список сгенерированных семантических ядер."""
    telegram_id = callback.from_user.id
    page = int(callback.data.split("_")[-1]) if callback.data.startswith("view_semantic_cores_page_") else 0

    await callback.message.edit_text("⏳ Загружаю список семантических ядер...")

    response = await bot_api_client.get_semantic_cores(user_id=telegram_id)
    
    if not response.success or not response.data:
        await callback.message.edit_text(
            "❌ У вас еще нет сгенерированных семантических ядер.",
            reply_markup=semantic_core_main_menu_keyboard()
        )
        return
        
    cores = response.data
    keyboard = create_view_cores_keyboard(cores, page=page)
    
    await callback.message.edit_text(
        "💎 <b>Ваши семантические ядра:</b>\n\n"
        "Выберите ядро для просмотра деталей.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("view_core_detail_"))
@handle_telegram_errors
async def view_semantic_core_detail(callback: CallbackQuery, state: FSMContext):
    """Отображает детали семантического ядра."""
    telegram_id = callback.from_user.id
    core_id = int(callback.data.split("_")[-1])

    await callback.message.edit_text("⏳ Загружаю детали ядра...")

    response = await bot_api_client.get_semantic_core_detail(core_id=core_id, user_id=telegram_id)
    
    if not response.success or not response.data:
        await callback.message.edit_text(
            "❌ Не удалось загрузить детали ядра.",
            reply_markup=semantic_core_main_menu_keyboard()
        )
        return
        
    core = response.data
    core_data = core.get("core_data", "Данные отсутствуют.")
    category_name = core.get("category_name", "Без категории")

    if len(core_data) > 4000:
        core_data = core_data[:4000] + "..."

    text = f"💎 <b>Семантическое ядро для категории: {category_name}</b>\n\n```{core_data}```"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к списку ядер", callback_data="view_semantic_cores")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

# --- Генерация нового ядра ---

@router.callback_query(F.data == "generate_semantic_core_start")
@router.callback_query(F.data.startswith("gen_core_cat_page_"))
@handle_telegram_errors
async def choose_category_for_generation(callback: CallbackQuery, state: FSMContext):
    """Показывает список категорий для выбора и генерации ядра."""
    telegram_id = callback.from_user.id
    page = int(callback.data.split("_")[-1]) if callback.data.startswith("gen_core_cat_page_") else 0
    
    await callback.message.edit_text("⏳ Загружаю список категорий ваших конкурентов...")
    
    response = await bot_api_client.get_semantic_core_categories(user_id=telegram_id)
    
    categories = response.data.get("categories") if response.success and response.data else []
    
    if not categories:
        await callback.message.edit_text(
            "❌ Не найдено категорий у ваших конкурентов.\n\n"
            "Сначала добавьте конкурентов и дождитесь, пока их товары будут отсканированы.",
            reply_markup=semantic_core_main_menu_keyboard()
        )
        return
        
    await state.update_data(categories=categories)
    keyboard = create_category_selection_keyboard(categories, page=page)
    
    await callback.message.edit_text(
        "🗂️ <b>Выберите категорию</b> для сбора семантического ядра.\n\n"
        "Ядро будет сгенерировано на основе описаний товаров всех ваших конкурентов в этой категории.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("gen_core_category_"))
@handle_telegram_errors
async def start_cabinet_semantic_core_generation(callback: CallbackQuery, state: FSMContext):
    """Запускает генерацию агрегированного семантического ядра."""
    telegram_id = callback.from_user.id
    category_name = callback.data.replace("gen_core_category_", "")
    
    await callback.message.edit_text(
        f"⏳ Запускаю генерацию ядра для категории «<b>{category_name}</b>»...\n\n"
        "Это может занять несколько минут. Я пришлю уведомление, когда всё будет готово.",
        parse_mode="HTML"
    )
    await callback.answer()

    response = await bot_api_client.generate_cabinet_semantic_core(
        category_name=category_name,
        user_id=telegram_id
    )

    if response.success:
        if response.status_code == 200 and response.data.get("status") == "already_exists":
            # Ядро уже существует, показываем его
            core = response.data.get("semantic_core", {})
            core_data = core.get("core_data", "Данные отсутствуют.")
            if len(core_data) > 3800:
                core_data = core_data[:3800] + "..."
            
            text = (
                f"✅ Ядро для категории «<b>{category_name}</b>» уже было сгенерировано ранее.\n\n"
                f"Вот результат:\n\n```{core_data}```"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"regen_core_category_{category_name}")],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="semantic_core_menu")]
            ])
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Генерация запущена, просто ждем webhook
            # Сообщение об этом уже было отправлено
            pass
    else:
        await callback.message.edit_text(
            f"❌ Не удалось запустить генерацию для категории «<b>{category_name}</b>».\n\n"
            f"Ошибка: {response.error}",
            parse_mode="HTML",
            reply_markup=semantic_core_main_menu_keyboard()
        )

@router.callback_query(F.data.startswith("regen_core_category_"))
@handle_telegram_errors
async def force_regenerate_cabinet_semantic_core(callback: CallbackQuery, state: FSMContext):
    """Принудительно перезапускает генерацию ядра."""
    telegram_id = callback.from_user.id
    category_name = callback.data.replace("regen_core_category_", "")

    await callback.message.edit_text(
        f"⏳ Принудительно перезапускаю генерацию для «<b>{category_name}</b>»...",
        parse_mode="HTML"
    )
    await callback.answer()

    response = await bot_api_client.generate_cabinet_semantic_core(
        category_name=category_name,
        user_id=telegram_id,
        force=True
    )
    
    if not response.success:
        await callback.message.edit_text(
            f"❌ Не удалось перезапустить генерацию для категории «<b>{category_name}</b>».\n\n"
            f"Ошибка: {response.error}",
            parse_mode="HTML",
            reply_markup=semantic_core_main_menu_keyboard()
        )