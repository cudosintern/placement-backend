from pydantic import BaseModel
from typing import Optional
from datetime import date


# ─── Student Profile Schemas ───────────────────────────────────────────────────

class StudentProfileCreate(BaseModel):
    student_id: int
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_path: Optional[str] = None
    current_cgpa: Optional[float] = None
    backlogs: Optional[int] = 0
    is_placement_eligible: Optional[int] = 1
    career_objective: Optional[str] = None
    preferred_locations: Optional[str] = None
    status: Optional[int] = 1


class StudentProfileUpdate(BaseModel):
    profile_id: int
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_path: Optional[str] = None
    current_cgpa: Optional[float] = None
    backlogs: Optional[int] = None
    is_placement_eligible: Optional[int] = None
    career_objective: Optional[str] = None
    preferred_locations: Optional[str] = None
    status: Optional[int] = None


# ─── Student Skill Schemas ─────────────────────────────────────────────────────

class StudentSkillCreate(BaseModel):
    profile_id: int
    student_id: int
    skill_name: str
    proficiency_level: Optional[str] = None   # BEGINNER / INTERMEDIATE / ADVANCED
    status: Optional[int] = 1


class StudentSkillUpdate(BaseModel):
    skill_id: int
    skill_name: Optional[str] = None
    proficiency_level: Optional[str] = None
    status: Optional[int] = None


# ─── Student Certification Schemas ────────────────────────────────────────────

class StudentCertificationCreate(BaseModel):
    profile_id: int
    student_id: int
    certification_name: str
    issuing_organization: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    status: Optional[int] = 1


class StudentCertificationUpdate(BaseModel):
    certification_id: int
    certification_name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    status: Optional[int] = None
