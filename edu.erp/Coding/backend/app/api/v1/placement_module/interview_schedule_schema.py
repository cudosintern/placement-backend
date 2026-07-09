from pydantic import BaseModel, validator
from datetime import date, time
from typing import Optional

class InterviewScheduleCreate(BaseModel):
    drive_id: int
    round_id: int
    venue_type: str  # "Online" or "Offline"
    venue_details: Optional[str] = None
    meeting_link: Optional[str] = None
    interview_date: date
    start_time: time
    end_time: time
    status: Optional[int] = 1

    @validator("end_time")
    def validate_times(cls, end_time, values):
        if "start_time" in values and values["start_time"] >= end_time:
            raise ValueError("Start Time must be less than End Time")
        return end_time

    @validator("meeting_link")
    def validate_meeting_link(cls, meeting_link, values):
        if "venue_type" in values and values["venue_type"] == "Online":
            if not meeting_link or not meeting_link.strip():
                raise ValueError("Meeting Link is required for Online interviews")
        return meeting_link

class InterviewScheduleUpdate(BaseModel):
    drive_id: Optional[int] = None
    round_id: Optional[int] = None
    venue_type: Optional[str] = None
    venue_details: Optional[str] = None
    meeting_link: Optional[str] = None
    interview_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[int] = None
