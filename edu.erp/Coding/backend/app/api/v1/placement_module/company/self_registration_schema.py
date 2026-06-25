"""
self_registration_schema.py
============================
Pydantic schemas for Module 2: Company Approval Master
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SelfRegCreate(BaseModel):
    """Company HR fills and submits this form (no auth needed at submit time)."""
    company_name:    str
    company_type:    Optional[str] = None
    industry:        Optional[str] = None
    website:         Optional[str] = None
    email:           Optional[str] = None
    phone:           Optional[str] = None
    address:         Optional[str] = None
    city:            Optional[str] = None
    state:           Optional[str] = None
    country:         Optional[str] = "India"
    pincode:         Optional[str] = None
    contact_person:  Optional[str] = None
    contact_email:   Optional[str] = None
    contact_phone:   Optional[str] = None
    description:     Optional[str] = None


class SelfRegApprove(BaseModel):
    """TPO approves a registration request."""
    reg_id:  int
    remarks: Optional[str] = None   # optional approval note


class SelfRegReject(BaseModel):
    """TPO rejects a registration request — reason is REQUIRED."""
    reg_id:  int
    remarks: str   # mandatory: TPO must give a reason for rejection
