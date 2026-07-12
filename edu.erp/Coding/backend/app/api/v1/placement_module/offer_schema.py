from pydantic import BaseModel, validator
from typing import Optional
from datetime import date

class OfferCreateSchema(BaseModel):
    company_id: int
    drive_id: int
    student_id: int
    designation: str
    package_ctc: float
    location: str
    offer_date: date
    joining_date: date
    status: str
    remarks: Optional[str] = None
    offer_letter_path: Optional[str] = None

    @validator("joining_date")
    def validate_joining_date(cls, v):
        if v <= date.today():
            raise ValueError("Joining Date must be a future date")
        return v

class OfferUpdateSchema(BaseModel):
    company_id: int
    drive_id: int
    student_id: int
    designation: str
    package_ctc: float
    location: str
    offer_date: date
    joining_date: date
    status: str
    remarks: Optional[str] = None
    offer_letter_path: Optional[str] = None
