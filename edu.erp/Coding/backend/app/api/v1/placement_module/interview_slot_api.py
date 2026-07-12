from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel

from app.core.database import get_db
from app.db.placement_models import (
    PlacementInterviewSchedule,
    PlacementInterviewSlot,
    PlacementApplication,
    PlacementDriveRound,
    PlacementRoundResult,
)
from app.db.models import PLMStudentProfile, IEMStudents
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()

# --- Pydantic Schemas ---
class SlotAssignSchema(BaseModel):
    application_ids: List[int]
    slot_time: Optional[datetime] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None

class SlotUpdateSchema(BaseModel):
    slot_time: Optional[datetime] = None
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    status: Optional[str] = None

class RoundResultSubmitSchema(BaseModel):
    application_id: int
    round_id: int
    result: str  # PASS, FAIL, HOLD, ABSENT
    feedback_notes: Optional[str] = None

# --- API Routes ---

@router.get("/slots/{schedule_id}")
def get_slots(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # Verify schedule belongs to this org
        schedule = db.query(PlacementInterviewSchedule).filter(
            PlacementInterviewSchedule.id == schedule_id,
            PlacementInterviewSchedule.org_id == org_id
        ).first()

        if not schedule:
            return returnException("Interview Schedule not found.")

        slots = (
            db.query(
                PlacementInterviewSlot.slot_id,
                PlacementInterviewSlot.schedule_id,
                PlacementInterviewSlot.application_id,
                PlacementInterviewSlot.slot_time,
                PlacementInterviewSlot.interviewer_name,
                PlacementInterviewSlot.interviewer_email,
                PlacementInterviewSlot.status,
                IEMStudents.name.label("student_name"),
                IEMStudents.usno.label("usn"),
                PlacementRoundResult.result.label("round_result"),
                PlacementRoundResult.feedback_notes.label("feedback_notes")
            )
            .join(PlacementApplication, PlacementApplication.application_id == PlacementInterviewSlot.application_id)
            .join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementApplication.profile_id)
            .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)
            .join(PlacementInterviewSchedule, PlacementInterviewSchedule.id == PlacementInterviewSlot.schedule_id)
            .outerjoin(
                PlacementRoundResult,
                and_(
                    PlacementRoundResult.application_id == PlacementInterviewSlot.application_id,
                    PlacementRoundResult.round_id == PlacementInterviewSchedule.round_id
                )
            )
            .filter(PlacementInterviewSlot.schedule_id == schedule_id)
            .all()
        )

        slots_list = []
        for s in slots:
            slots_list.append({
                "slot_id": s.slot_id,
                "schedule_id": s.schedule_id,
                "application_id": s.application_id,
                "student_name": s.student_name,
                "usn": s.usn,
                "slot_time": str(s.slot_time) if s.slot_time else None,
                "interviewer_name": s.interviewer_name,
                "interviewer_email": s.interviewer_email,
                "status": s.status,
                "round_result": s.round_result,
                "feedback_notes": s.feedback_notes,
            })

        return returnSuccess(slots_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/slots/{schedule_id}/assign")
def assign_slot(
    schedule_id: int,
    data: SlotAssignSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # Verify schedule
        schedule = db.query(PlacementInterviewSchedule).filter(
            PlacementInterviewSchedule.id == schedule_id,
            PlacementInterviewSchedule.org_id == org_id
        ).first()

        if not schedule:
            return returnException("Interview Schedule not found.")

        assigned_slots = []
        for app_id in data.application_ids:
            # Check if already assigned to this schedule
            existing = db.query(PlacementInterviewSlot).filter(
                PlacementInterviewSlot.schedule_id == schedule_id,
                PlacementInterviewSlot.application_id == app_id
            ).first()

            if existing:
                continue

            slot = PlacementInterviewSlot(
                schedule_id=schedule_id,
                application_id=app_id,
                slot_time=data.slot_time,
                interviewer_name=data.interviewer_name,
                interviewer_email=data.interviewer_email,
                status="SCHEDULED"
            )
            db.add(slot)
            assigned_slots.append(slot)

        db.commit()
        for slot in assigned_slots:
            db.refresh(slot)

        return returnSuccess(f"Successfully assigned {len(assigned_slots)} student(s).")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.put("/slots/update/{slot_id}")
def update_slot(
    slot_id: int,
    data: SlotUpdateSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        slot = db.query(PlacementInterviewSlot).filter(
            PlacementInterviewSlot.slot_id == slot_id
        ).first()

        if not slot:
            return returnException("Interview Slot not found.")

        if data.slot_time is not None:
            slot.slot_time = data.slot_time
        if data.interviewer_name is not None:
            slot.interviewer_name = data.interviewer_name
        if data.interviewer_email is not None:
            slot.interviewer_email = data.interviewer_email
        if data.status is not None:
            slot.status = data.status

        db.commit()
        db.refresh(slot)

        return returnSuccess({
            "slot_id": slot.slot_id,
            "schedule_id": slot.schedule_id,
            "application_id": slot.application_id,
            "slot_time": str(slot.slot_time) if slot.slot_time else None,
            "interviewer_name": slot.interviewer_name,
            "interviewer_email": slot.interviewer_email,
            "status": slot.status,
        })
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.delete("/slots/delete/{slot_id}")
def delete_slot(
    slot_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        slot = db.query(PlacementInterviewSlot).filter(
            PlacementInterviewSlot.slot_id == slot_id
        ).first()

        if not slot:
            return returnException("Interview Slot not found.")

        db.delete(slot)
        db.commit()

        return returnSuccess("Interview Slot assignment deleted successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.get("/slots/eligible-students/{schedule_id}")
def get_eligible_students(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        # Find schedule
        schedule = db.query(PlacementInterviewSchedule).filter(
            PlacementInterviewSchedule.id == schedule_id,
            PlacementInterviewSchedule.org_id == org_id
        ).first()

        if not schedule:
            return returnException("Interview Schedule not found.")

        drive_id = schedule.drive_id
        round_id = schedule.round_id

        # Find current round details
        current_round = db.query(PlacementDriveRound).filter(
            PlacementDriveRound.round_id == round_id
        ).first()

        if not current_round:
            return returnException("Round details not found.")

        # Find previous rounds of this drive (with smaller round_number)
        prev_round = db.query(PlacementDriveRound).filter(
            PlacementDriveRound.drive_id == drive_id,
            PlacementDriveRound.round_number < current_round.round_number
        ).order_by(PlacementDriveRound.round_number.desc()).first()

        # Base query for students who applied to this drive
        app_query = db.query(
            PlacementApplication.application_id,
            IEMStudents.name.label("student_name"),
            IEMStudents.usno.label("usn"),
            PLMStudentProfile.current_cgpa.label("cgpa")
        ).join(PLMStudentProfile, PLMStudentProfile.profile_id == PlacementApplication.profile_id)\
         .join(IEMStudents, IEMStudents.student_id == PLMStudentProfile.student_id)\
         .filter(
             PlacementApplication.drive_id == drive_id,
             PlacementApplication.status != "REJECTED",
             PLMStudentProfile.org_id == org_id
         )

        # If there's a previous round, filter students who passed that round
        if prev_round:
            app_query = app_query.join(
                PlacementRoundResult,
                and_(
                    PlacementRoundResult.application_id == PlacementApplication.application_id,
                    PlacementRoundResult.round_id == prev_round.round_id,
                    PlacementRoundResult.result == "PASS"
                )
            )

        # Exclude students who are already scheduled in this interview schedule
        already_assigned_slots = db.query(PlacementInterviewSlot.application_id).filter(
            PlacementInterviewSlot.schedule_id == schedule_id
        ).all()
        assigned_app_ids = [s[0] for s in already_assigned_slots]

        if assigned_app_ids:
            app_query = app_query.filter(PlacementApplication.application_id.notin_(assigned_app_ids))

        results = app_query.order_by(IEMStudents.name).all()

        eligible_list = []
        for r in results:
            eligible_list.append({
                "application_id": r.application_id,
                "student_name": r.student_name,
                "usn": r.usn,
                "cgpa": float(r.cgpa) if r.cgpa is not None else None,
            })

        return returnSuccess(eligible_list)
    except Exception as e:
        return returnException(str(e))


@router.post("/slots/result/submit")
def submit_round_result(
    data: RoundResultSubmitSchema,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # Verify application exists
        app = db.query(PlacementApplication).filter(
            PlacementApplication.application_id == data.application_id
        ).first()
        if not app:
            return returnException("Application not found.")

        # Check for existing round result
        existing_result = db.query(PlacementRoundResult).filter(
            PlacementRoundResult.application_id == data.application_id,
            PlacementRoundResult.round_id == data.round_id
        ).first()

        if existing_result:
            existing_result.result = data.result
            existing_result.feedback_notes = data.feedback_notes
            existing_result.recorded_by = user_id
            existing_result.recorded_at = datetime.now()
        else:
            new_result = PlacementRoundResult(
                application_id=data.application_id,
                round_id=data.round_id,
                result=data.result,
                feedback_notes=data.feedback_notes,
                recorded_by=user_id,
                recorded_at=datetime.now()
            )
            db.add(new_result)

        # Update application status
        if data.result in ["FAIL", "ABSENT"]:
            app.status = "REJECTED"
        elif data.result == "PASS":
            app.status = "SHORTLISTED"

        db.commit()
        return returnSuccess("Round result recorded successfully.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))

