from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import StudentCourse, IEMSGPACGPA, IEMSCGPA
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _course_to_dict(c: StudentCourse) -> dict:
    return {
        "std_crs_id": c.std_crs_id,
        "regno": c.regno,
        "usno": c.usno,
        "crs_code": c.crs_code,
        "result_year": c.result_year.isoformat() if c.result_year else None,
        "program_id": c.program_id,
        "batch_id": c.batch_id,
        "batch_cycle_id": c.batch_cycle_id,
        "org_id": c.org_id,
        "semester": c.semester,
        "section": c.section,
        "attendance_approved": c.attendance_approved,
        "attendance_eligibility": c.attendance_eligibility,
        "cia_approved": c.cia_approved,
        "cia_eligibility": c.cia_eligibility,
        "is_evaluated": c.is_evaluated,
        "total_cia": c.total_cia,
        "see1": c.see1,
        "see": c.see,
        "see_actual": c.see_actual,
        "cia_see": c.cia_see,
        "credits_earned": c.credits_earned,
        "is_see_consolidate": c.is_see_consolidate,
        "is_grade_evaluated": c.is_grade_evaluated,
        "grade": c.grade,
        "grade_point": c.grade_point,
        "grade_actual": c.grade_actual,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "updated_by": c.updated_by,
    }


def _sgpa_cgpa_to_dict(s: IEMSGPACGPA) -> dict:
    return {
        "id": s.id,
        "regno": s.regno,
        "program_id": s.program_id,
        "sem": s.sem,
        "sgpa": s.sgpa,
        "cgpa": s.cgpa,
        "result_year": s.result_year.isoformat() if s.result_year else None,
        "consider": s.consider,
        "org_id": s.org_id,
    }


def _cgpa_to_dict(c: IEMSCGPA) -> dict:
    return {
        "id": c.id,
        "regno": c.regno,
        "program_id": c.program_id,
        "cgpa": c.cgpa,
        "result_year": c.result_year.isoformat() if c.result_year else None,
        "org_id": c.org_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT ACADEMIC APIs
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 1. Get Student Courses ───────────────────────────────────────────────────

@router.get("/get_student_courses")
def get_student_courses(
    regno: str = Query(..., description="Student registration number"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        courses = db.query(StudentCourse).filter(
            StudentCourse.regno == regno,
            StudentCourse.org_id == org_id,
        ).order_by(StudentCourse.semester, StudentCourse.crs_code).all()

        return returnSuccess([_course_to_dict(c) for c in courses])
    except Exception as e:
        return returnException(str(e))


# ─── 2. Get Student SGPA/CGPA ────────────────────────────────────────────────

@router.get("/get_student_sgpa_cgpa")
def get_student_sgpa_cgpa(
    regno: str = Query(..., description="Student registration number"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        records = db.query(IEMSGPACGPA).filter(
            IEMSGPACGPA.regno == regno,
            IEMSGPACGPA.org_id == org_id,
        ).order_by(IEMSGPACGPA.sem).all()

        return returnSuccess([_sgpa_cgpa_to_dict(r) for r in records])
    except Exception as e:
        return returnException(str(e))


# ─── 3. Get Student CGPA ─────────────────────────────────────────────────────

@router.get("/get_student_cgpa")
def get_student_cgpa(
    regno: str = Query(..., description="Student registration number"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        record = db.query(IEMSCGPA).filter(
            IEMSCGPA.regno == regno,
            IEMSCGPA.org_id == org_id,
        ).first()

        if not record:
            return returnSuccess(None)

        return returnSuccess(_cgpa_to_dict(record))
    except Exception as e:
        return returnException(str(e))
