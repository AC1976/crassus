from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_user, require_role
from database import get_db
from models import Property, User
from schemas import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"])


def _get_or_404(db: Session, property_id: int, org_id: int) -> Property:
    row = db.query(Property).filter(Property.id == property_id, Property.org_id == org_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found.")
    return row


@router.get("", response_model=List[PropertyRead])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Property]:
    return db.query(Property).filter(Property.org_id == current_user.org_id).all()


@router.get("/{property_id}", response_model=PropertyRead)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Property:
    return _get_or_404(db, property_id, current_user.org_id)


@router.post("", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Property:
    row = Property(org_id=current_user.org_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner", "editor")),
) -> Property:
    row = _get_or_404(db, property_id, current_user.org_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("owner")),
) -> None:
    row = _get_or_404(db, property_id, current_user.org_id)
    db.delete(row)
    db.commit()
