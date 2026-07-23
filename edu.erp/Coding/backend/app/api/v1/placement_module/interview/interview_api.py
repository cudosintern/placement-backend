"""
interview_api.py
================
Placement Interview Management — API Endpoints

Endpoints:
  GET  /placement/interview/meta                          - Active drives + rounds for dropdowns
  GET  /placement/interview/slot/eligible-students        - Shortlisted students for a drive+round
  GET  /placement/interview/schedule/list                 - All schedules for a drive
  GET  /placement/interview/schedule/detail/{id}          - One schedule + all its slots
  POST /placement/interview/schedule/save                 - Create schedule + slots (atomic)
  PUT  /placement/interview/schedule/save                 - Update schedule + slots (atomic)
  DELETE /placement/interview/schedule/{schedule_id}      - Soft delete (is_active = 0)
  GET  /placement/interview/result/list                   - All results for a drive+round
  POST /placement/interview/result/save                   - Bulk upsert results
  GET  /placement/interview/holidays                      - Org holidays for calendar blocking
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.v1.placement_module.interview.interview_schema import (
    ResultBulkSavePayload,
    ResultOverridePayload,
    ScheduleSavePayload,
)
from app.core.database import get_db
from app.db.models import IEMSDepartment, IEMStudents
from app.db.placement_models import (
    PLMApplication,
    PLMStudentProfile,
    PLMStudentResume,
    PlacementCompany,
    PlacementDrive,
    PlacementDriveRound,
)
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()

# ---------------------------------------------------------------------------
# Helper: parse "YYYY-MM-DD HH:MM" or "YYYY-MM-DD HH:MM:SS" → datetime | None
# ---------------------------------------------------------------------------

VALID_RESULTS = {"PASS", "FAIL", "HOLD", "ABSENT"}
VALID_MODES = {
    "BATCH_SIMULTANEOUS",
    "BATCH_SEQUENTIAL",
    "ALL_SIMULTANEOUS",
    "ALL_SEQUENTIAL",
}
VALID_VENUE = {"PHYSICAL", "VIRTUAL"}


from datetime import date, datetime

def _parse_dt(s) -> Optional[datetime]:
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_date(s):
    if not s:
        return None
    if isinstance(s, date):
        return s
    if isinstance(s, datetime):
        return s.date()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Lazy-import interview models (defined in placement_models.py additions)
# We import inline to avoid circular-import risk during startup.
# ---------------------------------------------------------------------------


def _get_schedule_model():
    from app.db.placement_models import PlacementInterviewSchedule
    return PlacementInterviewSchedule


def _get_slot_model():
    from app.db.placement_models import PlacementInterviewSlot
    return PlacementInterviewSlot


def _get_result_model():
    from app.db.placement_models import PlacementRoundResult
    return PlacementRoundResult


def _get_holiday_model():
    from app.db.placement_models import PlacementOrgHoliday
    return PlacementOrgHoliday







# ===========================================================================
# 1. GET /placement/interview/meta
#    Active drives (status 1 or 2) with their rounds.
#    Joins plm_company for company_name.
#    Each round includes duration_minutes so the wizard can pre-fill.
# ===========================================================================


@router.get("/meta")
def get_interview_meta(
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Returns active drives and their rounds for the wizard dropdowns.
    - Only drives with status IN (1=Scheduled, 2=Active) are returned.
    - Each round carries duration_minutes from plm_drive_round.
    - Sorted: drives by create_date DESC, rounds by round_number ASC.
    """
    try:
        resolved_org = org_id or 1

        # Fetch active drives with company name
        drives = (
            db.query(PlacementDrive, PlacementCompany)
            .join(
                PlacementCompany,
                PlacementCompany.company_id == PlacementDrive.company_id,
            )
            .filter(
                PlacementDrive.org_id == resolved_org,
                PlacementDrive.status.in_([1, 2]),  # Scheduled or Active
            )
            .order_by(PlacementDrive.create_date.desc())
            .all()
        )

        result = []
        for drive, company in drives:
            # Rounds for this drive — ordered by sequence
            rounds = (
                db.query(PlacementDriveRound)
                .filter(PlacementDriveRound.drive_id == drive.drive_id)
                .order_by(PlacementDriveRound.round_number.asc())
                .all()
            )

            # Count shortlisted applicants for display
            shortlisted_count = (
                db.query(func.count(PLMApplication.application_id))
                .filter(
                    PLMApplication.drive_id == drive.drive_id,
                    PLMApplication.status == "SHORTLISTED",
                )
                .scalar()
                or 0
            )

            result.append(
                {
                    "drive_id": drive.drive_id,
                    "company_id": company.company_id,
                    "drive_name": drive.drive_name,
                    "company_name": company.company_name,
                    "status": drive.status,
                    "drive_date": str(drive.drive_date) if drive.drive_date else None,
                    "shortlisted_count": shortlisted_count,
                    "min_cgpa": float(drive.min_cgpa) if drive.min_cgpa is not None else 0.0,
                    "max_backlogs": drive.max_backlogs if drive.max_backlogs is not None else 0,
                    "job_role": drive.job_role,
                    "ctc_min": float(drive.ctc_min) if drive.ctc_min is not None else None,
                    "ctc_max": float(drive.ctc_max) if drive.ctc_max is not None else None,
                    "rounds": [
                        {
                            "round_id": r.round_id,
                            "round_name": r.round_name,
                            "round_number": r.round_number,
                            "round_type": r.round_type,
                            "duration_minutes": r.duration_minutes or 30,
                            "round_date": str(r.round_date) if r.round_date else None,
                        }
                        for r in rounds
                    ],
                }
            )

        return returnSuccess(
            {"drives": result, "total": len(result)},
            message=f"{len(result)} active drive(s) found.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 2. GET /placement/interview/slot/eligible-students
#    Shortlisted students for a drive+round.
#    Copies JOIN pattern from drive_api.py:808-830 exactly.
#    Optimized: single query with all needed JOINs, sorted by CGPA DESC.
# ===========================================================================


@router.get("/slot/eligible-students")
def get_eligible_students(
    drive_id: int = Query(..., description="plm_drive.drive_id"),
    round_id: int = Query(..., description="plm_drive_round.round_id"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Returns students eligible for scheduling for a given round.

    Round 1: filters PLMApplication.status == 'SHORTLISTED'
    Round 2+: filters applications where the student PASSED the previous round
              (plm_round_result.result = 'PASS' for prev_round_id)

    Excludes students already scheduled for this round (have a slot in plm_interview_slot).
    Sorted by current_cgpa DESC for TPO review.
    """
    try:
        resolved_org = org_id or 1

        # Validate drive exists in this org
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

        # Validate round belongs to this drive
        round_ = (
            db.query(PlacementDriveRound)
            .filter(
                PlacementDriveRound.round_id == round_id,
                PlacementDriveRound.drive_id == drive_id,
            )
            .first()
        )
        if not round_:
            return returnException(
                f"Round {round_id} does not belong to Drive {drive_id}."
            )

        # Find application_ids already scheduled for this round (to exclude)
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()
        PlacementRoundResult = _get_result_model()

        already_scheduled_ids = set()
        existing_schedule = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.drive_id == drive_id,
                PlacementInterviewSchedule.round_id == round_id,
                PlacementInterviewSchedule.is_active == 1,
            )
            .first()
        )
        if existing_schedule:
            slot_rows = (
                db.query(PlacementInterviewSlot.application_id)
                .filter(
                    PlacementInterviewSlot.schedule_id == existing_schedule.schedule_id
                )
                .all()
            )
            already_scheduled_ids = {r[0] for r in slot_rows}

        # ── Determine which application_ids are eligible ──────────────────────
        eligible_app_ids: Optional[set] = None  # None = no restriction (Round 1)

        if round_.round_number > 1:
            # Round 2+: only students who PASSED the previous round
            prev_round = (
                db.query(PlacementDriveRound)
                .filter(
                    PlacementDriveRound.drive_id == drive_id,
                    PlacementDriveRound.round_number == round_.round_number - 1,
                )
                .first()
            )
            if not prev_round:
                return returnException(
                    f"Cannot find round {round_.round_number - 1} for Drive {drive_id}."
                )
            pass_results = (
                db.query(PlacementRoundResult.application_id)
                .filter(
                    PlacementRoundResult.round_id == prev_round.round_id,
                    PlacementRoundResult.result == "PASS",
                )
                .all()
            )
            eligible_app_ids = {r[0] for r in pass_results}
            if not eligible_app_ids:
                return returnSuccess(
                    {
                        "students": [],
                        "total": 0,
                        "round_name": round_.round_name,
                        "round_number": round_.round_number,
                        "duration_minutes": round_.duration_minutes or 30,
                        "already_scheduled": len(already_scheduled_ids),
                    },
                    message=f"No students passed Round {round_.round_number - 1} yet.",
                )

        # ── Main query ────────────────────────────────────────────────────────
        query = (
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
        )

        if eligible_app_ids is None:
            # Round 1 — must be SHORTLISTED
            query = query.filter(PLMApplication.status == "SHORTLISTED")
        else:
            # Round 2+ — must be in the PASS set from previous round
            query = query.filter(PLMApplication.application_id.in_(eligible_app_ids))

        rows = query.order_by(PLMStudentProfile.current_cgpa.desc()).all()

        students = []
        for app, profile, student, dept in rows:
            if app.application_id in already_scheduled_ids:
                continue  # Skip already scheduled
            name = (
                student.name
                or f"{student.first_name or ''} {student.last_name or ''}".strip()
            )
            students.append(
                {
                    "application_id": app.application_id,
                    "student_id": student.student_id,
                    "student_name": name,
                    "usno": student.usno or "",
                    "email": student.email or "",
                    "branch": dept.dept_name if dept else "",
                    "cgpa": (
                        float(profile.current_cgpa)
                        if profile.current_cgpa is not None
                        else 0.0
                    ),
                    "backlogs": int(profile.backlogs or 0),
                }
            )

        return returnSuccess(
            {
                "students": students,
                "total": len(students),
                "round_name": round_.round_name,
                "round_number": round_.round_number,
                "duration_minutes": round_.duration_minutes or 30,
                "already_scheduled": len(already_scheduled_ids),
            },
            message=f"{len(students)} student(s) eligible for {round_.round_name}.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 3. GET /placement/interview/schedule/list?drive_id=X
#    All confirmed schedules for a drive (one card per round).
# ===========================================================================


@router.get("/schedule/list")
def get_schedule_list(
    drive_id: int = Query(..., description="plm_drive.drive_id"),
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Returns all active schedules for a drive, joined with drive + round names.
    Used to populate the schedule cards on InterviewSchedulePage.
    """
    try:
        resolved_org = org_id or 1
        PlacementInterviewSchedule = _get_schedule_model()

        rows = (
            db.query(PlacementInterviewSchedule, PlacementDrive, PlacementDriveRound, PlacementCompany)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementInterviewSchedule.drive_id)
            .join(PlacementDriveRound, PlacementDriveRound.round_id == PlacementInterviewSchedule.round_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .filter(
                PlacementInterviewSchedule.drive_id == drive_id,
                PlacementInterviewSchedule.is_active == 1,
                PlacementDrive.org_id == resolved_org,
            )
            .order_by(PlacementInterviewSchedule.schedule_id.desc())
            .all()
        )

        schedules = []
        for sched, drive, rnd, company in rows:
            # F4: count notified slots and find last sent timestamp
            notif_stats = db.execute(
                text("""
                    SELECT COUNT(*) as sent_count, MAX(notification_sent_at) as last_sent
                    FROM plm_interview_slot
                    WHERE schedule_id = :sid AND notification_sent_at IS NOT NULL
                """),
                {"sid": sched.schedule_id},
            ).first()
            notification_sent_count = notif_stats.sent_count if notif_stats else 0
            last_notification_sent_at = (
                notif_stats.last_sent.strftime("%Y-%m-%dT%H:%M:%S")
                if notif_stats and notif_stats.last_sent
                else None
            )
            all_notified = (
                notification_sent_count >= sched.total_students
                and sched.total_students > 0
            )

            schedules.append(
                {
                    "schedule_id": sched.schedule_id,
                    "drive_id": drive.drive_id,
                    "drive_name": drive.drive_name,
                    "company_name": company.company_name,
                    "round_id": rnd.round_id,
                    "round_name": rnd.round_name,
                    "round_number": rnd.round_number,
                    "round_type": rnd.round_type,
                    "scheduling_mode": sched.scheduling_mode,
                    "total_students": sched.total_students,
                    "total_slots": sched.total_slots,
                    "days_required": sched.days_required,
                    "start_date": str(sched.scheduled_date) if sched.scheduled_date else None,
                    "end_date": str(sched.end_date) if sched.end_date else None,
                    "venue_type": sched.venue_type,
                    "venue_details": sched.venue_details,
                    "meeting_link": sched.meeting_link,
                    "interviewer_names": sched.interviewer_names,
                    "created_at": str(sched.created_at) if sched.created_at else None,
                    "is_active": sched.is_active,
                    "status": sched.status or "DRAFT",
                    # F4: notification status fields
                    "notification_sent_count": notification_sent_count,
                    "all_notified": all_notified,
                    "last_notification_sent_at": last_notification_sent_at,
                }
            )

        return returnSuccess(
            {"schedules": schedules, "total": len(schedules)},
            message=f"{len(schedules)} schedule(s) found.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 4. GET /placement/interview/schedule/detail/{schedule_id}
#    Full schedule header + all slots with student info.
# ===========================================================================


@router.get("/schedule/detail/{schedule_id}")
def get_schedule_detail(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns one schedule and all its slots with student display data.
    Used by RoundResultPage and InterviewSlotPage.

    Optimized: joins slots with student info in a single query (no N+1).
    """
    try:
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        sched = (
            db.query(PlacementInterviewSchedule)
            .filter(PlacementInterviewSchedule.schedule_id == schedule_id)
            .first()
        )
        if not sched:
            return returnException(f"Schedule {schedule_id} not found.")

        rnd = (
            db.query(PlacementDriveRound)
            .filter(PlacementDriveRound.round_id == sched.round_id)
            .first()
        )

        # Single JOIN query for all slots — avoids N+1
        slot_rows = (
            db.query(PlacementInterviewSlot, PLMApplication, PLMStudentProfile, IEMStudents, IEMSDepartment)
            .join(PLMApplication, PLMApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(IEMSDepartment, IEMSDepartment.dept_id == IEMStudents.department_id)
            .filter(PlacementInterviewSlot.schedule_id == schedule_id)
            .order_by(
                PlacementInterviewSlot.batch_number.asc(),
                PlacementInterviewSlot.seq_number.asc(),
            )
            .all()
        )

        slots = []
        for slot, app, profile, student, dept in slot_rows:
            name = (
                student.name
                or f"{student.first_name or ''} {student.last_name or ''}".strip()
            )
            slots.append(
                {
                    "slot_id": slot.slot_id,
                    "schedule_id": slot.schedule_id,
                    "application_id": slot.application_id,
                    "student_name": name,
                    "usno": student.usno or "",
                    "email": student.email or "",
                    "branch": dept.dept_name if dept else "",
                    "cgpa": float(profile.current_cgpa) if profile.current_cgpa is not None else None,
                    "round_name": rnd.round_name if rnd else "",
                    "slot_time": (
                        slot.slot_time.strftime("%Y-%m-%d %H:%M")
                        if slot.slot_time
                        else None
                    ),
                    "batch_number": slot.batch_number,
                    "seq_number": slot.seq_number,
                    "interviewer_name": slot.interviewer_name,
                    "interviewer_email": slot.interviewer_email,
                    "interviewer_id": slot.interviewer_id,
                    "student_id": slot.student_id,
                    "contact_id": slot.contact_id,
                    "status": slot.status,
                }
            )

        schedule_out = {
            "schedule_id": sched.schedule_id,
            "drive_id": sched.drive_id,
            "round_id": sched.round_id,
            "scheduling_mode": sched.scheduling_mode,
            "batch_size": sched.batch_size,
            "total_students": sched.total_students,
            "total_slots": sched.total_slots,
            "days_required": sched.days_required,
            "start_date": str(sched.scheduled_date) if sched.scheduled_date else None,
            "end_date": str(sched.end_date) if sched.end_date else None,
            "venue_type": sched.venue_type,
            "venue_details": sched.venue_details,
            "meeting_link": sched.meeting_link,
            "interviewer_names": sched.interviewer_names,
            "status": sched.status or "DRAFT",
            "is_active": sched.is_active,
        }

        return returnSuccess(
            {"schedule": schedule_out, "slots": slots, "slots_count": len(slots)},
            message=f"Schedule loaded with {len(slots)} slot(s).",
        )
    except Exception as e:
        return returnException(str(e))


def check_interviewer_conflicts(db: Session, company_id: int, current_schedule_id: Optional[int], slots: list, contacts_map: dict) -> Optional[str]:
    from app.db.placement_models import PlacementInterviewSchedule, PlacementInterviewSlot, PlacementDrive
    
    # 1. Get all drives for this company
    drives = db.query(PlacementDrive).filter(PlacementDrive.company_id == company_id).all()
    drive_map = {d.drive_id: d for d in drives}
    drive_ids = list(drive_map.keys())
    if not drive_ids:
        return None
        
    # 2. Get all existing slots for these drives' active schedules
    query = db.query(
        PlacementInterviewSlot.slot_time,
        PlacementInterviewSlot.contact_id,
        PlacementInterviewSlot.interviewer_id,
        PlacementInterviewSlot.interviewer_name,
        PlacementInterviewSchedule.drive_id
    ).join(
        PlacementInterviewSchedule,
        PlacementInterviewSchedule.schedule_id == PlacementInterviewSlot.schedule_id
    ).filter(
        PlacementInterviewSchedule.drive_id.in_(drive_ids),
        PlacementInterviewSchedule.is_active == 1,
        PlacementInterviewSlot.status != "CANCELLED"
    )
    
    if current_schedule_id is not None:
        query = query.filter(PlacementInterviewSchedule.schedule_id != current_schedule_id)
        
    existing_slots = query.all()
    
    # Build conflict mapping of: (interviewer_identifier, slot_time_str) -> drive_id
    conflict_map = {}
    for slot_time, cid, iid, name, drive_id in existing_slots:
        if not slot_time:
            continue
        dt_str = slot_time.strftime("%Y-%m-%d %H:%M:%S")
        if cid:
            conflict_map[(cid, dt_str)] = drive_id
        if iid:
            conflict_map[(iid, dt_str)] = drive_id
        if name:
            conflict_map[(name.strip().lower(), dt_str)] = drive_id
            
    # 3. Check slots in payload for conflicts
    for item in slots:
        if not item.slot_time:
            continue
            
        parsed_dt = _parse_dt(item.slot_time)
        if not parsed_dt:
            continue
        dt_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        cid = item.contact_id or item.interviewer_id
        name_val = item.interviewer_name
        if cid and cid in contacts_map:
            name_val = contacts_map[cid].name
            
        conflicting_drive_id = None
        if cid and (cid, dt_str) in conflict_map:
            conflicting_drive_id = conflict_map[(cid, dt_str)]
        elif name_val and (name_val.strip().lower(), dt_str) in conflict_map:
            conflicting_drive_id = conflict_map[(name_val.strip().lower(), dt_str)]
            
        if conflicting_drive_id is not None:
            conflicting_drive = drive_map.get(conflicting_drive_id)
            conflicting_drive_name = conflicting_drive.drive_name if conflicting_drive else f"Drive ID {conflicting_drive_id}"
            return f"{name_val or 'Interviewer'} already assigned to this and {conflicting_drive_name} at this time we cannot assign him at same time"
            
    return None


# ===========================================================================
# 5. POST /placement/interview/schedule/save — CREATE schedule + slots
# 6. PUT  /placement/interview/schedule/save — UPDATE schedule + slots
#    Both use the same ScheduleSavePayload. PUT requires schedule_id in payload.
#    Atomic: one transaction for header + all slots.
# ===========================================================================


@router.post("/schedule/save")
def create_schedule(
    payload: ScheduleSavePayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Create a new interview schedule with all student slots.

    Validations:
      - Drive exists and belongs to org
      - Round belongs to the drive
      - No existing active schedule for this round (prevent duplicates)
      - Scheduling mode is one of the 4 valid options
      - venue_type is PHYSICAL or VIRTUAL
      - All slot application_ids belong to this drive

    Atomic:
      1. INSERT plm_interview_schedule (header)
      2. Bulk INSERT plm_interview_slot (all slots)
    """
    try:
        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        # ── Validations ───────────────────────────────────────────────────────
        if payload.scheduling_mode not in VALID_MODES:
            return returnException(
                f"Invalid scheduling_mode '{payload.scheduling_mode}'. "
                f"Must be one of: {', '.join(VALID_MODES)}"
            )
        if payload.venue_type not in VALID_VENUE:
            return returnException(
                f"Invalid venue_type '{payload.venue_type}'. Must be PHYSICAL or VIRTUAL."
            )

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

        round_ = (
            db.query(PlacementDriveRound)
            .filter(
                PlacementDriveRound.round_id == payload.round_id,
                PlacementDriveRound.drive_id == payload.drive_id,
            )
            .first()
        )
        if not round_:
            return returnException(
                f"Round {payload.round_id} does not belong to Drive {payload.drive_id}."
            )

        # Check duplicate — one active schedule per round per drive
        existing = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.drive_id == payload.drive_id,
                PlacementInterviewSchedule.round_id == payload.round_id,
                PlacementInterviewSchedule.is_active == 1,
            )
            .first()
        )
        if existing:
            return returnException(
                f"An active schedule already exists for Round {round_.round_name} "
                f"(Schedule ID: {existing.schedule_id}). "
                f"Use PUT to update or DELETE to remove it first."
            )

        # Fetch company contacts map for interviewer name/email auto-fill & conflict validation
        contacts_map = {}
        if drive:
            from app.db.placement_models import PLMCompanyContact
            contacts = db.query(PLMCompanyContact).filter(
                PLMCompanyContact.company_id == drive.company_id,
                PLMCompanyContact.is_active == 1
            ).all()
            contacts_map = {c.contact_id: c for c in contacts}

        # Check interviewer slot conflict
        conflict_msg = check_interviewer_conflicts(
            db=db,
            company_id=drive.company_id,
            current_schedule_id=None,
            slots=payload.slots,
            contacts_map=contacts_map
        )
        if conflict_msg:
            return returnException(conflict_msg)

        # ── Atomic insert ─────────────────────────────────────────────────────
        new_sched = PlacementInterviewSchedule(
            drive_id=payload.drive_id,
            round_id=payload.round_id,
            org_id=resolved_org,
            venue_type=payload.venue_type,
            venue_details=payload.venue_details,
            meeting_link=payload.meeting_link,
            scheduled_date=_parse_date(payload.start_date),
            start_time="09:00",
            end_time="17:00",
            scheduling_mode=payload.scheduling_mode,
            batch_size=payload.batch_size,
            total_students=payload.total_students,
            total_slots=payload.total_slots,
            days_required=payload.days_required,
            end_date=_parse_date(payload.end_date),
            interviewer_names=payload.interviewer_names,
            interviewer_email=payload.interviewer_email,
            status="DRAFT",
            is_active=1,
            created_by=user_id,
            created_at=datetime.now(),
        )
        db.add(new_sched)
        db.flush()  # Get schedule_id before inserting slots

        # Bulk insert slots (F2: write interviewer_id + student_id)
        slot_objects = []
        for item in payload.slots:
            name_val = item.interviewer_name
            email_val = item.interviewer_email
            if item.contact_id and item.contact_id in contacts_map:
                contact_rec = contacts_map[item.contact_id]
                name_val = contact_rec.name
                email_val = contact_rec.email

            slot_objects.append(
                PlacementInterviewSlot(
                    schedule_id=new_sched.schedule_id,
                    application_id=item.application_id,
                    slot_time=_parse_dt(item.slot_time),
                    batch_number=item.batch_number,
                    seq_number=item.seq_number,
                    interviewer_name=name_val,
                    interviewer_email=email_val,
                    interviewer_id=item.interviewer_id,   # F2
                    student_id=item.student_id,           # F2
                    contact_id=item.contact_id,
                    status="SCHEDULED",
                )
            )
        db.bulk_save_objects(slot_objects)
        db.commit()

        return returnSuccess(
            {
                "schedule_id": new_sched.schedule_id,
                "total_slots_saved": len(slot_objects),
                "drive_id": payload.drive_id,
                "round_id": payload.round_id,
            },
            message=(
                f"Schedule created for '{round_.round_name}' with "
                f"{len(slot_objects)} student slot(s)."
            ),
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.put("/schedule/save")
def update_schedule(
    payload: ScheduleSavePayload,
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Update an existing schedule — replaces all slots atomically.
    payload.schedule_id is required.

    Atomic:
      1. UPDATE plm_interview_schedule header
      2. DELETE existing slots for this schedule
      3. Bulk INSERT new slots
    """
    try:
        if not payload.schedule_id:
            return returnException(
                "schedule_id is required for update. Use POST to create a new schedule."
            )

        resolved_org = org_id or 1
        user_id = current_user.get("user_id", 1)

        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        sched = (
            db.query(PlacementInterviewSchedule)
            .filter(PlacementInterviewSchedule.schedule_id == payload.schedule_id)
            .first()
        )
        if not sched:
            return returnException(f"Schedule {payload.schedule_id} not found.")

        round_ = (
            db.query(PlacementDriveRound)
            .filter(PlacementDriveRound.round_id == sched.round_id)
            .first()
        )

        # Validate mode and venue
        if payload.scheduling_mode not in VALID_MODES:
            return returnException(f"Invalid scheduling_mode '{payload.scheduling_mode}'.")
        if payload.venue_type not in VALID_VENUE:
            return returnException(f"Invalid venue_type '{payload.venue_type}'.")

        # Update header
        sched.venue_type = payload.venue_type
        sched.venue_details = payload.venue_details
        sched.meeting_link = payload.meeting_link
        sched.scheduling_mode = payload.scheduling_mode
        sched.batch_size = payload.batch_size
        sched.total_students = payload.total_students
        sched.total_slots = payload.total_slots
        sched.days_required = payload.days_required
        sched.scheduled_date = _parse_date(payload.start_date)
        sched.end_date = _parse_date(payload.end_date)
        sched.interviewer_names = payload.interviewer_names
        sched.interviewer_email = payload.interviewer_email
        sched.updated_at = datetime.now()

        # Fetch company contacts map for interviewer name/email auto-fill & conflict validation
        contacts_map = {}
        if sched and sched.drive_id:
            from app.db.placement_models import PLMCompanyContact, PlacementDrive
            drive = db.query(PlacementDrive).filter(PlacementDrive.drive_id == sched.drive_id).first()
            if drive:
                contacts = db.query(PLMCompanyContact).filter(
                    PLMCompanyContact.company_id == drive.company_id,
                    PLMCompanyContact.is_active == 1
                ).all()
                contacts_map = {c.contact_id: c for c in contacts}

                # Check interviewer slot conflict
                conflict_msg = check_interviewer_conflicts(
                    db=db,
                    company_id=drive.company_id,
                    current_schedule_id=payload.schedule_id,
                    slots=payload.slots,
                    contacts_map=contacts_map
                )
                if conflict_msg:
                    return returnException(conflict_msg)

        # Replace slots — delete old, insert new
        db.query(PlacementInterviewSlot).filter(
            PlacementInterviewSlot.schedule_id == payload.schedule_id
        ).delete(synchronize_session=False)

        # F2: include interviewer_id + student_id
        slot_objects = []
        for item in payload.slots:
            name_val = item.interviewer_name
            email_val = item.interviewer_email
            if item.contact_id and item.contact_id in contacts_map:
                contact_rec = contacts_map[item.contact_id]
                name_val = contact_rec.name
                email_val = contact_rec.email

            slot_objects.append(
                PlacementInterviewSlot(
                    schedule_id=payload.schedule_id,
                    application_id=item.application_id,
                    slot_time=_parse_dt(item.slot_time),
                    batch_number=item.batch_number,
                    seq_number=item.seq_number,
                    interviewer_name=name_val,
                    interviewer_email=email_val,
                    interviewer_id=item.interviewer_id,   # F2
                    student_id=item.student_id,           # F2
                    contact_id=item.contact_id,
                    status="SCHEDULED",
                )
            )
        db.bulk_save_objects(slot_objects)
        db.commit()

        return returnSuccess(
            {
                "schedule_id": payload.schedule_id,
                "total_slots_saved": len(slot_objects),
            },
            message=(
                f"Schedule updated for '{round_.round_name if round_ else ''}' "
                f"with {len(slot_objects)} slot(s)."
            ),
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 7. DELETE /placement/interview/schedule/{schedule_id}
#    Soft delete — sets is_active = 0.
# ===========================================================================


@router.delete("/schedule/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a schedule (is_active = 0). Slots are retained for audit."""
    try:
        PlacementInterviewSchedule = _get_schedule_model()

        sched = (
            db.query(PlacementInterviewSchedule)
            .filter(PlacementInterviewSchedule.schedule_id == schedule_id)
            .first()
        )
        if not sched:
            return returnException(f"Schedule {schedule_id} not found.")

        sched.is_active = 0
        sched.updated_at = datetime.now()
        db.commit()

        return returnSuccess(
            {"schedule_id": schedule_id, "is_active": 0},
            message=f"Schedule {schedule_id} cancelled successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 7b. POST /placement/interview/schedule/dispatch/{schedule_id}
#     Marks a schedule as SCHEDULED (confirmed).
# ===========================================================================

@router.post("/schedule/dispatch/{schedule_id}")
def dispatch_schedule(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marks a schedule as SCHEDULED, indicating the round is officially scheduled.
    Status changes from DRAFT → SCHEDULED.
    """
    try:
        PlacementInterviewSchedule = _get_schedule_model()
        sched = db.query(PlacementInterviewSchedule).filter(PlacementInterviewSchedule.schedule_id == schedule_id).first()
        
        if not sched:
            return returnException(f"Schedule {schedule_id} not found.")
        
        if sched.status != "DRAFT":
            return returnException(f"Schedule is already {sched.status}. Can only schedule DRAFT schedules.")
            
        sched.status = "SCHEDULED"
        sched.updated_at = datetime.now()
        db.commit()
        
        return returnSuccess(
            {"schedule_id": schedule_id, "status": "SCHEDULED"}, 
            message="Schedule confirmed successfully. Round is now SCHEDULED."
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))

# ===========================================================================
# 7c. GET /placement/interview/schedule/slots?schedule_id=X
#     All slots for a schedule with full student info.
#     Used by InterviewSchedulePage slot-list view.
# ===========================================================================


@router.get("/schedule/slots")
def get_schedule_slots(
    schedule_id: int = Query(..., description="plm_interview_schedule.schedule_id"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all interview slots for a schedule with full student details.
    Used to render the slot list after a schedule is created.
    Includes: student_name, usno, branch, cgpa, slot_time, batch_number,
              interviewer_name, interviewer_email, status.
    """
    try:
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        sched = (
            db.query(PlacementInterviewSchedule, PlacementDrive, PlacementDriveRound, PlacementCompany)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementInterviewSchedule.drive_id)
            .join(PlacementDriveRound, PlacementDriveRound.round_id == PlacementInterviewSchedule.round_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .filter(PlacementInterviewSchedule.schedule_id == schedule_id)
            .first()
        )
        if not sched:
            return returnException(f"Schedule {schedule_id} not found.")

        schedule, drive, round_, company = sched

        slot_rows = (
            db.query(
                PlacementInterviewSlot,
                PLMApplication,
                PLMStudentProfile,
                IEMStudents,
                IEMSDepartment,
            )
            .join(PLMApplication, PLMApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(IEMSDepartment, IEMSDepartment.dept_id == IEMStudents.department_id)
            .filter(PlacementInterviewSlot.schedule_id == schedule_id)
            .order_by(
                PlacementInterviewSlot.batch_number.asc(),
                PlacementInterviewSlot.seq_number.asc(),
                PlacementInterviewSlot.slot_time.asc(),
            )
            .all()
        )

        slots = []
        for slot, app, profile, student, dept in slot_rows:
            name = (
                student.name
                or f"{student.first_name or ''} {student.last_name or ''}".strip()
            )
            slots.append(
                {
                    "slot_id": slot.slot_id,
                    "application_id": slot.application_id,
                    "student_name": name,
                    "usno": student.usno or "",
                    "email": student.email or "",
                    "branch": dept.dept_name if dept else "",
                    "cgpa": float(profile.current_cgpa) if profile.current_cgpa is not None else 0.0,
                    "slot_time": (
                        slot.slot_time.strftime("%Y-%m-%d %H:%M")
                        if slot.slot_time else None
                    ),
                    "batch_number": slot.batch_number,
                    "seq_number": slot.seq_number,
                    "interviewer_name": slot.interviewer_name,
                    "interviewer_email": slot.interviewer_email,
                    "interviewer_id": slot.interviewer_id,
                    "student_id": slot.student_id,
                    "status": slot.status or "SCHEDULED",
                }
            )

        return returnSuccess(
            {
                "slots": slots,
                "total": len(slots),
                "schedule_id": schedule_id,
                "drive_name": drive.drive_name,
                "company_name": company.company_name,
                "round_name": round_.round_name,
                "round_number": round_.round_number,
                "round_type": round_.round_type,
                "scheduled_date": str(schedule.scheduled_date) if schedule.scheduled_date else None,
                "end_date": str(schedule.end_date) if schedule.end_date else None,
                "venue_type": schedule.venue_type,
                "venue_details": schedule.venue_details,
                "meeting_link": schedule.meeting_link,
                "interviewer_names": schedule.interviewer_names,
            },
            message=f"{len(slots)} slot(s) loaded for schedule.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 8. GET /placement/interview/result/list?drive_id=X&round_id=Y
#    All results for a drive + round with student display data.
# ===========================================================================


@router.get("/result/list")
def get_result_list(
    schedule_id: int = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all interview slots for a schedule, outerjoined with plm_round_result.
    Used by TPO to view and record results for candidates who had slots in that schedule.
    """
    try:
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()
        PlacementRoundResult = _get_result_model()

        # Load the schedule first
        sched = (
            db.query(PlacementInterviewSchedule, PlacementDrive, PlacementDriveRound)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementInterviewSchedule.drive_id)
            .join(PlacementDriveRound, PlacementDriveRound.round_id == PlacementInterviewSchedule.round_id)
            .filter(PlacementInterviewSchedule.schedule_id == schedule_id)
            .first()
        )
        if not sched:
            return returnException(f"Schedule {schedule_id} not found.")

        schedule, drive, round_ = sched

        # Single JOIN query for all slots + student info + existing round result
        rows = (
            db.query(PlacementInterviewSlot, PLMApplication, PLMStudentProfile, IEMStudents, IEMSDepartment, PlacementRoundResult)
            .join(PLMApplication, PLMApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(IEMSDepartment, IEMSDepartment.dept_id == IEMStudents.department_id)
            .outerjoin(
                PlacementRoundResult,
                (PlacementRoundResult.application_id == PLMApplication.application_id) &
                (PlacementRoundResult.round_id == schedule.round_id)
            )
            .filter(PlacementInterviewSlot.schedule_id == schedule_id)
            .order_by(PLMStudentProfile.current_cgpa.desc())
            .all()
        )

        results = []
        for slot, app, profile, student, dept, res in rows:
            name = (
                student.name
                or f"{student.first_name or ''} {student.last_name or ''}".strip()
            )
            results.append(
                {
                    "result_id": res.result_id if res else None,
                    "application_id": app.application_id,
                    "round_id": schedule.round_id,
                    "round_name": round_.round_name,
                    "student_name": name,
                    "usno": student.usno or "",
                    "branch": dept.dept_name if dept else "",
                    "cgpa": float(profile.current_cgpa) if profile.current_cgpa is not None else None,
                    "result": res.result if res else None,
                    "feedback_notes": res.feedback_notes if res else None,
                    "recorded_at": str(res.recorded_at) if res and res.recorded_at else None,
                }
            )

        # F7: compute completion stats for the progress bar on RoundResultPage
        total_students = len(results)
        results_recorded = sum(1 for r in results if r["result"] is not None)
        pending_count = total_students - results_recorded
        all_results_complete = pending_count == 0 and total_students > 0

        return returnSuccess(
            {
                "results": results,
                "total": total_students,
                "round_name": round_.round_name,
                "drive_name": drive.drive_name,
                # F7: progress tracking fields
                "results_recorded": results_recorded,
                "pending_count": pending_count,
                "all_results_complete": all_results_complete,
            },
            message=f"{total_students} candidate(s) loaded for schedule.",
        )
    except Exception as e:
        return returnException(str(e))


# ===========================================================================
# 9. POST /placement/interview/result/save
#    Bulk upsert results using raw SQL INSERT ... ON DUPLICATE KEY UPDATE.
#    Leverages UNIQUE KEY uq_application_round (application_id, round_id)
#    on plm_round_result for conflict resolution.
# ===========================================================================


@router.post("/result/save")
def save_results(
    payload: ResultBulkSavePayload,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk save (create or update) round results.

    Uses INSERT ... ON DUPLICATE KEY UPDATE so re-saving is idempotent.
    Validates that all result values are PASS | FAIL | HOLD | ABSENT.

    Optimized: single raw SQL bulk INSERT instead of N individual ORM saves.
    Cascades status updates to plm_application and plm_interview_slot.
    """
    try:
        if not payload.results:
            return returnSuccess({"saved_count": 0}, message="No results to save.")

        user_id = current_user.get("user_id", 1)

        # Validate result values
        invalid = [
            r.result for r in payload.results if r.result not in VALID_RESULTS
        ]
        if invalid:
            return returnException(
                f"Invalid result value(s): {invalid}. "
                f"Allowed: {', '.join(VALID_RESULTS)}"
            )

        # F7: Block partial saves — get total student count for this round
        # Derive schedule_id from the first result's round_id
        first_round_id = payload.results[0].round_id
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        schedule_for_round = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.round_id == first_round_id,
                PlacementInterviewSchedule.is_active == 1,
            )
            .first()
        )
        if schedule_for_round:
            total_in_round = (
                db.query(func.count(PlacementInterviewSlot.slot_id))
                .filter(PlacementInterviewSlot.schedule_id == schedule_for_round.schedule_id)
                .scalar()
                or 0
            )
            submitted = len(payload.results)
            if submitted < total_in_round:
                pending = total_in_round - submitted
                return returnException(
                    f"Cannot save: {pending} student(s) still have no result assigned. "
                    f"All {total_in_round} students must have a result "
                    f"(PASS / FAIL / HOLD / ABSENT) before saving."
                )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build bulk INSERT ... ON DUPLICATE KEY UPDATE
        # This is more efficient than N individual ORM upserts.
        value_tuples = []
        params = {}
        for i, item in enumerate(payload.results):
            value_tuples.append(
                f"(:app_id_{i}, :round_id_{i}, :result_{i}, :notes_{i}, :by_{i}, :at_{i})"
            )
            params[f"app_id_{i}"] = item.application_id
            params[f"round_id_{i}"] = item.round_id
            params[f"result_{i}"] = item.result
            params[f"notes_{i}"] = item.feedback_notes
            params[f"by_{i}"] = user_id
            params[f"at_{i}"] = now

        sql = text(
            f"""
            INSERT INTO plm_round_result
              (application_id, round_id, result, feedback_notes, recorded_by, recorded_at)
            VALUES
              {", ".join(value_tuples)}
            ON DUPLICATE KEY UPDATE
              result         = VALUES(result),
              feedback_notes = VALUES(feedback_notes),
              recorded_by    = VALUES(recorded_by),
              recorded_at    = VALUES(recorded_at)
            """
        )

        db.execute(sql, params)

        # Build bulk updates for application and slot statuses
        # 1. Update applications
        app_params = {}
        app_case_parts = []
        for i, item in enumerate(payload.results):
            app_params[f"app_id_{i}"] = item.application_id
            app_params[f"res_{i}"] = item.result
            app_case_parts.append(f"WHEN application_id = :app_id_{i} THEN (CASE WHEN :res_{i} IN ('PASS', 'HOLD') THEN 'IN_PROCESS' ELSE 'REJECTED' END)")
            
        app_sql = text(
            f"""
            UPDATE plm_application
            SET status = CASE 
                {" ".join(app_case_parts)}
                ELSE status
            END
            WHERE application_id IN ({", ".join(f":app_id_{i}" for i in range(len(payload.results)))})
            """
        )
        db.execute(app_sql, app_params)

        # 2. Update slots
        slot_params = {}
        slot_case_parts = []
        slot_where_parts = []
        for i, item in enumerate(payload.results):
            slot_params[f"app_id_{i}"] = item.application_id
            slot_params[f"round_id_{i}"] = item.round_id
            slot_params[f"res_{i}"] = item.result
            slot_case_parts.append(f"WHEN s.application_id = :app_id_{i} AND sch.round_id = :round_id_{i} THEN (CASE WHEN :res_{i} = 'ABSENT' THEN 'NO_SHOW' ELSE 'COMPLETED' END)")
            slot_where_parts.append(f"(s.application_id = :app_id_{i} AND sch.round_id = :round_id_{i})")

        slot_sql = text(
            f"""
            UPDATE plm_interview_slot s
            JOIN plm_interview_schedule sch ON s.schedule_id = sch.schedule_id
            SET s.status = CASE 
                {" ".join(slot_case_parts)}
                ELSE s.status
            END
            WHERE {" OR ".join(slot_where_parts)}
            """
        )
        db.execute(slot_sql, slot_params)

        db.commit()

        return returnSuccess(
            {"saved_count": len(payload.results)},
            message=f"{len(payload.results)} result(s) saved successfully.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 9b. PATCH /placement/interview/result/override
#     Override a single result — TPO can change a saved FAIL/HOLD decision.
#     Cascades the updated result to plm_application status.
# ===========================================================================


@router.patch("/result/override")
def override_result(
    payload: ResultOverridePayload,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Override a single saved round result.
    Updates plm_round_result and cascades new status to plm_application.
    Useful when TPO needs to correct a decision (e.g., FAIL → PASS).
    """
    try:
        PlacementRoundResult = _get_result_model()
        user_id = current_user.get("user_id", 1)

        if payload.result not in VALID_RESULTS:
            return returnException(
                f"Invalid result '{payload.result}'. Allowed: {', '.join(VALID_RESULTS)}"
            )

        res = (
            db.query(PlacementRoundResult)
            .filter(PlacementRoundResult.result_id == payload.result_id)
            .first()
        )
        if not res:
            return returnException(f"Result record {payload.result_id} not found.")

        old_result = res.result
        res.result = payload.result
        res.feedback_notes = payload.feedback_notes
        res.recorded_by = user_id
        res.recorded_at = datetime.now()

        # Cascade to application status
        new_app_status = "IN_PROCESS" if payload.result in ("PASS", "HOLD") else "REJECTED"
        db.execute(
            text("UPDATE plm_application SET status = :s WHERE application_id = :a"),
            {"s": new_app_status, "a": res.application_id},
        )

        db.commit()

        return returnSuccess(
            {
                "result_id": res.result_id,
                "application_id": res.application_id,
                "old_result": old_result,
                "new_result": res.result,
            },
            message=f"Result updated from {old_result} to {res.result}.",
        )
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ===========================================================================
# 10. GET /placement/interview/holidays
#     Org holidays for calendar blocking in the scheduling wizard.
# ===========================================================================


@router.get("/holidays")
def get_holidays(
    current_user: dict = Depends(get_current_user),
    org_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    """Returns active org holidays. Frontend scheduleEngine uses these to skip blocked dates."""
    try:
        resolved_org = org_id or 1
        PlacementOrgHoliday = _get_holiday_model()

        holidays = (
            db.query(PlacementOrgHoliday)
            .filter(
                PlacementOrgHoliday.org_id == resolved_org,
                PlacementOrgHoliday.is_active == 1,
            )
            .order_by(PlacementOrgHoliday.holiday_date.asc())
            .all()
        )

        return returnSuccess(
            {
                "holidays": [
                    {
                        "holiday_id": h.holiday_id,
                        "holiday_date": str(h.holiday_date),
                        "holiday_name": h.holiday_name,
                        "holiday_type": h.holiday_type,
                    }
                    for h in holidays
                ]
            },
            message=f"{len(holidays)} holiday(s) found.",
        )
    except Exception as e:
        return returnException(str(e))




class NotifyRequest(BaseModel):
    schedule_id: int
    application_id: Optional[int] = None
    force: bool = False


@router.post("/schedule/notify")
def notify_schedule(
    payload: NotifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sends email notifications to all students (or a specific student) in the schedule.
    Checks if notifications have already been sent, returning a warning list if force=False.
    Logs each sent notification in plm_notification_log.
    """
    try:
        PlacementInterviewSchedule = _get_schedule_model()
        PlacementInterviewSlot = _get_slot_model()

        # 1. Fetch schedule, round, drive, company details
        sched = (
            db.query(PlacementInterviewSchedule, PlacementDrive, PlacementDriveRound, PlacementCompany)
            .join(PlacementDrive, PlacementDrive.drive_id == PlacementInterviewSchedule.drive_id)
            .join(PlacementDriveRound, PlacementDriveRound.round_id == PlacementInterviewSchedule.round_id)
            .join(PlacementCompany, PlacementCompany.company_id == PlacementDrive.company_id)
            .filter(
                PlacementInterviewSchedule.schedule_id == payload.schedule_id,
                PlacementInterviewSchedule.is_active == 1
            )
            .first()
        )
        if not sched:
            return returnException(f"Schedule {payload.schedule_id} not found.")

        schedule, drive, round_, company = sched

        # 2. Query slots with student details
        query = (
            db.query(
                PlacementInterviewSlot,
                PLMApplication,
                PLMStudentProfile,
                IEMStudents,
                IEMSDepartment
            )
            .join(PLMApplication, PLMApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .outerjoin(IEMSDepartment, IEMSDepartment.dept_id == IEMStudents.department_id)
            .filter(
                PlacementInterviewSlot.schedule_id == payload.schedule_id
            )
        )

        if payload.application_id is not None:
            query = query.filter(PlacementInterviewSlot.application_id == payload.application_id)

        slot_rows = query.all()
        if not slot_rows:
            return returnException("No interview slots found to notify.")

        # 3. Check for already notified slots if force is False
        if not payload.force:
            already_notified = []
            for slot, app, profile, student, dept in slot_rows:
                if slot.notification_sent_at is not None:
                    name = student.name or f"{student.first_name or ''} {student.last_name or ''}".strip()
                    already_notified.append({
                        "student_name": name,
                        "sent_at": slot.notification_sent_at.strftime("%d/%m/%Y %I:%M %p"),
                    })
            if already_notified:
                return returnSuccess({
                    "status": "warning",
                    "already_notified": already_notified
                })

        # 4. Fetch the email notification template from DB
        tmpl_row = db.execute(text(
            "SELECT template_id, subject_tmpl, body_tmpl FROM plm_notification_template WHERE event_type = 'INTERVIEW_SCHEDULED' LIMIT 1"
        )).first()

        if tmpl_row:
            template_id, subject_tmpl, body_tmpl = tmpl_row
        else:
            template_id = None
            subject_tmpl = "Interview Invitation: {{round_name}} for {{company_name}}"
            body_tmpl = (
                "Dear {{student_name}},\n\nYour interview slot for {{company_name}} ({{round_name}}) has been scheduled.\n\n"
                "Date & Time: {{slot_time}}\nInterviewer: {{interviewer_name}} ({{interviewer_email}})\n"
                "Venue/Link: {{location}}\n\nPlease be on time.\n\nBest regards,\nPlacement Cell"
            )

        # 5. Send notifications (simulate sending + update slot fields + insert log)
        location = schedule.venue_details if schedule.venue_type == "PHYSICAL" else schedule.meeting_link
        if not location:
            location = "TBA"

        for slot, app, profile, student, dept in slot_rows:
            name = student.name or f"{student.first_name or ''} {student.last_name or ''}".strip()
            slot_time_str = slot.slot_time.strftime("%d/%m/%Y %I:%M %p") if slot.slot_time else "TBA"

            # Interpolate subject and body
            subject = subject_tmpl.replace("{{round_name}}", round_.round_name or "").replace("{{company_name}}", company.company_name or "")
            body = body_tmpl.replace("{{student_name}}", name)\
                            .replace("{{company_name}}", company.company_name or "")\
                            .replace("{{round_name}}", round_.round_name or "")\
                            .replace("{{slot_time}}", slot_time_str)\
                            .replace("{{interviewer_name}}", slot.interviewer_name or "TBA")\
                            .replace("{{interviewer_email}}", slot.interviewer_email or "TBA")\
                            .replace("{{location}}", location)

            # F5: expiry = slot_time (interview start). Fallback 48h if slot_time missing.
            from datetime import timedelta
            if slot.slot_time:
                expires_at = slot.slot_time
            else:
                expires_at = datetime.now() + timedelta(hours=48)

            # F6: capture student's placement profile_status at notification time
            profile_status = None
            if profile:
                raw_status = getattr(profile, "placement_status", None)
                profile_status = raw_status if raw_status else "UNPLACED"

            # Update slot fields (F4 notification_sent_at already existed, F5 adds expires)
            slot.notification_sent_at = datetime.now()
            slot.notification_status = "SENT"
            slot.notification_expires_at = expires_at   # F5

            # Insert log (F5 expires_at, F6 profile_status added)
            log_query = text("""
                INSERT INTO plm_notification_log (
                    tenant_id, template_id, recipient_type, recipient_id,
                    channel, subject, body, sent_at, status, expires_at, profile_status
                ) VALUES (
                    1, :template_id, 'STUDENT', :recipient_id,
                    'EMAIL', :subject, :body, NOW(), 'SENT', :expires_at, :profile_status
                )
            """)
            db.execute(log_query, {
                "template_id": template_id,
                "recipient_id": student.student_id,
                "subject": subject,
                "body": body,
                "expires_at": expires_at,         # F5
                "profile_status": profile_status, # F6
            })

        db.commit()
        return returnSuccess({
            "status": "success",
            "message": "Notifications sent successfully!"
        })
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.get("/student-notifications")
def get_student_notifications(student_id: int, db: Session = Depends(get_db)):
    """
    Fetch notification logs for a specific student.
    Strictly verifies that the student has at least one scheduled slot in plm_interview_slot.
    Deletes expired notifications before returning the list.
    """
    try:
        from app.db.placement_models import PlacementInterviewSlot, PLMApplication, PLMStudentProfile
        from app.db.models import IEMStudents

        # 1. Verify student exists
        stud = db.query(IEMStudents).filter(IEMStudents.student_id == student_id).first()
        if not stud:
            return returnException(f"Student ID {student_id} not found.")

        # 2. Delete expired notifications from plm_notification_log
        now_dt = datetime.now()
        delete_query = text("""
            DELETE FROM plm_notification_log
            WHERE recipient_id = :student_id 
              AND recipient_type = 'STUDENT'
              AND expires_at IS NOT NULL
              AND expires_at < :now_dt
        """)
        db.execute(delete_query, {"student_id": student_id, "now_dt": now_dt})
        db.commit()

        # 3. Check if student has any active scheduled slot
        has_slot = (
            db.query(PlacementInterviewSlot.slot_id)
            .join(PLMApplication, PLMApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PLMApplication.profile_id)
            .filter(
                PLMStudentProfile.student_id == student_id,
                PlacementInterviewSlot.status == 'SCHEDULED'
            )
            .first()
        )

        if not has_slot:
            return returnSuccess({
                "student_id": student_id,
                "is_scheduled": False,
                "notifications": []
            })

        # 4. Retrieve notifications from plm_notification_log
        notifs_query = text("""
            SELECT log_id, subject, body, sent_at, status, expires_at
            FROM plm_notification_log 
            WHERE recipient_id = :student_id AND recipient_type = 'STUDENT'
            ORDER BY sent_at DESC
        """)
        rows = db.execute(notifs_query, {"student_id": student_id}).fetchall()

        notifications = []
        for r in rows:
            # F5: compute is_expired based on expires_at
            is_expired = False
            if r.expires_at:
                is_expired = r.expires_at < now_dt

            notifications.append({
                "log_id": r.log_id,
                "subject": r.subject,
                "body": r.body,
                "sent_at": r.sent_at.strftime("%d/%m/%Y %I:%M %p") if r.sent_at else "—",
                "status": r.status,
                "expires_at": r.expires_at.strftime("%Y-%m-%dT%H:%M:%S") if r.expires_at else None,
                "is_expired": is_expired,
            })

        return returnSuccess({
            "student_id": student_id,
            "is_scheduled": True,
            "notifications": notifications
        })
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.patch("/student-notifications/read/{log_id}")
def mark_notification_as_read(log_id: int, db: Session = Depends(get_db)):
    """
    Mark a student notification log as read.
    """
    try:
        db.execute(
            text("UPDATE plm_notification_log SET status = 'READ' WHERE log_id = :log_id"),
            {"log_id": log_id}
        )
        db.commit()
        return returnSuccess({"message": "Notification marked as read."})
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.get("/check_interviewer_conflict")
def check_interviewer_conflict_api(
    contact_id: int = Query(..., description="The contact/interviewer ID to check"),
    slot_time: str = Query(..., description="The slot time to check (YYYY-MM-DD HH:MM)"),
    schedule_id: Optional[int] = Query(None, description="Current schedule ID to exclude"),
    db: Session = Depends(get_db),
):
    try:
        from app.db.placement_models import PlacementInterviewSchedule, PlacementInterviewSlot, PlacementDrive
        
        parsed_dt = _parse_dt(slot_time)
        if not parsed_dt:
            return returnException("Invalid slot_time format.")
            
        # Get the company of the contact
        from app.db.placement_models import PLMCompanyContact
        contact = db.query(PLMCompanyContact).filter(PLMCompanyContact.contact_id == contact_id).first()
        if not contact:
            return returnException("Contact not found.")
            
        company_id = contact.company_id
        
        # Get all drives for this company
        drives = db.query(PlacementDrive).filter(PlacementDrive.company_id == company_id).all()
        drive_map = {d.drive_id: d for d in drives}
        drive_ids = list(drive_map.keys())
        if not drive_ids:
            return returnSuccess({"conflict": False, "drive_name": None})
            
        # Query active slot for this contact at this slot_time
        query = db.query(
            PlacementInterviewSchedule.drive_id
        ).join(
            PlacementInterviewSlot,
            PlacementInterviewSlot.schedule_id == PlacementInterviewSchedule.schedule_id
        ).filter(
            PlacementInterviewSchedule.drive_id.in_(drive_ids),
            PlacementInterviewSchedule.is_active == 1,
            PlacementInterviewSlot.status != "CANCELLED",
            PlacementInterviewSlot.slot_time == parsed_dt
        )
        
        # Check by contact_id/interviewer_id OR name
        query = query.filter(
            (PlacementInterviewSlot.contact_id == contact_id) | 
            (PlacementInterviewSlot.interviewer_id == contact_id) |
            (PlacementInterviewSlot.interviewer_name.ilike(contact.name))
        )
        
        if schedule_id is not None:
            query = query.filter(PlacementInterviewSchedule.schedule_id != schedule_id)
            
        conflicting_drive_row = query.first()
        
        if conflicting_drive_row:
            conflicting_drive_id = conflicting_drive_row[0]
            conflicting_drive = drive_map.get(conflicting_drive_id)
            drive_name = conflicting_drive.drive_name if conflicting_drive else f"Drive ID {conflicting_drive_id}"
            return returnSuccess({
                "conflict": True, 
                "drive_name": drive_name, 
                "interviewer_name": contact.name
            })
            
        return returnSuccess({"conflict": False, "drive_name": None})
    except Exception as e:
        return returnException(str(e))

