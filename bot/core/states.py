from aiogram.fsm.state import State, StatesGroup


class WBConnectionStates(StatesGroup):
    """Состояния для подключения WB кабинета"""
    waiting_for_api_key = State()
    validating_key = State()
    connection_success = State()
    connection_error = State()


class WBCabinetStates(StatesGroup):
    """Состояния для WB кабинета при первичной регистрации"""
    waiting_for_api_key = State()
    validating_key = State()
    connection_success = State()
    connection_error = State()


class SyncStates(StatesGroup):
    """Состояния для синхронизации"""
    waiting_for_confirmation = State()
    sync_in_progress = State()
    sync_completed = State()
    sync_error = State()


class NotificationStates(StatesGroup):
    """Состояния для уведомлений"""
    settings_menu = State()
    configuring_frequency = State()
    configuring_types = State()
    testing_notifications = State()


class AIChatStates(StatesGroup):
    """Состояния для AI чата"""
    waiting_for_message = State()


class GPTStates(StatesGroup):
    """Состояния для GPT чата"""
    gpt_chat = State()


class ExportStates(StatesGroup):
    """Состояния для экспорта в Google Sheets"""
    waiting_for_spreadsheet_url = State()


class CardGenerationStates(StatesGroup):
    """Состояния для генерации карточек товаров"""
    waiting_for_photo = State()
    waiting_for_characteristics = State()
    waiting_for_audience = State()
    waiting_for_selling_points = State()
    waiting_for_semantic_core = State()


class PhotoProcessingStates(StatesGroup):
    """Состояния для обработки фотографий"""
    waiting_for_photo = State()
    waiting_for_prompt = State()