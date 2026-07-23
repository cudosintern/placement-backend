"""
backfill_application_resume_ids.py
====================================
One-time script to backfill plm_application.resume_id for legacy rows
where resume_id is NULL.

Strategy:
  For each application where resume_id is NULL, find the resume that
  was uploaded (created_date <= applied_at) for that profile, ordered
  by created_date DESC (closest to application time). This gives us
  the resume that was most likely active when the student applied.

  If no resume was uploaded before applied_at (e.g. resume uploaded later),
  fall back to the earliest uploaded resume for that profile.

Run once after deploying the fix:
  cd c:\Placement Module\placement-backend\edu.erp\Coding\backend
  python backfill_application_resume_ids.py
"""

import sys, os
sys.path.insert(0, r'c:\Placement Module\placement-backend\edu.erp\Coding\backend')
os.chdir(r'c:\Placement Module\placement-backend\edu.erp\Coding\backend')

from dotenv import load_dotenv
load_dotenv('.env')

import app.db.models        # noqa: F401 — resolves SQLAlchemy relationships
import app.db.placement_models  # noqa: F401

from app.core.database import SessionLocal
from app.db.placement_models import PLMApplication, PLMStudentResume
from sqlalchemy import and_

db = SessionLocal()

try:
    # 1. Load all apps with null resume_id that have an applied_at timestamp
    null_apps = (
        db.query(PLMApplication)
        .filter(PLMApplication.resume_id == None)
        .all()
    )
    print(f"Found {len(null_apps)} applications with NULL resume_id")

    updated = 0
    skipped = 0

    for app in null_apps:
        best_resume = None

        if app.applied_at:
            # Find the resume uploaded on or before the application date (most recent first)
            best_resume = (
                db.query(PLMStudentResume)
                .filter(
                    PLMStudentResume.profile_id == app.profile_id,
                    PLMStudentResume.status == 1,
                    PLMStudentResume.created_date <= app.applied_at,
                )
                .order_by(PLMStudentResume.created_date.desc())
                .first()
            )

        if not best_resume:
            # Fallback: earliest uploaded resume for this profile (student had it before applying)
            best_resume = (
                db.query(PLMStudentResume)
                .filter(
                    PLMStudentResume.profile_id == app.profile_id,
                    PLMStudentResume.status == 1,
                )
                .order_by(PLMStudentResume.created_date.asc())
                .first()
            )

        if best_resume:
            app.resume_id = best_resume.resume_id
            updated += 1
            print(f"  app={app.application_id} drive={app.drive_id} profile={app.profile_id} "
                  f"applied_at={app.applied_at} -> resume_id={best_resume.resume_id} ({best_resume.file_name})")
        else:
            skipped += 1
            print(f"  SKIP app={app.application_id} drive={app.drive_id} profile={app.profile_id} "
                  f"(no resume found for this profile)")

    db.commit()
    print(f"\nDone. Updated: {updated}, Skipped (no resume): {skipped}")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    db.close()
