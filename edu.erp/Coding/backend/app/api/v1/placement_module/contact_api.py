from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import IEMSPlacementContact, IEMSUserDesignation
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from app.api.v1.placement_module.contact_schema import ContactCreate, ContactUpdate

router = APIRouter()


# ─── Helper ────────────────────────────────────────────────────────────────────

def _contact_to_dict(c: IEMSPlacementContact) -> dict:
    return {
        "contact_id": c.contact_id,
        "company_id": c.company_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "phone": c.phone,
        "designation_id": c.designation_id,
        "designation_name": c.designation.designation_name if c.designation else None,
        "is_primary": c.is_primary,
        "status": c.status,
        "created_date": c.created_date,
        "modified_date": c.modified_date,
    }


# ─── 1. Get Contact List (with optional company_id filter) ─────────────────────

@router.get("/get_contact_list")
def get_contact_list(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(IEMSPlacementContact).filter(
            IEMSPlacementContact.org_id == org_id,
            IEMSPlacementContact.status == 1,
        )
        if company_id is not None:
            query = query.filter(IEMSPlacementContact.company_id == company_id)

        contacts = query.order_by(
            IEMSPlacementContact.is_primary.desc(),
            IEMSPlacementContact.first_name,
        ).all()

        return returnSuccess([_contact_to_dict(c) for c in contacts])
    except Exception as e:
        return returnException(str(e))


# ─── 2. Add Contact ────────────────────────────────────────────────────────────

@router.post("/add_contact")
def add_contact(
    data: ContactCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # Primary contact logic: unset existing primary for this company
        if data.is_primary == 1:
            db.query(IEMSPlacementContact).filter(
                IEMSPlacementContact.company_id == data.company_id,
                IEMSPlacementContact.org_id == org_id,
                IEMSPlacementContact.is_primary == 1,
            ).update({"is_primary": 0, "modified_by": user_id, "modified_date": datetime.now()})

        contact = IEMSPlacementContact(
            company_id=data.company_id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip() if data.last_name else None,
            email=data.email.strip() if data.email else None,
            phone=data.phone.strip() if data.phone else None,
            designation_id=data.designation_id,
            is_primary=data.is_primary if data.is_primary is not None else 0,
            status=data.status if data.status is not None else 1,
            org_id=org_id,
            created_by=user_id,
            created_date=datetime.now(),
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return returnSuccess(_contact_to_dict(contact))
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 3. Update Contact ─────────────────────────────────────────────────────────

@router.put("/update_contact")
def update_contact(
    data: ContactUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        contact = db.query(IEMSPlacementContact).filter(
            IEMSPlacementContact.contact_id == data.contact_id,
            IEMSPlacementContact.org_id == org_id,
        ).first()

        if not contact:
            return returnException("Contact not found.")

        # Primary contact logic: unset existing primary for the target company
        target_company_id = data.company_id if data.company_id is not None else contact.company_id
        if data.is_primary == 1:
            db.query(IEMSPlacementContact).filter(
                IEMSPlacementContact.company_id == target_company_id,
                IEMSPlacementContact.org_id == org_id,
                IEMSPlacementContact.is_primary == 1,
                IEMSPlacementContact.contact_id != data.contact_id,
            ).update({"is_primary": 0, "modified_by": user_id, "modified_date": datetime.now()})

        # Apply updates only for fields provided
        if data.company_id is not None:
            contact.company_id = data.company_id
        if data.first_name is not None:
            contact.first_name = data.first_name.strip()
        if data.last_name is not None:
            contact.last_name = data.last_name.strip()
        if data.email is not None:
            contact.email = data.email.strip()
        if data.phone is not None:
            contact.phone = data.phone.strip()
        if data.designation_id is not None:
            contact.designation_id = data.designation_id
        if data.is_primary is not None:
            contact.is_primary = data.is_primary
        if data.status is not None:
            contact.status = data.status

        contact.modified_by = user_id
        contact.modified_date = datetime.now()

        db.commit()
        db.refresh(contact)
        return returnSuccess(_contact_to_dict(contact))
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 4. Get Designations ───────────────────────────────────────────────────────

@router.get("/get_designations")
def get_designations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        designations = db.query(IEMSUserDesignation).order_by(
            IEMSUserDesignation.designation_name
        ).all()

        result = [
            {
                "designation_id": d.designation_id,
                "designation_name": d.designation_name,
                "designation_description": d.designation_description,
            }
            for d in designations
        ]
        return returnSuccess(result)
    except Exception as e:
        return returnException(str(e))
