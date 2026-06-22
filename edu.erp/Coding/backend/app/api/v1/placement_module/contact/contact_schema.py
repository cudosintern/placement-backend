# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr
from typing import Optional


class ContactCreate(BaseModel):
    company_id: int
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation_id: Optional[int] = None
    is_primary: Optional[int] = 0
    status: Optional[int] = 1


class ContactUpdate(BaseModel):
    contact_id: int
    company_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation_id: Optional[int] = None
    is_primary: Optional[int] = None
    status: Optional[int] = None
