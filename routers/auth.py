import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import resend
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from config import settings
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)
from database import get_db
from models import Invitation, Organisation, User
from schemas import (
    AcceptInviteRequest,
    InviteRequest,
    InviteResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)


# ---------------------------------------------------------------------------
# Extra response schemas (team management)
# ---------------------------------------------------------------------------

class TeamMemberRead(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class PendingInviteRead(BaseModel):
    id: int
    invited_email: str
    role: str
    expires_at: datetime


class RoleUpdateRequest(BaseModel):
    role: str  # editor | viewer (owner cannot be assigned via this endpoint)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_MINUTES = 60
RESET_TOKEN_TYPE = "password_reset"


def _create_reset_token(user_id: int) -> str:
    from jose import jwt as _jwt
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "type": RESET_TOKEN_TYPE, "exp": expire}
    return _jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _verify_reset_token(token: str) -> int:
    """Returns user_id if valid, raises HTTPException otherwise."""
    from jose import jwt as _jwt, JWTError
    try:
        payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != RESET_TOKEN_TYPE:
            raise ValueError("wrong token type")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

INVITE_EXPIRE_HOURS = 72


def _configure_resend() -> None:
    resend.api_key = settings.RESEND_API_KEY


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    org = Organisation(name=payload.org_name)
    db.add(org)
    db.flush()  # get org.id before committing

    user = User(
        org_id=org.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")

    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    return TokenResponse(access_token=token)


@router.post("/invite", response_model=InviteResponse)
def invite_user(
    payload: InviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> dict:
    existing_user = (
        db.query(User)
        .filter(User.email == payload.email, User.org_id == current_user.org_id)
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already belongs to this organisation.")

    existing_invite = (
        db.query(Invitation)
        .filter(
            Invitation.invited_email == payload.email,
            Invitation.org_id == current_user.org_id,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if existing_invite:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A pending invite already exists for this email.")

    token = secrets.token_urlsafe(32)
    invite = Invitation(
        org_id=current_user.org_id,
        invited_email=payload.email,
        role=payload.role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=INVITE_EXPIRE_HOURS),
    )
    db.add(invite)
    db.commit()

    # Send invite email via Resend
    accept_url = f"{settings.APP_BASE_URL}/accept-invite?token={token}"
    to_email = settings.DEV_EMAIL or payload.email
    role_label = payload.role.capitalize()
    org = db.get(Organisation, current_user.org_id)
    org_name = org.name if org else "Crassus"

    if settings.RESEND_API_KEY:
        _configure_resend()
        invite_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:32px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;">

        <tr><td style="height:4px;background:#16a34a;"></td></tr>

        <tr><td style="padding:36px 40px 28px;">

          <p style="margin:0 0 20px;font-size:15px;color:#111;">Hi,</p>

          <p style="margin:0 0 24px;font-size:14px;color:#444;line-height:1.7;">
            <strong>{current_user.email}</strong> has invited you to join
            <strong>{org_name}</strong> on <strong>Crassus Property Management</strong>
            as <strong>{role_label}</strong>.
          </p>

          <!-- CTA button -->
          <table cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="background:#16a34a;border-radius:6px;">
                <a href="{accept_url}"
                   style="display:inline-block;padding:12px 28px;font-size:14px;font-weight:700;
                          color:#ffffff;text-decoration:none;letter-spacing:0.2px;">
                  Accept Invitation
                </a>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px;font-size:13px;color:#888;">Or copy this link into your browser:</p>
          <p style="margin:0 0 24px;font-size:12px;color:#555;word-break:break-all;
                    background:#f5f5f5;border-radius:4px;padding:10px 12px;">
            {accept_url}
          </p>

          <p style="margin:0 0 28px;font-size:13px;color:#888;">
            This invitation expires in 72 hours. If you did not expect this invitation, you can safely ignore this email.
          </p>

          <p style="margin:0;font-size:14px;color:#444;">
            Kind regards,<br>
            <strong style="color:#111;">The Crassus Team</strong>
          </p>

        </td></tr>

        <tr><td style="padding:16px 40px;background:#f8f8f8;border-top:1px solid #e8e8e8;
                       font-size:11px;color:#999;text-align:center;line-height:1.8;">
          Crassus Property Management &nbsp;·&nbsp; crassus.pro
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
        resend.Emails.send({
            "from": settings.INVITE_SENDER_EMAIL,
            "to": to_email,
            "subject": f"You've been invited to join {org_name} on Crassus",
            "html": invite_html,
        })

    return {"invite_token": token, "invited_email": payload.email, "role": payload.role}


@router.post("/accept-invite", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def accept_invite(payload: AcceptInviteRequest, db: Session = Depends(get_db)) -> TokenResponse:
    invite = (
        db.query(Invitation)
        .filter(Invitation.token == payload.token, Invitation.accepted_at.is_(None))
        .first()
    )
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or already used invite token.")
    if invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite token has expired.")

    existing = db.query(User).filter(User.email == invite.invited_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

    user = User(
        org_id=invite.org_id,
        email=invite.invited_email,
        hashed_password=hash_password(payload.password),
        role=invite.role,
    )
    db.add(user)
    invite.accepted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    return TokenResponse(access_token=token)


@router.get("/team", response_model=List[TeamMemberRead])
def list_team(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[User]:
    return (
        db.query(User)
        .filter(User.org_id == current_user.org_id)
        .order_by(User.id)
        .all()
    )


@router.patch("/team/{user_id}/role", response_model=TeamMemberRead)
def update_member_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> User:
    if payload.role not in ("editor", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be 'editor' or 'viewer'.")
    target = db.query(User).filter(User.id == user_id, User.org_id == current_user.org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot change the owner's role.")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target


@router.delete("/team/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    target = db.query(User).filter(User.id == user_id, User.org_id == current_user.org_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner.")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself.")
    db.delete(target)
    db.commit()


@router.get("/invitations", response_model=List[PendingInviteRead])
def list_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> List[Invitation]:
    return (
        db.query(Invitation)
        .filter(
            Invitation.org_id == current_user.org_id,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(timezone.utc),
        )
        .order_by(Invitation.expires_at.desc())
        .all()
    )


@router.delete("/invitations/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invitation(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    invite = db.query(Invitation).filter(
        Invitation.id == invite_id,
        Invitation.org_id == current_user.org_id,
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    db.delete(invite)
    db.commit()


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    """Send a password-reset link. Always returns 204 to avoid user enumeration."""
    user = db.query(User).filter(User.email == payload.email, User.is_active == True).first()  # noqa: E712
    if not user:
        return  # silently succeed — don't reveal whether the email exists

    reset_token = _create_reset_token(user.id)
    reset_url = f"{settings.APP_BASE_URL}/reset-password?token={reset_token}"
    to_email = settings.DEV_EMAIL or payload.email

    if settings.RESEND_API_KEY:
        _configure_resend()
        reset_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:32px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;">

        <tr><td style="height:4px;background:#16a34a;"></td></tr>

        <tr><td style="padding:36px 40px 28px;">

          <p style="margin:0 0 20px;font-size:15px;color:#111;">Hi,</p>

          <p style="margin:0 0 24px;font-size:14px;color:#444;line-height:1.7;">
            We received a request to reset the password for your
            <strong>Crassus Property Management</strong> account.
            Click the button below to choose a new password.
          </p>

          <!-- CTA button -->
          <table cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="background:#16a34a;border-radius:6px;">
                <a href="{reset_url}"
                   style="display:inline-block;padding:12px 28px;font-size:14px;font-weight:700;
                          color:#ffffff;text-decoration:none;letter-spacing:0.2px;">
                  Reset Password
                </a>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px;font-size:13px;color:#888;">Or copy this link into your browser:</p>
          <p style="margin:0 0 24px;font-size:12px;color:#555;word-break:break-all;
                    background:#f5f5f5;border-radius:4px;padding:10px 12px;">
            {reset_url}
          </p>

          <p style="margin:0 0 28px;font-size:13px;color:#888;">
            This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes.
            If you did not request a password reset, you can safely ignore this email —
            your account has not been changed.
          </p>

          <p style="margin:0;font-size:14px;color:#444;">
            Kind regards,<br>
            <strong style="color:#111;">The Crassus Team</strong>
          </p>

        </td></tr>

        <tr><td style="padding:16px 40px;background:#f8f8f8;border-top:1px solid #e8e8e8;
                       font-size:11px;color:#999;text-align:center;line-height:1.8;">
          Crassus Property Management &nbsp;·&nbsp; crassus.pro
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
        resend.Emails.send({
            "from": settings.INVITE_SENDER_EMAIL,
            "to": to_email,
            "subject": "Reset your Crassus password",
            "html": reset_html,
        })


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters.")
    user_id = _verify_reset_token(payload.token)
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found or inactive.")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()


@router.get("/me", response_model=UserRead)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    org = db.get(Organisation, current_user.org_id)
    return {
        "id": current_user.id,
        "org_id": current_user.org_id,
        "org_name": org.name if org else "",
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }
