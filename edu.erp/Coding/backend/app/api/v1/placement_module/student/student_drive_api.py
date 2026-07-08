"""
student_drive_api.py
====================
Placement Drive — Student-facing Endpoints

Endpoints:
  POST   /placement/student/apply              - Student applies to an active drive
  DELETE /placement/student/apply              - Student withdraws application
  GET    /placement/student/my-applications    - All applications for a student (drive_id → status)

Application status values (plm_application.status):
  APPLIED       – freshly submitted
  SHORTLISTED   – TPO shortlisted the student
  WAITLISTED    – on waitlist
  IN_PROCESS    – actively in interview rounds
  OFFERED       – received offer letter
  REJECTED      – rejected by company/TPO
  WITHDRAWN     – student withdrew the application
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import IEMStudents
from app.db.placement_models import (
    PlacementDrive,
    PlacementDriveEligibleBranch,
    PLMApplication,
    PLMStudentProfile,
    PLMStudentResume,
)
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()

# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

ACTIVE_APPLICATION_STATUSES = {"APPLIED", "SHORTLISTED", "WAITLISTED", "IN_PROCESS", "OFFERED"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ApplyPayload(BaseModel):
    drive_id:   int
    profile_id: int           # plm_student_profile.profile_id
    resume_id:  Optional[int] = None  # plm_student_resume.resume_id (optional)


class WithdrawPayload(BaseModel):
    drive_id:   int
    profile_id: int


# ---------------------------------------------------------------------------
# Eligibility helper
# ---------------------------------------------------------------------------

def _check_eligibility(
    db: Session,
    drive: PlacementDrive,
    student: IEMStudents,
    profile: PLMStudentProfile,
    org_id: int,
) -> tuple[bool, str]:
    """
    Returns (is_eligible: bool, reason: str).
    Checks:
      1. Drive must be ACTIVE (status == 2)
      2. Student CGPA >= drive.min_cgpa
      3. Student backlogs <= drive.max_backlogs
      4. Student's department must be in the eligible branches list
    """
    # 1. Drive status
    if drive.status != 2:
        return False, "Drive is not currently active."

    # 2. CGPA check
    student_cgpa = float(profile.current_cgpa) if profile.current_cgpa is not None else 0.0
    min_cgpa = float(drive.min_cgpa) if drive.min_cgpa is not None else 0.0
    if student_cgpa < min_cgpa:
        return False, f"CGPA {student_cgpa} is below the required {min_cgpa}."

    # 3. Backlog check
    student_backlogs = profile.backlogs if profile.backlogs is not None else 0
    max_backlogs = drive.max_backlogs if drive.max_backlogs is not None else 0
    if student_backlogs > max_backlogs:
        return False, f"Backlog count {student_backlogs} exceeds the maximum allowed {max_backlogs}."

    # 4. Branch/department eligibility
    eligible_branches = (
        db.query(PlacementDriveEligibleBranch)
        .filter(PlacementDriveEligibleBranch.drive_id == drive.drive_id)
        .all()
    )
    if eligible_branches:
        dept_ids = {b.dept_id for b in eligible_branches}
        if student.department_id not in dept_ids:
            return False, "Your branch/department is not eligible for this drive."

    return True, "Eligible"


# ===========================================================================
# 1. POST /apply — Student applies to a drive
# ===========================================================================

@router.post("/apply")
def apply_to_drive(
    payload: ApplyPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Submit a student application for an active placement drive.

    - Validates drive is ACTIVE (status == 2).
    - Validates student has a placement profile (plm_student_profile).
    - Checks eligibility (CGPA, backlogs, branch).
    - Inserts a row into plm_application.
    - Increments plm_drive.applied_count.
    - Prevents duplicate applications (unique on drive_id + profile_id).
    """
    try:
        resolved_org = org_id or 1

        # ── 1. Load drive ──────────────────────────────────────────────────
        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == payload.drive_id,
                PlacementDrive.org_id == resolved_org,
            )
            .first()
        )
        if not drive:
            return returnException(f"Drive {payload.drive_id} not found.")

        if drive.status != 2:
            return returnException("Applications are only accepted for Active drives.")

        # ── 2. Load student profile ────────────────────────────────────────
        profile = (
            db.query(PLMStudentProfile)
            .filter(
                PLMStudentProfile.profile_id == payload.profile_id,
                PLMStudentProfile.org_id == resolved_org,
                PLMStudentProfile.status == 1,
            )
            .first()
        )
        if not profile:
            return returnException(
                "Placement profile not found. Please complete your Student Profile first."
            )

        # ── 3. Load student (for eligibility check) ────────────────────────
        student = (
            db.query(IEMStudents)
            .filter(IEMStudents.student_id == profile.student_id)
            .first()
        )
        if not student:
            return returnException("Student record not found.")

        # ── 4. Eligibility check ───────────────────────────────────────────
        eligible, reason = _check_eligibility(db, drive, student, profile, resolved_org)

        # ── 5. Check for existing application ─────────────────────────────
        existing = (
            db.query(PLMApplication)
            .filter(
                PLMApplication.drive_id   == payload.drive_id,
                PLMApplication.profile_id == payload.profile_id,
            )
            .first()
        )
        if existing:
            if existing.status == "WITHDRAWN":
                # Re-apply after withdraw — reactivate
                existing.status     = "APPLIED"
                existing.is_eligible = 1 if eligible else 0
                existing.applied_at  = datetime.now()
                existing.resume_id   = payload.resume_id
                existing.tenant_id   = resolved_org
                db.commit()
                db.refresh(existing)
                # Increment counter only if it was WITHDRAWN before
                drive.applied_count = (drive.applied_count or 0) + 1
                db.commit()
                return returnSuccess(
                    _application_to_dict(existing),
                    message="Re-application submitted successfully.",
                )
            return returnException(
                f"You have already applied for this drive (status: {existing.status})."
            )

        # ── 6. Optionally validate resume belongs to this profile ──────────
        if payload.resume_id:
            resume = (
                db.query(PLMStudentResume)
                .filter(
                    PLMStudentResume.resume_id == payload.resume_id,
                    PLMStudentResume.profile_id == payload.profile_id,
                    PLMStudentResume.status == 1,
                )
                .first()
            )
            if not resume:
                return returnException("Resume not found or does not belong to this profile.")

        # ── 7. Insert application ──────────────────────────────────────────
        application = PLMApplication(
            tenant_id   = resolved_org,
            drive_id    = payload.drive_id,
            profile_id  = payload.profile_id,
            resume_id   = payload.resume_id,
            applied_at  = datetime.now(),
            status      = "APPLIED",
            is_eligible = 1 if eligible else 0,
        )
        db.add(application)
        db.flush()  # get application_id

        # ── 8. Increment applied_count on drive ────────────────────────────
        drive.applied_count = (drive.applied_count or 0) + 1

        db.commit()
        db.refresh(application)

        return returnSuccess(
            _application_to_dict(application),
            message="Application submitted successfully!" if eligible
                    else "Application submitted (eligibility flag set to ineligible — please review your profile).",
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 2. DELETE /apply — Student withdraws their application
# ===========================================================================

@router.delete("/apply")
def withdraw_application(
    drive_id:   int = Query(..., description="Drive ID to withdraw from"),
    profile_id: int = Query(..., description="Student profile ID"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Withdraw a student's application from a drive.

    - Sets plm_application.status = 'WITHDRAWN'.
    - Decrements plm_drive.applied_count (min 0).
    - Cannot withdraw if already SHORTLISTED / IN_PROCESS / OFFERED.
    """
    try:
        resolved_org = org_id or 1

        application = (
            db.query(PLMApplication)
            .filter(
                PLMApplication.drive_id   == drive_id,
                PLMApplication.profile_id == profile_id,
            )
            .first()
        )
        if not application:
            return returnException("No application found for this drive and profile.")

        if application.status == "WITHDRAWN":
            return returnException("Application is already withdrawn.")

        # Prevent withdrawal if TPO has already acted
        locked_statuses = {"SHORTLISTED", "IN_PROCESS", "OFFERED"}
        if application.status in locked_statuses:
            return returnException(
                f"Cannot withdraw — application is currently '{application.status}'. "
                "Please contact the TPO."
            )

        # Update status
        application.status = "WITHDRAWN"
        db.flush()

        # Decrement drive applied_count
        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == drive_id,
                PlacementDrive.org_id   == resolved_org,
            )
            .first()
        )
        if drive:
            drive.applied_count = max(0, (drive.applied_count or 1) - 1)

        db.commit()
        db.refresh(application)

        return returnSuccess(
            _application_to_dict(application),
            message="Application withdrawn successfully.",
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 3. GET /my-applications — All applications for a student
# ===========================================================================

@router.get("/my-applications")
def get_my_applications(
    profile_id: int = Query(..., description="Student profile ID"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Return all drive applications for a student profile.
    Frontend uses this to pre-populate the Apply/Applied/Withdrawn badge on
    each drive card when the page loads.

    Response:
        [{ drive_id, application_id, status, applied_at, resume_id, is_eligible }, ...]
    """
    try:
        applications = (
            db.query(PLMApplication)
            .filter(PLMApplication.profile_id == profile_id)
            .order_by(PLMApplication.applied_at.desc())
            .all()
        )
        return returnSuccess([_application_to_dict(a) for a in applications])
    except Exception as e:
        return returnException(str(e))


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def _application_to_dict(a: PLMApplication) -> dict:
    return {
        "application_id": a.application_id,
        "drive_id":        a.drive_id,
        "profile_id":      a.profile_id,
        "resume_id":       a.resume_id,
        "status":          a.status,
        "is_eligible":     a.is_eligible,
        "applied_at":      str(a.applied_at) if a.applied_at else None,
    }
