import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from auth import get_current_user, require_role
from config import settings as app_settings
from database import get_db
from i18n import get_translations
from models import Lessee, Property, RentalAgreement, Settings, Unit, User
from schemas import ApplyIndexRequest, RentalAgreementCreate, RentalAgreementRead, RentalAgreementUpdate

resend.api_key = app_settings.RESEND_API_KEY

router = APIRouter(prefix="/rental-agreements", tags=["rental-agreements"])


def _get_or_404(db: Session, agreement_id: int, org_id: int) -> RentalAgreement:
    row = (
        db.query(RentalAgreement)
        .filter(RentalAgreement.id == agreement_id, RentalAgreement.org_id == org_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental agreement not found.")
    return row


@router.get("", response_model=List[RentalAgreementRead])
def list_agreements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RentalAgreement]:
    return db.query(RentalAgreement).filter(RentalAgreement.org_id == current_user.org_id).all()


@router.get("/{agreement_id}", response_model=RentalAgreementRead)
def get_agreement(
    agreement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RentalAgreement:
    return _get_or_404(db, agreement_id, current_user.org_id)


@router.post("", response_model=RentalAgreementRead, status_code=status.HTTP_201_CREATED)
def create_agreement(
    payload: RentalAgreementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> RentalAgreement:
    prop = db.query(Property).filter(Property.id == payload.property_id, Property.org_id == current_user.org_id).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")

    if payload.unit_id is not None:
        unit = db.query(Unit).filter(Unit.id == payload.unit_id, Unit.org_id == current_user.org_id).first()
        if not unit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
        if unit.property_id != payload.property_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit does not belong to the selected property.")

    lessee = (
        db.query(Lessee)
        .filter(Lessee.lessee_uuid == payload.lessee_uuid, Lessee.org_id == current_user.org_id)
        .first()
    )
    if not lessee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lessee not found.")

    row = RentalAgreement(
        org_id=current_user.org_id,
        agreement_uuid=str(uuid.uuid4()),
        **payload.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{agreement_id}", response_model=RentalAgreementRead)
def update_agreement(
    agreement_id: int,
    payload: RentalAgreementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> RentalAgreement:
    row = _get_or_404(db, agreement_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{agreement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agreement(
    agreement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, agreement_id, current_user.org_id)
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------------------
# Rent indexation
# ---------------------------------------------------------------------------

@router.post("/{agreement_uuid}/apply-index")
def apply_index(
    agreement_uuid: str,
    payload: ApplyIndexRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> dict:
    """Apply a rent indexation to an agreement and optionally notify the lessee."""
    ag = db.query(RentalAgreement).filter(
        RentalAgreement.agreement_uuid == agreement_uuid,
        RentalAgreement.org_id == current_user.org_id,
    ).first()
    if not ag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agreement not found.")

    # ── Compute multiplier ───────────────────────────────────────────────────
    if payload.index_numerator is not None and payload.index_denominator is not None:
        multiplier = Decimal(str(payload.index_numerator)) / Decimal(str(payload.index_denominator))
        index_label = f"{payload.index_numerator} / {payload.index_denominator}"
    else:
        multiplier = Decimal("1") + Decimal(str(payload.index_percentage)) / Decimal("100")
        index_label = f"{payload.index_percentage}%"

    old_rent = Decimal(str(ag.base_rent_amount))
    new_rent = (old_rent * multiplier).quantize(Decimal("0.01"))

    # ── Update agreement ─────────────────────────────────────────────────────
    ag.base_rent_amount = new_rent
    # Record when the index was applied so the dashboard can hide this row
    # until the next annual cycle (≥ 335 days from now)
    ag.indexation_last_applied = payload.effective_date

    db.commit()

    # ── Send notification email ──────────────────────────────────────────────
    if payload.send_notification:
        _send_indexation_email(
            db=db,
            ag=ag,
            old_rent=old_rent,
            new_rent=new_rent,
            index_label=index_label,
            effective_date=payload.effective_date,
            org_id=current_user.org_id,
        )

    return {"old_rent": str(old_rent), "new_rent": str(new_rent)}


def _send_indexation_email(
    *,
    db: Session,
    ag: RentalAgreement,
    old_rent: Decimal,
    new_rent: Decimal,
    index_label: str,
    effective_date: date,
    org_id: int,
) -> None:
    """Build and dispatch the indexation notification email. Never raises."""
    try:
        _do_send_indexation_email(
            db=db, ag=ag, old_rent=old_rent, new_rent=new_rent,
            index_label=index_label, effective_date=effective_date, org_id=org_id,
        )
    except Exception as exc:
        logger.error("Indexation email failed for agreement %s: %s", ag.agreement_uuid, exc)


def _do_send_indexation_email(
    *,
    db: Session,
    ag: RentalAgreement,
    old_rent: Decimal,
    new_rent: Decimal,
    index_label: str,
    effective_date: date,
    org_id: int,
) -> None:
    """Internal: build and send the email (may raise)."""
    resend.api_key = app_settings.RESEND_API_KEY

    # ── Resolve related objects ──────────────────────────────────────────────
    lessee = db.query(Lessee).filter(
        Lessee.lessee_uuid == ag.lessee_uuid,
        Lessee.org_id == org_id,
    ).first()
    if not lessee:
        return

    unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag.unit_id else None
    prop_id = unit.property_id if unit else ag.property_id
    prop = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None

    org_settings = db.query(Settings).filter(Settings.org_id == org_id).first()

    # ── i18n ────────────────────────────────────────────────────────────────
    lang = org_settings.invoice_language if org_settings and org_settings.invoice_language else "en"
    t = get_translations(lang)

    lessee_name = (
        lessee.company_legal_name
        or " ".join(filter(None, [lessee.first_name, lessee.last_name]))
        or lessee.email
    )
    property_label = prop.name if prop else "your rental"
    if unit:
        property_label = f"{property_label} — {unit.unit_number}"

    currency = org_settings.currency if org_settings else "EUR"
    effective_str = effective_date.strftime("%d %b %Y")

    fmt_old = f"{currency} {old_rent:,.2f}"
    fmt_new = f"{currency} {new_rent:,.2f}"

    company_name = org_settings.company_name if org_settings else ""
    reply_to = org_settings.billing_email_sender if org_settings and org_settings.billing_email_sender else None

    to_email = app_settings.DEV_EMAIL if app_settings.DEV_EMAIL else lessee.email

    subject = t["idx_subject"].format(property=property_label)
    greeting = t["email_greeting"].format(name=lessee_name)
    intro = t["idx_intro"].format(property=property_label, effective_date=effective_str)
    closing = t["idx_closing"]
    kind_regards = t["email_kind_regards"]

    # ── HTML body ────────────────────────────────────────────────────────────
    html_body = f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;font-size:9pt;color:#1a1a1a;">
<div style="max-width:540px;margin:32px auto;padding:0 16px;">

  <p style="font-size:9pt;color:#1a1a1a;margin:0 0 20px;">{greeting}</p>
  <p style="font-size:9pt;color:#444;line-height:1.7;margin:0 0 24px;">{intro}</p>

  <!-- Summary table -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-collapse:collapse;border:1px solid #e8e8e8;border-radius:8px;margin-bottom:24px;">
    <tr style="background:#f8f8f8;border-bottom:1px solid #e8e8e8;">
      <td style="padding:10px 16px;font-size:7.5pt;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;">{t["idx_index_applied"]}</td>
      <td style="padding:10px 16px;font-size:9pt;font-weight:700;color:#0a0a0a;text-align:right;">{index_label}</td>
    </tr>
    <tr style="border-bottom:1px solid #f0f0f0;">
      <td style="padding:10px 16px;font-size:8.5pt;color:#555;">{t["idx_old_rent"]}</td>
      <td style="padding:10px 16px;font-size:8.5pt;color:#0a0a0a;text-align:right;">{fmt_old}</td>
    </tr>
    <tr style="border-bottom:1px solid #f0f0f0;">
      <td style="padding:10px 16px;font-size:8.5pt;font-weight:700;color:#0a0a0a;">{t["idx_new_rent"]}</td>
      <td style="padding:10px 16px;font-size:9pt;font-weight:700;color:#0a0a0a;text-align:right;">{fmt_new}</td>
    </tr>
    <tr>
      <td style="padding:10px 16px;font-size:8.5pt;color:#555;">{t["idx_effective_date"]}</td>
      <td style="padding:10px 16px;font-size:8.5pt;color:#0a0a0a;text-align:right;">{effective_str}</td>
    </tr>
  </table>

  <p style="font-size:9pt;color:#444;line-height:1.7;margin:0 0 24px;">{closing}</p>
  <p style="font-size:9pt;color:#1a1a1a;margin:0 0 4px;">{kind_regards}</p>
  <p style="font-size:9pt;font-weight:700;color:#0a0a0a;margin:0;">{company_name}</p>
</div>
</body>
</html>"""

    # ── Plain-text body ──────────────────────────────────────────────────────
    plain_body = "\n".join([
        lessee_name,
        "",
        t["plain_idx_intro"].format(property=property_label),
        "",
        t["plain_idx_index"].format(index=index_label),
        t["plain_idx_old_rent"].format(old_rent=fmt_old),
        t["plain_idx_new_rent"].format(new_rent=fmt_new),
        t["plain_idx_effective"].format(date=effective_str),
        "",
        closing,
        "",
        kind_regards,
        company_name,
    ])

    send_kwargs: dict = {
        "from": app_settings.INVOICE_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": plain_body,
    }
    if reply_to:
        send_kwargs["reply_to"] = reply_to

    resend.Emails.send(send_kwargs)
