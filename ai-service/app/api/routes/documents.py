import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import CurrentUser, get_current_user, require_admin
from app.core.config import get_settings
from app.services.document_metadata_service import (
    list_document_metadata,
)
from app.models.document import DocumentResponse
from app.services.document_file_type_service import (
    UnsupportedFileTypeError,
    resolve_supported_extension,
)
from app.services.document_ingestion_service import (
    DocumentProcessingError,
    ingest_document,
)
from app.services.document_storage_service import save_document
from app.services.workspace_service import (
    DEFAULT_WORKSPACE_ID,
    WorkspaceNotFoundError,
    document_workspace,
    ensure_workspace_exists,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


def remove_failed_upload(
    document_id: str,
    file_path: Path,
) -> None:

    settings = get_settings()

    vector_store_path = (
        Path(settings.storage_dir)
        / "vector_stores"
        / document_id
    )

    file_path.unlink(missing_ok=True)

    if vector_store_path.exists():
        shutil.rmtree(
            vector_store_path,
            ignore_errors=True,
        )


@router.post(
    "/upload",
    response_model=DocumentResponse,
)
def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(DEFAULT_WORKSPACE_ID),
    _: CurrentUser = Depends(require_admin),
) -> DocumentResponse:

    try:
        ensure_workspace_exists(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found.",
        ) from None

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    try:
        extension = resolve_supported_extension(
            file.filename,
            file.content_type,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from None

    document_id, file_path = save_document(file, extension)

    try:
        ingest_document(
            document_id,
            file_path,
            file.filename,
            workspace_id=workspace_id,
        )
    except DocumentProcessingError as exc:
        logger.warning(
            "Document rejected (document_id=%s): %s",
            document_id,
            exc,
        )
        remove_failed_upload(document_id, file_path)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from None
    except Exception:
        logger.exception(
            "Document ingestion failed (document_id=%s)",
            document_id,
        )
        remove_failed_upload(document_id, file_path)

        raise HTTPException(
            status_code=500,
            detail="Document processing failed. Please try again later.",
        ) from None

    return DocumentResponse(
        document_id=document_id,
        document_name=file.filename,
        workspace_id=workspace_id,
    )

@router.get(
    "",
    response_model=list[DocumentResponse],
)
def get_documents(
    workspace_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> list[DocumentResponse]:

    settings = get_settings()

    vector_stores_path = (
        Path(settings.storage_dir)
        / "vector_stores"
    )

    documents = list_document_metadata(
        vector_stores_path,
    )

    return [
        DocumentResponse(
            **{**document, "workspace_id": document_workspace(document)}
        )
        for document in documents
        if (
            workspace_id is None
            or document_workspace(document) == workspace_id
        )
        and user.can_access_workspace(document_workspace(document))
    ]
