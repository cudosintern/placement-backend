"""
placement_models.py
===================
SQLAlchemy ORM models for the Placement Module.
Kept separate from the main models.py to avoid bloat.
"""
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER, MEDIUMINT, TINYINT, YEAR
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.mysql import TINYINT, INTEGER as MySQLInteger
from sqlalchemy.orm import relationship

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
    status = Column(SmallInteger, nullable=False, default=1)  # 1=Active, 0=Inactive
    org_id = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    create_date = Column(DateTime, nullable=True, default=datetime.now)
    modify_date = Column(DateTime, nullable=True, onupdate=datetime.now)


class IEMSPlacementNotificationTemplate(Base):
    __tablename__ = 'plm_notification_template'

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_title = Column(Text, nullable=False)
    notification_message = Column(Text, nullable=False)
    notification_type = Column(String(100), nullable=False)
    
    event_type_id = Column(Integer, nullable=True)

    org_id = Column(Integer, nullable=True)
    status = Column(TINYINT, default=1)

    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)

    create_date = Column(DateTime, nullable=True)
    modify_date = Column(DateTime, nullable=True)
    
class IEMSPlacementNotificationEventType(Base):
    __tablename__ = 'plm_notification_event_type'

    id = Column(Integer, primary_key=True, autoincrement=True)

    event_code = Column(String(100), nullable=False)

    event_name = Column(String(255), nullable=False)

    status = Column(TINYINT, default=1)

    org_id = Column(Integer, nullable=True)

    created_by = Column(Integer, nullable=True)

    modified_by = Column(Integer, nullable=True)

    create_date = Column(DateTime, nullable=True)

    modify_date = Column(DateTime, nullable=True)


class IEMSPlacementNotificationLog(Base):
    __tablename__ = 'plm_notification_log'

    id = Column(Integer, primary_key=True, autoincrement=True)

    template_id = Column(Integer, nullable=True)

    recipient = Column(String(255), nullable=False)

    notification_type = Column(String(100), nullable=False)

    subject = Column(Text, nullable=True)

    message = Column(Text, nullable=True)

    status = Column(TINYINT, default=1)

    org_id = Column(Integer, nullable=True)

    created_by = Column(Integer, nullable=True)

    modified_by = Column(Integer, nullable=True)

    create_date = Column(DateTime, nullable=True)

    modify_date = Column(DateTime, nullable=True)


class PlacementCompanySelfRegistration(Base):
    """
    Module 2: Company Approval Master
    Stores recruiter self-registration requests submitted via the placement portal.
    TPO reviews each request and approves or rejects.

    status values:
        0 = PENDING  (freshly submitted, awaiting TPO review)
        1 = APPROVED (TPO approved → plm_company record auto-created, company_id FK filled)
        2 = REJECTED (TPO rejected with a reason in remarks)
    """

    __tablename__ = "plm_company_self_registration"

    reg_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer,
        ForeignKey("plm_company.company_id", ondelete="SET NULL"),
        nullable=True,
    )  # NULL at submit time; filled after TPO approves

    # Company details submitted by the recruiter
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
    contact_email = Column(String(150), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)

    # Workflow fields
    status = Column(SmallInteger, nullable=False, default=0)  # 0/1/2
    reviewed_by = Column(Integer, nullable=True)  # TPO's user_id
    review_date = Column(DateTime, nullable=True)
    remarks = Column(String(500), nullable=True)  # rejection reason / note

    # Audit fields
    org_id = Column(Integer, nullable=False, default=1)
    submitted_by = Column(Integer, nullable=True)
    create_date = Column(DateTime, nullable=True, default=datetime.now)
    modify_date = Column(DateTime, nullable=True, onupdate=datetime.now)


# =============================================================================
# Module 3: Placement Drive
# =============================================================================


class PlacementDrive(Base):
    """
    Main drive record.

    status values:
        0 = Draft
        1 = Scheduled
        2 = Active
        3 = Closed
        4 = Cancelled
    """

    __tablename__ = "plm_drive"

    drive_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, nullable=False)  # FK → plm_company
    drive_name = Column(String(200), nullable=False)
    job_role = Column(String(150), nullable=False)
    vacancy_count = Column(SmallInteger, nullable=True)  # Number of openings
    drive_type = Column(
        String(50), nullable=False, default="On-Campus"
    )  # On-Campus | Off-Campus | Pool Campus
    work_type = Column(
        String(50), nullable=False, default="Onsite"
    )  # Onsite | Remote | Hybrid
    location = Column(String(200), nullable=True)
    ctc_min = Column(Numeric(10, 2), nullable=True)  # LPA
    ctc_max = Column(Numeric(10, 2), nullable=True)  # LPA
    job_description = Column(Text, nullable=True)
    min_cgpa = Column(Numeric(4, 2), nullable=False, default=0.00)
    max_backlogs = Column(SmallInteger, nullable=False, default=0)
    application_start = Column(Date, nullable=True)
    application_deadline = Column(Date, nullable=True)
    drive_date = Column(Date, nullable=True)
    tier = Column(SmallInteger, nullable=False, default=1)  # 1 | 2 | 3
    status = Column(SmallInteger, nullable=False, default=0)
    eligible_student_count = Column(Integer, nullable=False, default=0)
    applied_count = Column(Integer, nullable=False, default=0)
    shortlisted_count = Column(Integer, nullable=False, default=0)
    org_id = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    create_date = Column(DateTime, nullable=True, default=datetime.now)
    modify_date = Column(DateTime, nullable=True, onupdate=datetime.now)


class PlacementDriveEligibleBranch(Base):
    """
    Maps a drive to eligible (department + batch_year) combinations.
    batch_year = iems_academic_batch.start_year  (e.g. 2025)
    """

    __tablename__ = "plm_drive_eligible_branch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drive_id = Column(Integer, nullable=False)  # FK → plm_drive
    dept_id = Column(Integer, nullable=False)  # FK → iems_department
    batch_year = Column(SmallInteger, nullable=False)  # e.g. 2025


class PlacementDriveRound(Base):
    """
    Interview/selection rounds associated with a drive.

    round_type choices:
        APTITUDE | TECHNICAL | HR | GD | ASSIGNMENT | OTHER
    """

    __tablename__ = "plm_drive_round"

    round_id = Column(Integer, primary_key=True, autoincrement=True)
    drive_id = Column(Integer, nullable=False)  # FK → plm_drive
    round_number = Column(SmallInteger, nullable=False)
    round_name = Column(String(150), nullable=False)
    round_type = Column(String(50), nullable=False)
    is_eliminatory = Column(SmallInteger, nullable=False, default=1)  # 1=Yes, 0=No
    round_date = Column(Date, nullable=True)
    duration_minutes = Column(SmallInteger, nullable=True)
    description = Column(Text, nullable=True)


# =============================================================================
# Module 4: Placement Application (plm_application)
# =============================================================================


class PLMApplication(Base):
    """
    Records a student's application to a placement drive.

    status values (matches SQL ENUM):
        APPLIED       – freshly submitted
        SHORTLISTED   – TPO shortlisted
        WAITLISTED    – on waitlist
        IN_PROCESS    – actively in interview rounds
        OFFERED       – received offer
        REJECTED      – rejected by company / TPO
        WITHDRAWN     – student withdrew

    Links:
        drive_id   → plm_drive.drive_id
        profile_id → plm_student_profile.profile_id
        resume_id  → plm_student_resume.resume_id (optional)
    """

    __tablename__ = "plm_application"

    application_id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id      = Column(Integer, nullable=False, default=1)
    drive_id       = Column(Integer, nullable=False)   # FK → plm_drive
    profile_id     = Column(Integer, nullable=False)   # FK → plm_student_profile
    resume_id      = Column(Integer, nullable=True)    # FK → plm_student_resume (optional)
    applied_at     = Column(DateTime, nullable=True, default=datetime.now)
    status         = Column(
        String(20), nullable=False, default="APPLIED"
    )  # APPLIED | SHORTLISTED | WAITLISTED | IN_PROCESS | OFFERED | REJECTED | WITHDRAWN
    is_eligible    = Column(SmallInteger, nullable=False, default=1)  # 1=Yes, 0=No


# =============================================================================
# Module 5: Student Profile, Skills, Certifications & Resume
# (Moved here from models.py so all placement tables stay together)
# =============================================================================


class PLMStudentProfile(Base):
    __tablename__ = 'plm_student_profile'

    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(MySQLInteger(unsigned=True), ForeignKey('iems_students.student_id', ondelete='CASCADE'), nullable=False, unique=True)
    linkedin_url = Column(String(255), nullable=True)
    github_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)
    resume_path = Column(String(500), nullable=True)
    current_cgpa = Column(DECIMAL(4, 2), nullable=True)
    backlogs = Column(Integer, default=0, nullable=True)
    is_placement_eligible = Column(TINYINT, default=1)
    career_objective = Column(Text, nullable=True)
    preferred_locations = Column(String(255), nullable=True)
    org_id = Column(Integer, nullable=False)
    status = Column(TINYINT, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    created_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)

    # Relationships
    student = relationship("IEMStudents", foreign_keys=[student_id])
    skills = relationship("PLMStudentSkill", back_populates="profile", cascade="all, delete-orphan")
    certifications = relationship("PLMStudentCertification", back_populates="profile", cascade="all, delete-orphan")


class PLMStudentSkill(Base):
    __tablename__ = 'plm_student_skill'

    skill_id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey('plm_student_profile.profile_id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, nullable=False)
    skill_name = Column(String(150), nullable=False)
    proficiency_level = Column(String(50), nullable=True)   # Beginner / Intermediate / Expert
    org_id = Column(Integer, nullable=False)
    status = Column(TINYINT, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    created_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)

    # Relationships
    profile = relationship("PLMStudentProfile", back_populates="skills")


class PLMStudentCertification(Base):
    __tablename__ = 'plm_student_certification'

    certification_id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey('plm_student_profile.profile_id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, nullable=False)
    certification_name = Column(String(255), nullable=False)
    issuing_organization = Column(String(255), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    credential_id = Column(String(150), nullable=True)
    credential_url = Column(String(500), nullable=True)
    org_id = Column(Integer, nullable=False)
    status = Column(TINYINT, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    created_date = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)

    # Relationships
    profile = relationship("PLMStudentProfile", back_populates="certifications")


class PLMStudentResume(Base):
    __tablename__ = 'plm_student_resume'

    resume_id     = Column(Integer, primary_key=True, autoincrement=True)
    profile_id    = Column(Integer, ForeignKey('plm_student_profile.profile_id', ondelete='CASCADE'), nullable=False)
    student_id    = Column(Integer, nullable=False)
    file_name     = Column(String(255), nullable=False)          # original uploaded filename
    stored_name   = Column(String(500), nullable=False)          # UUID-based stored filename
    file_path     = Column(String(1000), nullable=False)         # relative path inside uploads/
    file_size_kb  = Column(Integer, nullable=True)               # file size in KB
    is_active     = Column(TINYINT, default=1)                   # 1 = this is the current active resume
    org_id        = Column(Integer, nullable=False)
    status        = Column(TINYINT, default=1)                   # 1=active, 0=soft-deleted
    created_by    = Column(Integer, nullable=True)
    modified_by   = Column(Integer, nullable=True)
    created_date  = Column(DateTime, nullable=True)
    modified_date = Column(DateTime, nullable=True)

    # Relationships
    profile = relationship("PLMStudentProfile", foreign_keys=[profile_id])


class PlacementInterviewSchedule(Base):
    __tablename__ = "plm_interview_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drive_id = Column(Integer, ForeignKey("plm_drive.drive_id", ondelete="CASCADE"), nullable=False)
    round_id = Column(Integer, ForeignKey("plm_drive_round.round_id", ondelete="CASCADE"), nullable=False)
    venue_type = Column(String(50), nullable=False)  # Online / Offline
    venue_details = Column(Text, nullable=True)
    meeting_link = Column(String(500), nullable=True)
    interview_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(TINYINT, default=1)  # 1=Active, 0=Deleted (Soft Delete)
    org_id = Column(Integer, nullable=False, default=1)
    created_by = Column(Integer, nullable=True)
    modified_by = Column(Integer, nullable=True)
    create_date = Column(DateTime, nullable=True, default=datetime.now)
    modify_date = Column(DateTime, nullable=True, onupdate=datetime.now)

    # Relationships
    drive = relationship("PlacementDrive", foreign_keys=[drive_id])
    round = relationship("PlacementDriveRound", foreign_keys=[round_id])
