"""Stores answers (so they can be rated) and the thumbs up/down feedback.

Layout under ``<storage_dir>``:
  answers/<answer_id>.json                 question, answer, owner, workspace
  feedback/<answer_id>.<username>.json     one rating per user per answer (re-rating overwrites)

One small file per record keeps writes atomic and lookups O(1). Both ids are
validated (UUID / username pattern) before touching the filesystem.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import get_settings

logger = logging.getLogger("documind.ai")

MAX_ANSWER_CHARS = 20000


class AnswerNotFoundError(Exception):
    pass


def _root() -> Path:
    return Path(get_settings().storage_dir)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _clean_id(answer_id: str) -> str:
    try:
        return str(UUID(answer_id))
    except (ValueError, AttributeError, TypeError):
        raise AnswerNotFoundError(answer_id) from None


def record_answer(
    username: str,
    question: str,
    answer: str,
    workspace_id: str | None,
    document_ids: list[str],
) -> str | None:
    """Save an answer so it can be rated later. Never breaks the chat if disk fails."""
    answer_id = str(uuid4())

    try:
        _write_json(
            _root() / "answers" / f"{answer_id}.json",
            {
                "answer_id": answer_id,
                "username": username,
                "workspace_id": workspace_id,
                "document_ids": document_ids,
                "question": question[:MAX_ANSWER_CHARS],
                "answer": answer[:MAX_ANSWER_CHARS],
                "created_at": _now(),
            },
        )
    except OSError:
        logger.exception("Could not store answer for feedback")
        return None

    return answer_id


def get_answer(answer_id: str) -> dict:
    path = _root() / "answers" / f"{_clean_id(answer_id)}.json"

    if not path.exists():
        raise AnswerNotFoundError(answer_id)

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def submit_feedback(
    answer_id: str,
    username: str,
    rating: str,
    comment: str = "",
) -> dict:
    """Rate an answer. Only the person who received it may rate it."""
    answer = get_answer(answer_id)

    if answer["username"] != username:
        raise AnswerNotFoundError(answer_id)

    path = _root() / "feedback" / f"{answer['answer_id']}.{username}.json"
    now = _now()
    created_at = now

    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            created_at = json.load(file).get("created_at", now)

    record = {
        "answer_id": answer["answer_id"],
        "username": username,
        "rating": rating,
        "comment": comment.strip(),
        "created_at": created_at,
        "updated_at": now,
    }
    _write_json(path, record)
    return record


def list_feedback(rating: str | None = None, limit: int = 50) -> list[dict]:
    """Admin view, newest first, each entry joined with its question/answer."""
    directory = _root() / "feedback"
    if not directory.exists():
        return []

    entries = []
    for path in directory.glob("*.json"):
        with path.open("r", encoding="utf-8") as file:
            entry = json.load(file)

        if rating and entry["rating"] != rating:
            continue

        try:
            answer = get_answer(entry["answer_id"])
        except AnswerNotFoundError:
            answer = {}

        entries.append(
            {
                **entry,
                "workspace_id": answer.get("workspace_id"),
                "question": answer.get("question", ""),
                "answer": answer.get("answer", ""),
            }
        )

    entries.sort(key=lambda e: e["updated_at"], reverse=True)
    return entries[: max(1, min(limit, 500))]


def summarize_feedback() -> dict:
    directory = _root() / "feedback"
    up = down = 0
    by_workspace: dict[str, dict[str, int]] = {}

    if directory.exists():
        for path in directory.glob("*.json"):
            with path.open("r", encoding="utf-8") as file:
                entry = json.load(file)

            try:
                workspace = get_answer(entry["answer_id"]).get("workspace_id")
            except AnswerNotFoundError:
                workspace = None

            bucket = by_workspace.setdefault(workspace or "unknown", {"up": 0, "down": 0})
            bucket[entry["rating"]] += 1

            if entry["rating"] == "up":
                up += 1
            else:
                down += 1

    total = up + down
    return {
        "total": total,
        "up": up,
        "down": down,
        "satisfaction": round(up / total, 3) if total else None,
        "by_workspace": by_workspace,
    }
