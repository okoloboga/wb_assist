import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from handlers import gpt as gpt_handlers


@pytest.mark.asyncio
async def test_handle_user_prompt_escapes_markdown_and_splits(mock_message, mock_fsm_context):
    mock_message.text = "Привет"
    mock_fsm_context.get_data = AsyncMock(return_value={"gpt_history": []})
    mock_fsm_context.update_data = AsyncMock()

    long_answer = "Тест *звезды* и (скобки) _подчеркивание_ " + ("x" * 4100)
    dummy_client = SimpleNamespace(
        config=SimpleNamespace(system_prompt=""),
        complete_messages=lambda msgs: long_answer,
    )

    with patch.object(gpt_handlers, "_gpt_client", dummy_client):
        await gpt_handlers.handle_user_prompt(mock_message, mock_fsm_context)

    # Из-за разбиения длинного текста должно быть >= 2 сообщений
    assert mock_message.answer.call_count >= 2

    # Проверяем, что спецсимволы экранированы в отправленных частях
    sent_texts = [call.kwargs.get("text") for call in mock_message.answer.call_args_list]
    combined = "".join(sent_texts)
    assert "\\*" in combined and "\\(" in combined and "\\)" in combined and "\\_" in combined


@pytest.mark.asyncio
async def test_handle_user_prompt_client_not_initialized(mock_message, mock_fsm_context):
    mock_message.text = "Вопрос"
    mock_fsm_context.get_data = AsyncMock(return_value={"gpt_history": []})
    mock_fsm_context.update_data = AsyncMock()

    with patch.object(gpt_handlers, "_gpt_client", None):
        await gpt_handlers.handle_user_prompt(mock_message, mock_fsm_context)

    assert mock_message.answer.call_count == 1
    sent_text = mock_message.answer.call_args.kwargs.get("text")
    assert "GPT клиент не инициализирован" in sent_text