"""Platform admin endpoints — visible only to is_admin users or ADMIN_EMAILS."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import get_db
from models import Organisation, Property, User

router = APIRouter(prefix="/admin", tags=["admin"])

TRIAL_DAYS = settings.TRIAL_DAYS


# ---------------------------------------------------------------------------
# Admin auth dependency
# ---------------------------------------------------------------------------

def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not (current_user.is_admin or current_user.email.lower() in settings.ADMIN_EMAILS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------

class OrgRow(BaseModel):
    org_id: int
    org_name: str
    owner_email: str
    created_at: datetime
    trial_ends_at: date
    days_remaining: int          # negative = expired
    subscription_status: str     # trial | active | churned | exempt
    admin_notes: Optional[str]
    property_count: int
    user_count: int
    suggested_plan: str          # Starter | Growth | Portfolio

    model_config = {"from_attributes": True}


class OrgUpdateRequest(BaseModel):
    subscription_status: Optional[str] = None   # trial | active | churned | exempt
    admin_notes: Optional[str] = None


class ContactRequest(BaseModel):
    subject: str
    body: str   # plain-text or simple HTML


class AdminMeResponse(BaseModel):
    is_admin: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _suggested_plan(property_count: int) -> str:
    if property_count <= 3:
        return "Starter"
    if property_count <= 10:
        return "Growth"
    return "Portfolio"


def _build_org_row(org: Organisation, db: Session) -> OrgRow:
    owner = (
        db.query(User)
        .filter(User.org_id == org.id, User.role == "owner")
        .first()
    )
    owner_email = owner.email if owner else "—"

    property_count = (
        db.query(func.count(Property.id))
        .filter(Property.org_id == org.id)
        .scalar() or 0
    )
    user_count = (
        db.query(func.count(User.id))
        .filter(User.org_id == org.id, User.is_active == True)  # noqa: E712
        .scalar() or 0
    )

    created_date = org.created_at.date() if isinstance(org.created_at, datetime) else org.created_at
    trial_ends = created_date + timedelta(days=TRIAL_DAYS)
    days_remaining = (trial_ends - date.today()).days

    return OrgRow(
        org_id=org.id,
        org_name=org.name,
        owner_email=owner_email,
        created_at=org.created_at,
        trial_ends_at=trial_ends,
        days_remaining=days_remaining,
        subscription_status=org.subscription_status or "trial",
        admin_notes=org.admin_notes,
        property_count=property_count,
        user_count=user_count,
        suggested_plan=_suggested_plan(property_count),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=AdminMeResponse)
def admin_me(current_user: User = Depends(get_current_user)) -> AdminMeResponse:
    """Lightweight check — returns whether the caller has admin rights."""
    is_admin = current_user.is_admin or current_user.email.lower() in settings.ADMIN_EMAILS
    return AdminMeResponse(is_admin=is_admin)


@router.get("/orgs", response_model=List[OrgRow])
def list_orgs(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> List[OrgRow]:
    orgs = db.query(Organisation).order_by(Organisation.created_at.desc()).all()
    return [_build_org_row(org, db) for org in orgs]


@router.patch("/orgs/{org_id}", response_model=OrgRow)
def update_org(
    org_id: int,
    payload: OrgUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> OrgRow:
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    valid_statuses = {"trial", "active", "churned", "exempt"}
    if payload.subscription_status is not None:
        if payload.subscription_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}.")
        org.subscription_status = payload.subscription_status
    if payload.admin_notes is not None:
        org.admin_notes = payload.admin_notes

    db.commit()
    db.refresh(org)
    return _build_org_row(org, db)


@router.post("/orgs/{org_id}/contact", status_code=status.HTTP_204_NO_CONTENT)
def contact_org(
    org_id: int,
    payload: ContactRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> None:
    org = db.get(Organisation, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    owner = db.query(User).filter(User.org_id == org_id, User.role == "owner").first()
    if not owner:
        raise HTTPException(status_code=404, detail="No owner found for this organisation.")

    to_email = settings.DEV_EMAIL or owner.email

    if not settings.RESEND_API_KEY:
        raise HTTPException(status_code=503, detail="Email sending is not configured (missing RESEND_API_KEY).")

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.INVITE_SENDER_EMAIL,
        "to": to_email,
        "subject": payload.subject,
        "html": payload.body.replace("\n", "<br/>") if "<" not in payload.body else payload.body,
    })
