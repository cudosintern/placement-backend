from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.placement_models import (
    PlacementInterviewSchedule,
    PlacementDrive,
    PlacementDriveRound,
)
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

from app.api.v1.placement_module.interview_schedule_schema import (
    InterviewScheduleCreate,
    InterviewScheduleUpdate,
)

router = APIRouter()


def _schedule_to_dict(s: PlacementInterviewSchedule) -> dict:
    return {
        "id": s.id,
        "drive_id": s.drive_id,
        "drive_name": s.drive.drive_name if s.drive else None,
        "round_id": s.round_id,
        "round_name": s.round.round_name if s.round else None,
        "venue_type": s.venue_type,
        "venue_details": s.venue_details,
        "meeting_link": s.meeting_link,
        "interview_date": str(s.interview_date) if s.interview_date else None,
        "start_time": str(s.start_time) if s.start_time else None,
        "end_time": str(s.end_time) if s.end_time else None,
        "status": s.status,
    }


@router.post("/add_schedule")
def add_schedule(
    data: InterviewScheduleCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # 1. Validation: Round must belong to drive
        round_record = db.query(PlacementDriveRound).filter(
            PlacementDriveRound.round_id == data.round_id,
            PlacementDriveRound.drive_id == data.drive_id
        ).first()
        if not round_record:
            return returnException("Selected Round does not belong to the selected Placement Drive.")

        # 2. Validation: Prevent duplicate schedules
        duplicate = db.query(PlacementInterviewSchedule).filter(
            PlacementInterviewSchedule.drive_id == data.drive_id,
            PlacementInterviewSchedule.round_id == data.round_id,
            PlacementInterviewSchedule.interview_date == data.interview_date,
            PlacementInterviewSchedule.start_time == data.start_time,
            PlacementInterviewSchedule.status == 1,
            PlacementInterviewSchedule.org_id == org_id
        ).first()
        if duplicate:
            return returnException("A scheduled interview already exists for this Drive, Round, Date and Start Time.")

        # 3. Create schedule
        schedule = PlacementInterviewSchedule(
            drive_id=data.drive_id,
            round_id=data.round_id,
            venue_type=data.venue_type,
            venue_details=data.venue_details,
            meeting_link=data.meeting_link if data.venue_type == "Online" else None,
            interview_date=data.interview_date,
            start_time=data.start_time,
            end_time=data.end_time,
            status=1,
            org_id=org_id,
            created_by=user_id,
            create_date=datetime.now(),
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        return returnSuccess(_schedule_to_dict(schedule))

    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.get("/get_schedules")
def get_schedules(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        schedules = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.org_id == org_id,
                PlacementInterviewSchedule.status == 1,
            )
            .order_by(PlacementInterviewSchedule.interview_date.desc(), PlacementInterviewSchedule.start_time.asc())
            .all()
        )

        return returnSuccess([_schedule_to_dict(s) for s in schedules])
    except Exception as e:
        return returnException(str(e))


@router.get("/get_schedule/{schedule_id}")
def get_schedule(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        schedule = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.id == schedule_id,
                PlacementInterviewSchedule.org_id == org_id
            )
            .first()
        )
        if not schedule:
            return returnException("Interview Schedule not found.")

        return returnSuccess(_schedule_to_dict(schedule))
    except Exception as e:
        return returnException(str(e))


@router.put("/update_schedule/{schedule_id}")
def update_schedule(
    schedule_id: int,
    data: InterviewScheduleUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        schedule = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.id == schedule_id,
                PlacementInterviewSchedule.org_id == org_id
            )
            .first()
        )

        if not schedule:
            return returnException("Interview Schedule not found.")

        # Validate round belongs to drive if either is updated
        target_drive_id = data.drive_id if data.drive_id is not None else schedule.drive_id
        target_round_id = data.round_id if data.round_id is not None else schedule.round_id

        if data.drive_id is not None or data.round_id is not None:
            round_record = db.query(PlacementDriveRound).filter(
                PlacementDriveRound.round_id == target_round_id,
                PlacementDriveRound.drive_id == target_drive_id
            ).first()
            if not round_record:
                return returnException("Selected Round does not belong to the selected Placement Drive.")

        # Prevent duplicate check if times or dates are updated
        target_date = data.interview_date if data.interview_date is not None else schedule.interview_date
        target_start = data.start_time if data.start_time is not None else schedule.start_time

        if data.interview_date is not None or data.start_time is not None or data.drive_id is not None or data.round_id is not None:
            duplicate = db.query(PlacementInterviewSchedule).filter(
                PlacementInterviewSchedule.drive_id == target_drive_id,
                PlacementInterviewSchedule.round_id == target_round_id,
                PlacementInterviewSchedule.interview_date == target_date,
                PlacementInterviewSchedule.start_time == target_start,
                PlacementInterviewSchedule.status == 1,
                PlacementInterviewSchedule.id != schedule_id,
                PlacementInterviewSchedule.org_id == org_id
            ).first()
            if duplicate:
                return returnException("A scheduled interview already exists for this Drive, Round, Date and Start Time.")

        # Apply updates
        if data.drive_id is not None:
            schedule.drive_id = data.drive_id
        if data.round_id is not None:
            schedule.round_id = data.round_id
        if data.venue_type is not None:
            schedule.venue_type = data.venue_type
            if data.venue_type == "Offline":
                schedule.meeting_link = None
        if data.venue_details is not None:
            schedule.venue_details = data.venue_details
        if data.meeting_link is not None:
            schedule.meeting_link = data.meeting_link if schedule.venue_type == "Online" else None
        if data.interview_date is not None:
            schedule.interview_date = data.interview_date
        if data.start_time is not None:
            schedule.start_time = data.start_time
        if data.end_time is not None:
            schedule.end_time = data.end_time
        if data.status is not None:
            schedule.status = data.status

        schedule.modified_by = user_id
        schedule.modify_date = datetime.now()

        db.commit()
        db.refresh(schedule)

        return returnSuccess(_schedule_to_dict(schedule))

    except Exception as e:
        db.rollback()
        return returnException(str(e))


@router.delete("/delete_schedule/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        schedule = (
            db.query(PlacementInterviewSchedule)
            .filter(
                PlacementInterviewSchedule.id == schedule_id,
                PlacementInterviewSchedule.org_id == org_id
            )
            .first()
        )

        if not schedule:
            return returnException("Interview Schedule not found.")

        # Soft delete
        schedule.status = 0
        schedule.modified_by = user_id
        schedule.modify_date = datetime.now()

        db.commit()

        return returnSuccess("Interview Schedule deleted successfully.")

    except Exception as e:
        db.rollback()
        return returnException(str(e))
