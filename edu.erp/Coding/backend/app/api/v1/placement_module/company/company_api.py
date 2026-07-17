"""
Placement Company API
=====================
Endpoints:
  GET  /placement/company/list              - Get all companies (with optional filters)
  GET  /placement/company/detail/{id}       - Get single company details
  POST /placement/company/save              - Add new company
  PUT  /placement/company/save              - Update existing company (pass company_id in body)
  PUT  /placement/company/activate          - Activate a company  (status → 1)
  PUT  /placement/company/deactivate        - Deactivate a company (status → 0)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from app.db.placement_models import PlacementCompany, PlacementDrive, PlacementOffer
from app.db.models import PLMStudentProfile, IEMStudents, Country, State, City, IEMSUserDesignation
from app.api.v1.placement_module.company.company_schema import CompanyCreate, CompanyStatusUpdate

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: serialize a PlacementCompany ORM object → dict
# ---------------------------------------------------------------------------
def _company_to_dict(c: PlacementCompany, db: Session) -> dict:
    country_name = ""
    state_name = ""
    city_name = ""
    designation_name = ""

    if c.country:
        if c.country.isdigit():
            c_obj = db.query(Country).filter(Country.country_id == int(c.country)).first()
            if c_obj:
                country_name = c_obj.name
        else:
            country_name = c.country

    if c.state:
        if c.state.isdigit():
            s_obj = db.query(State).filter(State.state_id == int(c.state)).first()
            if s_obj:
                state_name = s_obj.name
        else:
            state_name = c.state

    if c.city:
        if c.city.isdigit():
            ct_obj = db.query(City).filter(City.city_id == int(c.city)).first()
            if ct_obj:
                city_name = ct_obj.name
        else:
            city_name = c.city

    if c.contact_designation:
        if c.contact_designation.isdigit():
            d_obj = db.query(IEMSUserDesignation).filter(IEMSUserDesignation.designation_id == int(c.contact_designation)).first()
            if d_obj:
                designation_name = d_obj.designation_name
        else:
            designation_name = c.contact_designation

    return {
        "company_id": c.company_id,
        "company_name": c.company_name,
        "company_type": c.company_type,
        "industry": c.industry,
        "website": c.website,
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "city": c.city,
        "state": c.state,
        "country": c.country,
        "pincode": c.pincode,
        "contact_person": c.contact_person,
        "contact_designation": c.contact_designation,
        "contact_phone": c.contact_phone,
        "contact_email": c.contact_email,
        "description": c.description,
        "logo_path": c.logo_path,
        "status": c.status,
        "org_id": c.org_id,
        "created_by": c.created_by,
        "modified_by": c.modified_by,
        "create_date": str(c.create_date) if c.create_date else None,
        "modify_date": str(c.modify_date) if c.modify_date else None,
        "country_name": country_name,
        "state_name": state_name,
        "city_name": city_name,
        "contact_designation_name": designation_name,
    }


# ---------------------------------------------------------------------------
# 1. Get Company List
# ---------------------------------------------------------------------------
@router.get("/list")
def get_company_list(
    status: Optional[int] = Query(None, description="Filter by status: 1=Active, 0=Inactive"),
    search: Optional[str] = Query(None, description="Search by company name"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Get all companies.
    Optional query params:
      - status (1/0) – filter active/inactive
      - search – partial match on company name
    """
    try:
        query = db.query(PlacementCompany)

        if org_id:
            query = query.filter(PlacementCompany.org_id == org_id)
        if status is not None:
            query = query.filter(PlacementCompany.status == status)
        if search:
            query = query.filter(
                PlacementCompany.company_name.ilike(f"%{search}%")
            )

        companies = query.order_by(PlacementCompany.company_name).all()
        print("Companies found:", companies)
        data = [_company_to_dict(c, db) for c in companies]
        return returnSuccess(data, message=f"{len(data)} company(ies) found")
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 2. Get Company Details by ID
# ---------------------------------------------------------------------------
@router.get("/detail/{company_id}")
def get_company_detail(
    
    company_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Get a single company record by company_id."""
    try:
        company = db.query(PlacementCompany).filter(
            PlacementCompany.company_id == company_id
        ).first()
        if not company:
            return returnException(f"Company with ID {company_id} not found.")

        drives = db.query(PlacementDrive).filter(
            PlacementDrive.company_id == company_id
        ).all()

        drives_data = []
        for d in drives:
            offers = db.query(
                PlacementOffer.offer_id,
                PlacementOffer.role,
                PlacementOffer.ctc,
                PlacementOffer.status,
                IEMStudents.name.label("student_name"),
                IEMStudents.usno.label("usn")
            ).join(
                PLMStudentProfile, PLMStudentProfile.profile_id == PlacementOffer.profile_id
            ).join(
                IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id
            ).filter(
                PlacementOffer.drive_id == d.drive_id
            ).all()

            drives_data.append({
                "drive_id": d.drive_id,
                "drive_name": d.drive_name,
                "academic_year": str(d.create_date.year) if d.create_date else "2026",
                "status": d.status,
                "students_passed": [
                    {
                        "offer_id": o.offer_id,
                        "student_name": o.student_name,
                        "usn": o.usn,
                        "role": o.role,
                        "ctc": str(o.ctc) if o.ctc else "0.0",
                        "status": o.status
                    }
                    for o in offers
                ]
            })

        company_dict = _company_to_dict(company, db)
        company_dict["drives"] = drives_data
        return returnSuccess(company_dict)
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 3. Add New Company
# ---------------------------------------------------------------------------
@router.post("/save")
def add_company(
    company_data: CompanyCreate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Add a new company.
    Do NOT pass company_id (or set it to null) in the request body.
    """
    try:
        if company_data.company_id:  # treat None and 0 both as "no ID provided"
            return returnException(
                "For adding a new company, do not provide company_id. "
                "Use PUT /save to update an existing company."
            )

        # Duplicate name check within the same org
        resolved_org = org_id or 1
        existing = db.query(PlacementCompany).filter(
            PlacementCompany.company_name == company_data.company_name.strip(),
            PlacementCompany.org_id == resolved_org,
        ).first()
        if existing:
            return returnException(
                f"A company named '{company_data.company_name}' already exists."
            )

        user_id = current_user.get("user_id", 1)
        new_company = PlacementCompany(
            company_name=company_data.company_name.strip(),
            company_type=company_data.company_type,
            industry=company_data.industry,
            website=company_data.website,
            email=company_data.email,
            phone=company_data.phone,
            address=company_data.address,
            city=company_data.city,
            state=company_data.state,
            country=company_data.country or "India",
            pincode=company_data.pincode,
            contact_person=company_data.contact_person,
            contact_designation=company_data.contact_designation,
            contact_phone=company_data.contact_phone,
            contact_email=company_data.contact_email,
            description=company_data.description,
            status=1,
            org_id=resolved_org,
            created_by=user_id,
            create_date=datetime.now(),
        )
        db.add(new_company)
        db.commit()
        db.refresh(new_company)

        # Also create a primary contact in plm_company_contact
        if new_company.contact_person:
            from app.db.placement_models import PLMCompanyContact
            primary_contact = PLMCompanyContact(
                company_id=new_company.company_id,
                name=new_company.contact_person,
                designation=new_company.contact_designation,
                email=new_company.contact_email,
                phone=new_company.contact_phone,
                is_primary=1,
                is_active=1
            )
            db.add(primary_contact)
            db.commit()

        return returnSuccess(
            _company_to_dict(new_company, db),
            message="Company added successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 4. Update Existing Company
# ---------------------------------------------------------------------------
@router.put("/save")
def update_company(
    company_data: CompanyCreate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Update an existing company.
    company_id is REQUIRED in the request body.
    """
    try:
        if not company_data.company_id:
            return returnException(
                "company_id is required for update. "
                "Use POST /save to add a new company."
            )

        resolved_org = org_id or 1
        company = db.query(PlacementCompany).filter(
            PlacementCompany.company_id == company_data.company_id,
            PlacementCompany.org_id == resolved_org,
        ).first()
        if not company:
            return returnException(
                f"Company with ID {company_data.company_id} not found."
            )

        # Duplicate name check (exclude self)
        dup = db.query(PlacementCompany).filter(
            PlacementCompany.company_name == company_data.company_name.strip(),
            PlacementCompany.org_id == resolved_org,
            PlacementCompany.company_id != company_data.company_id,
        ).first()
        if dup:
            return returnException(
                f"Another company named '{company_data.company_name}' already exists."
            )

        user_id = current_user.get("user_id", 1)
        company.company_name = company_data.company_name.strip()
        company.company_type = company_data.company_type
        company.industry = company_data.industry
        company.website = company_data.website
        company.email = company_data.email
        company.phone = company_data.phone
        company.address = company_data.address
        company.city = company_data.city
        company.state = company_data.state
        company.country = company_data.country or "India"
        company.pincode = company_data.pincode
        company.contact_person = company_data.contact_person
        company.contact_designation = company_data.contact_designation
        company.contact_phone = company_data.contact_phone
        company.contact_email = company_data.contact_email
        company.description = company_data.description
        company.status = company_data.status if company_data.status is not None else company.status
        company.modified_by = user_id
        company.modify_date = datetime.now()

        db.commit()
        db.refresh(company)

        # Update or create primary contact in plm_company_contact
        from app.db.placement_models import PLMCompanyContact
        primary_contact = db.query(PLMCompanyContact).filter(
            PLMCompanyContact.company_id == company.company_id,
            PLMCompanyContact.is_primary == 1
        ).first()

        if primary_contact:
            primary_contact.name = company.contact_person
            primary_contact.designation = company.contact_designation
            primary_contact.email = company.contact_email
            primary_contact.phone = company.contact_phone
            db.commit()
        else:
            if company.contact_person:
                primary_contact = PLMCompanyContact(
                    company_id=company.company_id,
                    name=company.contact_person,
                    designation=company.contact_designation,
                    email=company.contact_email,
                    phone=company.contact_phone,
                    is_primary=1,
                    is_active=1
                )
                db.add(primary_contact)
                db.commit()

        return returnSuccess(
            _company_to_dict(company, db),
            message="Company updated successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 5. Activate Company
# ---------------------------------------------------------------------------
@router.put("/activate")
def activate_company(
    payload: CompanyStatusUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Set company status to 1 (Active)."""
    try:
        resolved_org = org_id or 1
        company = db.query(PlacementCompany).filter(
            PlacementCompany.company_id == payload.company_id,
            PlacementCompany.org_id == resolved_org,
        ).first()
        if not company:
            return returnException(
                f"Company with ID {payload.company_id} not found."
            )
        if company.status == 1:
            return returnException("Company is already active.")

        company.status = 1
        company.modified_by = current_user.get("user_id", 1)
        company.modify_date = datetime.now()
        db.commit()
        return returnSuccess(
            {"company_id": company.company_id, "status": 1},
            message="Company activated successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ---------------------------------------------------------------------------
# 6. Deactivate Company
# ---------------------------------------------------------------------------
@router.put("/deactivate")
def deactivate_company(
    payload: CompanyStatusUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Set company status to 0 (Inactive)."""
    try:
        resolved_org = org_id or 1
        company = db.query(PlacementCompany).filter(
            PlacementCompany.company_id == payload.company_id,
            PlacementCompany.org_id == resolved_org,
        ).first()
        if not company:
            return returnException(
                f"Company with ID {payload.company_id} not found."
            )
        if company.status == 0:
            return returnException("Company is already inactive.")

        # Check if there are any active/ongoing placement drives for this company
        active_drives = db.query(PlacementDrive).filter(
            PlacementDrive.company_id == payload.company_id,
            PlacementDrive.status.in_([0, 1, 2]) # 0=Draft, 1=Scheduled, 2=Active
        ).first()
        if active_drives:
            return returnException(
                f"Cannot deactivate company. An active placement drive '{active_drives.drive_name}' is currently ongoing for this company."
            )

        company.status = 0
        company.modified_by = current_user.get("user_id", 1)
        company.modify_date = datetime.now()
        db.commit()
        return returnSuccess(
            {"company_id": company.company_id, "status": 0},
            message="Company deactivated successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))
