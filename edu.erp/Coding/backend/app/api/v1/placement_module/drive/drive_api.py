"""
drive_api.py
============
Placement Drive Module — API Endpoints

Endpoints:
  GET  /placement/drive/meta                  - Dropdown data: companies, depts, batch years
  GET  /placement/drive/list                  - All drives with filters
  GET  /placement/drive/detail/{drive_id}     - Full drive + branches + rounds
  POST /placement/drive/save                  - Create drive (atomic: drive + branches + rounds)
  PUT  /placement/drive/save                  - Update drive (atomic: replace branches + rounds)
  PUT  /placement/drive/status                - Change drive status only
  GET  /placement/drive/eligible-count        - Live count of eligible students (for form preview)

Status codes (plm_drive.status):
  0 = Draft
  1 = Scheduled
  2 = Active
  3 = Closed
  4 = Cancelled
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel

from app.api.v1.placement_module.drive.drive_schema import (
    DriveCreate,
    DriveStatusUpdate,
)
from app.core.database import get_db
from app.db.models import IEMSAcademicBatch, IEMSDepartment, IEMStudents
from app.db.placement_models import (
    PlacementCompany,
    PlacementDrive,
    PlacementDriveEligibleBranch,
    PlacementDriveRound,
)
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import distinct, func, text
from sqlalchemy.orm import Session

router = APIRouter()

# ---------------------------------------------------------------------------
# Status label map
# ---------------------------------------------------------------------------
STATUS_LABELS = {
    0: "Draft",
    1: "Scheduled",
    2: "Active",
    3: "Closed",
    4: "Cancelled",
}

ROUND_TYPES = ["APTITUDE", "TECHNICAL", "HR", "GD", "ASSIGNMENT", "OTHER"]
DRIVE_TYPES = ["On-Campus", "Off-Campus", "Pool Campus"]
WORK_TYPES = ["Onsite", "Remote", "Hybrid"]


# ---------------------------------------------------------------------------
# Serializer helpers
# ---------------------------------------------------------------------------


def _drive_to_dict(d: PlacementDrive, company_name: str = None) -> dict:
    """Serialize PlacementDrive ORM → flat dict (for list view)."""
    return {
        "drive_id": d.drive_id,
        "drive_name": d.drive_name,
        "company_id": d.company_id,
        "company_name": company_name or "",
        "job_role": d.job_role,
        "vacancy_count": d.vacancy_count,
        "drive_type": d.drive_type,
        "work_type": d.work_type,
        "location": d.location,
        "ctc_min": float(d.ctc_min) if d.ctc_min is not None else None,
        "ctc_max": float(d.ctc_max) if d.ctc_max is not None else None,
        "min_cgpa": float(d.min_cgpa) if d.min_cgpa is not None else 0.0,
        "max_backlogs": d.max_backlogs,
        "application_start": str(d.application_start) if d.application_start else None,
        "application_deadline": str(d.application_deadline)
        if d.application_deadline
        else None,
        "drive_date": str(d.drive_date) if d.drive_date else None,
        "tier": d.tier,
        "status": d.status,
        "status_label": STATUS_LABELS.get(d.status, "Unknown"),
        "eligible_student_count": d.eligible_student_count,
        "applied_count": d.applied_count,
        "shortlisted_count": d.shortlisted_count,
        "org_id": d.org_id,
        "created_by": d.created_by,
        "create_date": str(d.create_date) if d.create_date else None,
        "modify_date": str(d.modify_date) if d.modify_date else None,
    }


def _branch_to_dict(
    b: PlacementDriveEligibleBranch, dept_name: str = "", dept_acronym: str = ""
) -> dict:
    return {
        "id": b.id,
        "drive_id": b.drive_id,
        "dept_id": b.dept_id,
        "dept_name": dept_name,
        "dept_acronym": dept_acronym,
        "batch_year": b.batch_year,
    }


def _round_to_dict(r: PlacementDriveRound) -> dict:
    return {
        "round_id": r.round_id,
        "drive_id": r.drive_id,
        "round_number": r.round_number,
        "round_name": r.round_name,
        "round_type": r.round_type,
        "is_eliminatory": bool(r.is_eliminatory),
        "round_date": str(r.round_date) if r.round_date else None,
        "duration_minutes": r.duration_minutes,
        "description": r.description,
    }


# ---------------------------------------------------------------------------
# Helper: compute eligible student count
# ---------------------------------------------------------------------------


def _compute_eligible_count(
    db: Session,
    org_id: int,
    eligible_branches: list,  # list of (dept_id, batch_year) tuples
) -> int:
    """
    Count distinct students whose (department_id, academic_batch.start_year)
    matches any combo in eligible_branches.
    """
    if not eligible_branches:
        return 0

    try:
        # Build IN-clause as list of tuples
        # We do this with a subquery approach that works across DBs
        total = 0
        seen_students = set()

        for dept_id, batch_year in eligible_branches:
            rows = (
                db.query(IEMStudents.student_id)
                .join(
                    IEMSAcademicBatch,
                    IEMSAcademicBatch.academic_batch_id
                    == IEMStudents.academic_batch_id,
                )
                .filter(
                    IEMStudents.org_id == org_id,
                    IEMStudents.status == 1,
                    IEMStudents.department_id == dept_id,
                    IEMSAcademicBatch.start_year == batch_year,
                )
                .all()
            )
            for (sid,) in rows:
                seen_students.add(sid)

        return len(seen_students)
    except Exception:
        return 0


# ===========================================================================
# 1. GET /placement/drive/meta — dropdown data for Create Drive form
# ===========================================================================


@router.get("/meta")
def get_drive_meta(
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Returns all dropdown data needed for the Create/Edit Drive form:
      - Active companies
      - Active departments
      - Available batch years
      - Static option lists (drive_types, work_types, round_types)
    """
    try:
        resolved_org = org_id or 1

        # Active companies
        companies = (
            db.query(PlacementCompany)
            .filter(
                PlacementCompany.status == 1,
                PlacementCompany.org_id == resolved_org,
            )
            .order_by(PlacementCompany.company_name)
            .all()
        )

        # Active departments
        departments = (
            db.query(IEMSDepartment)
            .filter(
                IEMSDepartment.status == 1,
                IEMSDepartment.org_id == resolved_org,
            )
            .order_by(IEMSDepartment.dept_name)
            .all()
        )

        # Distinct batch years (from iems_academic_batch.start_year)
        batch_year_rows = (
            db.query(distinct(IEMSAcademicBatch.start_year))
            .filter(
                IEMSAcademicBatch.status == 1,
                IEMSAcademicBatch.org_id == resolved_org,
            )
            .order_by(IEMSAcademicBatch.start_year)
            .all()
        )

        data = {
            "companies": [
                {
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "industry": c.industry,
                }
                for c in companies
            ],
            "departments": [
                {
                    "dept_id": d.dept_id,
                    "dept_name": d.dept_name,
                    "dept_acronym": d.dept_acronym,
                }
                for d in departments
            ],
            "batch_years": [row[0] for row in batch_year_rows if row[0]],
            "drive_types": DRIVE_TYPES,
            "work_types": WORK_TYPES,
            "round_types": ROUND_TYPES,
        }

        return returnSuccess(data, message="Meta data loaded")
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 2. GET /placement/drive/list — drive list with filters
# ===========================================================================


@router.get("/list")
def get_drive_list(
    search: Optional[str] = Query(
        None, description="Search by drive name, company name, or job role"
    ),
    status: Optional[int] = Query(
        None, description="0=Draft 1=Scheduled 2=Active 3=Closed 4=Cancelled"
    ),
    drive_type: Optional[str] = Query(
        None, description="On-Campus | Off-Campus | Pool Campus"
    ),
    tier: Optional[int] = Query(None, description="1 | 2 | 3"),
    batch_year: Optional[int] = Query(
        None, description="Filter by eligible batch year, e.g. 2025"
    ),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Return drives matching optional filters.
    Also returns summary counts for the header bar
    (total, active, scheduled, closed).
    """
    try:
        resolved_org = org_id or 1

        query = (
            db.query(PlacementDrive, PlacementCompany.company_name)
            .join(
                PlacementCompany,
                PlacementCompany.company_id == PlacementDrive.company_id,
            )
            .filter(PlacementDrive.org_id == resolved_org)
        )

        if status is not None:
            query = query.filter(PlacementDrive.status == status)
        if drive_type:
            query = query.filter(PlacementDrive.drive_type == drive_type)
        if tier is not None:
            query = query.filter(PlacementDrive.tier == tier)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                PlacementDrive.drive_name.ilike(pattern)
                | PlacementDrive.job_role.ilike(pattern)
                | PlacementCompany.company_name.ilike(pattern)
            )
        if batch_year is not None:
            # Only drives that have at least one eligible_branch with this batch_year
            query = query.filter(
                PlacementDrive.drive_id.in_(
                    db.query(PlacementDriveEligibleBranch.drive_id)
                    .filter(PlacementDriveEligibleBranch.batch_year == batch_year)
                    .subquery()
                )
            )

        rows = query.order_by(PlacementDrive.create_date.desc()).all()
        drives = [_drive_to_dict(d, cname) for d, cname in rows]

        # Summary counts (all drives for this org, regardless of filters)
        all_drives = (
            db.query(PlacementDrive.status, func.count(PlacementDrive.drive_id))
            .filter(PlacementDrive.org_id == resolved_org)
            .group_by(PlacementDrive.status)
            .all()
        )
        counts_by_status = {row[0]: row[1] for row in all_drives}
        total = sum(counts_by_status.values())

        summary = {
            "total": total,
            "active": counts_by_status.get(2, 0),
            "scheduled": counts_by_status.get(1, 0),
            "draft": counts_by_status.get(0, 0),
            "closed": counts_by_status.get(3, 0),
            "cancelled": counts_by_status.get(4, 0),
        }

        return returnSuccess(
            {"drives": drives, "summary": summary},
            message=f"{len(drives)} drive(s) found",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 3. GET /placement/drive/detail/{drive_id} — full drive with branches + rounds
# ===========================================================================


@router.get("/detail/{drive_id}")
def get_drive_detail(
    drive_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Return full drive record including eligible_branches and rounds."""
    try:
        resolved_org = org_id or 1

        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == drive_id,
                PlacementDrive.org_id == resolved_org,
            )
            .first()
        )
        if not drive:
            return returnException(f"Drive with ID {drive_id} not found.")

        # Company name
        company = (
            db.query(PlacementCompany)
            .filter(PlacementCompany.company_id == drive.company_id)
            .first()
        )
        company_name = company.company_name if company else ""

        # Eligible branches — join department for names
        branch_rows = (
            db.query(
                PlacementDriveEligibleBranch,
                IEMSDepartment.dept_name,
                IEMSDepartment.dept_acronym,
            )
            .join(
                IEMSDepartment,
                IEMSDepartment.dept_id == PlacementDriveEligibleBranch.dept_id,
            )
            .filter(PlacementDriveEligibleBranch.drive_id == drive_id)
            .all()
        )
        branches = [
            _branch_to_dict(b, dname, dacronym) for b, dname, dacronym in branch_rows
        ]

        # Rounds ordered by round_number
        rounds = (
            db.query(PlacementDriveRound)
            .filter(PlacementDriveRound.drive_id == drive_id)
            .order_by(PlacementDriveRound.round_number)
            .all()
        )

        result = _drive_to_dict(drive, company_name)
        result["job_description"] = drive.job_description
        result["eligible_branches"] = branches
        result["rounds"] = [_round_to_dict(r) for r in rounds]

        return returnSuccess(result)
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 4. POST /placement/drive/save — Create new drive (atomic)
# ===========================================================================


@router.post("/save")
def create_drive(
    payload: DriveCreate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Create a new placement drive.
    - drive_id must be None (or absent) in the payload.
    - Inserts drive + eligible_branches + rounds in one transaction.
    - Computes eligible_student_count and caches it.
    """
    try:
        if payload.drive_id:
            return returnException(
                "Do not provide drive_id when creating a new drive. "
                "Use PUT /save to update an existing drive."
            )

        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        # Validate company exists and is active
        company = (
            db.query(PlacementCompany)
            .filter(
                PlacementCompany.company_id == payload.company_id,
                PlacementCompany.status == 1,
            )
            .first()
        )
        if not company:
            return returnException(
                f"Company ID {payload.company_id} not found or is inactive."
            )

        # Compute eligible student count
        branch_tuples = [(b.dept_id, b.batch_year) for b in payload.eligible_branches]
        eligible_count = _compute_eligible_count(db, resolved_org, branch_tuples)

        # Create drive
        new_drive = PlacementDrive(
            company_id=payload.company_id,
            drive_name=payload.drive_name.strip(),
            job_role=payload.job_role.strip(),
            vacancy_count=payload.vacancy_count,
            drive_type=payload.drive_type,
            work_type=payload.work_type,
            location=payload.location,
            ctc_min=payload.ctc_min,
            ctc_max=payload.ctc_max,
            job_description=payload.job_description,
            min_cgpa=payload.min_cgpa,
            max_backlogs=payload.max_backlogs,
            application_start=payload.application_start,
            application_deadline=payload.application_deadline,
            drive_date=payload.drive_date,
            tier=payload.tier,
            status=payload.status,
            eligible_student_count=eligible_count,
            applied_count=0,
            shortlisted_count=0,
            org_id=resolved_org,
            created_by=user_id,
            create_date=datetime.now(),
        )
        db.add(new_drive)
        db.flush()  # get drive_id before inserting children

        # Insert eligible branches
        for branch in payload.eligible_branches:
            db.add(
                PlacementDriveEligibleBranch(
                    drive_id=new_drive.drive_id,
                    dept_id=branch.dept_id,
                    batch_year=branch.batch_year,
                )
            )

        # Insert rounds
        for rnd in payload.rounds:
            db.add(
                PlacementDriveRound(
                    drive_id=new_drive.drive_id,
                    round_number=rnd.round_number,
                    round_name=rnd.round_name.strip(),
                    round_type=rnd.round_type.upper(),
                    is_eliminatory=1 if rnd.is_eliminatory else 0,
                    round_date=rnd.round_date,
                    duration_minutes=rnd.duration_minutes,
                    description=rnd.description,
                )
            )

        db.commit()
        db.refresh(new_drive)

        return returnSuccess(
            _drive_to_dict(new_drive, company.company_name),
            message="Placement drive created successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 5. PUT /placement/drive/save — Update existing drive (atomic)
# ===========================================================================


@router.put("/save")
def update_drive(
    payload: DriveCreate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Update an existing placement drive.
    - drive_id is REQUIRED in the payload.
    - Replaces all eligible_branches and rounds atomically.
    """
    try:
        if not payload.drive_id:
            return returnException(
                "drive_id is required for update. Use POST /save to create a new drive."
            )

        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == payload.drive_id,
                PlacementDrive.org_id == resolved_org,
            )
            .first()
        )
        if not drive:
            return returnException(f"Drive with ID {payload.drive_id} not found.")

        # Validate company
        company = (
            db.query(PlacementCompany)
            .filter(
                PlacementCompany.company_id == payload.company_id,
                PlacementCompany.status == 1,
            )
            .first()
        )
        if not company:
            return returnException(
                f"Company ID {payload.company_id} not found or is inactive."
            )

        # Recompute eligible student count
        branch_tuples = [(b.dept_id, b.batch_year) for b in payload.eligible_branches]
        eligible_count = _compute_eligible_count(db, resolved_org, branch_tuples)

        # Update drive fields
        drive.company_id = payload.company_id
        drive.drive_name = payload.drive_name.strip()
        drive.job_role = payload.job_role.strip()
        drive.vacancy_count = payload.vacancy_count
        drive.drive_type = payload.drive_type
        drive.work_type = payload.work_type
        drive.location = payload.location
        drive.ctc_min = payload.ctc_min
        drive.ctc_max = payload.ctc_max
        drive.job_description = payload.job_description
        drive.min_cgpa = payload.min_cgpa
        drive.max_backlogs = payload.max_backlogs
        drive.application_start = payload.application_start
        drive.application_deadline = payload.application_deadline
        drive.drive_date = payload.drive_date
        drive.tier = payload.tier
        drive.status = payload.status
        drive.eligible_student_count = eligible_count
        drive.modified_by = user_id
        drive.modify_date = datetime.now()

        # Replace eligible branches
        db.query(PlacementDriveEligibleBranch).filter(
            PlacementDriveEligibleBranch.drive_id == drive.drive_id
        ).delete(synchronize_session=False)

        for branch in payload.eligible_branches:
            db.add(
                PlacementDriveEligibleBranch(
                    drive_id=drive.drive_id,
                    dept_id=branch.dept_id,
                    batch_year=branch.batch_year,
                )
            )

        # Replace rounds
        db.query(PlacementDriveRound).filter(
            PlacementDriveRound.drive_id == drive.drive_id
        ).delete(synchronize_session=False)

        for rnd in payload.rounds:
            db.add(
                PlacementDriveRound(
                    drive_id=drive.drive_id,
                    round_number=rnd.round_number,
                    round_name=rnd.round_name.strip(),
                    round_type=rnd.round_type.upper(),
                    is_eliminatory=1 if rnd.is_eliminatory else 0,
                    round_date=rnd.round_date,
                    duration_minutes=rnd.duration_minutes,
                    description=rnd.description,
                )
            )

        db.commit()
        db.refresh(drive)

        return returnSuccess(
            _drive_to_dict(drive, company.company_name),
            message="Placement drive updated successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 6. PUT /placement/drive/status — Change status only
# ===========================================================================


@router.put("/status")
def update_drive_status(
    payload: DriveStatusUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Change the status of a drive.
    Valid statuses: 0=Draft 1=Scheduled 2=Active 3=Closed 4=Cancelled
    """
    try:
        resolved_org = org_id or 1

        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == payload.drive_id,
                PlacementDrive.org_id == resolved_org,
            )
            .first()
        )
        if not drive:
            return returnException(f"Drive with ID {payload.drive_id} not found.")

        if drive.status == payload.status:
            return returnException(
                f"Drive is already in '{STATUS_LABELS.get(payload.status)}' status."
            )

        old_label = STATUS_LABELS.get(drive.status, "Unknown")
        drive.status = payload.status
        drive.modified_by = current_user.get("user_id", 1)
        drive.modify_date = datetime.now()

        db.commit()

        return returnSuccess(
            {
                "drive_id": drive.drive_id,
                "status": drive.status,
                "status_label": STATUS_LABELS.get(drive.status),
            },
            message=f"Drive status changed from '{old_label}' to '{STATUS_LABELS.get(payload.status)}'.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 7. GET /placement/drive/eligible-count — Live eligible student count
# ===========================================================================


@router.get("/eligible-count")
def get_eligible_count(
    dept_ids: str = Query(..., description="Comma-separated dept_ids, e.g. '5,6,7'"),
    batch_years: str = Query(
        ..., description="Comma-separated batch years, e.g. '2025,2026'"
    ),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Returns the count of students eligible based on selected departments
    and batch years. Called in real-time as the TPO toggles branches/batch
    years in the Create Drive form.

    Query params:
        dept_ids    — comma-separated dept_id values (required)
        batch_years — comma-separated start_year values (required)
    """
    try:
        resolved_org = org_id or 1

        # Parse comma-separated params
        try:
            dept_id_list = [int(x.strip()) for x in dept_ids.split(",") if x.strip()]
            batch_year_list = [
                int(x.strip()) for x in batch_years.split(",") if x.strip()
            ]
        except ValueError:
            return returnException(
                "dept_ids and batch_years must be comma-separated integers."
            )

        if not dept_id_list or not batch_year_list:
            return returnSuccess(
                {"eligible_count": 0}, message="No branches or batch years provided."
            )

        # Build all (dept_id, batch_year) combos
        branch_tuples = [
            (dept_id, batch_year)
            for dept_id in dept_id_list
            for batch_year in batch_year_list
        ]

        count = _compute_eligible_count(db, resolved_org, branch_tuples)

        return returnSuccess(
            {"eligible_count": count},
            message=f"{count} student(s) eligible based on current settings.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 8. GET /placement/drive/applications — Applicants for a drive (shortlisting)
# ===========================================================================


@router.get("/applications")
def get_drive_applications(
    drive_id: int = Query(..., description="plm_drive.drive_id"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Return all applicants for a drive from plm_application.
    Joins with plm_student_profile, iems_students, iems_department.
    CGPA pulled from plm_student_profile.current_cgpa.
    Results sorted by CGPA DESC.
    """
    try:
        from app.db.placement_models import PLMApplication, PLMStudentProfile, PLMStudentResume
        from app.db.models import IEMStudents, IEMSDepartment

        resolved_org = org_id or 1

        # Verify drive exists
        drive = (
            db.query(PlacementDrive)
            .filter(
                PlacementDrive.drive_id == drive_id,
                PlacementDrive.org_id == resolved_org,
            )
            .first()
        )
        if not drive:
            return returnException(f"Drive {drive_id} not found.")

        # Query: application → profile → student → department
        rows = (
            db.query(
                PLMApplication,
                PLMStudentProfile,
                IEMStudents,
                IEMSDepartment,
            )
            .join(
                PLMStudentProfile,
                PLMStudentProfile.profile_id == PLMApplication.profile_id,
            )
            .join(
                IEMStudents,
                IEMStudents.student_id == PLMStudentProfile.student_id,
            )
            .outerjoin(
                IEMSDepartment,
                IEMSDepartment.dept_id == IEMStudents.department_id,
            )
            .filter(PLMApplication.drive_id == drive_id)
            .order_by(PLMStudentProfile.current_cgpa.desc())
            .all()
        )

        # Fetch active resumes in bulk
        profile_ids = [row[1].profile_id for row in rows]
        resume_map: dict = {}
        if profile_ids:
            resumes = (
                db.query(PLMStudentResume)
                .filter(
                    PLMStudentResume.profile_id.in_(profile_ids),
                    PLMStudentResume.is_active == 1,
                    PLMStudentResume.status == 1,
                )
                .all()
            )
            for r in resumes:
                resume_map[r.profile_id] = {"resume_id": r.resume_id, "file_path": r.file_path}

        applicants = []
        for app, profile, student, dept in rows:
            resume_info = resume_map.get(profile.profile_id)
            applicants.append({
                "application_id": app.application_id,
                "profile_id": app.profile_id,
                "student_id": profile.student_id,
                "name": student.name or f"{student.first_name or ''} {student.last_name or ''}".strip(),
                "usno": student.usno or "",
                "email": student.email or "",
                "department": dept.dept_name if dept else "",
                "department_id": student.department_id or 0,
                "cgpa": float(profile.current_cgpa) if profile.current_cgpa is not None else 0.0,
                "backlogs": int(profile.backlogs or 0),
                "resume_id": resume_info["resume_id"] if resume_info else None,
                "resume_url": resume_info["file_path"] if resume_info else None,
                "applied_at": str(app.applied_at) if app.applied_at else None,
                "status": app.status,
                "override_reason": app.override_reason or None,
            })

        return returnSuccess(
            {"applicants": applicants, "total": len(applicants)},
            message=f"{len(applicants)} applicant(s) found.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 9. POST /placement/drive/applications/shortlist — Bulk shortlist
# ===========================================================================


from pydantic import BaseModel as _PydanticBase


class ShortlistPayload(_PydanticBase):
    drive_id: int
    application_ids: List[int]


@router.post("/applications/shortlist")
def shortlist_applications(
    payload: ShortlistPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Bulk-set selected application_ids to SHORTLISTED.
    Enforces vacancy cap — rejects if already-shortlisted + new > vacancy.
    Updates plm_drive.shortlisted_count.
    """
    try:
        from app.db.placement_models import PLMApplication

        resolved_org = org_id or 1

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

        # Vacancy cap check
        current_shortlisted = (
            db.query(func.count(PLMApplication.application_id))
            .filter(
                PLMApplication.drive_id == payload.drive_id,
                PLMApplication.status == "SHORTLISTED",
            )
            .scalar()
            or 0
        )
        if drive.vacancy_count is not None:
            if current_shortlisted + len(payload.application_ids) > drive.vacancy_count:
                return returnException(
                    f"Vacancy cap exceeded. Vacancy: {drive.vacancy_count}, "
                    f"Already shortlisted: {current_shortlisted}, "
                    f"Trying to add: {len(payload.application_ids)}."
                )

        # Update application statuses
        # Accept both APPLIED and WAITLISTED so TPO can manually promote
        # waitlisted students.
        updated = (
            db.query(PLMApplication)
            .filter(
                PLMApplication.application_id.in_(payload.application_ids),
                PLMApplication.drive_id == payload.drive_id,
                PLMApplication.status.in_(["APPLIED", "WAITLISTED"]),
            )
            .all()
        )

        # Capture the current shortlisted count BEFORE updating statuses
        current_shortlisted = (
            db.query(func.count(PLMApplication.application_id))
            .filter(
                PLMApplication.drive_id == payload.drive_id,
                PLMApplication.status == "SHORTLISTED",
            )
            .scalar()
            or 0
        )

        for app in updated:
            app.status = "SHORTLISTED"

        # shortlisted_count = existing shortlisted + newly shortlisted
        drive.shortlisted_count = current_shortlisted + len(updated)
        drive.modify_date = datetime.now()

        db.commit()

        return returnSuccess(
            {"shortlisted": len(updated)},
            message=f"{len(updated)} student(s) shortlisted successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 10. POST /placement/drive/applications/reject — Reject one application
# ===========================================================================


class RejectPayload(_PydanticBase):
    application_id: int
    reason: Optional[str] = None


def _promote_waitlisted(db: Session, drive: PlacementDrive):
    """
    Finds the top WAITLISTED candidate by CGPA and promotes them to SHORTLISTED.
    Adjusts drive.shortlisted_count accordingly.
    """
    from app.db.placement_models import PLMApplication, PLMStudentProfile
    top_waitlisted = (
        db.query(PLMApplication)
        .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
        .filter(
            PLMApplication.drive_id == drive.drive_id,
            PLMApplication.status == "WAITLISTED",
        )
        .order_by(PLMStudentProfile.current_cgpa.desc())
        .first()
    )
    if top_waitlisted:
        top_waitlisted.status = "SHORTLISTED"
        drive.shortlisted_count = (drive.shortlisted_count or 0) + 1
        db.flush()


@router.post("/applications/reject")
def reject_application(
    payload: RejectPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Reject a single application — sets status to REJECTED."""
    try:
        from app.db.placement_models import PLMApplication

        app = (
            db.query(PLMApplication)
            .filter(PLMApplication.application_id == payload.application_id)
            .first()
        )
        if not app:
            return returnException(f"Application {payload.application_id} not found.")

        if app.status in ("OFFERED",):
            return returnException(
                f"Cannot reject an application that is already '{app.status}'."
            )

        was_shortlisted = (app.status == "SHORTLISTED")
        app.status = "REJECTED"
        
        if was_shortlisted:
            drive = db.query(PlacementDrive).filter(PlacementDrive.drive_id == app.drive_id).first()
            if drive:
                drive.shortlisted_count = max(0, (drive.shortlisted_count or 1) - 1)
                _promote_waitlisted(db, drive)

        db.commit()

        return returnSuccess(
            {"application_id": app.application_id, "status": "REJECTED"},
            message="Application rejected.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 11. POST /placement/drive/applications/waitlist — SHORTLISTED → WAITLISTED
# ===========================================================================


class WaitlistPayload(_PydanticBase):
    application_id: int


@router.post("/applications/waitlist")
def waitlist_application(
    payload: WaitlistPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Move a SHORTLISTED application back to WAITLISTED (TPO manual demotion).
    Decrements the drive's shortlisted_count.
    """
    try:
        from app.db.placement_models import PLMApplication

        app = (
            db.query(PLMApplication)
            .filter(PLMApplication.application_id == payload.application_id)
            .first()
        )
        if not app:
            return returnException(f"Application {payload.application_id} not found.")

        if app.status != "SHORTLISTED":
            return returnException(
                f"Only SHORTLISTED applications can be moved to waitlist. "
                f"Current status: '{app.status}'."
            )

        app.status = "WAITLISTED"

        # Decrement shortlisted_count on the drive
        drive = (
            db.query(PlacementDrive)
            .filter(PlacementDrive.drive_id == app.drive_id)
            .first()
        )
        if drive and drive.shortlisted_count and drive.shortlisted_count > 0:
            drive.shortlisted_count = drive.shortlisted_count - 1
            drive.modify_date = datetime.now()

        db.commit()

        return returnSuccess(
            {"application_id": app.application_id, "status": "WAITLISTED"},
            message="Application moved to waitlist.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 12. POST /placement/drive/applications/auto-shortlist — Auto shortlist
#     Two-phase priority logic:
#       PHASE 1: Branch-eligible students (APPLIED/WAITLISTED, backlogs OK)
#         → sorted by CGPA DESC, shortlisted first up to vacancy.
#       PHASE 2: Other-branch students with CGPA >= min_cgpa (backlogs OK)
#         → fill remaining slots sorted by CGPA DESC (9.3 → 9.0 → 8.7…)
#         until shortlisted == vacancy.
#       Everyone else → WAITLISTED.
# ===========================================================================


class AutoShortlistPayload(_PydanticBase):
    drive_id: int


@router.post("/applications/auto-shortlist")
def auto_shortlist_applications(
    payload: AutoShortlistPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Automatically shortlist applicants for a drive based on:
      - Eligible branches configured for the drive
      - Minimum CGPA criteria
      - Maximum backlogs criteria
    Picks the top N applicants sorted by CGPA DESC (N = vacancy_count).
    All remaining APPLIED applicants are moved to WAITLISTED.
    Only processes applicants currently in APPLIED status.
    """
    try:
        from app.db.placement_models import PLMApplication, PLMStudentProfile
        from app.db.models import IEMStudents

        resolved_org = org_id or 1

        # 1. Fetch the drive
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

        vacancy = drive.vacancy_count
        is_unlimited = (vacancy is None or vacancy <= 0)

        # 2. Count TOTAL applications
        applied_count = (
            db.query(func.count(PLMApplication.application_id))
            .filter(
                PLMApplication.drive_id == payload.drive_id,
            )
            .scalar()
            or 0
        )

        if not is_unlimited and applied_count <= vacancy:
            return returnException(
                f"Auto-shortlisting requires more applicants than vacancies. "
                f"Applied: {applied_count}, Vacancy: {vacancy}. "
                f"When applied ≤ vacancy, you can shortlist all directly."
            )

        # 3. Get eligible branch dept_ids for this drive
        eligible_dept_ids = [
            row.dept_id
            for row in db.query(PlacementDriveEligibleBranch.dept_id)
            .filter(PlacementDriveEligibleBranch.drive_id == payload.drive_id)
            .all()
        ]

        min_cgpa = float(drive.min_cgpa) if drive.min_cgpa is not None else 0.0
        max_backlogs = drive.max_backlogs if drive.max_backlogs is not None else 999

        # 4. Fetch all APPLIED + WAITLISTED applicants with profile + student info.
        #    WAITLISTED are included so Phase 2 can promote other-branch high-CGPA
        #    students on re-runs when some slots remain unfilled.
        rows = (
            db.query(PLMApplication, PLMStudentProfile, IEMStudents)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .filter(
                PLMApplication.drive_id == payload.drive_id,
                PLMApplication.status.in_(["APPLIED", "WAITLISTED"]),
            )
            .all()
        )

        if not rows:
            return returnException(
                "No processable candidates found (all are already shortlisted, offered, or rejected)."
            )

        # 5. Split into two pools (two-phase priority):
        #    Pool A (Phase 1): branch-eligible students (backlogs OK)
        #      → shortlisted first, sorted by CGPA DESC, up to remaining_vacancy
        #    Pool B (Phase 2): other-branch students with CGPA >= min_cgpa (backlogs OK)
        #      → fill remaining slots, sorted by CGPA DESC (9.3 → 9.0 → 8.7…)
        pool_a = []   # (app, cgpa) — branch-eligible
        pool_b = []   # (app, cgpa) — other-branch, high CGPA
        ineligible_ids = []

        for app, profile, student in rows:
            cgpa = float(profile.current_cgpa) if profile.current_cgpa is not None else 0.0
            backlogs = int(profile.backlogs or 0)
            dept_id = student.department_id

            backlogs_ok = backlogs <= max_backlogs
            branch_ok = (dept_id in eligible_dept_ids) if eligible_dept_ids else True

            if not backlogs_ok:
                ineligible_ids.append(app.application_id)
            elif branch_ok:
                pool_a.append((app, cgpa))   # Phase 1 — eligible branch, always priority
            elif cgpa >= min_cgpa:
                pool_b.append((app, cgpa))   # Phase 2 — other branch, CGPA fill-up
            else:
                ineligible_ids.append(app.application_id)

        # 6. Sort both pools by CGPA DESC
        pool_a.sort(key=lambda x: x[1], reverse=True)
        pool_b.sort(key=lambda x: x[1], reverse=True)

        # 6b. Check remaining vacancy
        current_shortlisted = (
            db.query(func.count(PLMApplication.application_id))
            .filter(
                PLMApplication.drive_id == payload.drive_id,
                PLMApplication.status == "SHORTLISTED",
            )
            .scalar()
            or 0
        )
        
        remaining_vacancy = None
        if not is_unlimited:
            remaining_vacancy = vacancy - current_shortlisted
            if remaining_vacancy <= 0:
                return returnException("Vacancy cap has already been reached. Cannot auto-shortlist further.")

        shortlist_ids = []
        waitlist_ids = list(ineligible_ids)

        # ── Phase 1: Shortlist from eligible-branch pool ──────────────────────
        if is_unlimited:
            phase1_picks = pool_a
            phase1_leftover = []
        else:
            phase1_picks = pool_a[:remaining_vacancy]
            phase1_leftover = pool_a[remaining_vacancy:]
            
        for app, _ in phase1_picks:
            shortlist_ids.append(app.application_id)
        for app, _ in phase1_leftover:
            waitlist_ids.append(app.application_id)

        # ── Phase 2: Fill remaining slots from other-branch / CGPA pool ───────
        phase2_count = 0
        if is_unlimited:
            phase2_picks = pool_b
            phase2_leftover = []
            phase2_count = len(phase2_picks)
            for app, _ in phase2_picks:
                shortlist_ids.append(app.application_id)
        else:
            slots_left = remaining_vacancy - len(shortlist_ids)
            if slots_left > 0 and pool_b:
                phase2_picks = pool_b[:slots_left]
                phase2_leftover = pool_b[slots_left:]
                phase2_count = len(phase2_picks)
                for app, _ in phase2_picks:
                    shortlist_ids.append(app.application_id)
                for app, _ in phase2_leftover:
                    waitlist_ids.append(app.application_id)
            else:
                for app, _ in pool_b:
                    waitlist_ids.append(app.application_id)

        # 7. Bulk update statuses
        if shortlist_ids:
            db.query(PLMApplication).filter(
                PLMApplication.application_id.in_(shortlist_ids)
            ).update({"status": "SHORTLISTED", "is_eligible": 1}, synchronize_session=False)

        if waitlist_ids:
            db.query(PLMApplication).filter(
                PLMApplication.application_id.in_(waitlist_ids)
            ).update({"status": "WAITLISTED"}, synchronize_session=False)

        # 8. Update drive shortlisted_count (add newly shortlisted to existing count)
        drive.shortlisted_count = current_shortlisted + len(shortlist_ids)
        drive.modify_date = datetime.now()

        db.commit()

        phase1_count = len(phase1_picks) if is_unlimited else len(phase1_picks)

        return returnSuccess(
            {
                "shortlisted": len(shortlist_ids),
                "shortlisted_phase1_branch": phase1_count,
                "shortlisted_phase2_cgpa": phase2_count,
                "waitlisted": len(waitlist_ids),
                "vacancy": vacancy,
                "applied_processed": len(rows),
            },
            message=(
                f"Auto-shortlisting complete. {len(shortlist_ids)} student(s) shortlisted "
                f"({phase1_count} from eligible branches"
                + (f", {phase2_count} filled from other branches by CGPA" if phase2_count > 0 else "")
                + f"). {len(waitlist_ids)} moved to waiting list."
            ),
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 12. POST /placement/drive/applications/override-shortlist
# ===========================================================================
class OverrideShortlistPayload(BaseModel):
    application_id: int
    reason: Optional[str] = None

@router.post("/applications/override-shortlist")
def override_shortlist_application(
    payload: OverrideShortlistPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Promote a WAITLISTED student to SHORTLISTED bypassing vacancy limits.
    Requires providing a reason (justification).
    """
    try:
        from app.db.placement_models import PLMApplication
        
        app = (
            db.query(PLMApplication)
            .filter(PLMApplication.application_id == payload.application_id)
            .first()
        )
        if not app:
            return returnException(f"Application {payload.application_id} not found.")

        if app.status != "WAITLISTED":
            return returnException(f"Can only override waitlisted applications (current: {app.status}).")

        app.status = "SHORTLISTED"
        if payload.reason and payload.reason.strip():
            app.override_reason = payload.reason.strip()
        
        drive = db.query(PlacementDrive).filter(PlacementDrive.drive_id == app.drive_id).first()
        if drive:
            drive.shortlisted_count = (drive.shortlisted_count or 0) + 1

        db.commit()

        return returnSuccess(
            {"application_id": app.application_id, "status": "SHORTLISTED"},
            message="Student shortlisted via override.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 13. POST /placement/drive/applications/override-reject
# ===========================================================================
class OverrideRejectPayload(BaseModel):
    application_id: int
    reason: Optional[str] = None

@router.post("/applications/override-reject")
def override_reject_application(
    payload: OverrideRejectPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Reject a WAITLISTED student permanently from the override page.
    """
    try:
        from app.db.placement_models import PLMApplication
        
        app = (
            db.query(PLMApplication)
            .filter(PLMApplication.application_id == payload.application_id)
            .first()
        )
        if not app:
            return returnException(f"Application {payload.application_id} not found.")

        if app.status != "WAITLISTED":
            return returnException(f"Can only reject waitlisted applications via this endpoint (current: {app.status}).")

        # Revert to normal waitlist by clearing the override reason/request
        app.status = "WAITLISTED"
        app.override_reason = None
        db.commit()

        return returnSuccess(
            {"application_id": app.application_id, "status": "WAITLISTED"},
            message="Override request rejected, student reverted to waitlist.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 14. POST /placement/drive/applications/override-request
# ===========================================================================
class OverrideRequestPayload(BaseModel):
    application_id: int
    reason: str

@router.post("/applications/override-request")
def override_request_application(
    payload: OverrideRequestPayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Officer requests override for a WAITLISTED student, saving justification/remarks.
    """
    try:
        from app.db.placement_models import PLMApplication
        
        app = (
            db.query(PLMApplication)
            .filter(PLMApplication.application_id == payload.application_id)
            .first()
        )
        if not app:
            return returnException(f"Application {payload.application_id} not found.")

        if app.status != "WAITLISTED":
            return returnException(f"Can only request override for waitlisted applications (current: {app.status}).")

        if not payload.reason.strip():
            return returnException("Reason is required for override request.")

        app.override_reason = payload.reason.strip()
        db.commit()

        return returnSuccess(
            {"application_id": app.application_id, "status": "WAITLISTED"},
            message="Override request submitted successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


