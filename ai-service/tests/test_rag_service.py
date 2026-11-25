import asyncio
from unittest.mock import AsyncMock, patch

from app.services.rag_service import answer_question


def run(coro):
    return asyncio.run(coro)


def test_answer_question():
    results = [
        {"document_id": "d1", "page_number": 1, "text": "Python is a programming language."},
        {"document_id": "d1", "page_number": 2, "text": "Python is easy to learn."},
    ]

    with patch(
        "app.services.rag_service.search_document",
        new=AsyncMock(return_value=results),
    ) as mock_search, patch(
        "app.services.rag_service.generate_answer",
        return_value="Python is a programming language.",
    ) as mock_generate:
        result = run(answer_question("d1", "What is Python?", k=2))

    assert result["answer"] == "Python is a programming language."
    assert result["sources"] == [
        {"document_id": "d1", "page_number": 1},
        {"document_id": "d1", "page_number": 2},
    ]
    mock_search.assert_awaited_once_with("d1", "What is Python?", k=2)
    mock_generate.assert_called_once_with(
        "What is Python?",
        "Python is a programming language.\n\nPython is easy to learn.",
    )


def test_answer_question_no_results():
    with patch(
        "app.services.rag_service.search_document",
        new=AsyncMock(return_value=[]),
    ), patch("app.services.rag_service.generate_answer") as mock_generate:
        result = run(answer_question("d1", "What is Python?"))

    assert result == {
        "answer": "I don't know based on the provided document.",
        "sources": [],
    }
    mock_generate.assert_not_called()
