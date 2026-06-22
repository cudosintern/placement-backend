"""
self_registration_api.py
========================
Module 2: Company Approval Master

Endpoints:
  POST /placement/company-registration/submit          - Company submits registration form
  GET  /placement/company-registration/list            - TPO views all registrations (filter by status)
  GET  /placement/company-registration/detail/{reg_id} - TPO views full record
  PUT  /placement/company-registration/approve         - TPO approves → creates plm_company row
  PUT  /placement/company-registration/reject          - TPO rejects with reason

Status codes:
  0 = PENDING   (submitted, awaiting TPO review)
  1 = APPROVED  (TPO approved → company_id FK filled → new row in plm_company)
  2 = REJECTED  (TPO rejected with reason in remarks)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from app.db.placement_models import PlacementCompany, PlacementCompanySelfRegistration
from app.db.models import Country, State, City
from app.api.v1.placement_module.company.self_registration_schema import (
    SelfRegCreate, SelfRegApprove, SelfRegReject
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: serialize a self-registration ORM object → dict
# ---------------------------------------------------------------------------
def _reg_to_dict(r: PlacementCompanySelfRegistration) -> dict:
    return {
        "reg_id":           r.reg_id,
        "company_id":       r.company_id,
        "company_name":     r.company_name,
        "company_type":     r.company_type,
        "industry":         r.industry,
        "website":          r.website,
        "email":            r.email,
        "phone":            r.phone,
        "address":          r.address,
        "city":             r.city,
        "state":            r.state,
        "country":          r.country,
        "pincode":          r.pincode,
        "contact_person":   r.contact_person,
        "contact_email":    r.contact_email,
        "contact_phone":    r.contact_phone,
        "description":      r.description,
        "status":           r.status,
        "status_label":     {0: "Pending", 1: "Approved", 2: "Rejected"}.get(r.status, "Unknown"),
        "reviewed_by":      r.reviewed_by,
        "review_date":      str(r.review_date) if r.review_date else None,
        "remarks":          r.remarks,
        "org_id":           r.org_id,
        "submitted_by":     r.submitted_by,
        "create_date":      str(r.create_date) if r.create_date else None,
        "modify_date":      str(r.modify_date) if r.modify_date else None,
    }


# ---------------------------------------------------------------------------
# 1. POST /submit — Company submits registration form (NO auth required)
# ---------------------------------------------------------------------------
@router.post("/submit")
def submit_registration(
    data: SelfRegCreate,
    db: Session = Depends(get_db),
    org_id: Optional[int] = Header(None),
):
    """
    Public endpoint — company HR fills and submits the registration form.
    Creates a new row in plm_company_self_registration with status=0 (PENDING).
    No auth token required.
    """
    try:
        resolved_org = org_id or 1

        # Duplicate check: same company_name + pending or approved already
        existing = db.query(PlacementCompanySelfRegistration).filter(
            PlacementCompanySelfRegistration.company_name == data.company_name.strip(),
            PlacementCompanySelfRegistration.org_id == resolved_org,
            PlacementCompanySelfRegistration.status.in_([0, 1]),   # PENDING or APPROVED
        ).first()
        if existing:
            return returnException(
                f"A registration for '{data.company_name}' is already "
                f"{'pending' if existing.status == 0 else 'approved'}."
            )

        reg = PlacementCompanySelfRegistration(
            company_name   = data.company_name.strip(),
            company_type   = data.company_type,
            industry       = data.industry,
            website        = data.website,
            email          = data.email,
            phone          = data.phone,
            address        = data.address,
            city           = data.city,
            state          = data.state,
            country        = data.country or "India",
            pincode        = data.pincode,
            contact_person = data.contact_person,
            contact_email  = data.contact_email,
            contact_phone  = data.contact_phone,
            description    = data.description,
            status         = 0,          # PENDING
            org_id         = resolved_org,
            create_date    = datetime.now(),
        )
        db.add(reg)
        db.commit()
        db.refresh(reg)
        return returnSuccess(
            _reg_to_dict(reg),
            message="Registration submitted successfully. Awaiting TPO approval.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 2. GET /list — TPO views all registrations (filter by status)
# ---------------------------------------------------------------------------
@router.get("/list")
def get_registration_list(
    status: Optional[int] = Query(None, description="0=Pending, 1=Approved, 2=Rejected"),
    search: Optional[str] = Query(None, description="Search by company name"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    TPO sees all registration requests.
    Optional filters: status (0/1/2), search (company name).
    """
    try:
        resolved_org = org_id or 1
        query = db.query(PlacementCompanySelfRegistration).filter(
            PlacementCompanySelfRegistration.org_id == resolved_org
        )

        if status is not None:
            query = query.filter(PlacementCompanySelfRegistration.status == status)
        if search:
            query = query.filter(
                PlacementCompanySelfRegistration.company_name.ilike(f"%{search}%")
            )

        records = query.order_by(PlacementCompanySelfRegistration.create_date.desc()).all()
        data = [_reg_to_dict(r) for r in records]
        return returnSuccess(data, message=f"{len(data)} registration(s) found")
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 3. GET /detail/{reg_id} — TPO views single record details
# ---------------------------------------------------------------------------
@router.get("/detail/{reg_id}")
def get_registration_detail(
    reg_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """TPO views full details of a single registration request."""
    try:
        resolved_org = org_id or 1
        reg = db.query(PlacementCompanySelfRegistration).filter(
            PlacementCompanySelfRegistration.reg_id == reg_id,
            PlacementCompanySelfRegistration.org_id == resolved_org,
        ).first()

        if not reg:
            return returnException(f"Registration with ID {reg_id} not found.")
        return returnSuccess(_reg_to_dict(reg))
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 4. PUT /approve — TPO approves → creates plm_company row
# ---------------------------------------------------------------------------
@router.put("/approve")
def approve_registration(
    payload: SelfRegApprove,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    TPO approves a registration:
    1. Validates reg exists and is still PENDING (status=0)
    2. Creates a new PlacementCompany row from the registration data
    3. Updates registration: status=1, company_id=<new id>, reviewed_by, review_date
    Returns both the updated registration record AND the new company record.
    """
    try:
        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        # Fetch the registration
        reg = db.query(PlacementCompanySelfRegistration).filter(
            PlacementCompanySelfRegistration.reg_id == payload.reg_id,
            PlacementCompanySelfRegistration.org_id == resolved_org,
        ).first()

        if not reg:
            return returnException(f"Registration with ID {payload.reg_id} not found.")
        if reg.status != 0:
            label = {1: "already approved", 2: "already rejected"}.get(reg.status, "already processed")
            return returnException(f"Registration is {label}. Only PENDING registrations can be approved.")

        # Check if company name already exists in plm_company
        dup = db.query(PlacementCompany).filter(
            PlacementCompany.company_name == reg.company_name,
            PlacementCompany.org_id == resolved_org,
        ).first()
        if dup:
            return returnException(
                f"A company named '{reg.company_name}' already exists in company master (ID: {dup.company_id}). "
                "Cannot create duplicate."
            )

        # Create new PlacementCompany row from registration data
        new_company = PlacementCompany(
            company_name       = reg.company_name,
            company_type       = reg.company_type,
            industry           = reg.industry,
            website            = reg.website,
            email              = reg.email,
            phone              = reg.phone,
            address            = reg.address,
            city               = reg.city,
            state              = reg.state,
            country            = reg.country or "India",
            pincode            = reg.pincode,
            contact_person     = reg.contact_person,
            contact_email      = reg.contact_email,
            contact_phone      = reg.contact_phone,
            description        = reg.description,
            status             = 1,           # Active
            org_id             = resolved_org,
            created_by         = user_id,
            create_date        = datetime.now(),
        )
        db.add(new_company)
        db.flush()   # get new_company.company_id without full commit

        # Update registration record
        reg.status      = 1                    # APPROVED
        reg.company_id  = new_company.company_id
        reg.reviewed_by = user_id
        reg.review_date = datetime.now()
        reg.remarks     = payload.remarks

        db.commit()
        db.refresh(reg)
        db.refresh(new_company)

        return returnSuccess(
            {
                "registration": _reg_to_dict(reg),
                "company": {
                    "company_id":   new_company.company_id,
                    "company_name": new_company.company_name,
                    "status":       new_company.status,
                },
            },
            message=f"Registration approved. Company '{new_company.company_name}' added to company master (ID: {new_company.company_id}).",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 5. PUT /reject — TPO rejects with a mandatory reason
# ---------------------------------------------------------------------------
@router.put("/reject")
def reject_registration(
    payload: SelfRegReject,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    TPO rejects a registration:
    1. Validates reg exists and is still PENDING (status=0)
    2. Updates registration: status=2, remarks=reason, reviewed_by, review_date
    NO row is created in plm_company.
    """
    try:
        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        reg = db.query(PlacementCompanySelfRegistration).filter(
            PlacementCompanySelfRegistration.reg_id == payload.reg_id,
            PlacementCompanySelfRegistration.org_id == resolved_org,
        ).first()

        if not reg:
            return returnException(f"Registration with ID {payload.reg_id} not found.")
        if reg.status != 0:
            label = {1: "already approved", 2: "already rejected"}.get(reg.status, "already processed")
            return returnException(f"Registration is {label}. Only PENDING registrations can be rejected.")

        # Update registration record
        reg.status      = 2                    # REJECTED
        reg.reviewed_by = user_id
        reg.review_date = datetime.now()
        reg.remarks     = payload.remarks      # mandatory reason

        db.commit()
        db.refresh(reg)

        return returnSuccess(
            _reg_to_dict(reg),
            message="Registration rejected.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 6. GET /countries — Get all countries
# ---------------------------------------------------------------------------
@router.get("/countries")
def get_countries(db: Session = Depends(get_db)):
    """Public endpoint to fetch all countries."""
    try:
        countries = db.query(Country).order_by(Country.name.asc()).all()
        data = [
            {"country_id": c.country_id, "name": c.name, "sortname": c.sortname}
            for c in countries
        ]
        return returnSuccess(data, message="Countries retrieved successfully")
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 7. GET /states — Get states filtered by country_id or country_name
# ---------------------------------------------------------------------------
@router.get("/states")
def get_states(
    country_id: Optional[int] = None,
    country_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Public endpoint to fetch states by country filter."""
    try:
        query = db.query(State)
        if country_id is not None:
            query = query.filter(State.country_id == country_id)
        elif country_name:
            country = db.query(Country).filter(Country.name == country_name).first()
            if country:
                query = query.filter(State.country_id == country.country_id)
            else:
                return returnSuccess([], message="Country not found")
        
        states = query.order_by(State.name.asc()).all()
        data = [
            {"state_id": s.state_id, "name": s.name, "country_id": s.country_id}
            for s in states
        ]
        return returnSuccess(data, message="States retrieved successfully")
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 8. GET /cities — Get cities filtered by state_id or state_name
# ---------------------------------------------------------------------------
@router.get("/cities")
def get_cities(
    state_id: Optional[int] = None,
    state_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Public endpoint to fetch cities by state filter."""
    try:
        query = db.query(City)
        if state_id is not None:
            query = query.filter(City.state_id == state_id)
        elif state_name:
            state = db.query(State).filter(State.name == state_name).first()
            if state:
                query = query.filter(City.state_id == state.state_id)
            else:
                return returnSuccess([], message="State not found")
        
        cities = query.order_by(City.name.asc()).all()
        data = [
            {"city_id": c.city_id, "name": c.name, "state_id": c.state_id}
            for c in cities
        ]
        return returnSuccess(data, message="Cities retrieved successfully")
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 9. GET /check-pincode — Check if 'pincode' column is in self-registration table
# ---------------------------------------------------------------------------
@router.get("/check-pincode")
def check_pincode_availability(db: Session = Depends(get_db)):
    """Public endpoint to check if pincode column exists in self-registration table."""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        columns = [col["name"] for col in inspector.get_columns("plm_company_self_registration")]
        pincode_available = "pincode" in columns
        return returnSuccess({"pincode_available": pincode_available})
    except Exception as e:
        return returnException(str(e))
