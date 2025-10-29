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