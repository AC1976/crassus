import hmac
import hashlib
import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models import Invoice

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")

# Map Resend event types to our internal email_delivery_status values.
# Only advance status; never downgrade (e.g. opened → delivered shouldn't
# overwrite opened, but that ordering doesn't occur in practice).
_STATUS_MAP: dict[str, str] = {
    "email.delivered": "delivered",
    "email.opened": "opened",
    "email.bounced": "bounced",
}

# Priority order — higher index wins if two events arrive out of order.
_PRIORITY = ["unsent", "sent", "delivered", "opened", "bounced"]


def _priority(status: str) -> int:
    try:
        return _PRIORITY.index(status)
    except ValueError:
        return -1


def _verify_signature(request_body: bytes, svix_id: str, svix_timestamp: str, svix_signature: str) -> bool:
    """Verify Resend webhook signature (Svix format)."""
    if not RESEND_WEBHOOK_SECRET:
        return True  # Skip verification in dev if secret not configured
    secret = RESEND_WEBHOOK_SECRET.removeprefix("whsec_")
    import base64
    secret_bytes = base64.b64decode(secret)
    signed_content = f"{svix_id}.{svix_timestamp}.{request_body.decode()}".encode()
    expected = hmac.new(key=secret_bytes, msg=signed_content, digestmod=hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected).decode()
    # Svix sends comma-separated list of "v1,<sig>" pairs
    sigs = [s.removeprefix("v1,") for s in svix_signature.split(" ")]
    return any(hmac.compare_digest(expected_b64, sig) for sig in sigs)


@router.post("/resend", status_code=status.HTTP_204_NO_CONTENT)
async def resend_webhook(request: Request, db: Session = Depends(get_db)) -> None:
    body = await request.body()

    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if RESEND_WEBHOOK_SECRET and not _verify_signature(body, svix_id, svix_timestamp, svix_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")

    try:
        import json
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.")

    event_type: str = payload.get("type", "")
    new_status = _STATUS_MAP.get(event_type)
    if not new_status:
        return  # Ignore unrecognised event types

    email_id: str | None = payload.get("data", {}).get("email_id")
    if not email_id:
        return

    invoice = db.query(Invoice).filter(Invoice.resend_email_id == email_id).first()
    if not invoice:
        return  # No matching invoice — silently ignore

    # Only update if the new status has equal or higher priority
    if _priority(new_status) >= _priority(invoice.email_delivery_status or "unsent"):
        invoice.email_delivery_status = new_status
        db.commit()
