from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import Invoice, Payment, User
from schemas import PaymentCreate, PaymentRead

router = APIRouter(prefix="/payments", tags=["payments"])


def _get_or_404(db: Session, payment_id: int, org_id: int) -> Payment:
    row = db.query(Payment).filter(Payment.id == payment_id, Payment.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    return row


@router.get("", response_model=List[PaymentRead])
def list_payments(
    invoice_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Payment]:
    q = db.query(Payment).filter(Payment.org_id == current_user.org_id)
    if invoice_id is not None:
        q = q.filter(Payment.invoice_id == invoice_id)
    return q.all()


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    return _get_or_404(db, payment_id, current_user.org_id)


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Payment:
    invoice = db.query(Invoice).filter(
        Invoice.id == payload.invoice_id,
        Invoice.org_id == current_user.org_id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    if invoice.invoice_status not in ("pending", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payments can only be recorded against pending or overdue invoices.",
        )

    row = Payment(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, payment_id, current_user.org_id)
    db.delete(row)
    db.commit()
