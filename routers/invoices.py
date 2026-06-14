import base64
import calendar
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List

import resend
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from i18n import get_translations
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from config import settings as app_settings
from database import get_db
from models import Document, Invoice, Lessee, Payment, Property, RentalAgreement, Settings, Unit, User
from schemas import (
    BatchGenerateRequest,
    BatchPreviewRequest,
    BatchPreviewRow,
    InvoiceCreate,
    InvoiceRead,
    InvoiceUpdate,
    NextPeriodResponse,
    RecordPaymentRequest,
    SendInvoiceRequest,
)
from services import s3 as s3_service

# Jinja2 environment — templates/ relative to project root
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=False)

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(db: Session, invoice_id: int, org_id: int) -> Invoice:
    row = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    return row


def _mark_overdue(db: Session, org_id: int) -> None:
    """Flip all pending invoices past their due date to overdue."""
    today = date.today()
    db.query(Invoice).filter(
        Invoice.org_id == org_id,
        Invoice.invoice_status == "pending",
        Invoice.due_date < today,
    ).update({"invoice_status": "overdue"}, synchronize_session=False)
    db.commit()


def _org_scheme(db: Session, org_id: int) -> str:
    """Return the invoice numbering scheme for the org ('sequential' or 'property_ref')."""
    s = db.query(Settings).filter(Settings.org_id == org_id).first()
    return (s.invoice_numbering_scheme or "sequential") if s else "sequential"


def _next_sequential_number(db: Session, org_id: int, year: int | None = None) -> str:
    y = year or date.today().year
    prefix = f"INV-{y}-"
    rows = db.query(Invoice.invoice_number).filter(
        Invoice.org_id == org_id, Invoice.invoice_number.like(f"{prefix}%")
    ).all()
    max_seq = 0
    for (num,) in rows:
        try:
            max_seq = max(max_seq, int(num[len(prefix):]))
        except (ValueError, IndexError):
            pass
    return f"{prefix}{max_seq + 1:04d}"


def _property_ref_number(
    db: Session,
    org_id: int,
    agreement_uuid: str,
    billing_period_start: date,
) -> str:
    """Build a property-ref invoice number, e.g. M2/2026/07.
    Falls back to sequential if the property has no reference set."""
    ag = db.query(RentalAgreement).filter(
        RentalAgreement.agreement_uuid == agreement_uuid,
        RentalAgreement.org_id == org_id,
    ).first()
    unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag and ag.unit_id else None
    prop_id = unit.property_id if unit else (ag.property_id if ag else None)
    prop = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
    ref = prop.property_reference if prop and prop.property_reference else None
    if not ref:
        return _next_sequential_number(db, org_id, billing_period_start.year)
    return f"{ref}/{billing_period_start.year}/{billing_period_start.month:02d}"


def _next_invoice_number(
    db: Session,
    org_id: int,
    agreement_uuid: str | None = None,
    billing_period_start: date | None = None,
) -> str:
    """Dispatch to the correct numbering scheme for the org."""
    scheme = _org_scheme(db, org_id)
    if scheme == "property_ref" and agreement_uuid and billing_period_start:
        return _property_ref_number(db, org_id, agreement_uuid, billing_period_start)
    return _next_sequential_number(db, org_id)


def _credit_note_number(db: Session, org_id: int, parent_invoice_number: str) -> str:
    """Credit note number: append /CR for property_ref scheme, else sequential."""
    scheme = _org_scheme(db, org_id)
    if scheme == "property_ref":
        return f"{parent_invoice_number}/CR"
    return _next_sequential_number(db, org_id)


def _period_end(start: date, interval: str) -> date:
    if interval == "monthly":
        last_day = calendar.monthrange(start.year, start.month)[1]
        return start.replace(day=last_day)
    elif interval == "quarterly":
        # 3 months from start, last day of that month
        month = start.month + 2
        year = start.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)
    else:  # annually
        return start.replace(year=start.year + 1) - timedelta(days=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[InvoiceRead])
def list_invoices(
    invoice_status: str | None = None,
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    _mark_overdue(db, current_user.org_id)
    q = db.query(Invoice).filter(Invoice.org_id == current_user.org_id)
    if invoice_status:
        q = q.filter(Invoice.invoice_status == invoice_status)
    if property_id is not None:
        q = (
            q.join(RentalAgreement, RentalAgreement.agreement_uuid == Invoice.agreement_uuid)
            .outerjoin(Unit, Unit.id == RentalAgreement.unit_id)
            .filter(
                (Unit.property_id == property_id)
                | (
                    RentalAgreement.unit_id.is_(None)
                    & (RentalAgreement.property_id == property_id)
                )
            )
        )
    invoices = q.order_by(Invoice.issue_date.desc()).all()

    # Enrich with unit_number via agreement → unit lookup
    result = []
    for inv in invoices:
        ag = db.query(RentalAgreement).filter(
            RentalAgreement.agreement_uuid == inv.agreement_uuid
        ).first()
        unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag else None
        row = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
        row["unit_number"] = unit.unit_number if unit else None
        result.append(row)
    return result


@router.post("/batch-preview", response_model=List[BatchPreviewRow])
def batch_preview(
    payload: BatchPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> List[BatchPreviewRow]:
    today = payload.reference_date or date.today()

    # All currently active agreements for this org
    agreements = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.org_id == current_user.org_id,
            RentalAgreement.valid_time_start <= datetime.combine(today, datetime.min.time()),
            RentalAgreement.valid_time_end >= datetime.combine(today, datetime.min.time()),
        )
        .all()
    )

    # Compute starting invoice sequence for this batch (increment per row without committing)
    scheme = _org_scheme(db, current_user.org_id)

    # For sequential scheme: pre-compute the starting sequence number so we can
    # allocate numbers in-memory without committing between rows.
    year = today.year
    prefix = f"INV-{year}-"
    seq = 1
    if scheme == "sequential":
        existing_nums = (
            db.query(Invoice.invoice_number)
            .filter(Invoice.org_id == current_user.org_id, Invoice.invoice_number.like(f"{prefix}%"))
            .all()
        )
        max_seq = 0
        for (num,) in existing_nums:
            try:
                max_seq = max(max_seq, int(num[len(prefix):]))
            except (ValueError, IndexError):
                pass
        seq = max_seq + 1

    rows: List[BatchPreviewRow] = []
    for agreement in agreements:
        # Next period logic (mirrors /next-period endpoint)
        latest = (
            db.query(Invoice)
            .filter(
                Invoice.agreement_uuid == agreement.agreement_uuid,
                Invoice.org_id == current_user.org_id,
                Invoice.invoice_type == "standard",
            )
            .order_by(Invoice.billing_period_end.desc())
            .first()
        )
        if latest:
            period_start = latest.billing_period_end + timedelta(days=1)
        else:
            period_start = agreement.valid_time_start.date()
            while _period_end(period_start, agreement.payment_interval) < today:
                period_start = _period_end(period_start, agreement.payment_interval) + timedelta(days=1)

        period_end = _period_end(period_start, agreement.payment_interval)
        due_date = period_start - timedelta(days=1)

        # If the next unbilled period starts AFTER the reference date (last day of selected
        # billing month), the selected month is already fully covered by an existing invoice.
        already_invoiced = period_start > today
        if already_invoiced and latest:
            # Show the already-issued period so the row is informative
            period_start = latest.billing_period_start
            period_end = latest.billing_period_end
            due_date = period_start - timedelta(days=1)

        # Resolve labels
        unit = db.query(Unit).filter(Unit.id == agreement.unit_id).first() if agreement.unit_id else None
        prop_id = unit.property_id if unit else agreement.property_id
        property_obj = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
        lessee = (
            db.query(Lessee)
            .filter(Lessee.lessee_uuid == agreement.lessee_uuid, Lessee.org_id == current_user.org_id)
            .first()
        )
        if unit and property_obj:
            unit_label = f"{property_obj.name} — {unit.unit_number}"
        elif property_obj:
            unit_label = property_obj.name
        else:
            unit_label = "Unknown property"
        if lessee:
            lessee_name = lessee.company_legal_name or " ".join(filter(None, [lessee.first_name, lessee.last_name])) or lessee.email
        else:
            lessee_name = "Unknown lessee"

        net = Decimal(str(agreement.base_rent_amount)) + Decimal(str(agreement.service_charges))
        vat = (net * Decimal(str(agreement.vat_rate_applied)) / Decimal("100")).quantize(Decimal("0.01"))
        gross = net + vat

        if scheme == "property_ref":
            suggested = _property_ref_number(db, current_user.org_id, agreement.agreement_uuid, period_start)
        else:
            suggested = f"{prefix}{seq:04d}"

        rows.append(BatchPreviewRow(
            agreement_uuid=agreement.agreement_uuid,
            unit_label=unit_label,
            lessee_name=lessee_name,
            billing_period_start=period_start,
            billing_period_end=period_end,
            due_date=due_date,
            net_amount=net,
            vat_amount=vat,
            gross_amount=gross,
            suggested_invoice_number=suggested,
            already_invoiced=already_invoiced,
        ))
        if not already_invoiced and scheme == "sequential":
            seq += 1  # Only advance sequence for rows that will actually be created

    return rows


@router.post("/batch-generate", response_model=List[InvoiceRead], status_code=status.HTTP_201_CREATED)
def batch_generate(
    payload: BatchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> List[Invoice]:
    created: List[Invoice] = []
    for item in payload.items:
        # Verify agreement belongs to org
        agreement = (
            db.query(RentalAgreement)
            .filter(
                RentalAgreement.agreement_uuid == item.agreement_uuid,
                RentalAgreement.org_id == current_user.org_id,
            )
            .first()
        )
        if not agreement:
            continue  # Skip silently — race condition / invalid uuid

        # Deduplicate — skip if already invoiced for this period
        exists = (
            db.query(Invoice)
            .filter(
                Invoice.org_id == current_user.org_id,
                Invoice.invoice_number == item.invoice_number,
            )
            .first()
        )
        if exists:
            continue

        net = item.net_amount.quantize(Decimal("0.01"))
        vat = item.vat_amount.quantize(Decimal("0.01"))
        gross = net + vat

        row = Invoice(
            org_id=current_user.org_id,
            invoice_number=item.invoice_number,
            agreement_uuid=item.agreement_uuid,
            invoice_type="standard",
            billing_period_start=item.billing_period_start,
            billing_period_end=item.billing_period_end,
            issue_date=item.issue_date,
            due_date=item.due_date,
            net_amount=net,
            vat_amount=vat,
            gross_amount=gross,
            invoice_status="pending",
        )
        db.add(row)
        db.flush()  # Get ID without full commit
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return created


@router.get("/next-period", response_model=NextPeriodResponse)
def get_next_period(
    agreement_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NextPeriodResponse:
    agreement = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.agreement_uuid == agreement_uuid,
            RentalAgreement.org_id == current_user.org_id,
        )
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found.")

    # Find the latest standard invoice for this agreement
    latest = (
        db.query(Invoice)
        .filter(
            Invoice.agreement_uuid == agreement_uuid,
            Invoice.org_id == current_user.org_id,
            Invoice.invoice_type == "standard",
        )
        .order_by(Invoice.billing_period_end.desc())
        .first()
    )

    if latest:
        period_start = latest.billing_period_end + timedelta(days=1)
    else:
        # No invoices yet — fast-forward to the next period whose start is in the future
        period_start = agreement.valid_time_start.date()
        today = date.today()
        while period_start <= today:
            period_start = _period_end(period_start, agreement.payment_interval) + timedelta(days=1)

    period_end = _period_end(period_start, agreement.payment_interval)
    due_date = period_start - timedelta(days=1)

    net = Decimal(str(agreement.base_rent_amount)) + Decimal(str(agreement.service_charges))
    vat = (net * Decimal(str(agreement.vat_rate_applied)) / Decimal("100")).quantize(Decimal("0.01"))
    gross = net + vat

    return NextPeriodResponse(
        billing_period_start=period_start,
        billing_period_end=period_end,
        due_date=due_date,
        net_amount=net,
        vat_amount=vat,
        gross_amount=gross,
        suggested_invoice_number=_next_invoice_number(
            db, current_user.org_id,
            agreement_uuid=agreement.agreement_uuid,
            billing_period_start=period_start,
        ),
    )


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    return _get_or_404(db, invoice_id, current_user.org_id)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Invoice:
    agreement = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.agreement_uuid == payload.agreement_uuid,
            RentalAgreement.org_id == current_user.org_id,
        )
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental agreement not found.")

    if payload.parent_invoice_id is not None:
        parent = _get_or_404(db, payload.parent_invoice_id, current_user.org_id)
        if parent.invoice_type != "standard":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Credit notes can only reference standard invoices.",
            )

    existing = db.query(Invoice).filter(
        Invoice.invoice_number == payload.invoice_number,
        Invoice.org_id == current_user.org_id,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invoice number already exists.")

    row = Invoice(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Invoice:
    row = _get_or_404(db, invoice_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{invoice_id}/credit", response_model=InvoiceRead)
def credit_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.org_id)
    if invoice.invoice_status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending or overdue invoices can be credited.",
        )
    if invoice.invoice_type != "standard":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot credit a credit note.",
        )

    today = date.today()
    credit_note = Invoice(
        org_id=current_user.org_id,
        invoice_number=_credit_note_number(db, current_user.org_id, invoice.invoice_number),
        agreement_uuid=invoice.agreement_uuid,
        parent_invoice_id=invoice.id,
        invoice_type="credit_note",
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        issue_date=today,
        due_date=today,
        net_amount=-Decimal(str(invoice.net_amount)),
        vat_amount=-Decimal(str(invoice.vat_amount)),
        gross_amount=-Decimal(str(invoice.gross_amount)),
        invoice_status="pending",
    )
    db.add(credit_note)
    invoice.invoice_status = "credited"
    db.commit()
    db.refresh(credit_note)
    return credit_note


@router.post("/{invoice_id}/pay", response_model=InvoiceRead)
def pay_invoice(
    invoice_id: int,
    payload: RecordPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.org_id)
    if invoice.invoice_status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending or overdue invoices can be marked as paid.",
        )

    payment = Payment(
        org_id=current_user.org_id,
        invoice_id=invoice.id,
        payment_date=datetime.combine(payload.payment_date, datetime.min.time()),
        amount_received=payload.amount_received,
        payment_method=payload.payment_method,
        transaction_reference=payload.transaction_reference,
        notes=payload.notes,
    )
    db.add(payment)
    invoice.invoice_status = "paid"
    db.commit()
    db.refresh(invoice)
    return invoice


def _get_template(invoice_type: str):
    name = "credit_note.html" if invoice_type == "credit_note" else "invoice.html"
    return _jinja_env.get_template(name)


def _build_invoice_context(invoice: Invoice, db: Session, org_id: int) -> dict:
    """Gather all data needed to render the invoice template."""
    agreement = (
        db.query(RentalAgreement)
        .filter(RentalAgreement.agreement_uuid == invoice.agreement_uuid, RentalAgreement.org_id == org_id)
        .order_by(RentalAgreement.id.desc())
        .first()
    )
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found.")

    unit = db.query(Unit).filter(Unit.id == agreement.unit_id).first() if agreement.unit_id else None
    # Resolve property: prefer via unit, fall back to agreement.property_id for unit-less properties
    prop_id = unit.property_id if unit else agreement.property_id
    property_obj = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
    lessee = (
        db.query(Lessee)
        .filter(Lessee.lessee_uuid == agreement.lessee_uuid, Lessee.org_id == org_id)
        .first()
    )
    org_settings = db.query(Settings).filter(Settings.org_id == org_id).first()

    # Lessee display name
    if lessee:
        if lessee.company_legal_name:
            lessee_name = lessee.company_legal_name
        else:
            lessee_name = " ".join(filter(None, [lessee.first_name, lessee.last_name])) or lessee.email
    else:
        lessee_name = "Unknown Lessee"

    # Logo as base64 data URL
    logo_data_url = None
    if org_settings and org_settings.logo_s3_key:
        try:
            ext = org_settings.logo_s3_key.rsplit(".", 1)[-1].lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "image/png")
            logo_data_url = s3_service.download_as_data_url(org_settings.logo_s3_key, mime)
        except Exception:
            pass

    # Parent invoice number (for credit notes)
    parent_invoice_number = None
    if invoice.parent_invoice_id:
        parent = db.query(Invoice).filter(Invoice.id == invoice.parent_invoice_id).first()
        parent_invoice_number = parent.invoice_number if parent else None

    currency = org_settings.currency if org_settings else "EUR"
    vat_rate = str(Decimal(str(agreement.vat_rate_applied)).quantize(Decimal("0.01"))).rstrip("0").rstrip(".")
    lang = (org_settings.invoice_language if org_settings and org_settings.invoice_language else "en")
    t    = get_translations(lang)

    return {
        "invoice": invoice,
        "agreement": agreement,
        "unit": unit,
        "property_obj": property_obj,
        "lessee": lessee,
        "lessee_name": lessee_name,
        "org_settings": org_settings,
        "logo_data_url": logo_data_url,
        "currency": currency,
        "vat_rate": vat_rate,
        "parent_invoice_number": parent_invoice_number,
        "net_amount": f"{Decimal(str(invoice.net_amount)):,.2f}",
        "vat_amount": f"{Decimal(str(invoice.vat_amount)):,.2f}",
        "gross_amount": f"{Decimal(str(invoice.gross_amount)):,.2f}",
        "lang": lang,
        "t": t,
    }


@router.get("/{invoice_id}/download")
def download_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    invoice = _get_or_404(db, invoice_id, current_user.org_id)
    if not invoice.pdf_s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF on file for this invoice. Send it first.",
        )
    url = s3_service.presigned_download_url(invoice.pdf_s3_key)
    return JSONResponse({"url": url, "expires_in": 900})


@router.get("/{invoice_id}/preview")
def preview_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    invoice = _get_or_404(db, invoice_id, current_user.org_id)
    ctx = _build_invoice_context(invoice, db, current_user.org_id)
    html = _get_template(invoice.invoice_type).render(**ctx)
    return JSONResponse({"html": html})


@router.post("/{invoice_id}/send", response_model=InvoiceRead)
def send_invoice(
    invoice_id: int,
    payload: SendInvoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Invoice:
    invoice = _get_or_404(db, invoice_id, current_user.org_id)
    if invoice.invoice_status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only pending or overdue invoices can be sent.",
        )

    ctx = _build_invoice_context(invoice, db, current_user.org_id)
    lessee = ctx["lessee"]
    org_settings = ctx["org_settings"]

    if not lessee:
        raise HTTPException(status_code=404, detail="Lessee not found.")

    # Decode PDF
    pdf_bytes = base64.b64decode(payload.pdf_base64)

    # Upload to S3
    s3_key = f"invoices/{current_user.org_id}/{payload.filename}"
    s3_service.upload_bytes(s3_key, pdf_bytes, "application/pdf")

    # ── Build rich HTML email ──────────────────────────────────────────────
    resend.api_key = app_settings.RESEND_API_KEY
    t            = ctx["t"]
    lang         = ctx["lang"]
    company_name = org_settings.company_name if org_settings else "Your Landlord"
    currency     = ctx["currency"]
    lessee_name  = ctx["lessee_name"]
    net_amount   = ctx["net_amount"]
    vat_amount   = ctx["vat_amount"]
    gross_amount = ctx["gross_amount"]
    vat_rate     = ctx["vat_rate"]
    period_start = invoice.billing_period_start.strftime("%d %b %Y")
    period_end   = invoice.billing_period_end.strftime("%d %b %Y")
    due_date_str = invoice.due_date.strftime("%d %b %Y")

    # Company footer lines
    company_address = (org_settings.company_address or "").replace("\n", " · ") if org_settings else ""
    company_vat     = org_settings.company_vat_number if org_settings and org_settings.company_vat_number else None
    reply_to        = org_settings.billing_email_sender if org_settings and org_settings.billing_email_sender else None

    # Description label
    property_obj = ctx.get("property_obj")
    unit         = ctx.get("unit")
    if property_obj:
        desc_line = property_obj.name
        if unit:
            desc_line += f" — {unit.unit_number}"
    else:
        desc_line = ""

    def _row(label: str, value: str, bold: bool = False) -> str:
        weight = "font-weight:600;" if bold else ""
        size   = "font-size:15px;" if bold else "font-size:13px;"
        return (
            f'<tr>'
            f'<td style="padding:7px 16px 7px 0;color:#666;{size}">{label}</td>'
            f'<td style="padding:7px 0;color:#111;{size}{weight}text-align:right;">{value}</td>'
            f'</tr>'
        )

    summary_rows = (
        _row(t["email_invoice_no"], invoice.invoice_number)
        + _row(t["email_period"], f"{period_start} – {period_end}")
        + (f'<tr><td style="padding:7px 16px 7px 0;color:#666;font-size:13px;">{t["email_description"]}</td>'
           f'<td style="padding:7px 0;color:#111;font-size:13px;text-align:right;">{desc_line}</td></tr>'
           if desc_line else "")
        + f'<tr><td colspan="2" style="padding:4px 0;border-bottom:1px solid #e8e8e8;"></td></tr>'
        + _row(t["email_net"], f"{currency} {net_amount}")
        + _row(f'{t["email_vat_prefix"]} ({vat_rate}%)', f"{currency} {vat_amount}")
        + f'<tr><td colspan="2" style="padding:2px 0;border-bottom:2px solid #111;"></td></tr>'
        + _row(t["email_total_due"], f"{currency} {gross_amount}", bold=True)
    )

    bank_block = ""
    if org_settings and org_settings.bank_account:
        bank_block = (
            f'<tr><td style="height:16px;"></td></tr>'
            f'<tr><td colspan="2" style="padding:12px 14px;background:#f5f5f5;border-radius:6px;'
            f'font-size:12px;color:#555;line-height:1.7;">'
            f'<strong style="color:#111;">{t["email_payment_details"]}</strong><br>'
            f'{t["email_bank_account"]} <span style="font-family:monospace;font-weight:600;color:#111;">'
            f'{org_settings.bank_account}</span><br>'
            f'{t["email_reference"]} <span style="font-weight:600;color:#111;">{invoice.invoice_number}</span>'
            f'</td></tr>'
        )

    greeting_html = (
        f'<p style="margin:0 0 20px;font-size:15px;color:#111;">'
        f'{t["email_greeting"].format(name=lessee_name)}</p>'
    )

    footer_parts = [company_name]
    if company_address:
        footer_parts.append(company_address)
    if company_vat:
        footer_parts.append(f'{t["vat_company_label"]} {company_vat}')
    footer_text = " &nbsp;·&nbsp; ".join(footer_parts)

    if payload.is_reminder:
        period_mm_yy = invoice.billing_period_start.strftime("%m/%y")
        subject = t["email_subject_reminder"].format(
            period=period_mm_yy, property=desc_line or company_name, company=company_name
        )
        intro_html = (
            f'<p style="margin:0 0 20px;font-size:14px;color:#444;line-height:1.7;">'
            + t["email_intro_reminder"].format(
                number=invoice.invoice_number, date=due_date_str
            )
            + '</p>'
        )
        due_block_color = "#b91c1c"
        due_label       = t["email_overdue_label"]
        intro_plain = (
            f'{t["email_greeting"].format(name=lessee_name)}\n\n'
            + t["email_intro_reminder"].replace("<strong>", "").replace("</strong>", "").format(
                number=invoice.invoice_number, date=due_date_str
            )
            + "\n\n"
        )
    else:
        period_mm_yy = invoice.billing_period_start.strftime("%m/%y")
        subject = t["email_subject_invoice"].format(
            period=period_mm_yy, property=desc_line or company_name, company=company_name
        )
        intro_html = (
            f'<p style="margin:0 0 20px;font-size:14px;color:#444;line-height:1.7;">'
            + t["email_intro_invoice"].format(start=period_start, end=period_end)
            + '</p>'
        )
        due_block_color = "#1d4ed8"
        due_label       = t["email_due_label"]
        intro_plain = (
            f'{t["email_greeting"].format(name=lessee_name)}\n\n'
            + t["email_intro_invoice"].replace("<strong>", "").replace("</strong>", "").format(
                start=period_start, end=period_end
            )
            + "\n\n"
        )

    email_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:32px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#ffffff;">

        <!-- Top accent bar -->
        <tr><td style="height:4px;background:#111111;"></td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 40px 28px;">

          {greeting_html}

          {intro_html}

          <!-- Due date callout -->
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="margin-bottom:24px;border-radius:6px;background:{due_block_color};overflow:hidden;">
            <tr>
              <td style="padding:12px 16px;">
                <span style="font-size:11px;font-weight:700;text-transform:uppercase;
                             letter-spacing:0.8px;color:rgba(255,255,255,0.75);">{due_label}</span><br>
                <span style="font-size:20px;font-weight:700;color:#ffffff;">{due_date_str}</span>
              </td>
              <td style="padding:12px 16px;text-align:right;vertical-align:middle;">
                <span style="font-size:22px;font-weight:800;color:#ffffff;">{currency} {gross_amount}</span>
              </td>
            </tr>
          </table>

          <!-- Invoice summary table -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
            {summary_rows}
            {bank_block}
          </table>

          <!-- Closing -->
          <p style="margin:28px 0 0;font-size:14px;color:#444;line-height:1.7;">
            {t["email_closing"]}
          </p>
          <p style="margin:16px 0 0;font-size:14px;color:#444;">
            {t["email_kind_regards"]}<br>
            <strong style="color:#111;">{company_name}</strong>
          </p>

        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:16px 40px;background:#f8f8f8;border-top:1px solid #e8e8e8;
                       font-size:11px;color:#999;text-align:center;line-height:1.8;">
          {footer_text}
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    # Plain-text fallback
    bank_plain = ""
    if org_settings and org_settings.bank_account:
        bank_plain = (
            f'{t["plain_bank"]} {org_settings.bank_account}\n'
            f'{t["plain_reference"]} {invoice.invoice_number}\n\n'
        )
    email_text = (
        f"{intro_plain}"
        f'{t["plain_invoice_no"]} {invoice.invoice_number}\n'
        f'{t["plain_period"]} {period_start} – {period_end}\n'
        f'{t["plain_net"]} {currency} {net_amount}\n'
        f'{t["plain_vat_prefix"]} ({vat_rate}%): {currency} {vat_amount}\n'
        f'{t["plain_total_due"]} {currency} {gross_amount}\n'
        f'{t["plain_due_date"]} {due_date_str}\n\n'
        f"{bank_plain}"
        f'{t["email_kind_regards"]}\n{company_name}\n'
    )

    attachments: list[dict] = [{"filename": payload.filename, "content": list(pdf_bytes)}]

    to_address = app_settings.DEV_EMAIL if app_settings.DEV_EMAIL else lessee.email
    send_kwargs: dict = {
        "from": app_settings.INVOICE_FROM_EMAIL,
        "to": [to_address],
        "subject": subject,
        "html": email_html,
        "text": email_text,
        "attachments": attachments,
    }
    if reply_to:
        send_kwargs["reply_to"] = reply_to
    # CC the landlord (billing sender) so they receive a copy of every invoice sent
    if reply_to and not app_settings.DEV_EMAIL:
        send_kwargs["cc"] = [reply_to]

    result = resend.Emails.send(send_kwargs)

    # Update invoice record
    invoice.pdf_s3_key = s3_key
    invoice.pdf_s3_bucket = app_settings.AWS_S3_BUCKET_NAME
    invoice.resend_email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
    invoice.email_delivery_status = "sent"

    # Upsert Document record so the invoice PDF appears in the Documents archive
    existing_doc = (
        db.query(Document)
        .filter(Document.related_entity_type == "invoice", Document.related_entity_id == invoice.id)
        .first()
    )
    if existing_doc:
        existing_doc.s3_key = s3_key
        existing_doc.s3_bucket = app_settings.AWS_S3_BUCKET_NAME
        existing_doc.display_name = payload.filename
        existing_doc.file_size_bytes = len(pdf_bytes)
    else:
        doc = Document(
            org_id=current_user.org_id,
            display_name=payload.filename,
            s3_bucket=app_settings.AWS_S3_BUCKET_NAME,
            s3_key=s3_key,
            file_size_bytes=len(pdf_bytes),
            mime_type="application/pdf",
            related_entity_type="invoice",
            related_entity_id=invoice.id,
            document_category="invoice",
            uploaded_by_user_id=current_user.id,
        )
        db.add(doc)

    db.commit()
    db.refresh(invoice)
    return invoice
