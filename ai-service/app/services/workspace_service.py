"""Workspaces group documents (e.g. HR, IT, Policies).

Each document belongs to exactly one workspace. Workspaces are stored in
``<storage_dir>/workspaces.json``; a document's workspace is stored in its
``metadata.json`` (documents without one belong to the default workspace).
"""

import json
import re
from pathlib import Path

from app.core.config import get_settings
from app.services.document_metadata_service import list_document_metadata

DEFAULT_WORKSPACE_ID = "general"
DEFAULT_WORKSPACE = {
    "workspace_id": DEFAULT_WORKSPACE_ID,
    "name": "General",
    "description": "Default workspace",
}


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceExistsError(Exception):
    pass


def _storage() -> Path:
    return Path(get_settings().storage_dir)


def _workspaces_file() -> Path:
    return _storage() / "workspaces.json"


def _vector_stores_path() -> Path:
    return _storage() / "vector_stores"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "workspace"


def _load() -> dict[str, dict]:
    path = _workspaces_file()
    workspaces: dict[str, dict] = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            for item in json.load(file):
                workspaces[item["workspace_id"]] = item

    workspaces.setdefault(DEFAULT_WORKSPACE_ID, dict(DEFAULT_WORKSPACE))
    return workspaces


def _save(workspaces: dict[str, dict]) -> None:
    path = _workspaces_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(list(workspaces.values()), file, indent=2)


def document_workspace(metadata: dict) -> str:
    return metadata.get("workspace_id") or DEFAULT_WORKSPACE_ID


def list_all_documents() -> list[dict]:
    return list_document_metadata(_vector_stores_path())


def list_workspace_documents(workspace_id: str) -> list[dict]:
    return [
        document
        for document in list_document_metadata(_vector_stores_path())
        if document_workspace(document) == workspace_id
    ]


def get_workspace(workspace_id: str) -> dict:
    workspaces = _load()
    if workspace_id not in workspaces:
        raise WorkspaceNotFoundError(workspace_id)
    return workspaces[workspace_id]


def ensure_workspace_exists(workspace_id: str) -> None:
    get_workspace(workspace_id)


def list_workspaces() -> list[dict]:
    documents = list_document_metadata(_vector_stores_path())
    counts: dict[str, int] = {}
    for document in documents:
        key = document_workspace(document)
        counts[key] = counts.get(key, 0) + 1

    return [
        {**workspace, "document_count": counts.get(workspace["workspace_id"], 0)}
        for workspace in _load().values()
    ]


def create_workspace(name: str, description: str = "") -> dict:
    workspaces = _load()
    workspace_id = slugify(name)

    if workspace_id in workspaces:
        raise WorkspaceExistsError(workspace_id)

    workspace = {
        "workspace_id": workspace_id,
        "name": name.strip(),
        "description": description.strip(),
    }
    workspaces[workspace_id] = workspace
    _save(workspaces)
    return {**workspace, "document_count": 0}


def delete_workspace(workspace_id: str) -> None:
    """Delete an empty workspace. The default workspace cannot be deleted."""
    if workspace_id == DEFAULT_WORKSPACE_ID:
        raise ValueError("The default workspace cannot be deleted.")

    workspaces = _load()
    if workspace_id not in workspaces:
        raise WorkspaceNotFoundError(workspace_id)

    if list_workspace_documents(workspace_id):
        raise ValueError("Workspace still contains documents.")

    del workspaces[workspace_id]
    _save(workspaces)
