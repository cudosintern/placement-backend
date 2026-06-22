from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import outerjoin

from app.core.database import get_db
from app.db.models import PLMStudentProfile, PLMStudentSkill, PLMStudentCertification, IEMStudents, IEMSCGPA, IEMSDepartment
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from app.api.v1.placement_module.student.student_profile_schema import (
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentSkillCreate,
    StudentSkillUpdate,
    StudentCertificationCreate,
    StudentCertificationUpdate,
)

router = APIRouter()



# ─── Helpers ──────────────────────────────────────────────────────────────────

def _profile_to_dict(p: PLMStudentProfile, db=None) -> dict:
    student = p.student
    dept_name = None
    if db and student and student.department_id:
        dept = db.query(IEMSDepartment).filter(
            IEMSDepartment.dept_id == student.department_id
        ).first()
        dept_name = dept.dept_name if dept else None
    return {
        "profile_id": p.profile_id,
        "student_id": p.student_id,
        "student_name": student.name if student else None,
        "usno": student.usno if student else None,
        "regno": student.regno if student else None,
        "email": student.email if student else None,
        "department_id": student.department_id if student else None,
        "department_name": dept_name,
        "linkedin_url": p.linkedin_url,
        "github_url": p.github_url,
        "portfolio_url": p.portfolio_url,
        "resume_path": p.resume_path,
        "current_cgpa": float(p.current_cgpa) if p.current_cgpa is not None else None,
        "backlogs": p.backlogs,
        "is_placement_eligible": p.is_placement_eligible,
        "career_objective": p.career_objective,
        "preferred_locations": p.preferred_locations,
        "status": p.status,
        "created_date": p.created_date,
        "modified_date": p.modified_date,
    }


def _skill_to_dict(s: PLMStudentSkill) -> dict:
    return {
        "skill_id": s.skill_id,
        "profile_id": s.profile_id,
        "student_id": s.student_id,
        "skill_name": s.skill_name,
        "proficiency_level": s.proficiency_level,
        "status": s.status,
        "created_date": s.created_date,
        "modified_date": s.modified_date,
    }


def _certification_to_dict(c: PLMStudentCertification) -> dict:
    return {
        "certification_id": c.certification_id,
        "profile_id": c.profile_id,
        "student_id": c.student_id,
        "certification_name": c.certification_name,
        "issuing_organization": c.issuing_organization,
        "issue_date": c.issue_date,
        "expiry_date": c.expiry_date,
        "credential_id": c.credential_id,
        "credential_url": c.credential_url,
        "status": c.status,
        "created_date": c.created_date,
        "modified_date": c.modified_date,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT PROFILE APIs
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 1. Get All Students (For Dropdown) ─────────────────────────────────────────

@router.get("/get_students")
def get_students(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        students = db.query(
            IEMStudents.student_id,
            IEMStudents.name,
            IEMStudents.usno,
            IEMStudents.department_id
        ).filter(
            IEMStudents.org_id == org_id,
            IEMStudents.status == 1,
        ).order_by(IEMStudents.name).all()

        return returnSuccess([
            {
                "student_id": s.student_id,
                "name": s.name,
                "usno": s.usno,
                "department_id": s.department_id,
            }
            for s in students
        ])
    except Exception as e:
        return returnException(str(e))


# ─── 1b. Get ALL Students with Registration Status ───────────────────────────

@router.get("/get_all_students_list")
def get_all_students_list(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    """
    Returns ALL students from iems_students (not just placement-registered ones).
    Each row includes:
      - is_registered: bool  — whether they have a plm_student_profile record
      - profile_id, current_cgpa, backlogs, is_placement_eligible from profile (if registered)
      - cgpa_actual from iems_cgpa (academic result)
    """
    try:
        # Fetch all students
        students = db.query(IEMStudents).filter(
            IEMStudents.org_id == org_id,
            IEMStudents.status == 1,
        ).order_by(IEMStudents.name).all()

        # Build a lookup: student_id -> profile
        profiles = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.org_id == org_id,
            PLMStudentProfile.status == 1,
        ).all()
        profile_map = {p.student_id: p for p in profiles}

        # Build a lookup: regno -> cgpa (take the max result_year record)
        cgpa_rows = db.query(IEMSCGPA).filter(
            IEMSCGPA.org_id == org_id,
        ).order_by(IEMSCGPA.result_year.desc()).all()
        cgpa_map: dict = {}
        for c in cgpa_rows:
            if c.regno not in cgpa_map:
                cgpa_map[c.regno] = float(c.cgpa) if c.cgpa is not None else None

        # Build a lookup: dept_id -> dept_name
        depts = db.query(IEMSDepartment).all()
        dept_map = {d.dept_id: d.dept_name for d in depts}

        result = []
        for s in students:
            p = profile_map.get(s.student_id)
            cgpa_actual = cgpa_map.get(s.regno)
            result.append({
                "student_id":           s.student_id,
                "name":                 s.name,
                "usno":                 s.usno,
                "regno":                s.regno,
                "email":                s.email,
                "department_id":        s.department_id,
                "department_name":      dept_map.get(s.department_id) if s.department_id else None,
                "is_registered":        p is not None,
                # Placement profile fields (None if not registered)
                "profile_id":           p.profile_id if p else None,
                "current_cgpa":         float(p.current_cgpa) if p and p.current_cgpa is not None else None,
                "backlogs":             p.backlogs if p else None,
                "is_placement_eligible": p.is_placement_eligible if p else None,
                "status":               p.status if p else None,
                # CGPA from academic result system (read-only, pre-fills registration)
                "cgpa_actual":          cgpa_actual,
            })

        return returnSuccess(result)
    except Exception as e:
        return returnException(str(e))


# ─── 2. Get Student Profile ───────────────────────────────────────────────────

@router.get("/get_profile")
def get_profile(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.org_id == org_id,
            PLMStudentProfile.status == 1,
        )
        if student_id is not None:
            query = query.filter(PLMStudentProfile.student_id == student_id)

        profiles = query.all()
        return returnSuccess([_profile_to_dict(p, db=db) for p in profiles])
    except Exception as e:
        return returnException(str(e))


# ─── 2. Add Student Profile ───────────────────────────────────────────────────

@router.post("/add_profile")
def add_profile(
    data: StudentProfileCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        # Check student exists
        student = db.query(IEMStudents).filter(
            IEMStudents.student_id == data.student_id
        ).first()
        if not student:
            return returnException("Student not found.")

        # Check if active profile already exists for this student
        existing = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.student_id == data.student_id,
            PLMStudentProfile.org_id == org_id,
            PLMStudentProfile.status == 1,
        ).first()
        if existing:
            return returnException("Student profile already exists for this student.")

        # Check if a soft-deleted profile exists — reactivate it instead of inserting
        soft_deleted = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.student_id == data.student_id,
            PLMStudentProfile.org_id == org_id,
            PLMStudentProfile.status == 0,
        ).first()

        if soft_deleted:
            # Reactivate the old profile with updated fields
            soft_deleted.linkedin_url = data.linkedin_url
            soft_deleted.github_url = data.github_url
            soft_deleted.portfolio_url = data.portfolio_url
            soft_deleted.resume_path = data.resume_path
            soft_deleted.current_cgpa = data.current_cgpa
            soft_deleted.backlogs = data.backlogs if data.backlogs is not None else 0
            soft_deleted.is_placement_eligible = data.is_placement_eligible if data.is_placement_eligible is not None else 1
            soft_deleted.career_objective = data.career_objective
            soft_deleted.preferred_locations = data.preferred_locations
            soft_deleted.status = 1
            soft_deleted.modified_by = user_id
            soft_deleted.modified_date = datetime.now()
            db.commit()
            db.refresh(soft_deleted)
            return returnSuccess(_profile_to_dict(soft_deleted))

        profile = PLMStudentProfile(
            student_id=data.student_id,
            linkedin_url=data.linkedin_url,
            github_url=data.github_url,
            portfolio_url=data.portfolio_url,
            resume_path=data.resume_path,
            current_cgpa=data.current_cgpa,
            backlogs=data.backlogs if data.backlogs is not None else 0,
            is_placement_eligible=data.is_placement_eligible if data.is_placement_eligible is not None else 1,
            career_objective=data.career_objective,
            preferred_locations=data.preferred_locations,
            status=data.status if data.status is not None else 1,
            org_id=org_id,
            created_by=user_id,
            created_date=datetime.now(),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return returnSuccess(_profile_to_dict(profile))

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 3. Update Student Profile ────────────────────────────────────────────────

@router.put("/update_profile")
def update_profile(
    data: StudentProfileUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        profile = db.query(PLMStudentProfile).filter(
            PLMStudentProfile.profile_id == data.profile_id,
            PLMStudentProfile.org_id == org_id,
        ).first()
        if not profile:
            return returnException("Student profile not found.")

        if data.linkedin_url is not None:
            profile.linkedin_url = data.linkedin_url
        if data.github_url is not None:
            profile.github_url = data.github_url
        if data.portfolio_url is not None:
            profile.portfolio_url = data.portfolio_url
        if data.resume_path is not None:
            profile.resume_path = data.resume_path
        if data.current_cgpa is not None:
            profile.current_cgpa = data.current_cgpa
        if data.backlogs is not None:
            profile.backlogs = data.backlogs
        if data.is_placement_eligible is not None:
            profile.is_placement_eligible = data.is_placement_eligible
        if data.career_objective is not None:
            profile.career_objective = data.career_objective
        if data.preferred_locations is not None:
            profile.preferred_locations = data.preferred_locations
        if data.status is not None:
            profile.status = data.status

        profile.modified_by = user_id
        profile.modified_date = datetime.now()

        db.commit()
        db.refresh(profile)
        return returnSuccess(_profile_to_dict(profile))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT SKILL APIs
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 4. Get Skills ────────────────────────────────────────────────────────────

@router.get("/get_skills")
def get_skills(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    profile_id: Optional[int] = Query(None, description="Filter by profile ID"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(PLMStudentSkill).filter(
            PLMStudentSkill.org_id == org_id,
            PLMStudentSkill.status == 1,
        )
        if student_id is not None:
            query = query.filter(PLMStudentSkill.student_id == student_id)
        if profile_id is not None:
            query = query.filter(PLMStudentSkill.profile_id == profile_id)

        skills = query.order_by(PLMStudentSkill.skill_name).all()
        return returnSuccess([_skill_to_dict(s) for s in skills])
    except Exception as e:
        return returnException(str(e))


# ─── 5. Add Skill ─────────────────────────────────────────────────────────────

@router.post("/add_skill")
def add_skill(
    data: StudentSkillCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        skill = PLMStudentSkill(
            profile_id=data.profile_id,
            student_id=data.student_id,
            skill_name=data.skill_name.strip(),
            proficiency_level=data.proficiency_level,
            status=data.status if data.status is not None else 1,
            org_id=org_id,
            created_by=user_id,
            created_date=datetime.now(),
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return returnSuccess(_skill_to_dict(skill))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 6. Update Skill ──────────────────────────────────────────────────────────

@router.put("/update_skill")
def update_skill(
    data: StudentSkillUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        skill = db.query(PLMStudentSkill).filter(
            PLMStudentSkill.skill_id == data.skill_id,
            PLMStudentSkill.org_id == org_id,
        ).first()
        if not skill:
            return returnException("Skill not found.")

        if data.skill_name is not None:
            skill.skill_name = data.skill_name.strip()
        if data.proficiency_level is not None:
            skill.proficiency_level = data.proficiency_level
        if data.status is not None:
            skill.status = data.status

        skill.modified_by = user_id
        skill.modified_date = datetime.now()

        db.commit()
        db.refresh(skill)
        return returnSuccess(_skill_to_dict(skill))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 7. Delete Skill (Soft Delete) ────────────────────────────────────────────

@router.delete("/delete_skill")
def delete_skill(
    skill_id: int = Query(..., description="Skill ID to delete"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        skill = db.query(PLMStudentSkill).filter(
            PLMStudentSkill.skill_id == skill_id,
            PLMStudentSkill.org_id == org_id,
        ).first()
        if not skill:
            return returnException("Skill not found.")

        skill.status = 0
        skill.modified_by = user_id
        skill.modified_date = datetime.now()

        db.commit()
        return returnSuccess({"message": "Skill deleted successfully."})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT CERTIFICATION APIs
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 8. Get Certifications ────────────────────────────────────────────────────

@router.get("/get_certifications")
def get_certifications(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    profile_id: Optional[int] = Query(None, description="Filter by profile ID"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(PLMStudentCertification).filter(
            PLMStudentCertification.org_id == org_id,
            PLMStudentCertification.status == 1,
        )
        if student_id is not None:
            query = query.filter(PLMStudentCertification.student_id == student_id)
        if profile_id is not None:
            query = query.filter(PLMStudentCertification.profile_id == profile_id)

        certs = query.order_by(PLMStudentCertification.issue_date.desc()).all()
        return returnSuccess([_certification_to_dict(c) for c in certs])
    except Exception as e:
        return returnException(str(e))


# ─── 9. Add Certification ─────────────────────────────────────────────────────

@router.post("/add_certification")
def add_certification(
    data: StudentCertificationCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        cert = PLMStudentCertification(
            profile_id=data.profile_id,
            student_id=data.student_id,
            certification_name=data.certification_name.strip(),
            issuing_organization=data.issuing_organization,
            issue_date=data.issue_date,
            expiry_date=data.expiry_date,
            credential_id=data.credential_id,
            credential_url=data.credential_url,
            status=data.status if data.status is not None else 1,
            org_id=org_id,
            created_by=user_id,
            created_date=datetime.now(),
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        return returnSuccess(_certification_to_dict(cert))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 10. Update Certification ─────────────────────────────────────────────────

@router.put("/update_certification")
def update_certification(
    data: StudentCertificationUpdate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        cert = db.query(PLMStudentCertification).filter(
            PLMStudentCertification.certification_id == data.certification_id,
            PLMStudentCertification.org_id == org_id,
        ).first()
        if not cert:
            return returnException("Certification not found.")

        if data.certification_name is not None:
            cert.certification_name = data.certification_name.strip()
        if data.issuing_organization is not None:
            cert.issuing_organization = data.issuing_organization
        if data.issue_date is not None:
            cert.issue_date = data.issue_date
        if data.expiry_date is not None:
            cert.expiry_date = data.expiry_date
        if data.credential_id is not None:
            cert.credential_id = data.credential_id
        if data.credential_url is not None:
            cert.credential_url = data.credential_url
        if data.status is not None:
            cert.status = data.status

        cert.modified_by = user_id
        cert.modified_date = datetime.now()

        db.commit()
        db.refresh(cert)
        return returnSuccess(_certification_to_dict(cert))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))


# ─── 11. Delete Certification (Soft Delete) ───────────────────────────────────

@router.delete("/delete_certification")
def delete_certification(
    certification_id: int = Query(..., description="Certification ID to delete"),
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        cert = db.query(PLMStudentCertification).filter(
            PLMStudentCertification.certification_id == certification_id,
            PLMStudentCertification.org_id == org_id,
        ).first()
        if not cert:
            return returnException("Certification not found.")

        cert.status = 0
        cert.modified_by = user_id
        cert.modified_date = datetime.now()

        db.commit()
        return returnSuccess({"message": "Certification deleted successfully."})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return returnException(str(e))
