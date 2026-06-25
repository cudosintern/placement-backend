"""
drive_schema.py
===============
Pydantic request / response schemas for the Placement Drive module.

Schemas:
    EligibleBranchIn   — one dept + batch_year combo (request body)
    RoundIn            — one interview round (request body)
    DriveCreate        — full create / update payload
    DriveStatusUpdate  — status-change-only payload
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, validator

# ---------------------------------------------------------------------------
# Nested schemas (used inside DriveCreate)
# ---------------------------------------------------------------------------


class EligibleBranchIn(BaseModel):
    """One eligible department + batch-year combination."""

    dept_id: int = Field(..., description="iems_department.dept_id")
    batch_year: int = Field(..., description="Batch admission year, e.g. 2025")


class RoundIn(BaseModel):
    """One interview / selection round."""

    round_number: int = Field(..., ge=1, description="Round order number")
    round_name: str = Field(..., min_length=1, max_length=150)
    round_type: str = Field(
        ..., description="APTITUDE | TECHNICAL | HR | GD | ASSIGNMENT | OTHER"
    )
    is_eliminatory: bool = Field(True, description="True = eliminatory round")
    round_date: Optional[date] = None
    duration_minutes: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Main drive schema (create & update)
# ---------------------------------------------------------------------------


class DriveCreate(BaseModel):
    """
    Payload for POST /placement/drive/save  (create)  — drive_id must be None.
    Payload for PUT  /placement/drive/save  (update)  — drive_id must be provided.
    """

    # ── identity ──────────────────────────────────────────────────────────────
    drive_id: Optional[int] = None  # None → create, int → update

    # ── required fields ───────────────────────────────────────────────────────
    company_id: int = Field(..., description="plm_company.company_id")
    drive_name: str = Field(..., min_length=3, max_length=200)
    job_role: str = Field(..., min_length=2, max_length=150)
    vacancy_count: Optional[int] = Field(None, ge=1, description="Number of openings")

    # ── drive classification ───────────────────────────────────────────────────
    drive_type: str = Field(
        "On-Campus", description="On-Campus | Off-Campus | Pool Campus"
    )
    work_type: str = Field("Onsite", description="Onsite | Remote | Hybrid")
    location: Optional[str] = Field(None, max_length=200)
    tier: int = Field(1, ge=1, le=3, description="Company tier: 1 | 2 | 3")

    # ── compensation ──────────────────────────────────────────────────────────
    ctc_min: Optional[float] = Field(None, ge=0, description="CTC min in LPA")
    ctc_max: Optional[float] = Field(None, ge=0, description="CTC max in LPA")

    # ── description ───────────────────────────────────────────────────────────
    job_description: Optional[str] = None

    # ── eligibility ───────────────────────────────────────────────────────────
    min_cgpa: float = Field(0.0, ge=0, le=10, description="Minimum CGPA required")
    max_backlogs: int = Field(0, ge=0, description="Max active backlogs allowed")

    # ── dates ─────────────────────────────────────────────────────────────────
    # NOTE: drive_date MUST be declared before application_deadline so the
    # Pydantic v1 cross-field validator below has access to it via `values`.
    application_start: Optional[date] = None
    drive_date: Optional[date] = None
    application_deadline: Optional[date] = None

    # ── status ────────────────────────────────────────────────────────────────
    status: int = Field(
        0, ge=0, le=4, description="0=Draft 1=Scheduled 2=Active 3=Closed 4=Cancelled"
    )

    # ── nested lists ──────────────────────────────────────────────────────────
    eligible_branches: List[EligibleBranchIn] = Field(
        ..., description="At least one dept + batch_year combo required"
    )
    rounds: List[RoundIn] = Field(
        default_factory=list, description="Interview rounds (can be empty)"
    )

    @validator("eligible_branches")
    def at_least_one_branch(cls, v):
        if not v or len(v) == 0:
            raise ValueError(
                "At least one eligible branch (dept + batch_year) is required."
            )
        return v

    # ── validators ────────────────────────────────────────────────────────────
    @validator("ctc_max")
    def ctc_max_gte_min(cls, v, values):
        ctc_min = values.get("ctc_min")
        if v is not None and ctc_min is not None and v < ctc_min:
            raise ValueError("ctc_max must be >= ctc_min")
        return v

    @validator("application_deadline")
    def deadline_before_drive(cls, v, values):
        drive_date = values.get("drive_date")
        if v and drive_date and v > drive_date:
            raise ValueError(
                f"application_deadline ({v}) must be on or before drive_date ({drive_date})."
            )
        return v

    @validator("drive_type")
    def validate_drive_type(cls, v):
        allowed = {"On-Campus", "Off-Campus", "Pool Campus"}
        if v not in allowed:
            raise ValueError(f"drive_type must be one of {allowed}")
        return v

    @validator("work_type")
    def validate_work_type(cls, v):
        allowed = {"Onsite", "Remote", "Hybrid"}
        if v not in allowed:
            raise ValueError(f"work_type must be one of {allowed}")
        return v


# ---------------------------------------------------------------------------
# Status-change-only schema
# ---------------------------------------------------------------------------


class DriveStatusUpdate(BaseModel):
    """Payload for PUT /placement/drive/status."""

    drive_id: int = Field(..., description="plm_drive.drive_id")
    status: int = Field(
        ..., ge=0, le=4, description="0=Draft 1=Scheduled 2=Active 3=Closed 4=Cancelled"
    )
