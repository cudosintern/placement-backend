from pydantic import BaseModel, EmailStr
from typing import Optional


class CompanyCreate(BaseModel):
    """Schema for creating or updating a company."""
    company_id: Optional[int] = None          # None = new, int = update
    company_name: str
    company_type: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    pincode: Optional[str] = None
    contact_person: Optional[str] = None
    contact_designation: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = 1


class CompanyStatusUpdate(BaseModel):
    """Schema for activate / deactivate only."""
    company_id: int
    status: int  # 1 = Active, 0 = Inactive
