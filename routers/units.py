from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import Property, Unit, User
from schemas import UnitCreate, UnitRead, UnitUpdate

router = APIRouter(prefix="/units", tags=["units"])


def _get_or_404(db: Session, unit_id: int, org_id: int) -> Unit:
    row = db.query(Unit).filter(Unit.id == unit_id, Unit.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
    return row


def _assert_property_owned(db: Session, property_id: int, org_id: int) -> None:
    prop = db.query(Property).filter(Property.id == property_id, Property.org_id == org_id).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")


@router.get("", response_model=List[UnitRead])
def list_units(
    property_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Unit]:
    q = db.query(Unit).filter(Unit.org_id == current_user.org_id)
    if property_id is not None:
        q = q.filter(Unit.property_id == property_id)
    return q.all()


@router.get("/{unit_id}", response_model=UnitRead)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Unit:
    return _get_or_404(db, unit_id, current_user.org_id)


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Unit:
    _assert_property_owned(db, payload.property_id, current_user.org_id)
    row = Unit(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{unit_id}", response_model=UnitRead)
def update_unit(
    unit_id: int,
    payload: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Unit:
    row = _get_or_404(db, unit_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, unit_id, current_user.org_id)
    db.delete(row)
    db.commit()
