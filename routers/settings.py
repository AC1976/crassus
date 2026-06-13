import io
import json
import zipfile
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import (
    Document, Expense, Invoice, Lessee, Organisation,
    Payment, Property, RentalAgreement, Settings, Unit, User,
)
from schemas import SettingsCreate, SettingsRead, SettingsUpdate
from services import s3 as s3_service

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/svg+xml"}
LOGO_MIME_TO_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg"}


@router.get("", response_model=SettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Settings:
    row = db.query(Settings).filter(Settings.org_id == current_user.org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured yet.")
    return row


@router.post("", response_model=SettingsRead, status_code=status.HTTP_201_CREATED)
def create_settings(
    payload: SettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> Settings:
    existing = db.query(Settings).filter(Settings.org_id == current_user.org_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settings already exist. Use PATCH to update.")
    row = Settings(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> Settings:
    row = db.query(Settings).filter(Settings.org_id == current_user.org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured yet.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/logo", response_model=SettingsRead)
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> Settings:
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo must be PNG, JPEG, or SVG.",
        )
    # Upload to S3 FIRST — if this fails, nothing touches the database
    ext = LOGO_MIME_TO_EXT[file.content_type]
    key = f"logos/{current_user.org_id}/logo.{ext}"
    data = file.file.read()
    s3_service.upload_bytes(key, data, file.content_type)

    # S3 succeeded — now create or update the settings row
    row = db.query(Settings).filter(Settings.org_id == current_user.org_id).first()
    if not row:
        from models import Organisation
        org = db.get(Organisation, current_user.org_id)
        row = Settings(
            org_id=current_user.org_id,
            company_name=org.name if org else "",
            company_address="",
            billing_email_sender=None,
        )
        db.add(row)

    row.logo_s3_key = key
    db.commit()
    db.refresh(row)
    return row


@router.delete("/logo", response_model=SettingsRead)
def delete_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> Settings:
    row = db.query(Settings).filter(Settings.org_id == current_user.org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not configured yet.")
    if row.logo_s3_key:
        try:
            s3_service.delete_object(row.logo_s3_key)
        except Exception:
            pass
        row.logo_s3_key = None
        db.commit()
        db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Data export
# ---------------------------------------------------------------------------

def _serialize(obj: object) -> object:
    """JSON-serialise dates and decimals that are not natively serialisable."""
    if isinstance(obj, (date,)):
        return obj.isoformat()
    return str(obj)


@router.get("/export")
def export_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> StreamingResponse:
    """Stream a ZIP archive containing all org data as JSON + all S3 documents."""
    org_id = current_user.org_id

    # ── Collect SQL data ────────────────────────────────────────────────────
    def rows_to_list(query_result: list) -> list[dict]:
        return [
            {c.name: getattr(row, c.name) for c in row.__table__.columns}
            for row in query_result
        ]

    sql_exports: dict[str, list[dict]] = {
        "properties":  rows_to_list(db.query(Property).filter(Property.org_id == org_id).all()),
        "units":       rows_to_list(db.query(Unit).filter(Unit.org_id == org_id).all()),
        "lessees":     rows_to_list(db.query(Lessee).filter(Lessee.org_id == org_id).all()),
        "agreements":  rows_to_list(db.query(RentalAgreement).filter(RentalAgreement.org_id == org_id).all()),
        "invoices":    rows_to_list(db.query(Invoice).filter(Invoice.org_id == org_id).all()),
        "expenses":    rows_to_list(db.query(Expense).filter(Expense.org_id == org_id).all()),
        "payments":    rows_to_list(db.query(Payment).filter(Payment.org_id == org_id).all()),
        "documents":   rows_to_list(db.query(Document).filter(Document.org_id == org_id).all()),
    }

    # ── Build S3 document list ───────────────────────────────────────────────
    doc_rows: list[Document] = db.query(Document).filter(Document.org_id == org_id).all()

    # ── Stream ZIP ──────────────────────────────────────────────────────────
    def generate_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # JSON data files
            for name, records in sql_exports.items():
                zf.writestr(
                    f"data/{name}.json",
                    json.dumps(records, indent=2, default=_serialize),
                )

            # S3 documents — fetched individually, placed in category sub-folders
            for doc in doc_rows:
                try:
                    file_bytes = s3_service.download_bytes(doc.s3_key)
                    category_folder = doc.document_category or "other"
                    safe_name = doc.display_name.replace("/", "_").replace("\\", "_")
                    zf.writestr(f"documents/{category_folder}/{safe_name}", file_bytes)
                except Exception:
                    # If an S3 object is missing, skip it rather than failing the whole export
                    pass

        buf.seek(0)
        yield from buf

    today_str = date.today().isoformat()
    return StreamingResponse(
        generate_zip(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="crassus-export-{today_str}.zip"'
        },
    )


# ---------------------------------------------------------------------------
# Account deletion
# ---------------------------------------------------------------------------

@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    """Permanently delete the organisation, all its data, and all S3 objects."""
    org_id = current_user.org_id

    # 1. Delete all S3 objects belonging to this org
    #    Known prefixes: documents, invoices, logos
    for prefix in [
        f"orgs/{org_id}/",
        f"invoices/{org_id}/",
        f"logos/{org_id}/",
    ]:
        try:
            keys = s3_service.list_keys_by_prefix(prefix)
            s3_service.delete_keys(keys)
        except Exception:
            pass  # S3 errors must not block DB deletion

    # 2. Delete all users in the org (FK is RESTRICT, so must go before the org)
    db.query(User).filter(User.org_id == org_id).delete(synchronize_session=False)

    # 3. Delete the org — CASCADE removes everything else (settings, properties,
    #    units, lessees, agreements, invoices, expenses, documents, …)
    org = db.get(Organisation, org_id)
    if org:
        db.delete(org)

    db.commit()
