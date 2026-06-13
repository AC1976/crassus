from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import Expense, Property, User
from schemas import ExpenseCreate, ExpenseRead, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _get_or_404(db: Session, expense_id: int, org_id: int) -> Expense:
    row = db.query(Expense).filter(Expense.id == expense_id, Expense.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found.")
    return row


@router.get("", response_model=List[ExpenseRead])
def list_expenses(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Expense]:
    q = db.query(Expense).filter(Expense.org_id == current_user.org_id)
    if property_id is not None:
        q = q.filter(Expense.property_id == property_id)
    return q.all()


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Expense:
    return _get_or_404(db, expense_id, current_user.org_id)


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Expense:
    prop = db.query(Property).filter(
        Property.id == payload.property_id,
        Property.org_id == current_user.org_id,
    ).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")

    row = Expense(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Expense:
    row = _get_or_404(db, expense_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.post("/{expense_id}/pay", response_model=ExpenseRead)
def mark_expense_paid(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Expense:
    row = _get_or_404(db, expense_id, current_user.org_id)
    row.is_paid = True
    row.paid_date = date.today()
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, expense_id, current_user.org_id)
    db.delete(row)
    db.commit()
