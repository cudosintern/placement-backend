"""
placement_models.py
===================
SQLAlchemy ORM models for the Placement Module.
Kept separate from the main models.py to avoid bloat.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, SmallInteger, String, Text
from app.core.database import Base


class PlacementCompany(Base):
    """Represents a company that participates in placement drives."""

    __tablename__ = "plm_company"

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(200), nullable=False)
    company_type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="India")
    pincode = Column(String(10), nullable=True)
    contact_person = Column(String(150), nullable=True)
    contact_designation = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    logo_path = Column(String(500), nullable=True)
    status = Column(SmallInteger, nullable=False, default=1)   # 1=Active, 0=Inactive
    org_id = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    create_date = Column(DateTime, nullable=True, default=datetime.now)
    modify_date = Column(DateTime, nullable=True, onupdate=datetime.now)
