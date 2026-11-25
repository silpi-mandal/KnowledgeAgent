from unittest.mock import patch

from app.services.llm_service import create_llm, generate_answer


def test_create_llm_uses_configured_settings():
    with patch("app.services.llm_service.OpenAI") as mock_sync, patch(
        "app.services.llm_service.AsyncOpenAI"
    ) as mock_async:
        llm = create_llm()

        assert llm.model == "test-model"
        assert mock_sync.call_args.kwargs["api_key"] == "test-key"
        assert "base_url" in mock_sync.call_args.kwargs
        assert "base_url" in mock_async.call_args.kwargs


def test_generate_answer():
    mock_response = type(
        "MockResponse",
        (),
        {"content": "Python is a programming language."},
    )()

    with patch("app.services.llm_service.create_llm") as mock_create_llm:
        mock_llm = mock_create_llm.return_value
        mock_llm.invoke.return_value = mock_response

        result = generate_answer(
            "What is Python?",
            "Python is a programming language.",
        )

        assert result == "Python is a programming language."
        mock_llm.invoke.assert_called_once()