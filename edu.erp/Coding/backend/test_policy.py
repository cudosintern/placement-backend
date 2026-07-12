import os
import sys
from datetime import datetime

# Add the app directory to the system path to allow imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.db.placement_models import PlacementOfferCapPolicy
from app.db.models import PLMStudentProfile, IEMStudents, IEMSAcademicBatch
from app.api.v1.placement_module.offer_api import handle_offer_status_change

def run_test():
    db = SessionLocal()
    try:
        print("--- STARTING OFFER CAP POLICY TEST ---")
        
        # 1. Fetch any student profile to run the test
        profile = db.query(PLMStudentProfile).first()
        if not profile:
            print("Error: No PLMStudentProfile found in database to run the test.")
            return

        student = db.query(IEMStudents).filter(IEMStudents.student_id == profile.student_id).first()
        if not student:
            print(f"Error: IEMStudent not found for student_id {profile.student_id}.")
            return

        # Ensure student has an academic batch
        batch = None
        if student.academic_batch_id:
            batch = db.query(IEMSAcademicBatch).filter(IEMSAcademicBatch.academic_batch_id == student.academic_batch_id).first()
        
        if not batch:
            # Create a temporary batch year for testing
            batch_year = 2026
            print(f"No batch found. Using batch year: {batch_year}")
        else:
            batch_year = batch.start_year
            print(f"Found student batch: {batch.academic_batch_code} (Start Year: {batch_year})")

        org_id = profile.org_id
        
        # 2. Check if a policy already exists for this batch; if not, create a temporary one
        policy = db.query(PlacementOfferCapPolicy).filter(
            PlacementOfferCapPolicy.tenant_id == org_id,
            PlacementOfferCapPolicy.batch_year == batch_year
        ).first()

        original_policy_state = None
        if policy:
            original_policy_state = {
                "allow_multiple": policy.allow_multiple,
                "max_offers_per_student": policy.max_offers_per_student
            }
            print(f"Found existing policy: allow_multiple={policy.allow_multiple}, max_offers={policy.max_offers_per_student}")
            # Force policy to allow_multiple = False (0) for testing the bug fix
            policy.allow_multiple = 0
            policy.max_offers_per_student = 1
        else:
            print("Creating temporary policy: allow_multiple=0, max_offers=1")
            policy = PlacementOfferCapPolicy(
                tenant_id=org_id,
                batch_year=batch_year,
                allow_multiple=0,  # 0 means multiple offers not allowed
                max_offers_per_student=1,
                created_at=datetime.now()
            )
            db.add(policy)
            db.flush()

        # Save student's original locking state
        original_profile_state = {
            "active_offer_count": profile.active_offer_count,
            "placement_status": profile.placement_status,
            "is_locked": profile.is_locked
        }

        # ─── TEST CASE 1: Student has 0 offers and multiple offers are disabled ───
        print("\nTest Case 1: Student has 0 offers. Checking lock status...")
        profile.active_offer_count = 0
        
        # Run offer status check (simulate no change or transition that keeps it at 0)
        handle_offer_status_change(db, profile.profile_id, "NONE", "NONE", org_id)
        
        print(f"Result -> active_offer_count: {profile.active_offer_count}, is_locked: {profile.is_locked}")
        if profile.is_locked == 0:
            print("✅ PASS: Student with 0 offers remains UNLOCKED (Your fix worked!).")
        else:
            print("❌ FAIL: Student with 0 offers was prematurely LOCKED.")

        # ─── TEST CASE 2: Student receives their first offer ───
        print("\nTest Case 2: Student receives 1 offer. Checking lock status...")
        # Simulate status change to ACCEPTED
        handle_offer_status_change(db, profile.profile_id, "NONE", "ACCEPTED", org_id, recorded_by=1)
        
        print(f"Result -> active_offer_count: {profile.active_offer_count}, is_locked: {profile.is_locked}")
        if profile.is_locked == 1:
            print("✅ PASS: Student is locked after receiving their offer.")
        else:
            print("❌ FAIL: Student profile was not locked after receiving the offer.")

    except Exception as e:
        print(f"An error occurred during testing: {e}")
    finally:
        # ALWAYS rollback database changes to keep DB pristine
        print("\nRolling back database changes to keep your database pristine...")
        db.rollback()
        db.close()
        print("Done!")

if __name__ == "__main__":
    run_test()
