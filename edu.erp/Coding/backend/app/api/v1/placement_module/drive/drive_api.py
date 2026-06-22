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
