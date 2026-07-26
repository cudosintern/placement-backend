"""
student_resume_api.py
=====================
PLM-BE-008 — Resume Upload API

Endpoints:
  POST   /upload_resume       → Upload a PDF resume (multipart)
  GET    /get_resumes         → List all resumes for a student
  PUT    /set_active_resume   → Mark a resume as active (deactivates others)
  DELETE /delete_resume       → Soft-delete a resume
  GET    /download_resume     → Stream a resume file for download/preview
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.placement_models import PLMStudentResume, PLMStudentProfile, PLMApplication, PlacementDrive
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()

# ─── Upload directory ────────────────────────────────────────────────────────
UPLOAD_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "..", "uploads", "resumes"
)
UPLOAD_BASE = os.path.normpath(UPLOAD_BASE)
os.makedirs(UPLOAD_BASE, exist_ok=True)

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_MB = 5


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper
# ═══════════════════════════════════════════════════════════════════════════════

def _resume_to_dict(r: PLMStudentResume) -> dict:
    return {
        "resume_id":    r.resume_id,
        "profile_id":   r.profile_id,
        "student_id":   r.student_id,
        "file_name":    r.file_name,
        "stored_name":  r.stored_name,
        "file_path":    r.file_path,
        "file_size_kb": r.file_size_kb,
        "is_active":    r.is_active,
        "status":       r.status,
        "created_date": r.created_date.isoformat() if r.created_date else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  1. Upload Resume
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/upload_resume")
async def upload_resume(
    profile_id: int = Query(..., description="Student Profile ID"),
    student_id: int = Query(..., description="Student ID"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # ── Validate profile exists ──────────────────────────────────────────
        profile = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.profile_id == profile_id,
            PLMStudentProfile.org_id == org_id,
            PLMStudentProfile.status == 1,
        ).first()
        if not profile:
            return returnException("Student profile not found.")

        # ── Validate file type ───────────────────────────────────────────────
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            return returnException("Only PDF files are allowed.")

        # ── Read & validate file size ────────────────────────────────────────
        contents = await file.read()
        size_kb = len(contents) // 1024
        if size_kb > MAX_FILE_SIZE_MB * 1024:
            return returnException(f"File size exceeds {MAX_FILE_SIZE_MB} MB limit.")

        original_name = file.filename or "resume.pdf"

        # ── Check for duplicate filename (replace existing matching resume) ──
        dup_resume = db.query(PLMStudentResume).filter(
            PLMStudentResume.student_id == student_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.status == 1,
            PLMStudentResume.file_name.ilike(original_name),
        ).first()

        if dup_resume:
            # Overwrite duplicate filename entry by marking old one inactive/deleted
            dup_resume.status = 0
            dup_resume.is_active = 0
            dup_resume.modified_by = user_id
            dup_resume.modified_date = datetime.now()
            db.flush()

        # ── Quota check: max 5 active resumes per student ───────────────────
        active_count = db.query(PLMStudentResume).filter(
            PLMStudentResume.student_id == student_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.status == 1,
        ).count()

        if active_count >= 5:
            return returnException("Maximum limit of 5 resumes reached. Please delete an existing resume before uploading a new one.")

        # ── Save file with UUID name ─────────────────────────────────────────
        unique_name   = f"{uuid.uuid4().hex}_{original_name}"
        dest_path     = os.path.join(UPLOAD_BASE, unique_name)

        with open(dest_path, "wb") as f_out:
            f_out.write(contents)

        relative_path = f"uploads/resumes/{unique_name}"

        # ── Deactivate all previous resumes for this student ─────────────────
        db.query(PLMStudentResume).filter(
            PLMStudentResume.student_id == student_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.status == 1,
        ).update({"is_active": 0, "modified_by": user_id, "modified_date": datetime.now()})

        # ── Insert new resume record ─────────────────────────────────────────
        resume = PLMStudentResume(
            profile_id   = profile_id,
            student_id   = student_id,
            file_name    = original_name,
            stored_name  = unique_name,
            file_path    = relative_path,
            file_size_kb = size_kb,
            is_active    = 1,
            org_id       = org_id,
            status       = 1,
            created_by   = user_id,
            created_date = datetime.now(),
        )
        db.add(resume)

        # ── Update resume_path on profile ────────────────────────────────────
        profile.resume_path = relative_path
        profile.modified_by = user_id
        profile.modified_date = datetime.now()

        db.commit()
        db.refresh(resume)

        return returnSuccess(_resume_to_dict(resume), "Resume uploaded successfully.")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  2. Get All Resumes for a Student
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/get_resumes")
def get_resumes(
    student_id: int = Query(..., description="Student ID"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        resumes = db.query(PLMStudentResume).filter(
            PLMStudentResume.student_id == student_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.status == 1,
        ).order_by(PLMStudentResume.created_date.desc()).all()

        return returnSuccess([_resume_to_dict(r) for r in resumes])
    except Exception as e:
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  3. Set Active Resume
# ═══════════════════════════════════════════════════════════════════════════════

@router.put("/set_active_resume")
def set_active_resume(
    resume_id: int = Query(..., description="Resume ID to activate"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        target = db.query(PLMStudentResume).filter(
            PLMStudentResume.resume_id == resume_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.status == 1,
        ).first()
        if not target:
            return returnException("Resume not found.")

        # Deactivate all other resumes for this student
        db.query(PLMStudentResume).filter(
            PLMStudentResume.student_id == target.student_id,
            PLMStudentResume.org_id == org_id,
            PLMStudentResume.resume_id != resume_id,
        ).update({"is_active": 0, "modified_by": user_id, "modified_date": datetime.now()})

        target.is_active = 1
        target.modified_by = user_id
        target.modified_date = datetime.now()

        # Sync resume_path on profile
        profile = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.profile_id == target.profile_id
        ).first()
        if profile:
            profile.resume_path = target.file_path
            profile.modified_by = user_id
            profile.modified_date = datetime.now()

        db.commit()
        return returnSuccess(_resume_to_dict(target), "Resume set as active.")
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  4. Delete Resume (Soft Delete)
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/delete_resume")
def delete_resume(
    resume_id: int = Query(..., description="Resume ID to delete"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        resume = db.query(PLMStudentResume).filter(
            PLMStudentResume.resume_id == resume_id,
            PLMStudentResume.org_id == org_id,
        ).first()
        if not resume:
            return returnException("Resume not found.")

        # Check if linked to any active placement application
        ACTIVE_APPLICATION_STATUSES = {"APPLIED", "SHORTLISTED", "WAITLISTED", "IN_PROCESS", "OFFERED"}
        linked_app = (
            db.query(PLMApplication, PlacementDrive)
            .join(PlacementDrive, PlacementDrive.drive_id == PLMApplication.drive_id)
            .filter(
                PLMApplication.resume_id == resume_id,
                PLMApplication.status.in_(ACTIVE_APPLICATION_STATUSES),
            )
            .first()
        )
        if linked_app:
            app_obj, drive_obj = linked_app
            drive_name = drive_obj.drive_name if drive_obj else "an active drive"
            return returnException(
                f"Cannot delete resume: It is attached to your active application for '{drive_name}' (Status: {app_obj.status})."
            )

        resume.status = 0
        resume.is_active = 0
        resume.modified_by = user_id
        resume.modified_date = datetime.now()
        db.commit()

        return returnSuccess({"message": "Resume deleted successfully."})
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  5. Download / Preview Resume
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/download_resume")
def download_resume(
    resume_id: int = Query(..., description="Resume ID to download"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        resume = db.query(PLMStudentResume).filter(
            PLMStudentResume.resume_id == resume_id,
            PLMStudentResume.org_id == org_id,
        ).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found.")

        full_path = os.path.join(UPLOAD_BASE, resume.stored_name)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Resume file missing from storage.")

        return FileResponse(
            path=full_path,
            media_type="application/pdf",
            filename=resume.file_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        return returnException(str(e))
