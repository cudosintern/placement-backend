from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel

from app.core.database import get_db
from app.db.placement_models import (
    PlacementApplication,
    PlacementShortlist,
    PlacementWaitlist,
    PlacementDrive,
)
from app.db.models import PLMStudentProfile, IEMStudents, IEMSDepartment
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()

# --- Pydantic Schemas ---
class ApplicationUpdateSchema(BaseModel):
    application_id: int
    status: str

class ShortlistCreateSchema(BaseModel):
    application_id: int
    shortlist_type: Optional[str] = "SYSTEM"
    justification: Optional[str] = None

class WaitlistCreateSchema(BaseModel):
    application_id: int

class ActionWithIdSchema(BaseModel):
    shortlist_id: Optional[int] = None
    waitlist_id: Optional[int] = None
    application_id: int

# --- API Routes ---

@router.post("/application_list")
def get_application_list(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # Fetch all applications, joining with student profile, student details, and department
        results = (
            db.query(
                PlacementApplication.application_id,
                PlacementApplication.status,
                PlacementApplication.applied_at,
                IEMStudents.name.label("student_name"),
                IEMStudents.usno.label("usn"),
                IEMSDepartment.dept_name.label("branch"),
                PLMStudentProfile.current_cgpa.label("cgpa")
            )
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(IEMSDepartment, IEMSDepartment.dept_id == IEMStudents.department_id)
            .filter(PLMStudentProfile.org_id == org_id)
            .all()
        )

        app_list = []
        for r in results:
            app_list.append({
                "application_id": r.application_id,
                "student_name": r.student_name,
                "usn": r.usn,
                "branch": r.branch or "Unknown",
                "cgpa": float(r.cgpa) if r.cgpa is not None else None,
                "status": r.status,
                "applied_at": str(r.applied_at) if r.applied_at else None,
            })

        return returnSuccess(app_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/application/update")
def update_application(
    data: ApplicationUpdateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id,
            PlacementApplication.tenant_id == org_id
        ).first()

        if not app:
            return returnException("Application not found.")

        app.status = data.status
        db.commit()
        return returnSuccess("Application status updated successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.post("/shortlist/create")
def create_shortlist(
    data: ShortlistCreateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # Check if already shortlisted
        existing = db.query(PlacementShortlist).filter(
            PlacementShortlist.application_id == data.application_id
        ).first()
        if existing:
            return returnException("Candidate is already shortlisted.")

        # Update application status
        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id
        ).first()
        if not app:
            return returnException("Application not found.")

        app.status = "SHORTLISTED"

        # Create shortlist entry
        shortlist = PlacementShortlist(
            application_id=data.application_id,
            shortlist_type=data.shortlist_type or "SYSTEM",
            shortlisted_by=user_id,
            justification=data.justification,
            shortlisted_at=datetime.now()
        )
        db.add(shortlist)
        db.commit()

        return returnSuccess("Candidate shortlisted successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.post("/shortlist/withdraw")
def withdraw_shortlist(
    data: ActionWithIdSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        shortlist = db.query(PlacementShortlist).filter(
            PlacementShortlist.application_id == data.application_id
        ).first()

        if shortlist:
            db.delete(shortlist)

        # Revert application status back to APPLIED
        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id
        ).first()
        if app:
            app.status = "APPLIED"

        db.commit()
        return returnSuccess("Shortlist entry withdrawn successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.post("/shortlist/list")
def get_shortlist_list(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        results = (
            db.query(
                PlacementShortlist.shortlist_id,
                PlacementShortlist.application_id,
                PlacementShortlist.shortlist_type,
                PlacementShortlist.shortlisted_at,
                PlacementApplication.status,
                IEMStudents.name.label("student_name"),
                PlacementDrive.drive_name.label("drive_name")
            )
            .join(PlacementApplication, PlacementApplication.application_id == PlacementShortlist.application_id)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementApplication.drive_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .filter(PLMStudentProfile.org_id == org_id)
            .all()
        )

        shortlist_list = []
        for r in results:
            shortlist_list.append({
                "shortlist_id": r.shortlist_id,
                "application_id": r.application_id,
                "student_name": r.student_name,
                "drive_name": r.drive_name,
                "shortlist_type": r.shortlist_type,
                "shortlisted_at": str(r.shortlisted_at) if r.shortlisted_at else None,
                "status": r.status,
            })

        return returnSuccess(shortlist_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/waitlist/create")
def create_waitlist(
    data: WaitlistCreateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # Check if already waitlisted
        existing = db.query(PlacementWaitlist).filter(
            PlacementWaitlist.application_id == data.application_id
        ).first()
        if existing:
            return returnException("Candidate is already waitlisted.")

        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id
        ).first()
        if not app:
            return returnException("Application not found.")

        app.status = "WAITLISTED"

        # Calculate next position in waitlist for this drive
        max_pos = db.query(PlacementWaitlist.position).filter(
            PlacementWaitlist.drive_id == app.drive_id
        ).order_by(PlacementWaitlist.position.desc()).first()
        
        next_pos = (max_pos[0] + 1) if max_pos else 1

        waitlist = PlacementWaitlist(
            application_id=data.application_id,
            drive_id=app.drive_id,
            position=next_pos
        )
        db.add(waitlist)
        db.commit()

        return returnSuccess("Candidate added to waitlist successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.post("/waitlist/promote")
def promote_waitlist(
    data: ActionWithIdSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        waitlist = db.query(PlacementWaitlist).filter(
            PlacementWaitlist.application_id == data.application_id
        ).first()

        if not waitlist:
            return returnException("Waitlist record not found.")

        drive_id = waitlist.drive_id

        # 1. Update application status
        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id
        ).first()
        if app:
            app.status = "SHORTLISTED"

        # 2. Add to shortlist
        shortlist = PlacementShortlist(
            application_id=data.application_id,
            shortlist_type="SYSTEM",
            shortlisted_by=user_id,
            shortlisted_at=datetime.now()
        )
        db.add(shortlist)

        # 3. Delete from waitlist
        db.delete(waitlist)

        # 4. Shift positions of remaining candidates in waitlist for this drive
        remaining = db.query(PlacementWaitlist).filter(
            PlacementWaitlist.drive_id == drive_id
        ).order_by(PlacementWaitlist.position.asc()).all()

        for idx, item in enumerate(remaining):
            item.position = idx + 1

        db.commit()
        return returnSuccess("Candidate promoted to shortlist successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.post("/waitlist/list")
def get_waitlist_list(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        results = (
            db.query(
                PlacementWaitlist.waitlist_id,
                PlacementWaitlist.application_id,
                PlacementWaitlist.position,
                PlacementApplication.status,
                IEMStudents.name.label("student_name"),
                PlacementDrive.drive_name.label("drive_name")
            )
            .join(PlacementApplication, PlacementApplication.application_id == PlacementWaitlist.application_id)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementApplication.drive_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .filter(PLMStudentProfile.org_id == org_id)
            .order_by(PlacementWaitlist.position.asc())
            .all()
        )

        waitlist_list = []
        for r in results:
            waitlist_list.append({
                "waitlist_id": r.waitlist_id,
                "application_id": r.application_id,
                "student_name": r.student_name,
                "drive_name": r.drive_name,
                "position": r.position,
                "status": r.status,
            })

        return returnSuccess(waitlist_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/override/list")
def get_override_list(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    # Returns empty override list as default
    return returnSuccess([])
