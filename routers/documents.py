import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from config import settings
from database import get_db
from models import Document, User
from schemas import DocumentCategory, DocumentDownloadResponse, DocumentRead
from services import s3

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/heic",
    "image/heif",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def _get_or_404(db: Session, document_id: int, org_id: int) -> Document:
    row = (
        db.query(Document)
        .filter(Document.id == document_id, Document.org_id == org_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return row


@router.get("", response_model=List[DocumentRead])
def list_documents(
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Document]:
    q = db.query(Document).filter(Document.org_id == current_user.org_id)
    if related_entity_type:
        q = q.filter(Document.related_entity_type == related_entity_type)
    if related_entity_id is not None:
        q = q.filter(Document.related_entity_id == related_entity_id)
    return q.order_by(Document.created_at.desc()).all()


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    related_entity_type: str = Form(...),
    related_entity_id: int = Form(...),
    document_category: DocumentCategory = Form("lease_agreement"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Document:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Allowed: PDF, PNG, JPEG, HEIC.",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 25 MB limit.",
        )

    filename = file.filename or "file"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    key = (
        f"orgs/{current_user.org_id}/documents/"
        f"{related_entity_type}/{related_entity_id}/{uuid.uuid4()}.{ext}"
    )

    s3.upload_bytes(key, data, content_type)

    row = Document(
        org_id=current_user.org_id,
        display_name=display_name,
        s3_bucket=settings.AWS_S3_BUCKET_NAME,
        s3_key=key,
        file_size_bytes=len(data),
        mime_type=content_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        document_category=document_category,
        uploaded_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{document_id}/download", response_model=DocumentDownloadResponse)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDownloadResponse:
    row = _get_or_404(db, document_id, current_user.org_id)
    url = s3.presigned_download_url(row.s3_key, expires_in=900)
    return DocumentDownloadResponse(url=url, expires_in=900)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    return _get_or_404(db, document_id, current_user.org_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, document_id, current_user.org_id)
    try:
        s3.delete_object(row.s3_key)
    except Exception:
        pass  # tolerate missing S3 object; DB record still removed
    db.delete(row)
    db.commit()
