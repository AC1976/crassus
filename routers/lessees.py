from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import Lessee, User
from schemas import LesseeCreate, LesseeRead, LesseeUpdate

router = APIRouter(prefix="/lessees", tags=["lessees"])


def _get_or_404(db: Session, lessee_id: int, org_id: int) -> Lessee:
    row = db.query(Lessee).filter(Lessee.id == lessee_id, Lessee.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lessee not found.")
    return row


@router.get("", response_model=List[LesseeRead])
def list_lessees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Lessee]:
    return db.query(Lessee).filter(Lessee.org_id == current_user.org_id).all()


@router.get("/{lessee_id}", response_model=LesseeRead)
def get_lessee(
    lessee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Lessee:
    return _get_or_404(db, lessee_id, current_user.org_id)


@router.post("", response_model=LesseeRead, status_code=status.HTTP_201_CREATED)
def create_lessee(
    payload: LesseeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Lessee:
    row = Lessee(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{lessee_id}", response_model=LesseeRead)
def update_lessee(
    lessee_id: int,
    payload: LesseeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Lessee:
    row = _get_or_404(db, lessee_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{lessee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lessee(
    lessee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, lessee_id, current_user.org_id)
    db.delete(row)
    db.commit()
